<!-- COVER IMAGE SUGGESTION: A dark-toned cinematic illustration of a glowing AI neural network overlaid on a rural Indian village scene at dusk — warm amber lights in mud huts, a doctor silhouette on one side, and a LangGraph-style node flow diagram dissolving into the night sky. Aspect ratio: 16:9. Tools: Midjourney or DALL-E 3 with prompt: "cinematic dark banner, rural Indian village at dusk, AI neural network nodes glowing blue and teal overlaid on the landscape, futuristic meets earthy aesthetic, single doctor silhouette, 16:9" -->

# I Built an AI Doctor for Rural India — Here's Every Technical Decision Behind It

### *LangGraph multi-agent diagnosis · three-layer evidence grounding · live voice consultations · production-grade governance — built for the 800 million people underserved by modern healthcare*

India has roughly **1 doctor for every 11,000 people** in rural areas. The national average is already dire — WHO recommends 1 per 1,000 — but once you filter out the urban centres where most doctors actually practice, that number becomes staggering. People in villages wait hours to reach a primary health centre, describe symptoms to an overworked community health worker who may or may not be medically trained, and leave with a gut-feel diagnosis and a prescription for paracetamol.

I kept thinking: what if the first point of contact wasn't a guess?

That question turned into **Rural AI Doctor** — a full-stack, production-grade clinical decision-support platform that I've been building over the last several months. This post is a deep technical breakdown of every major system: the LangGraph multi-agent diagnosis engine, the three-layer evidence grounding architecture, the voice pipeline for users who can't read, and the governance layer that makes this responsible to deploy. I'll also be honest about the parts that were harder than I expected.

---

## Why I Built This (and Why It Needs to Be More Than a Chatbot)

The initial version of this idea — like most people's first AI health project — was basically "put a prompt in front of Gemini and let it answer medical questions." That version took about two hours to build and was immediately useless. It hallucinated drug names with confidence. It had no way to verify anything it said. It gave the same answer to a 70-year-old diabetic that it gave to a healthy 25-year-old.

Real clinical decision support needs structure. It needs:
- A way to gather patient context before jumping to conclusions
- An explicit safety escape hatch when something looks life-threatening
- Evidence that can be audited — not just "the AI said so"
- Accessibility for people who speak but cannot read

So I threw out the chatbot and built a system. Here's what it actually looks like.

---

## System Architecture Overview

The system is a clean separation of three layers that talk to each other through well-defined APIs.

```
                         ┌──────────────────────────────────┐
                         │         Next.js Frontend          │
                         │  React 19 · TypeScript · Zustand  │
                         │   Radix UI · React Query · TW     │
                         └──────────────┬───────────────────┘
                                        │  REST / WebSocket
                         ┌──────────────▼───────────────────┐
                         │         FastAPI Backend            │
                         │  SQLAlchemy · Alembic · Uvicorn   │
                         │  Prometheus · Sentry · JWT Auth   │
                         └────┬──────────┬──────────┬───────┘
                              │          │          │
               ┌──────────────▼──┐  ┌────▼────┐  ┌─▼──────────────────┐
               │  LangGraph      │  │  pgvec  │  │  External APIs      │
               │  Agent Graph    │  │  -tor   │  │  PubMed · OpenFDA   │
               │  (6 nodes)      │  │  RAG    │  │  MedlinePlus        │
               └──────┬──────────┘  └────▲────┘  │  ClinicalTrials    │
                      │                  │        └────────────────────┘
               ┌──────▼──────────────────┴──────────────────────────────┐
               │                 PostgreSQL + pgvector                   │
               │   medical_documents · audit_logs · evidence_sources     │
               └────────────────────────────────────────────────────────┘
                Voice Pipeline: Whisper → Gemini → gTTS / ElevenLabs
                Vision Pipeline: OpenCV + Pillow → Gemini Vision → Report
```

The backend folder structure reflects the clean separation of concerns I needed to maintain as the system grew:

