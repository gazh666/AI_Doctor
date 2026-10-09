"""Voice endpoints rebuilt from scratch for stability and frontend compatibility."""

import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_confidence import derive_confidence_band
from app.core.deps import CurrentUser
from app.core.security import decode_access_token
from app.db.models import AIDecisionAudit, ChatHistory, Diagnosis, Patient, User, VoiceInteraction
from app.db.session import AsyncSessionLocal, get_db
from app.schemas.voice import TranscriptionResponse, TTSRequest, VoiceDiagnosisResponse
from app.services.agents.graph import get_medical_agent_graph
from app.services.llm.gemini_client import gemini_client
from app.services.llm.prompts import MEDICAL_SYSTEM_PROMPT
from app.services.voice.audio_utils import audio_utils

logger = logging.getLogger(__name__)
router = APIRouter()

UNAUTHORIZED_RESPONSE = {
    401: {
        "description": "Not authenticated. Provide a valid Bearer access token.",
    }
}


medical_agent_graph = get_medical_agent_graph()

RED_FLAG_KEYWORDS = [
    "chest pain",
    "difficulty breathing",
    "shortness of breath",
    "severe bleeding",
    "unconscious",
    "stroke",
    "seizure",
]


def _detect_red_flags(text: str) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in RED_FLAG_KEYWORDS if keyword in lowered]


