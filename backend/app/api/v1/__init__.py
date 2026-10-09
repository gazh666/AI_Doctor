from fastapi import APIRouter
from app.api.v1.endpoints import (
	chat,
	vision,
	agents,
	voice,
	triage,
	followups,
	medications,
	sync,
	audit,
	health,
	auth,
	users,
	reports,
	admin,
	export,
	appointments,
	backup,
	rag,
	lung_sound,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router)
api_router.include_router(reports.router)
api_router.include_router(admin.router)
api_router.include_router(export.router)
api_router.include_router(appointments.router)
api_router.include_router(backup.router)
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(lung_sound.router, prefix="/lung_sound", tags=["lung_sound"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(vision.router, prefix="/vision", tags=["vision"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(triage.router, prefix="/triage", tags=["triage"])
api_router.include_router(followups.router, prefix="/followups", tags=["followups"])
api_router.include_router(medications.router, prefix="/medications", tags=["medications"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])