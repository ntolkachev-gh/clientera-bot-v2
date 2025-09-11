#!/usr/bin/env python3
"""
Pydantic models for OpenAI Realtime API events.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Realtime API event types."""
    # Session events
    SESSION_UPDATE = "session.update"
    SESSION_UPDATED = "session.updated"
    
    # Conversation events
    CONVERSATION_ITEM_CREATE = "conversation.item.create"
    CONVERSATION_ITEM_CREATED = "conversation.item.created"
    CONVERSATION_ITEM_DELETE = "conversation.item.delete"
    CONVERSATION_ITEM_DELETED = "conversation.item.deleted"
    
    # Response events
    RESPONSE_CREATE = "response.create"
    RESPONSE_CREATED = "response.created"
    RESPONSE_DONE = "response.done"
    RESPONSE_CANCEL = "response.cancel"
    RESPONSE_CANCELLED = "response.cancelled"
    
    # Response output events
    RESPONSE_OUTPUT_ITEM_ADDED = "response.output_item.added"
    RESPONSE_OUTPUT_ITEM_DONE = "response.output_item.done"
    
    # Response content events
    RESPONSE_CONTENT_PART_ADDED = "response.content_part.added"
    RESPONSE_CONTENT_PART_DONE = "response.content_part.done"
    
    # Text delta events
    RESPONSE_TEXT_DELTA = "response.text.delta"
    RESPONSE_TEXT_DONE = "response.text.done"
    
    # Function calling events
    RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA = "response.function_call_arguments.delta"
    RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE = "response.function_call_arguments.done"
    
    # Error events
    ERROR = "error"


class ContentType(str, Enum):
    """Content types."""
    INPUT_TEXT = "input_text"
    INPUT_AUDIO = "input_audio"
    TEXT = "text"
    AUDIO = "audio"
    FUNCTION_CALL = "function_call"
    FUNCTION_CALL_OUTPUT = "function_call_output"


