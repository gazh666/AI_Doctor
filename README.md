# 🏥 Rural AI Doctor

**Rural AI Doctor** is an advanced, AI-assisted healthcare platform engineered specifically for rural and low-resource clinical environments. It brings together conversational triage, multi-step diagnosis support, voice and image workflows, retrieval-augmented medical knowledge, auditability, and operational tooling into a single, cohesive full-stack web application.

The codebase features a robust **FastAPI backend** and a modern **Next.js frontend**. The infrastructure is built for practical, real-world deployment with technologies like PostgreSQL with `pgvector`, structured logging, rate limiting, comprehensive health checks, observability hooks, and highly modular API services.

---

## ✨ Core Highlights & Features

- 💬 **Conversational Triage:** AI-driven chat and symptom triage workflows for guided, accurate first-pass patient assessments.
- 🩺 **Multi-Agent Diagnosis:** Advanced diagnosis support including treatment planning, emergency action nodes, and comprehensive report generation.
- 🎙️ **Live Voice Consultations:** Real-time, live sessions where users can talk directly to the AI doctor, featuring seamless transcription, speech output, and spoken diagnosis flows for maximum accessibility.
- 🩻 **Vision Workflows:** Cutting-edge image and chest X-ray analysis integration.
- 📚 **RAG Medical Workspace:** Retrieval-Augmented Generation workspace for searching indexed medical documents and internal knowledge sources.
- 🏛️ **Evidence Grounding:** Trusted source catalog (WHO, CDC, NICE + curated references) with deep citation metadata for every generated response.
- 📅 **Clinical Operations:** Follow-up planning, appointment scheduling, export tooling, offline-sync endpoints, and clinical ops screens.
- 🛡️ **Safety & Governance:** Medication safety checks, comprehensive audit trails, and clinician override feedback paths.

---

## 🔍 Evidence Grounding Architecture

Medical answers are strictly grounded through a multi-layer retrieval strategy before generation:

1. **Trusted Source Catalog:** Stored in PostgreSQL (`medical_evidence_sources`).
2. **Local Knowledge Base:** Uploaded medical documents chunked using `pgvector` (`medical_documents`).
3. **Reputable Public Sources:** Integration with PubMed, MedlinePlus, OpenFDA, and ClinicalTrials.

Every diagnosis and RAG response includes detailed citation metadata: **Provider, Source URL, Excerpt, Similarity Score, Evidence Level, and Verification Timestamps** to ensure complete auditability.

---

## 📸 Product Screenshots

### 🏠 Welcome + Feature Access
![Welcome page](frontend/public/WelcomePage.png)
![Feature access and quick links](frontend/public/WelcomePage_EndPoints_Paths.png)

### 🏥 User Dashboard + Diagnosis
![User dashboard](frontend/public/User_Dashboard.png)
![Multi-agent diagnosis system](frontend/public/Diagnosis_System.png)
![Diagnosis result and treatment plan](frontend/public/Result_of_Diagnosis.png)

### 🧠 Knowledge / RAG Assistant
![RAG report assistant](frontend/public/Knowledge_RAG_Assistant.png)

### 🩻 Vision / X-Ray Analysis
![Chest X-ray analysis](frontend/public/Chest_X_Ray_Analysis.png)

### ⚙️ Clinical Ops Console & Admin Governance
![Clinical operations console](frontend/public/Clinical_Ops_Console.png)
![Admin dashboard overview](frontend/public/Admin_Dashboard.png)
![Admin audit logs](frontend/public/Admin_Dashboard_Audit_Logs.png)
![Bias monitoring dashboard](frontend/public/AdminDashboard_BiasMonitoring.png)

---

## 🛠️ Tech Stack

| Layer | Stack |
| --- | --- |
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS, Radix UI, Zustand, React Query |
| **Backend** | FastAPI, SQLAlchemy, Pydantic Settings, Uvicorn, Gunicorn |
| **Data** | PostgreSQL, `pgvector`, Alembic, Redis-compatible cache configuration |
| **AI Layer** | Google Gemini, LangChain, LangGraph, LangSmith |
| **Media / Vision**| OpenCV, Pillow, PyMuPDF, pydub, gTTS, ElevenLabs |
| **Observability** | Prometheus instrumentation, structured logging, Sentry |
| **Testing** | Pytest, Jest, React Testing Library |

---

## 🏗️ Project Architecture

```text
Rural_AI_Doctor/
├── backend/
│   ├── alembic/         # Database migrations
│   ├── app/
│   │   ├── api/         # FastAPI Route handlers
│   │   ├── core/        # Config, Security, and Setup
│   │   ├── db/          # SQLAlchemy Models & Engine
│   │   ├── schemas/     # Pydantic Schemas
│   │   └── services/    # Business logic (AI, Voice, Vision, RAG)
│   ├── scripts/         # Init & DB scripts
│   └── tests/           # Backend API and workflow coverage
├── frontend/
│   ├── public/          # Assets and images
│   └── src/
│       ├── app/         # Next.js App Router pages
│       ├── components/  # Feature-specific UI modules
│       ├── hooks/       # React hooks
│       ├── lib/         # API wrappers & Auth
│       └── store/       # Zustand state management
├── docs/                # Architecture and design documentation
└── scripts/             # Global utility scripts
```

---

## 🚀 Local Development Guide

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 16 with `pgvector`
- npm

### 1. Database Setup
A local Docker setup is provided for PostgreSQL:
```bash
cd backend
docker-compose up -d
```
> Exposes PostgreSQL on `localhost:5434` with a database named `rural_ai_doctor`.

### 2. Environment Variables
```bash
cd backend
copy .env.example .env
```
Ensure you update variables like `DATABASE_URL`, `SECRET_KEY`, `GOOGLE_API_KEY`, `OPENFDA_API_KEY`, etc.

### 3. Backend Setup
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Initialize Database
Sync the schema, enable `pgvector`, and seed the admin account:
```bash
python scripts/init_db.py
```

### 5. Run the Services

**Backend API:**
```bash
cd backend
uvicorn app.main:app --reload
```
> Available at `http://127.0.0.1:8000`. API Docs at `/docs`.

**Frontend Application:**
```bash
cd frontend
npm install
npm run dev
```
> Available at `http://localhost:3000`.

---

## 🧪 Testing

**Backend:**
```bash
cd backend
pytest
```
*Coverage includes clinical triage, medication safety, sync conflict handling, and audit paths.*

**Frontend:**
```bash
cd frontend
npm test
npm run test:e2e
```
*Run `npx playwright install chromium` once before E2E tests.*

---

## ⚠️ Safety & Compliance Note

This project is a **clinical decision-support application** and is **NOT** a replacement for licensed medical judgment. Any real-world deployment must undergo rigorous clinical validation, privacy/security review (HIPAA/GDPR), and incorporate appropriate regulatory and operational safeguards.

---

## 🌟 Resume / Portfolio Value

This project actively demonstrates:
- **Full-stack product engineering** across modern frontend, backend, and data layers.
- **Production-grade API design** with integrated observability, caching, and rate limiting.
- **Applied AI integration** moving far beyond simple chat interfaces into multi-agent workflows.
- **Healthcare domain modeling** with strict auditability, grounding, and safety controls.
- **Multimodal UX design** effortlessly blending text, voice, documents, and medical imaging.