```
backend/app/
├── api/         → FastAPI route handlers (triage, diagnosis, voice, vision, rag, admin)
├── core/        → Config, security, JWT, rate limiting, startup hooks
├── db/          → SQLAlchemy models and async engine (AsyncSessionLocal)
├── schemas/     → Pydantic v2 schemas for all request/response shapes
├── services/
│   ├── agents/  → LangGraph graph definition, state, and all 7 agent nodes
│   ├── rag/     → Grounding layer: local vector search + external API retrieval
│   ├── voice/   → Whisper transcription + gTTS/ElevenLabs TTS
│   ├── vision/  → OpenCV + Pillow X-ray analysis pipeline
│   └── llm/     → Gemini client with structured output support
```

---

## The Multi-Agent Diagnosis Engine (LangGraph)

This is the most technically interesting part of the system — and the part that required the most rethinking.

The core insight is that medical diagnosis isn't a single inference step. It's a *workflow*. You gather symptoms, you assess urgency, you look at images if there are any, you make a differential, you plan treatment, and you write a report. Each of those steps has its own context requirements, its own failure modes, and its own outputs that feed the next step. Stuffing all of that into one giant prompt is the wrong abstraction.

LangGraph lets you model this as a proper state machine — a directed graph where each node is an agent function, and edges determine flow (including conditional branching).

Here's the actual graph definition from `backend/app/services/agents/graph.py`:

```python
from langgraph.graph import END, START, StateGraph
from app.services.agents.state import AgentState


def triage_router(state: AgentState) -> Literal["emergency_action", "image_analysis", "diagnosis"]:
    """Emergency bypass routing after symptom analysis."""
    if state.get("is_emergency"):
        return "emergency_action"
    if state.get("has_image"):
        return "image_analysis"
    return "diagnosis"


def create_medical_agent_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("triage",            triage_node)
    workflow.add_node("symptom_analysis",  symptom_analyzer_node)
    workflow.add_node("emergency_action",  emergency_action_node)
    workflow.add_node("image_analysis",    image_analyzer_node)
    workflow.add_node("diagnosis",         diagnostician_node)
    workflow.add_node("treatment_planning",treatment_planner_node)
    workflow.add_node("generate_report",   report_generator_node)

    workflow.add_edge(START, "triage")
    workflow.add_edge("triage", "symptom_analysis")

    workflow.add_conditional_edges(
        "symptom_analysis",
        triage_router,
        {
            "emergency_action": "emergency_action",
            "image_analysis":   "image_analysis",
            "diagnosis":        "diagnosis",
        },
    )

    workflow.add_edge("image_analysis",    "diagnosis")
    workflow.add_edge("diagnosis",         "treatment_planning")
    workflow.add_edge("treatment_planning","generate_report")
    workflow.add_edge("generate_report",   END)
    workflow.add_edge("emergency_action",  END)

    return workflow.compile()
```

The flow reads like a clinical protocol: triage first, then structured symptom extraction, then branch based on what we found.

### What Each Node Actually Does

**`triage_node`** — A lightweight gating agent. It takes the patient's raw input and basic demographics and performs an initial severity categorisation. Its job is not to diagnose; it's to classify urgency level and set up the state for downstream agents.

**`symptom_analyzer_node`** — This is where raw patient language gets converted into structured clinical data. I use Gemini with a Pydantic structured output schema (`SymptomExtraction`) that extracts `primary_symptoms`, `severity`, `onset`, `aggravating_factors`, `red_flags`, and `emergency_reason`. The red flags field is the critical one — it drives the conditional edge that follows.

```python
class SymptomExtraction(BaseModel):
    primary_symptoms: List[str]
    duration: str
    severity: Literal["mild", "moderate", "severe", "unknown"]
    associated_symptoms: List[str] = Field(default_factory=list)
    aggravating_factors: List[str] = Field(default_factory=list)
    relieving_factors: List[str] = Field(default_factory=list)
    onset: Literal["sudden", "gradual", "unknown"]
    pattern: Literal["constant", "intermittent", "worsening", "improving", "unknown"]
    red_flags: List[str] = Field(
        default_factory=list,
        description="Chest pain, breathing difficulty, severe bleeding, stroke signs"
    )
    emergency_reason: str = Field(default="")
```

The `triage_router` function reads the populated state after this node runs. If `is_emergency` is `True` (set by the symptom analyzer when red flags are detected), the entire remainder of the normal diagnosis pipeline is bypassed — we go directly to `emergency_action`.