async def _ws_send_error(websocket: WebSocket, message: str, turn_id: Optional[str] = None) -> None:
    await websocket.send_json(
        {
            "type": "turn.error",
            "message": message,
            "turn_id": turn_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


async def _authenticate_ws_user(websocket: WebSocket, db: AsyncSession) -> Optional[User]:
    try:
        raw = await websocket.receive_json()
    except Exception:
        await _ws_send_error(websocket, "Authentication frame is required.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    if raw.get("type") != "auth":
        await _ws_send_error(websocket, "First frame must be 'auth'.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    token_header = str(raw.get("token") or "").strip()
    if not token_header.startswith("Bearer "):
        await _ws_send_error(websocket, "Auth token must use Bearer format.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    token = token_header.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    user_id = payload.get("sub") if payload else None
    if not user_id:
        await _ws_send_error(websocket, "Invalid or expired token.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        await _ws_send_error(websocket, "Invalid token subject.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    result = await db.execute(select(User).where(User.id == user_id_int))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        await _ws_send_error(websocket, "User not found or inactive.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    return user


async def _persist_live_turn(
    db: AsyncSession,
    *,
    user_id: int,
    session_id: str,
    language: str,
    audio_filename: str,
    duration_seconds: float,
    transcription: str,
    assistant_response: str,
    urgency: str,
    red_flags: list[str],
) -> None:
    db.add(
        VoiceInteraction(
            session_id=session_id,
            user_id=user_id,
            audio_filename=audio_filename,
            transcription=transcription,
            language=language,
            duration_seconds=duration_seconds,
            confidence=0.9,
        )
    )
    db.add(
        ChatHistory(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=transcription,
        )
    )
    db.add(
        ChatHistory(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=assistant_response,
        )
    )
    db.add(
        AIDecisionAudit(
            user_id=user_id,
            session_id=session_id,
            source_endpoint="/api/v1/voice/live",
            decision_type="voice_live_turn",
            input_summary=transcription[:2000],
            output_summary=assistant_response[:2000],
            confidence_band=derive_confidence_band(
                urgency_level=urgency,
                red_flags_count=len(red_flags),
                output_summary=assistant_response[:2000],
            ),
            urgency_level=urgency.lower(),
            red_flags_json=red_flags,
            model_name="gemini-voice-live",
            model_version="v1",
            prompt_version="voice-live-v1",
        )
    )
    await db.commit()


@router.websocket("/live")
async def live_voice_consultation(websocket: WebSocket):
    from app.services.voice.service import voice_service

    await websocket.accept()
    audio_chunks: list[bytes] = []
    history: list[dict[str, str]] = []
    active_turn_id: Optional[str] = None
    session_context: dict[str, Any] = {
        "session_id": str(uuid.uuid4()),
        "language": "en",
        "age": None,
        "gender": None,
        "medical_history": None,
    }

    try:
        async with AsyncSessionLocal() as db:
            user = await _authenticate_ws_user(websocket, db)
            if user is None:
                return

            await websocket.send_json(
                {
                    "type": "auth.ok",
                    "session_id": session_context["session_id"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            while True:
                packet = await websocket.receive()

                if packet.get("type") == "websocket.disconnect":
                    break

                if packet.get("bytes") is not None:
                    audio_chunks.append(packet["bytes"])
                    continue

                text_payload = packet.get("text")
                if not text_payload:
                    continue

                try:
                    payload = json.loads(text_payload)
                except json.JSONDecodeError:
                    await _ws_send_error(websocket, "Malformed JSON payload.", active_turn_id)
                    continue

                event_type = payload.get("type")

                if event_type == "ping":
                    await websocket.send_json(
                        {
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    continue

                if event_type == "session.configure":
                    if payload.get("session_id"):
                        session_context["session_id"] = str(payload["session_id"])
                    if payload.get("language"):
                        session_context["language"] = str(payload["language"])
                    session_context["age"] = payload.get("age")
                    session_context["gender"] = payload.get("gender")
                    session_context["medical_history"] = payload.get("medical_history")
                    continue

                if event_type == "turn.start":
                    active_turn_id = str(payload.get("turn_id") or uuid.uuid4())
                    audio_chunks = []
                    continue

                if event_type == "turn.audio_chunk":
                    audio_b64 = payload.get("audio")
                    if not audio_b64:
                        await _ws_send_error(websocket, "Audio chunk is missing.", active_turn_id)
                        continue
                    try:
                        audio_chunks.append(base64.b64decode(audio_b64))
                    except Exception:
                        await _ws_send_error(websocket, "Invalid audio chunk encoding.", active_turn_id)
                    continue

                if event_type == "turn.end":
                    if not audio_chunks:
                        await _ws_send_error(websocket, "No audio received for this turn.", active_turn_id)
                        continue

                    turn_id = active_turn_id or str(uuid.uuid4())
                    audio_data = b"".join(audio_chunks)
                    audio_chunks = []
                    active_turn_id = None

                    is_valid, error_msg = audio_utils.validate_audio(audio_data)
                    if not is_valid:
                        await _ws_send_error(websocket, error_msg or "Invalid audio.", turn_id)
                        continue

                    duration_seconds = float(audio_utils.get_audio_duration(audio_data) or 0.0)

                    try:
                        transcript = await voice_service.transcribe_audio(
                            audio_data,
                            language=session_context["language"],
                            filename=f"{turn_id}.webm",
                            content_type="audio/webm",
                        )
                    except Exception as exc:
                        logger.warning("Live transcription failed: %s", exc)
                        await _ws_send_error(websocket, "Transcription failed for this turn.", turn_id)
                        continue

                    await websocket.send_json(
                        {
                            "type": "turn.transcript",
                            "session_id": session_context["session_id"],
                            "turn_id": turn_id,
                            "transcript": transcript,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                    history.append({"role": "user", "content": transcript})
                    model_messages = history[-20:]
                    if session_context.get("medical_history"):
                        model_messages = [
                            {
                                "role": "assistant",
                                "content": (
                                    "Patient context:\n"
                                    f"Age: {session_context.get('age')}\n"
                                    f"Gender: {session_context.get('gender')}\n"
                                    f"Medical history: {session_context.get('medical_history')}"
                                ),
                            }
                        ] + model_messages

                    try:
                        assistant_response = await gemini_client.chat(
                            model_messages,
                            system_prompt=MEDICAL_SYSTEM_PROMPT,
                        )
                    except Exception as exc:
                        logger.warning("Live response generation failed: %s", exc)
                        assistant_response = (
                            "I could not generate a full response right now. "
                            "Please repeat your symptoms or try again."
                        )

                    red_flags = _detect_red_flags(transcript)
                    urgency = "EMERGENCY" if red_flags else "ROUTINE"
                    history.append({"role": "assistant", "content": assistant_response})

                    await websocket.send_json(
                        {
                            "type": "turn.response",
                            "session_id": session_context["session_id"],
                            "turn_id": turn_id,
                            "response_text": assistant_response,
                            "urgency": urgency,
                            "red_flags": red_flags,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                    try:
                        audio_response = await voice_service.generate_speech(
                            assistant_response,
                            language=session_context["language"],
                        )
                        await websocket.send_json(
                            {
                                "type": "turn.audio",
                                "session_id": session_context["session_id"],
                                "turn_id": turn_id,
                                "audio": base64.b64encode(audio_response).decode("utf-8"),
                                "mime_type": "audio/mpeg",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                    except Exception as exc:
                        logger.warning("Live TTS generation failed: %s", exc)

                    try:
                        await _persist_live_turn(
                            db,
                            user_id=user.id,
                            session_id=session_context["session_id"],
                            language=session_context["language"],
                            audio_filename=f"{turn_id}.webm",
                            duration_seconds=duration_seconds,
                            transcription=transcript,
                            assistant_response=assistant_response,
                            urgency=urgency,
                            red_flags=red_flags,
                        )
                    except SQLAlchemyError as exc:
                        await db.rollback()
                        logger.warning("Live voice persistence failed: %s", exc)
                    continue

                await _ws_send_error(websocket, f"Unsupported event type: {event_type}", active_turn_id)

    except WebSocketDisconnect:
        logger.info("Voice live websocket disconnected.")
    except Exception as exc:
        logger.exception("Live voice websocket failed: %s", exc)
        try:
            await _ws_send_error(websocket, "Unexpected live consultation error.")
        except Exception:
            pass
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass


@router.get("/languages", responses=UNAUTHORIZED_RESPONSE)
async def get_supported_languages(current_user: CurrentUser):
    from app.services.voice.service import voice_service

    langs = voice_service.get_languages()
    return {
        "transcription_languages": langs,
        "tts_languages": langs,
    }


@router.post("/transcribe", response_model=TranscriptionResponse, responses=UNAUTHORIZED_RESPONSE)
async def transcribe_audio(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    from app.services.voice.service import voice_service

    clean_lang = None if language in {"", "string", None} else language
    audio_data = await file.read()

    is_valid, error_msg = audio_utils.validate_audio(audio_data)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        text = await voice_service.transcribe_audio(
            audio_data,
            language=clean_lang,
            filename=file.filename,
            content_type=file.content_type,
        )

        duration_seconds = 0.0
        try:
            duration_seconds = float(audio_utils.get_audio_duration(audio_data) or 0.0)
        except Exception:
            duration_seconds = 0.0

        record = VoiceInteraction(
            session_id=session_id or str(uuid.uuid4()),
            user_id=current_user.id,
            audio_filename=file.filename,
            transcription=text,
            language=clean_lang or "auto",
            duration_seconds=duration_seconds,
            confidence=0.9,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Voice transcription failed: %s", exc)
        raise HTTPException(status_code=500, detail="Transcription failed")


@router.post("/tts", responses=UNAUTHORIZED_RESPONSE)
@router.post("/speak", responses=UNAUTHORIZED_RESPONSE)
async def text_to_speech(request: TTSRequest, current_user: CurrentUser):
    from app.services.voice.service import voice_service

    try:
        return StreamingResponse(
            voice_service.tts_service.stream_speech(request.text, request.language),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=response.mp3"},
        )
    except Exception as exc:
        logger.exception("TTS generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Voice generation failed")


@router.post("/diagnose", response_model=VoiceDiagnosisResponse, responses=UNAUTHORIZED_RESPONSE)
async def voice_diagnosis(
    current_user: CurrentUser,
    audio: UploadFile = File(...),
    language: str = Form("en"),
    age: int = Form(...),
    gender: str = Form(...),
    medical_history: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    from app.services.voice.service import voice_service

    try:
        audio_data = await audio.read()
        try:
            symptoms_text = await voice_service.transcribe_audio(
                audio_data,
                language=language,
                filename=audio.filename,
                content_type=audio.content_type,
            )
        except Exception as stt_exc:
            logger.warning("STT failed in diagnose flow, using fallback text: %s", stt_exc)
            symptoms_text = "Voice received but transcription was unavailable."

        state = {
            "patient_id": None,
            "symptoms": symptoms_text,
            "user_location": None,
            "age": age,
            "gender": gender,
            "medical_history": medical_history,
            "vitals": None,
            "has_image": False,
            "image_type": None,
            "image_analysis": None,
            "urgency_level": "ROUTINE",
            "messages": [],
            "confidence": 0.0,
            "triage_result": None,
            "symptom_analysis": None,
            "rag_context": None,
            "diagnosis": None,
            "treatment_plan": None,
            "is_emergency": False,
            "emergency_info": None,
            "next_step": None,
            "final_report": None,
        }
        final_state = await medical_agent_graph.ainvoke(state)

        patient_id: Optional[int] = None
        try:
            patient_result = await db.execute(
                select(Patient)
                .where(Patient.user_id == current_user.id)
                .order_by(Patient.id.desc())
                .limit(1)
            )
            patient = patient_result.scalar_one_or_none()
            if patient is None:
                patient = Patient(
                    user_id=current_user.id,
                    name=current_user.full_name or current_user.email,
                    age=age,
                    gender=gender,
                )
                db.add(patient)
                await db.flush()
            patient_id = patient.id
        except SQLAlchemyError as patient_exc:
            await db.rollback()
            logger.warning("Patient lookup/create skipped: %s", patient_exc)

        urgency = str(final_state.get("urgency_level") or "ROUTINE")
        diagnosis_name = str(
            final_state.get("diagnosis", {}).get("primary_diagnosis") or "General clinical concern"
        )
        confidence = float(final_state.get("confidence") or 0.0)
        treatment_summary = final_state.get("treatment_plan", {}).get("immediate_care") or [
            "Consult a clinician for further evaluation."
        ]
        full_report = str(final_state.get("final_report") or "")

        severity_map = {
            "EMERGENCY": "Critical",
            "URGENT": "High",
            "ROUTINE": "Low",
            "SELF-CARE": "Low",
        }

        try:
            if patient_id is not None:
                diagnosis_row = Diagnosis(
                    user_id=current_user.id,
                    patient_id=patient_id,
                    symptoms=symptoms_text,
                    diagnosis=diagnosis_name,
                    confidence=confidence,
                    severity=severity_map.get(urgency, "Low"),
                    treatment_plan={"immediate_care": treatment_summary},
                    full_report=full_report,
                    urgency_level=urgency,
                )
                db.add(diagnosis_row)

            duration_seconds = 0.0
            try:
                duration_seconds = float(audio_utils.get_audio_duration(audio_data) or 0.0)
            except Exception:
                duration_seconds = 0.0

            interaction_session_id = str(uuid.uuid4())
            db.add(
                VoiceInteraction(
                    session_id=interaction_session_id,
                    user_id=current_user.id,
                    audio_filename=audio.filename,
                    transcription=symptoms_text,
                    language=language,
                    duration_seconds=duration_seconds,
                    confidence=confidence,
                )
            )
            db.add(
                AIDecisionAudit(
                    user_id=current_user.id,
                    session_id=interaction_session_id,
                    source_endpoint="/api/v1/voice/diagnose",
                    decision_type="voice_diagnosis",
                    input_summary=symptoms_text[:2000],
                    output_summary=full_report[:2000],
                    urgency_level=urgency.lower(),
                    model_name="medical-agent-graph",
                    model_version="v1",
                    prompt_version="voice-diagnose-v2",
                )
            )
            await db.commit()
        except SQLAlchemyError as persist_exc:
            await db.rollback()
            logger.warning("Voice diagnose persistence skipped: %s", persist_exc)

        summary = f"Assessment suggests {diagnosis_name}."
        if urgency == "EMERGENCY":
            summary = f"Emergency warning. Seek immediate care. {summary}"
        elif urgency == "URGENT":
            summary = f"Urgent attention advised today. {summary}"

        audio_b64: Optional[str] = None
        try:
            audio_bytes = await voice_service.generate_speech(summary, language=language)
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        except Exception as tts_exc:
            logger.warning("Diagnosis TTS skipped: %s", tts_exc)

        return VoiceDiagnosisResponse(
            transcription=symptoms_text,
            diagnosis_result={
                "diagnosis": diagnosis_name,
                "confidence": confidence,
                "urgency": urgency,
                "treatment_summary": treatment_summary,
                "full_report": full_report,
            },
            audio_response=audio_b64,
            urgency_level=urgency,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Voice diagnostic process failed: %s", exc)
        raise HTTPException(status_code=500, detail="Voice diagnostic process failed")


@router.get("/history/{session_id}", responses=UNAUTHORIZED_RESPONSE)
async def get_voice_history(
    session_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VoiceInteraction)
        .where(
            VoiceInteraction.session_id == session_id,
            VoiceInteraction.user_id == current_user.id,
        )
        .order_by(VoiceInteraction.created_at.desc())
    )
    records = result.scalars().all()
    return {
        "session_id": session_id,
        "count": len(records),
        "items": [
            {
                "id": item.id,
                "transcription": item.transcription,
                "language": item.language,
                "duration_seconds": item.duration_seconds,
                "created_at": item.created_at,
            }
            for item in records
        ],
    }
