"""
LangSmith monitoring integration.
Refined for better error handling and singleton management.
"""

import os
import logging
from typing import Optional, Any, Dict
from langsmith import Client
from app.core.config import settings

# Standard logger - will be captured by your structured logging setup
logger = logging.getLogger(__name__)

class MonitoringService:
    def __init__(self):
        # Configuration check
        self.enabled = getattr(settings, "LANGCHAIN_TRACING_V2", False)
        self.api_key = getattr(settings, "LANGCHAIN_API_KEY", None)
        self.client: Optional[Client] = None
        
        if self.enabled and self.api_key:
            try:
                self.client = Client(
                    api_key=self.api_key,
                    api_url="https://api.smith.langchain.com"
                )
                logger.info("LangSmith monitoring initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize LangSmith client: {str(e)}")
                self.enabled = False
        else:
            logger.info("LangSmith monitoring is currently disabled in settings")
    
    def log_agent_run(
        self,
        run_name: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        if not self.enabled or not self.client:
            return
        
        try:
            self.client.create_run(
                name=run_name,
                inputs=inputs,
                outputs=outputs,
                run_type="chain",
                extra=metadata or {}
            )
        except Exception as e:
            logger.error(f"LangSmith execution logging failed: {str(e)}")
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        if not self.enabled or not self.client:
            return
        
        try:
            error_msg = str(error)
            self.client.create_run(
                name="agent_error_trace",
                inputs=context or {},
                outputs={"error_detail": error_msg},
                run_type="chain",
                error=error_msg
            )
        except Exception as e:
            logger.error(f"LangSmith error reporting failed: {str(e)}")

monitoring = MonitoringService()