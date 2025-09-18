#!/usr/bin/env python3
"""
Structured logging configuration with PII masking.
"""

import logging
import re
import sys
from typing import Any, Dict

import structlog

from ..config.env import get_settings

settings = get_settings()


class TLSErrorFilter(logging.Filter):
    """Filter to suppress TLS handshake errors from aiohttp."""

    def filter(self, record):
        """Filter out TLS-related error messages."""
        message = record.getMessage()
        if "Invalid method encountered" in message:
            return False
        if "BadStatusLine" in message:
            return False
        if "SSL handshake failed" in message:
            return False
        if "TLS handshake timeout" in message:
            return False
        return True

def mask_sensitive_data(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Mask sensitive data in log messages."""
    if "event" in event_dict:
        message = str(event_dict["event"])
        
        # Mask phone numbers
        message = re.sub(
            r'\+7\d{10}',
            lambda m: f"+7{m.group(0)[2:5]}***{m.group(0)[-2:]}",
            message
        )
        
        # Mask email addresses
        message = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            lambda m: f"{m.group(0)[:3]}***@{m.group(0).split('@')[1]}",
            message
        )
        
        # Mask tokens (keep first 8 chars)
        message = re.sub(
            r'\b(?:sk-|bot)[A-Za-z0-9_-]{20,}\b',
            lambda m: f"{m.group(0)[:8]}***masked***",
            message
        )
        
        # Mask names (keep first letter)
        message = re.sub(
            r'\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\b',
            lambda m: f"{m.group(0)[0]}*** {m.group(0).split()[1][0]}***",
            message
        )
        
        event_dict["event"] = message
    
    return event_dict


def configure_logging() -> None:
    """Configure structured logging."""
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="ISO"),
            mask_sensitive_data,
            structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL),
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    
    # Apply TLS error filter to aiohttp loggers
    tls_filter = TLSErrorFilter()
    aiohttp_logger = logging.getLogger('aiohttp.server')
    aiohttp_logger.addFilter(tls_filter)
    aiohttp_access_logger = logging.getLogger('aiohttp.access')
    aiohttp_access_logger.addFilter(tls_filter)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get structured logger instance."""
    return structlog.get_logger(name)


# Configure logging on import
configure_logging()
