# Rural AI Doctor 🏥

GenAI-powered medical assistant for rural healthcare access.

## Tech Stack

### Backend
- FastAPI
- PostgreSQL + pgvector
- LangChain + LangGraph
- Vertex AI (Gemini 2.0 Flash)

### Frontend
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Shadcn/UI
- Zustand

## Setup

### Backend
\`\`\`bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
docker-compose up -d  # Start PostgreSQL
python scripts/init_db.py
uvicorn app.main:app --reload
\`\`\`

### Frontend
\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

## Features (Week 1)

✅ Medical chat interface
✅ Symptom analysis
✅ Conversation history
✅ Real-time streaming responses
✅ PostgreSQL storage

## Roadmap

- Week 2: RAG with medical knowledge base
- Week 3-4: Vision analysis (X-rays)
- Week 5-6: Multi-agent system (LangGraph)
- Week 7-8: Voice interface (Whisper)
- Week 9-10: Testing & monitoring
- Week 11-12: Production deployment

## License

MIT