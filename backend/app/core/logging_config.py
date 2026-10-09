"""
Structured JSON logging configuration for the Rural AI Doctor backend.
"""

import logging
import sys
from pathlib import Path
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with standardized field names for log aggregation."""
    
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Standardize fields for easier searching in logs
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['timestamp'] = self.formatTime(record, self.datefmt)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure the root logger
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # Clear any existing handlers to avoid duplicate logs during hot-reloads
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    
    # Use a consistent format string for the JSON formatter
    log_format = '%(timestamp)s %(level)s %(name)s %(message)s'
    formatter = CustomJsonFormatter(log_format)
    
    # Console Handler (Standard Output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    #  General Application File Handler
    file_handler = logging.FileHandler(log_dir / "app.log", encoding='utf-8')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    #  Dedicated Error File Handler
    error_handler = logging.FileHandler(log_dir / "error.log", encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # Suppress noisy external library loggers
    for library in ["httpx", "httpcore", "urllib3", "openai", "python_multipart", "onnxruntime"]:
        logging.getLogger(library).setLevel(logging.WARNING)
    
    logger.info(f"Structured logging initialized at level: {log_level}")
    return root_logger


logger = logging.getLogger(__name__)