**`emergency_action_node`** — This is the safety circuit breaker. When triggered, it does four things simultaneously: pulls the patient's GPS coordinates from state, finds the three nearest Community Health Centres using Haversine distance computation against a CHC catalog, generates context-aware first aid instructions based on detected red flags, and fires a notification to an emergency worker. It terminates the graph immediately after — there's no treatment planning, no lengthy report. The only output is: *"Call emergency services immediately. Nearest CHC is X km away."*

```python
async def emergency_action_node(state: AgentState) -> AgentState:
    lat = float(location.get("lat", 28.6139))
    lng = float(location.get("lng", 77.2090))

    nearby_facilities = get_nearby_clinics(lat=lat, lng=lng, limit=3)
    first_aid = _first_aid_from_flags(detected_red_flags)

    await notification_service.notify_emergency_worker(
        user_id=state.get("patient_id"),
        user_location={"lat": lat, "lng": lng},
        emergency_info=emergency_info,
    )

    logger.warning("Emergency path triggered for patient_id=%s", state.get("patient_id"))
    return {**state, "urgency_level": "EMERGENCY", "final_report": "\n".join(message_lines)}
```

**`image_analyzer_node`** — If the patient uploaded a chest X-ray, this node runs before diagnosis. It uses OpenCV and Pillow for preprocessing (contrast normalisation, edge sharpening), then passes the processed image to Gemini Vision for analysis. The output populates `image_analysis` in state, which the diagnostician node reads as additional context.

**`diagnostician_node`** — The core differential diagnosis agent. It receives: structured symptom data, image analysis results (if any), RAG context from the grounding layer, patient vitals and history. It produces a differential with confidence scores and the `urgency_level` that drives downstream agents.

**`treatment_planner_node`** — Takes the diagnosis output and generates a treatment plan, including medication recommendations. Before any medication suggestion surfaces in the response, it goes through the **medication safety check** — a rule-based validation layer that cross-references drug names against the patient's age, gender, and flagged conditions. Recommending an NSAID to someone with kidney disease or a beta-blocker to someone with asthma doesn't make it through.

**`report_generator_node`** — Assembles the complete clinical report from all accumulated state. This is what the frontend renders: diagnosis summary, treatment plan, evidence citations, urgency level, follow-up instructions, and a Clinician Notes section where a real doctor can annotate or override.

---

## Evidence Grounding — Why This Matters More in Healthcare

Let's talk about hallucination. Language models hallucinate — everyone knows this. In most applications it's annoying. In healthcare, a confident hallucination about a drug interaction or a diagnostic criterion could cause serious harm.

Evidence grounding is the system's answer to this problem. Every diagnosis response is anchored to verifiable citations before it's generated. I implemented a **three-layer retrieval strategy** that runs before the LLM ever generates a word of clinical content.

**Layer 1: Trusted Source Catalog (PostgreSQL)**
The `medical_evidence_sources` table stores a pre-seeded catalog of verified source metadata — WHO treatment guidelines, CDC protocols, NICE clinical pathways, and curated reference texts. When a query comes in, the system first checks this catalog for direct matches. These sources carry the highest evidence weight.

**Layer 2: Local Knowledge Base (pgvector semantic search)**
Medical documents uploaded to the system — PDF clinical guidelines, hospital protocols, disease handbooks — are chunked, embedded using Google's embedding model, and stored in `medical_documents` with their vector representations. The `retrieve_medical_grounding` function performs cosine similarity search over this local corpus. Here's the actual retrieval code:

