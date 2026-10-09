"""
Production-grade metrics collection using Prometheus.
Tracks clinical API performance, AI agent latency, and RAG relevancy.
"""

import logging
from datetime import datetime
from typing import Dict
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# --- Clinical API Metrics ---
# Tracks total volume and status of medical requests
REQUEST_COUNT = Counter(
    'medical_api_requests_total', 
    'Total count of clinical API requests', 
    ['method', 'endpoint', 'status']
)

# Measures API latency to ensure fast responses for rural healthcare users
REQUEST_LATENCY = Histogram(
    'medical_api_latency_seconds', 
    'Latency of clinical API calls in seconds', 
    ['endpoint']
)

# --- AI & Agentic Workflow Metrics ---
# Monitors the confidence of AI diagnoses across sessions
AI_CONFIDENCE_SCORE = Gauge(
    'diagnosis_confidence_score', 
    'Confidence score of the latest AI diagnosis',
    ['session_id']
)

# Tracks time spent in specific LangGraph nodes (e.g., triage, diagnostician)
AGENT_STEP_DURATION = Histogram(
    'agent_workflow_step_seconds', 
    'Time spent in each node of the LangGraph workflow', 
    ['node_name']
)

# --- RAG & Feature Usage Metrics ---
FEATURE_USAGE = Counter(
    'feature_usage_total',
    'Total executions of specific application features',
    ['feature_name']
)

VECTOR_SEARCH_RELEVANCY = Histogram(
    'vector_search_top_score', 
    'Relevancy score of the top medical document retrieved'
)

class MetricsManager:
    """Utility class to record application performance and clinical outcomes."""
    
    @staticmethod
    def record_request(method: str, endpoint: str, status: int):
        """Increments the total request counter with metadata."""
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()

    @staticmethod
    def track_latency(endpoint: str):
        """Returns a context manager to measure the duration of a code block."""
        return REQUEST_LATENCY.labels(endpoint=endpoint).time()

    @staticmethod
    def record_feature_usage(feature: str):
        """Tracks usage of core features like RAG, voice, or vision analysis."""
        FEATURE_USAGE.labels(feature_name=feature).inc()

    @staticmethod
    def record_agent_step(node_name: str, duration: float):
        """Logs the time taken for an AI agent to complete a specific task."""
        AGENT_STEP_DURATION.labels(node_name=node_name).observe(duration)

    @staticmethod
    def record_diagnosis_confidence(session_id: str, score: float):
        """Updates the current confidence gauge for a diagnostic session."""
        AI_CONFIDENCE_SCORE.labels(session_id=session_id).set(score)

# Global manager instance
metrics = MetricsManager()