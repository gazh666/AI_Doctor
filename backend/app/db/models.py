from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base


# USER MANAGEMENT TABLES

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, default="patient")  # patient, doctor, admin
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    phone = Column(String)
    date_of_birth = Column(DateTime)
    gender = Column(String)
    address = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    patients = relationship("Patient", back_populates="user")
    diagnoses = relationship("Diagnosis", back_populates="user")
    appointments = relationship("Appointment", back_populates="user")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    phone = Column(String)
    blood_type = Column(String)
    allergies = Column(Text)
    chronic_conditions = Column(Text)
    emergency_contact = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="patients")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    symptoms = Column(Text)
    diagnosis = Column(Text)
    confidence = Column(Float)
    severity = Column(String)
    treatment_plan = Column(JSON)
    full_report = Column(Text)
    urgency_level = Column(String)
    lung_sound_path = Column(String)
    lung_sound_result_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="diagnoses")


class MedicalDocument(Base):
    __tablename__ = "medical_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768))
    metadata_json = Column("metadata", JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MedicalEvidenceSource(Base):
    __tablename__ = "medical_evidence_sources"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    excerpt = Column(Text, nullable=False)
    condition_tags = Column(JSON, nullable=True)
    evidence_level = Column(String, nullable=True)  # guideline, systematic_review, rct, observational, expert_consensus
    published_at = Column(DateTime(timezone=True), nullable=True)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    embedding = Column(Vector(768))
    metadata_json = Column("metadata", JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ImageAnalysis(Base):
    __tablename__ = "image_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    patient_id = Column(Integer, nullable=True)
    image_type = Column(String)
    original_filename = Column(String)
    analysis_result = Column(JSON)
    findings = Column(Text)
    confidence = Column(Float)
    severity = Column(String)
    recommendations = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VoiceInteraction(Base):
    __tablename__ = "voice_interactions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    audio_filename = Column(String)
    transcription = Column(Text)
    language = Column(String)
    duration_seconds = Column(Float)
    confidence = Column(Float)
    patient_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# APPOINTMENT SYSTEM

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    appointment_type = Column(String)  # consultation, followup, emergency
    scheduled_date = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    status = Column(String, default="scheduled")  # scheduled, completed, cancelled, no-show
    notes = Column(Text)
    diagnosis_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="appointments")


# ANALYTICS

class UserActivity(Base):
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    activity_type = Column(String)  # chat, rag_query, image_analysis, voice, diagnosis
    endpoint = Column(String)
    duration_ms = Column(Float)
    status_code = Column(Integer)
    metadata_json = Column("metadata", JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UsageMetrics(Base):
    __tablename__ = "usage_metrics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    metric_type = Column(String)  # api_calls, users_active, diagnoses_made
    value = Column(Integer)
    metadata_json = Column("metadata", JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TriageAssessment(Base):
    __tablename__ = "triage_assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    symptoms_text = Column(Text, nullable=False)
    age = Column(Integer, nullable=True)
    vitals_json = Column("vitals", JSON, nullable=True)
    risk_factors_json = Column("risk_factors", JSON, nullable=True)
    urgency_level = Column(String, nullable=False)  # emergency, urgent, routine
    red_flags_json = Column("red_flags", JSON, nullable=True)
    rationale = Column(Text, nullable=True)
    recommended_action = Column(Text, nullable=False)
    escalated = Column(Boolean, default=False)
    escalation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FollowUpPlan(Base):
    __tablename__ = "followup_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    diagnosis_id = Column(Integer, ForeignKey("diagnoses.id"), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=False)
    channel = Column(String, default="sms")  # sms, call, whatsapp, in_app
    reminder_enabled = Column(Boolean, default=True)
    reminder_sent = Column(Boolean, default=False)
    status = Column(String, default="scheduled")  # scheduled, completed, missed, cancelled
    notes = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MedicationSafetyCheck(Base):
    __tablename__ = "medication_safety_checks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    medications_json = Column("medications", JSON, nullable=False)
    allergies_json = Column("allergies", JSON, nullable=True)
    conditions_json = Column("conditions", JSON, nullable=True)
    risk_level = Column(String, nullable=False)  # low, moderate, high, critical
    interactions_json = Column("interactions", JSON, nullable=True)
    contraindications_json = Column("contraindications", JSON, nullable=True)
    recommendation = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SyncEvent(Base):
    __tablename__ = "sync_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False)  # diagnosis, followup, triage, note
    entity_id = Column(String, nullable=False)
    operation = Column(String, nullable=False)  # create, update, delete
    payload_json = Column("payload", JSON, nullable=True)
    client_updated_at = Column(DateTime(timezone=True), nullable=False)
    server_updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sync_status = Column(String, default="applied")  # applied, conflict, resolved
    conflict_reason = Column(Text, nullable=True)
    resolution_strategy = Column(String, nullable=True)  # client_wins, server_wins, merge
    resolved_by_user = Column(Boolean, default=False)


class AIDecisionAudit(Base):
    __tablename__ = "ai_decision_audits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(String, index=True, nullable=True)
    source_endpoint = Column(String, nullable=False)
    decision_type = Column(String, nullable=False)  # chat, triage, medication
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    confidence_band = Column(String, nullable=True)  # low, medium, high
    urgency_level = Column(String, nullable=True)
    red_flags_json = Column("red_flags", JSON, nullable=True)
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
    override_applied = Column(Boolean, default=False)
    override_reason = Column(Text, nullable=True)
    clinician_feedback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