class Role(str, Enum):
    """Message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# Base event model
class BaseEvent(BaseModel):
    """Base event model."""
    type: EventType
    event_id: Optional[str] = None


# Content models
class InputTextContent(BaseModel):
    """Input text content."""
    type: Literal[ContentType.INPUT_TEXT] = ContentType.INPUT_TEXT
    text: str


class TextContent(BaseModel):
    """Text content."""
    type: Literal[ContentType.TEXT] = ContentType.TEXT
    text: str


class FunctionCall(BaseModel):
    """Function call content."""
    type: Literal[ContentType.FUNCTION_CALL] = ContentType.FUNCTION_CALL
    name: str
    call_id: str
    arguments: str


class FunctionCallOutput(BaseModel):
    """Function call output content."""
    type: Literal[ContentType.FUNCTION_CALL_OUTPUT] = ContentType.FUNCTION_CALL_OUTPUT
    call_id: str
    output: str


ContentUnion = Union[InputTextContent, TextContent, FunctionCall, FunctionCallOutput]


# Item models
class ConversationItem(BaseModel):
    """Conversation item."""
    id: Optional[str] = None
    type: Literal["message", "function_call", "function_call_output"] = "message"
    status: Optional[Literal["completed", "in_progress", "incomplete"]] = None
    role: Role
    content: List[ContentUnion]


# Tool/Function models
class FunctionParameter(BaseModel):
    """Function parameter schema."""
    type: str
    description: Optional[str] = None
    enum: Optional[List[str]] = None
    items: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None
    required: Optional[List[str]] = None


class FunctionSchema(BaseModel):
    """Function schema for tools."""
    name: str
    description: str
    parameters: Dict[str, Any]


class Tool(BaseModel):
    """Tool definition for OpenAI Realtime API."""
    name: str
    type: Literal["function"] = "function"
    description: str
    parameters: Dict[str, Any]


# Session models
class SessionConfig(BaseModel):
    """Session configuration."""
    modalities: List[Literal["text", "audio"]] = ["text"]
    instructions: str = ""
    voice: Optional[Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]] = None
    input_audio_format: Optional[Literal["pcm16", "g711_ulaw", "g711_alaw"]] = None
    output_audio_format: Optional[Literal["pcm16", "g711_ulaw", "g711_alaw"]] = None
    input_audio_transcription: Optional[Dict[str, Any]] = None
    turn_detection: Optional[Dict[str, Any]] = None
    tools: List[Tool] = []
    tool_choice: Optional[Union[Literal["auto", "none"], Dict[str, Any]]] = "auto"
    temperature: float = 0.8
    max_response_output_tokens: Optional[int] = None


# Event models
class SessionUpdateEvent(BaseEvent):
    """Session update event."""
    type: Literal[EventType.SESSION_UPDATE] = EventType.SESSION_UPDATE
    session: SessionConfig


class ConversationItemCreateEvent(BaseEvent):
    """Conversation item create event."""
    type: Literal[EventType.CONVERSATION_ITEM_CREATE] = EventType.CONVERSATION_ITEM_CREATE
    previous_item_id: Optional[str] = None
    item: ConversationItem


class ResponseCreateEvent(BaseEvent):
    """Response create event."""
    type: Literal[EventType.RESPONSE_CREATE] = EventType.RESPONSE_CREATE
    response: Optional[Dict[str, Any]] = None


class ResponseCancelEvent(BaseEvent):
    """Response cancel event."""
    type: Literal[EventType.RESPONSE_CANCEL] = EventType.RESPONSE_CANCEL


# Incoming event models
class SessionUpdatedEvent(BaseEvent):
    """Session updated event."""
    type: Literal[EventType.SESSION_UPDATED] = EventType.SESSION_UPDATED
    session: SessionConfig


class ResponseCreatedEvent(BaseEvent):
    """Response created event."""
    type: Literal[EventType.RESPONSE_CREATED] = EventType.RESPONSE_CREATED
    response: Dict[str, Any]


class ResponseDoneEvent(BaseEvent):
    """Response done event."""
    type: Literal[EventType.RESPONSE_DONE] = EventType.RESPONSE_DONE
    response: Dict[str, Any]


class ResponseTextDeltaEvent(BaseEvent):
    """Response text delta event."""
    type: Literal[EventType.RESPONSE_TEXT_DELTA] = EventType.RESPONSE_TEXT_DELTA
    response_id: str
    item_id: str
    output_index: int
    content_index: int
    delta: str


class ResponseTextDoneEvent(BaseEvent):
    """Response text done event."""
    type: Literal[EventType.RESPONSE_TEXT_DONE] = EventType.RESPONSE_TEXT_DONE
    response_id: str
    item_id: str
    output_index: int
    content_index: int
    text: str


class ResponseFunctionCallArgumentsDeltaEvent(BaseEvent):
    """Function call arguments delta event."""
    type: Literal[EventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA] = EventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA
    response_id: str
    item_id: str
    output_index: int
    call_id: str
    delta: str


class ResponseFunctionCallArgumentsDoneEvent(BaseEvent):
    """Function call arguments done event."""
    type: Literal[EventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE] = EventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE
    response_id: str
    item_id: str
    output_index: int
    call_id: str
    name: str
    arguments: str


class ErrorEvent(BaseEvent):
    """Error event."""
    type: Literal[EventType.ERROR] = EventType.ERROR
    error: Dict[str, Any]


# Union of all incoming events
IncomingEvent = Union[
    SessionUpdatedEvent,
    ResponseCreatedEvent,
    ResponseDoneEvent,
    ResponseTextDeltaEvent,
    ResponseTextDoneEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    ErrorEvent,
]

# Union of all outgoing events
OutgoingEvent = Union[
    SessionUpdateEvent,
    ConversationItemCreateEvent,
    ResponseCreateEvent,
    ResponseCancelEvent,
]


# Stream controller models
class StreamState(str, Enum):
    """Stream state."""
    IDLE = "idle"
    STREAMING = "streaming"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class StreamController(BaseModel):
    """Stream controller for managing response streaming."""
    user_id: int
    message_id: Optional[int] = None
    response_id: Optional[str] = None
    state: StreamState = StreamState.IDLE
    accumulated_text: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True