```python
async def retrieve_medical_grounding(query: str, top_k: int = 3) -> list[dict]:
    """Vector-first retrieval with lexical fallback."""
    embedding = await _embed_query(query)  # Google embedding API

    async with AsyncSessionLocal() as db:
        if embedding:
            # Primary path: cosine similarity search via pgvector
            vector_stmt = (
                select(
                    MedicalDocument.id,
                    MedicalDocument.title,
                    MedicalDocument.content,
                    MedicalDocument.metadata_json,
                    (1 - MedicalDocument.embedding.cosine_distance(embedding)).label("similarity"),
                )
                .where(MedicalDocument.embedding.is_not(None))
                .order_by(MedicalDocument.embedding.cosine_distance(embedding))
                .limit(top_k)
            )
            rows = (await db.execute(vector_stmt)).all()

        if not rows:
            # Fallback: lexical ILIKE match when embeddings unavailable
            lexical_stmt = (
                select(MedicalDocument.id, MedicalDocument.title, MedicalDocument.content)
                .where(
                    or_(
                        MedicalDocument.title.ilike(f"%{query}%"),
                        MedicalDocument.content.ilike(f"%{query}%"),
                    )
                )
                .limit(top_k)
            )
            rows = (await db.execute(lexical_stmt)).all()

    return [
        {
            "provider": "LocalRAG",
            "title": row.title,
            "excerpt": _trim_excerpt(row.content),
            "similarity": float(getattr(row, "similarity", 0.0)),
            "source": row.metadata_json.get("source", "") if row.metadata_json else "",
        }
        for row in rows
    ]
```

The lexical fallback is important. In a rural deployment where network latency is real and embedding calls can fail, you cannot afford to return a zero-context response. The `ILIKE` match is less precise but infinitely better than nothing.

**Layer 3: External Reputable APIs (async fan-out)**
The `retrieve_reputable_citations` function fans out four concurrent requests: PubMed (NCBI E-utilities), MedlinePlus Connect, OpenFDA drug labels, and ClinicalTrials.gov v2. All four run with `asyncio.gather` so total latency is bounded by the slowest single API, not the sum.

Each citation that makes it into the final response includes: Provider, Source URL, Excerpt, Similarity Score, Evidence Level, and Verification Timestamp. The provider weights (`PubMed: 1.0`, `OpenFDA: 0.95`, `MedlinePlus: 0.9`, `ClinicalTrials: 0.85`) determine citation ranking when sources are merged. The LLM is explicitly instructed to ground its generation in these citations and flag when it is reasoning beyond them.

---

## Voice + Vision: Making It Accessible to Actual Rural Users

Here's the uncomfortable truth about building for rural India: a significant portion of the target users are functionally illiterate or read in regional languages that most AI systems don't handle well. A text-only interface isn't accessible — it's a product for urban users cosplaying as a rural health solution.

I approached this with two separate pipelines.

### Live Voice Consultations

This is the feature I'm most proud of from an accessibility standpoint, and the one that sets this apart from every other "AI health chatbot" I've seen.

**Live Voice Consultations** allow a user to talk directly to the AI doctor in real time — no typing required. They describe their symptoms out loud, the system listens, processes, thinks, and responds with a spoken diagnosis and care plan. For a patient in a remote village who may have never used a smartphone app but has described symptoms to a health worker verbally their entire life, this is the natural interface. There's no learning curve. You just talk.

The session flow works like this:

```
User speaks → Whisper transcription → LangGraph agent pipeline
    → Gemini processes + generates diagnosis
        → TTSService synthesises response → streamed audio back to user
```

The entire exchange is real-time and stateful. A user can ask a follow-up — *"what if I can't get that medicine?"* — and the system maintains session context through the same LangGraph state machine that handles text queries. There's no separate "voice mode" internally; speech is just another input format that resolves to the same structured pipeline.

The frontend exposes a large, prominent **"Start Voice Consultation"** button on the dashboard — designed deliberately so that a first-time user with no digital literacy can figure it out without reading a single instruction.

### Under the Hood: The Voice Pipeline

The voice flow is: **audio in → transcription → AI processing → speech out**.

The transcription layer uses Whisper (via `whisper_service.py`) which runs locally or on a hosted endpoint. Whisper handles accented English and code-switched speech reasonably well, which matters when a user in Karnataka is describing symptoms in a mix of Kannada and English. The transcription goes through the same LangGraph pipeline as a text query — no separate path, no special handling. The AI doesn't know or care whether the input was typed or spoken.

On the output side, the `TTSService` handles synthesis. The primary provider is gTTS — it's lightweight, has decent multilingual coverage (English, Hindi, Tamil, Telugu, Bengali are all supported), and runs reliably without API key management. ElevenLabs is configured as a higher-quality alternative for cases where voice naturalness matters more:

