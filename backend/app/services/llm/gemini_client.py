from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.core.config import settings
from typing import Any, List, Dict, Type, TypeVar, Optional
import os

T = TypeVar("T")

class GeminiClient:
    def __init__(self):
        self.llm: Optional[ChatGoogleGenerativeAI] = None

    def _get_llm(self) -> ChatGoogleGenerativeAI:
        """Create the LLM client lazily to avoid crashing application startup."""
        if self.llm is not None:
            return self.llm

        if not settings.GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY is not configured")

        os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-3.1-flash-lite-preview",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1,
            max_retries=2,
        )
        return self.llm

    def _normalize_content(self, content: Any) -> str:
        """Normalize multimodal/structured model payloads into plain text."""
        if isinstance(content, str):
            return content

        if isinstance(content, dict):
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text
            parts = content.get("parts")
            if isinstance(parts, list):
                normalized = "\n".join(
                    self._normalize_content(part) for part in parts if self._normalize_content(part).strip()
                )
                if normalized.strip():
                    return normalized
            return str(content)

        if isinstance(content, list):
            normalized_parts: list[str] = []
            for part in content:
                normalized = self._normalize_content(part)
                if normalized.strip():
                    normalized_parts.append(normalized)
            if normalized_parts:
                return "\n".join(normalized_parts)
            return ""

        return str(content)
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> str:
        llm = self._get_llm()
        lc_messages = []
        
        if system_prompt:
            lc_messages.append(SystemMessage(content=system_prompt))
        
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
        
        response = await llm.ainvoke(lc_messages)
        return self._normalize_content(response.content)
    
    async def generate(self, prompt: str) -> str:
        """Standard text generation."""
        llm = self._get_llm()
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return self._normalize_content(response.content)

    async def generate_structured(self, prompt: str, response_model: Type[T]) -> T:
        """
        Generates a structured response mapped to a Pydantic model.
        Fixes the AttributeError in agent nodes by using LangChain's native parser.
        """
        llm = self._get_llm()
        # .with_structured_output handles the JSON schema conversion automatically
        structured_llm = llm.with_structured_output(response_model)
        
        response = await structured_llm.ainvoke([HumanMessage(content=prompt)])
        
        return response

# Singleton instance
gemini_client = GeminiClient()