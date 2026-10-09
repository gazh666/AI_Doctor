"""
Final Corrected conftest.py for Rural AI Doctor.
Ensures database tables exist and LLM methods are correctly mocked.
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
# Explicitly import models to ensure Base.metadata is fully populated before create_all
from app.db.models import MedicalDocument, ChatHistory, VoiceInteraction, Diagnosis
from app.db.session import get_db
from app.services.llm.gemini_client import GeminiClient

# 1. Database Configuration for Testing
# StaticPool is required for in-memory SQLite to persist data across connections in the same process
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_database_schema():
    """
    FIX: Create all tables once for the entire test session.
    Ensures 'chat_history' and other tables exist before any tests execute.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provides a fresh transactional session for each test case."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
async def client(db_session: Session) -> AsyncGenerator[AsyncClient, None]:
    """
    Asynchronous Test Client.
    Overrides the database dependency to use the transactional test session.
    """
    app.dependency_overrides[get_db] = lambda: db_session
    
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture(scope="session")
def event_loop():
    """Maintain a single event loop for the test session to avoid 'Loop Closed' errors."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# 2. Universal LLM Mocking Fix
@pytest.fixture(autouse=True)
def mock_gemini():
    """
    FIX: Broad class-level mock for GeminiClient.
    This prevents AttributeError by returning an AsyncMock that responds to 
    any method call, effectively bypassing '429 RESOURCE_EXHAUSTED'.
    """
    mock_instance = AsyncMock()
    
    # Configure default return values for the most common LLM calls
    mock_instance.chat.return_value = "Based on your symptoms, I recommend rest and hydration."
    mock_instance.generate_chat_response.return_value = "Mocked chat response."
    mock_instance.generate_medical_report.return_value = {"diagnosis": "Viral Fever", "confidence": 0.85}
    
    # Patch the class itself so that any instantiation returns our mock instance
    with patch("app.services.llm.gemini_client.GeminiClient", return_value=mock_instance):
        yield mock_instance

@pytest.fixture
def sample_patient_data():
    """Standardized patient data for diagnostic testing."""
    return {
        "language": "en",
        "age": 35,
        "gender": "Male",
        "medical_history": "No significant history"
    }