```python
class TTSService:
    SUPPORTED_LANGUAGES = {
        "en": "English", "hi": "Hindi", "ta": "Tamil",
        "te": "Telugu", "bn": "Bengali", "ar": "Arabic", ...
    }

    async def text_to_speech_async(self, text: str, language: str = "en") -> bytes:
        """Non-blocking wrapper — gTTS runs synchronously, we push it to a thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._generate_audio, text, language, False)

    async def stream_speech(self, text: str, language: str = "en", chunk_size: int = 1024):
        """Chunked streaming for low-bandwidth connections."""
        audio_data = await self.text_to_speech_async(text, language)
        audio_io = io.BytesIO(audio_data)
        while chunk := audio_io.read(chunk_size):
            yield chunk
            await asyncio.sleep(0)
```

The streaming endpoint (`stream_speech`) is specifically for low-bandwidth environments — instead of waiting for the full audio to generate and transferring it at once, it streams in 1KB chunks. On a 2G connection, this is the difference between a response that feels live and one that times out.

### The Vision Pipeline

Chest X-rays are one of the most common diagnostic tools in rural PHCs, and they're also one of the most frequently misread due to lack of trained radiologists. The vision workflow is:

1. Image upload via the frontend (JPEG/PNG/DICOM-adjacent formats)
2. OpenCV preprocessing: grayscale normalisation, contrast-limited adaptive histogram equalisation (CLAHE), edge enhancement
3. Pillow for format standardisation and metadata extraction
4. Gemini Vision receives the processed image with a structured radiology-oriented prompt
5. Analysis output (`image_analysis` in state) flows directly into the diagnosis agent

The vision results don't replace the symptom analysis — they augment it. The diagnostician sees both: *"Patient reports: chest pain, shortness of breath for 3 days. Image analysis: bilateral opacity in lower lobes, consistent with consolidation."*

---

## Production-Grade Infrastructure — The Parts That Aren't Glamorous

There's a certain category of engineering work that doesn't make it into most student project write-ups because it doesn't produce impressive screenshots. I want to document exactly why I built each of these components, because each one exists to solve a real failure mode.

### Prometheus Instrumentation
Metrics are collected for API response times, active diagnosis sessions, agent node latency, and error rates. The `why` is simple: you cannot debug a system you cannot observe. When the treatment planner node starts taking 4× longer than usual, Prometheus tells you before your users do.

### Sentry Error Tracking
Every unhandled exception in the FastAPI backend ships to Sentry with full context: the request path, the patient session ID (anonymised), and the stack trace. Without this, debugging production errors in a deployed backend is guesswork. Structured logging (JSON format, to a log file and stdout) gives you the chronological sequence that Sentry's isolated exceptions miss.

### Comprehensive Audit Trails
Every diagnosis session writes an audit record: who requested it, what symptoms were submitted, which agents executed, what citations were retrieved, what the output was, and when it happened. This is non-negotiable for a healthcare application. If a clinician disputes an AI recommendation or a patient has an adverse outcome, you need to be able to reconstruct exactly what happened. The admin dashboard exposes an audit log viewer with filtering by patient, date range, urgency level, and agent path taken.

### Bias Monitoring Dashboard
This is the one that most people don't expect in a student project, and it's the one I'm most serious about. Clinical AI systems trained on Western datasets routinely underperform for South Asian presentations of common diseases. The bias dashboard tracks diagnosis confidence scores segmented by patient demographics — age, gender, reported location. If the system is systematically less confident for women, or for patients above 60, that pattern is visible and actionable before it causes harm. It doesn't fix bias — nothing in software fixes bias — but it makes it visible.

### Medication Safety Checks
Before any treatment plan that includes medication recommendations leaves the `treatment_planner_node`, it goes through rule-based contraindication checks. NSAIDs flagged for renal warnings, certain antibiotics flagged for paediatric age groups, drugs with known interactions checked against the patient's existing medications list. This is belt-and-suspenders engineering: the LLM is prompted to avoid contraindicated drugs, and a separate rules layer catches what prompting misses.

### Offline Sync Endpoints
Rural clinics often have intermittent connectivity. The API exposes dedicated `/sync` endpoints that accept batched updates with conflict detection — a community health worker can enter several patient interactions offline, and when connectivity returns, the sync reconciles state with last-write-wins semantics and flags conflicts for review. Without this, the system is useless the moment cell signal drops.

---

