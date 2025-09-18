#!/usr/bin/env python3
"""
Environment configuration using pydantic BaseSettings.
"""

import os
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Telegram Bot
    TG_BOT_TOKEN: str = Field(..., description="Telegram bot token from @BotFather")
    TG_WEBHOOK_URL: Optional[str] = Field(None, description="Webhook URL for production")
    TG_WEBHOOK_PATH: str = Field("/webhook", description="Webhook path")
    TG_WEBHOOK_PORT: int = Field(8080, description="Webhook server port")
    
    # OpenAI Realtime API
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    REALTIME_MODEL: str = Field("gpt-4o-realtime-preview", description="Realtime model name")
    REALTIME_WS_URL: str = Field(
        "wss://api.openai.com/v1/realtime", 
        description="OpenAI Realtime WebSocket URL"
    )
    OPENAI_TEMPERATURE: float = Field(1.1, description="OpenAI model temperature (0.0-2.0)")
    
    # YCLIENTS (for future real integration)
    YC_PARTNER_TOKEN: Optional[str] = Field(None, description="YCLIENTS partner token")
    YC_USER_TOKEN: Optional[str] = Field(None, description="YCLIENTS user token")
    YC_BASE_URL: str = Field("https://api.yclients.com/api/v1", description="YCLIENTS API base URL")
    
    # YCLIENTS legacy naming support
    YCLIENTS_TOKEN: Optional[str] = Field(None, description="YCLIENTS token (legacy)")
    YCLIENTS_COMPANY_ID: Optional[int] = Field(None, description="YCLIENTS company ID")
    YCLIENTS_LOGIN: Optional[str] = Field(None, description="YCLIENTS login")
    YCLIENTS_PASSWORD: Optional[str] = Field(None, description="YCLIENTS password")
    
    # Application settings
    LOG_LEVEL: str = Field("INFO", description="Logging level")
    DEBUG: bool = Field(False, description="Debug mode")
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = Field(5, description="Max requests per window")
    RATE_LIMIT_WINDOW: int = Field(30, description="Rate limit window in seconds")
    
    # Streaming settings
    STREAM_THROTTLE_MS: int = Field(300, description="Throttle between message edits in ms")
    RESPONSE_TIMEOUT: int = Field(10, description="Timeout for first response delta in seconds")
    MAX_RESPONSE_LENGTH: int = Field(1500, description="Max response length in characters")
    
    # WebSocket settings
    WS_CONNECT_TIMEOUT: int = Field(15, description="WebSocket connection timeout")
    WS_PING_INTERVAL: int = Field(30, description="WebSocket ping interval")
    WS_PING_TIMEOUT: int = Field(15, description="WebSocket ping timeout")
    WS_MAX_RETRIES: int = Field(10, description="Max WebSocket reconnection attempts")
    
    # Connection pool settings
    WS_POOL_SIZE: int = Field(3, description="Number of WebSocket connections in pool")
    WS_MAX_USERS_PER_CONNECTION: int = Field(20, description="Max concurrent users per connection")
    WS_POOL_STRATEGY: str = Field("least_connections", description="Load balancing strategy")
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()
    
    @field_validator("TG_BOT_TOKEN")
    @classmethod
    def validate_bot_token(cls, v):
        """Validate bot token format."""
        if not v or ":" not in v:
            raise ValueError("Invalid bot token format")
        return v
    
    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_key(cls, v):
        """Validate OpenAI API key."""
        if not v or not v.startswith("sk-"):
            raise ValueError("Invalid OpenAI API key format")
        return v
    
    @field_validator("OPENAI_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v):
        """Validate OpenAI temperature value."""
        if not 0.0 <= v <= 2.0:
            raise ValueError("OPENAI_TEMPERATURE must be between 0.0 and 2.0")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # Разрешаем дополнительные поля
        
    def get_realtime_ws_url(self) -> str:
        """Get complete WebSocket URL with model parameter."""
        return f"{self.REALTIME_WS_URL}?model={self.REALTIME_MODEL}"
    
    def get_realtime_headers(self) -> dict:
        """Get WebSocket headers for OpenAI Realtime API."""
        return {
            "Authorization": f"Bearer {self.OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    
    def mask_sensitive_data(self) -> dict:
        """Get config dict with masked sensitive data for logging."""
        config = self.model_dump()
        
        # Mask sensitive fields
        sensitive_fields = [
            "TG_BOT_TOKEN", "OPENAI_API_KEY", 
            "YC_PARTNER_TOKEN", "YC_USER_TOKEN"
        ]
        
        for field in sensitive_fields:
            if config.get(field):
                config[field] = f"{config[field][:8]}***masked***"
        
        return config


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
