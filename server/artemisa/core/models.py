"""Enums espejo de los tipos de Postgres y filas que escribe el backend (05-DATOS.md)."""

from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

from artemisa.core.schemas import Classification
from artemisa.core.schemas import Flag as LayerFlag

__all__ = [
    "ActionLevel",
    "AlertSensitivity",
    "BridgeStatus",
    "Classification",
    "DispatchChannel",
    "DispatchStatus",
    "DispatchTarget",
    "HomeType",
    "LayerFlag",
    "MessageRole",
    "PipelineRun",
    "PipelineStep",
    "PushInterruption",
    "SpaceStatus",
    "ThreadStatus",
]


class ActionLevel(StrEnum):
    informar = "informar"
    alertar = "alertar"
    contactar = "contactar"
    emergencia = "emergencia"


class ThreadStatus(StrEnum):
    composing = "composing"
    active = "active"
    closed = "closed"


class SpaceStatus(StrEnum):
    pending = "pending"
    active = "active"
    offline = "offline"


class BridgeStatus(StrEnum):
    online = "online"
    offline = "offline"


class DispatchChannel(StrEnum):
    push = "push"
    call = "call"
    whatsapp = "whatsapp"
    sms = "sms"


class DispatchTarget(StrEnum):
    owner = "owner"
    contact = "contact"
    emergency_services = "emergency_services"


class DispatchStatus(StrEnum):
    queued = "queued"
    sent = "sent"
    delivered = "delivered"
    opened = "opened"
    answered = "answered"
    no_answer = "no_answer"
    failed = "failed"
    cancelled = "cancelled"


class PushInterruption(StrEnum):
    passive = "passive"
    time_sensitive = "time_sensitive"
    critical = "critical"


class AlertSensitivity(StrEnum):
    low = "low"
    balanced = "balanced"
    high = "high"


class HomeType(StrEnum):
    apartment = "apartment"
    house = "house"
    small_business = "small_business"


class PipelineStep(StrEnum):
    describe = "describe"
    state = "state"
    analyze = "analyze"
    reason = "reason"
    live_read = "live_read"
    chat = "chat"
    tts = "tts"


class MessageRole(StrEnum):
    user = "user"
    assistant = "assistant"


class PipelineRun(BaseModel):
    """Una fila de pipeline_runs. Solo métricas: nunca prompts, respuestas ni imágenes."""

    user_id: str | None = None
    space_id: UUID | None = None
    thread_id: UUID | None = None
    step: PipelineStep
    role: str
    provider: str
    model: str
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    visual_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    cost_usd: Decimal | None = None
    latency_ms: int | None = None
    ok: bool
    error: str | None = None