## One Honest Challenge: LangGraph State Management Across Async Nodes

I want to walk through the hardest debugging session I had during this build, because the solution isn't obvious from the LangGraph docs.

The problem: the `AgentState` TypedDict has a `messages` field that uses `Annotated[List[BaseMessage], add_messages]`. LangGraph uses this annotation to **merge** message lists across state updates rather than replace them. That's the correct behaviour for a conversational agent — you want to accumulate messages. But in a medical diagnosis pipeline, each node was *also* returning `{**state, "messages": [new_message]}`. What I expected: the new message appended to the existing list. What I got: LangGraph *merging* the sparse `[new_message]` return with the existing state using `add_messages`, which worked correctly — but the symptom analyzer and the diagnostician were both adding messages, and I was getting duplicates in the final report because the accumulator was working exactly as designed.

The fix was understanding that with `add_messages`, you never spread the whole state and return a fresh messages list — you return only the *delta*. Each node should return only the keys it actually modified, not `{**state, ...}` for everything. This is a subtle but important distinction: LangGraph's state merging means that returning an unchanged key is different from not returning that key at all.

The deeper lesson: when you're debugging LangGraph state issues, `print(state)` at the start of every node is your best friend. The state object is immutable per-step — you can always inspect exactly what a node received.

---

## What I Would Do Differently

**1. Use Alembic migrations from day one.** I started with `Base.metadata.create_all()` during development for speed, and transitioning to Alembic-managed migrations midway through was genuinely painful. Every schema change became a delicate manual operation instead of a one-line `alembic revision --autogenerate`. If you're building anything that will persist data, start with Alembic.

**2. Abstract the LLM client earlier.** The `gemini_client` module is a thin wrapper around the Google Generative AI SDK, which is fine — but it's used directly in every agent node. When I wanted to add LangSmith tracing, I had to touch every node. A proper `BaseLLMClient` abstraction with the Gemini implementation behind it would have made that a one-file change.

**3. Build the voice pipeline for real regional languages, not as a future consideration.** gTTS Hindi support is passable. gTTS support for Kannada, Odia, Assamese, or Maithili is either missing or severely accented to the point of incomprehension. The users who most need this system are exactly the ones underserved by English and Hindi. The right move would have been to evaluate AI4Bharat's Indic TTS models earlier in the project rather than defaulting to gTTS and promising "better language support later."

---

## ⚠️ An Honest Safety Disclaimer

**Rural AI Doctor is a clinical decision-support tool, not a medical practitioner.** It is designed to improve the quality of the *first assessment* that reaches a clinician, not to replace clinical judgment. The system is explicit about this: every diagnosis output includes a mandatory disclaimer, every treatment plan is labelled as a recommendation for clinician review, and the clinician override path is always available.

Any real-world deployment of this system would require rigorous clinical validation (ideally a prospective study with actual PHC data), compliance review against India's Digital Health Mission and the Personal Data Protection Bill, a trained community health worker as the interface between the AI output and the patient, and proper incident reporting infrastructure.

I built this because the status quo — overworked health workers making underpowered guesses — is also risky. AI-assisted decision support is not a radical idea in 2025; it's increasingly standard practice in well-resourced hospitals. The gap I'm trying to close is access, not trust. Whether this ever makes it into an actual deployment is a question for regulators, clinicians, and the communities it would serve. The engineering is ready to be evaluated.

---

## Where to Find the Code

The full codebase — backend, frontend, LangGraph agents, RAG grounding, voice pipeline, and admin dashboard — is on GitHub:

👉 **[github.com/RakshitKaintura/Rural_AI_Doctor](https://github.com/RakshitKaintura/Rural_AI_Doctor)** 

If you're working on AI for healthcare access, or you've tackled LangGraph multi-agent systems and have thoughts on the state management patterns, I'd genuinely like to hear from you. The problem is hard enough that nobody is going to solve it alone.

---

*Rakshit Kaintura — 3rd-year B.E. CSE @ SIRMVIT, VTU Bengaluru. Building full-stack AI systems that work where connectivity is bad and stakes are high.*

---

<!-- tags: AI, Healthcare, LangGraph, FastAPI, RAG, Multi-Agent, Python, NextJS, GeminiAI, IndiaTech -->
