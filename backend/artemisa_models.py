"""
Artemisa — Modelos de datos (Python / Pydantic)

Estos modelos espejan 1:1 el schema de Supabase definido en
docs/ARTEMISA_03_DATOS.md. Los usa el servicio Python del pipeline
(Pasos 1-4) para validar lo que lee y escribe en la base de datos.

No modificar los nombres de campo sin actualizar
docs/ARTEMISA_03_DATOS.md, frontend/lib/types/artemisa-types.ts y las
migraciones de Supabase en simultáneo — deben quedar sincronizados
siempre.
"""

from __future__ import annotations

from datetime import datetime, time
from enum import Enum, IntEnum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================
# ENUMS
# ============================================================

class Classification(str, Enum):
    """
    Resultado del Paso 2b (Análisis) o Paso 3 (Razonamiento).
    Ver ARTEMISA_02_ARQUITECTURA.md secciones 4 y 5.
    """
    NORMAL = "normal"
    ATTENTION = "attention"
    EMERGENCY = "emergency"


class AlertLevel(IntEnum):
    """
    Los 4 niveles de acción, como entero — para badges/orden en UI.
    Ver ARTEMISA_03_DATOS.md sección 4 para el mapeo completo.
    """
    NIVEL_1 = 1  # Informar
    NIVEL_2 = 2  # Alertar
    NIVEL_3 = 3  # Contactar
    NIVEL_4 = 4  # Emergencia


class ActionLevel(str, Enum):
    """
    El nombre de la acción correspondiente a cada AlertLevel.
    Jerarquía de impacto: a mayor nivel, mayor certeza requerida
    antes de ejecutar. NUNCA saltar directo a EMERGENCIA sin pasar
    por el Paso 3 (razonamiento) primero.
    """
    INFORMAR = "informar"      # Nivel 1 — relevante, no urgente
    ALERTAR = "alertar"        # Nivel 2 — requiere atención ahora
    CONTACTAR = "contactar"    # Nivel 3 — mensaje/llamada a persona de confianza
    EMERGENCIA = "emergencia"  # Nivel 4 — 911 + contactos vía Twilio


class SpaceStatus(str, Enum):
    """Estado de conexión de una cámara/espacio."""
    ACTIVE = "active"
    OFFLINE = "offline"
    PENDING = "pending"  # recién agregado, esperando primer frame


class CameraType(str, Enum):
    """Protocolo de conexión de la cámara. Hoy solo RTSP en v1."""
    RTSP = "rtsp"


class ContactRelationship(str, Enum):
    SPOUSE_PARTNER = "spouse_partner"
    PARENT = "parent"
    SIBLING = "sibling"
    FRIEND = "friend"
    NEIGHBOR = "neighbor"
    OTHER = "other"


class HomeType(str, Enum):
    APARTMENT = "apartment"
    HOUSE = "house"
    SMALL_BUSINESS = "small_business"


class EventType(str, Enum):
    """Tipo de evento en activity_log — para agrupar/filtrar en UI."""
    THREAD_LOGGED = "thread_logged"
    DISPATCH_TRIGGERED = "dispatch_triggered"
    DISPATCH_CANCELLED = "dispatch_cancelled"
    SPACE_CONNECTED = "space_connected"
    SPACE_WENT_OFFLINE = "space_went_offline"
    SPACE_RECONNECTED = "space_reconnected"


class AlertSensitivity(str, Enum):
    """
    Afecta dos umbrales del pipeline: cuándo `attention` escala a
    Paso 3 (vía confidence), y el corte de severity_score entre
    Nivel 2 y Nivel 3. Ver ARTEMISA_03_DATOS.md sección 4.
    """
    LOW = "low"
    BALANCED = "balanced"
    HIGH = "high"


# ============================================================
# USERS
# ============================================================

class User(BaseModel):
    """
    Tabla: users
    custom_instructions se alimenta en dos momentos: onboarding
    y de forma continua vía las preguntas contextuales que Artemisa
    hace (ARTEMISA_02_ARQUITECTURA.md sección 8).
    """
    id: UUID
    email: str
    name: str
    timezone: str = "America/Argentina/Buenos_Aires"
    account_type: str = "beta"
    home_type: Optional[HomeType] = None
    area_type: Optional[str] = None
    has_children: bool = False
    custom_instructions: Optional[str] = Field(
        default=None,
        description="Texto libre acumulativo — la rutina del hogar "
                    "que Artemisa usa como contexto en el Paso 2b.",
    )
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    """Payload para crear un user durante el onboarding."""
    email: str
    name: str
    timezone: str = "America/Argentina/Buenos_Aires"
    home_type: Optional[HomeType] = None
    has_children: bool = False


# ============================================================
# SPACES (cámara + espacio, 1:1 en el MVP)
# ============================================================

class Space(BaseModel):
    """
    Tabla: spaces
    Un space = una cámara conectada. MVP: 1 usuario -> 1 space ->
    1 cámara. La cámara vive embebida acá (camera_url, camera_type),
    no como tabla separada — ver ARTEMISA_03_DATOS.md sección 1.

    camera_url NUNCA se expone al frontend. El tipo TS público es
    SpacePublic (sin este campo) — ver artemisa-types.ts.
    """
    id: UUID
    user_id: UUID
    name: str
    camera_url: str = Field(description="URL RTSP de la cámara — solo backend")
    camera_type: CameraType = CameraType.RTSP
    status: SpaceStatus = SpaceStatus.PENDING
    last_frame: Optional[datetime] = Field(
        default=None,
        description="Timestamp del último frame recibido — usado "
                    "para detectar cámaras offline.",
    )
    last_update: datetime


class SpaceCreate(BaseModel):
    user_id: UUID
    name: str
    camera_url: str
    camera_type: CameraType = CameraType.RTSP


class SpaceTestConnectionResult(BaseModel):
    """Respuesta del endpoint de test de conexión en Onboarding."""
    success: bool
    error_message: Optional[str] = None


# ============================================================
# LAYERS (Paso 2a — Descripción, puramente factual)
# ============================================================

class Layer(BaseModel):
    """
    Tabla: layers
    Una layer = una descripción de texto generada a partir de UN
    frame. El frame en sí NUNCA se persiste.

    SIN classification: Paso 2a solo describe, nunca clasifica.
    Ver ARTEMISA_03_DATOS.md sección 3 para el porqué (costo y
    coherencia de threads).

    IMPORTANTE: esta tabla no tiene, y nunca debe tener, ninguna
    columna de tipo blob/bytea para contenido de imagen o video.
    """
    id: UUID
    space_id: UUID
    description: str = Field(
        description="Descripción factual generada por GPT-4o mini. "
                    "Ver el prompt exacto en "
                    "ARTEMISA_02_ARQUITECTURA.md sección 3."
    )
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class LayerCreate(BaseModel):
    space_id: UUID
    description: str
    confidence: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================
# THREADS (Paso 2b análisis / Paso 3 razonamiento)
# ============================================================

class Thread(BaseModel):
    """
    Tabla: threads
    Un thread = varias layers agrupadas en una narrativa, con
    clasificación y acción resultante. Ver ARTEMISA_02_ARQUITECTURA.md
    secciones 4 y 5, y ARTEMISA_03_DATOS.md sección 4, para el detalle
    completo de cómo se genera cada campo.

    Un thread queda "abierto" (end_time=None) mientras sigan llegando
    layers del mismo espacio dentro de la ventana de continuidad.
    """
    id: UUID
    space_id: UUID
    layers: list[UUID] = Field(
        default_factory=list,
        description="IDs de los layers que componen este thread.",
    )
    narrative: str = Field(
        description="La narrativa humana del evento — esto es lo "
                    "que se muestra en Activity."
    )
    classification: Classification
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Certeza de la clasificación. attention con "
                    "confidence < 0.6 escala a Paso 3.",
    )
    severity_score: float = Field(
        ge=0.0, le=1.0,
        description="Gravedad SI la clasificación es correcta. "
                    "Decide Nivel 2 vs Nivel 3 dentro de attention. "
                    "Distinto de confidence.",
    )
    reasoning: str = Field(
        description="Por qué se llegó a esta clasificación, en voz "
                    "humana — alimenta 'Why this mattered' en la UI. "
                    "Nunca el reasoning técnico crudo de "
                    "EmergencyVerification (Paso 3). Nunca debe "
                    "sonar a log de sistema.",
    )
    alert_level: AlertLevel
    action: Optional[ActionLevel] = Field(
        default=None,
        description="None si classification=normal implica "
                    "alert_level 1 (informar). Ver resolve_action_level().",
    )
    start_time: datetime
    end_time: Optional[datetime] = Field(
        default=None,
        description="None mientras el thread sigue abierto "
                    "(acumulando layers dentro de la ventana de "
                    "continuidad).",
    )
    escalated_to_reasoning: bool = Field(
        default=False,
        description="True si este thread pasó por el Paso 3 "
                    "(razonamiento profundo) antes de esta "
                    "clasificación final.",
    )


class ThreadCreate(BaseModel):
    """
    Payload que arma el Paso 2b (análisis) al cerrar un batch de
    layers. Este es el shape esperado como output estructurado del
    modelo de Groq.
    """
    space_id: UUID
    layers: list[UUID] = Field(default_factory=list)
    narrative: str
    classification: Classification
    confidence: float
    severity_score: float
    reasoning: str
    start_time: datetime
    end_time: Optional[datetime] = None


class EmergencyVerification(BaseModel):
    """
    Output del Paso 3 (GPT-4.1 mini). Se ejecuta cuando
    classification == emergency (siempre) o attention con
    confidence < 0.6.

    reasoning acá es INTERNO — nunca se muestra tal cual en la UI.
    Cuando Paso 3 corre, el pipeline debe reescribir Thread.reasoning
    en voz humana con la síntesis del resultado, no volcar este campo
    directo.
    """
    severity_high: bool
    reasoning: str = Field(description="Solo para logs internos — NUNCA en UI.")
    confidence: float = Field(ge=0.0, le=1.0)


ATTENTION_CONTACT_THRESHOLD = 0.7
"""
Punto de corte de severity_score entre Nivel 2 (alertar) y Nivel 3
(contactar) dentro de classification=attention. Punto de partida —
ajustar con datos reales de la beta y con alert_sensitivity.
"""


def resolve_action_level(
    classification: Classification,
    severity_score: float,
    severity_high: Optional[bool] = None,
) -> tuple[AlertLevel, ActionLevel]:
    """
    Mapeo determinístico classification -> (alert_level, action),
    según ARTEMISA_03_DATOS.md sección 4.

    `severity_high` lo decide el Paso 3 (EmergencyVerification) y
    solo es relevante (no debe ser None) cuando classification ==
    EMERGENCY, que SIEMPRE escala a Paso 3 antes de llamar a esta
    función.

    normal     -> (NIVEL_1, informar)
    attention  -> severity_score < 0.7  -> (NIVEL_2, alertar)
               -> severity_score >= 0.7 -> (NIVEL_3, contactar)
    emergency  -> severity_high True    -> (NIVEL_4, emergencia)
               -> severity_high False   -> (NIVEL_3, contactar) [degradado]

    Regla de oro (ARTEMISA_01_PRODUCTO.md #5): nunca ejecutar un
    Nivel 4 con evidencia de Nivel 2. EMERGENCIA solo se alcanza si
    classification == EMERGENCY Y el Paso 3 confirmó severity_high.
    """
    if classification == Classification.NORMAL:
        return AlertLevel.NIVEL_1, ActionLevel.INFORMAR

    if classification == Classification.ATTENTION:
        if severity_score >= ATTENTION_CONTACT_THRESHOLD:
            return AlertLevel.NIVEL_3, ActionLevel.CONTACTAR
        return AlertLevel.NIVEL_2, ActionLevel.ALERTAR

    if classification == Classification.EMERGENCY:
        if severity_high:
            return AlertLevel.NIVEL_4, ActionLevel.EMERGENCIA
        return AlertLevel.NIVEL_3, ActionLevel.CONTACTAR

    raise ValueError(f"Clasificación desconocida: {classification}")


# ============================================================
# EMERGENCY CONTACTS
# ============================================================

class EmergencyContact(BaseModel):
    """Tabla: emergency_contacts"""
    id: UUID
    user_id: UUID
    name: str
    phone: str = Field(description="Formato E.164, ej. +5491122334455")
    relationship: ContactRelationship
    priority: int = Field(
        ge=1,
        description="Orden de llamado. 1 = primero. 911 siempre "
                    "antecede a esta lista, no es una fila acá.",
    )
    confirmed: bool = Field(
        default=False,
        description="True solo después de que el contacto confirmó "
                    "(vía Twilio) que acepta ser contactado en una "
                    "emergencia. Un contacto no confirmado no se llama.",
    )


class EmergencyContactCreate(BaseModel):
    user_id: UUID
    name: str
    phone: str
    relationship: ContactRelationship
    priority: int = 1


# ============================================================
# USER PREFERENCES
# ============================================================

class UserPreferences(BaseModel):
    """
    Tabla: user_preferences
    alert_sensitivity y do_not_disturb_* corresponden a "What's
    worth an alert" y "Quiet hours" en Settings.
    """
    id: UUID
    user_id: UUID
    alert_sensitivity: AlertSensitivity = AlertSensitivity.BALANCED
    cancel_timer_seconds: int = Field(
        default=30,
        description="Ventana de cancelación antes del dispatch "
                    "de Nivel 4 (emergencia).",
    )
    contact_cancel_timer_seconds: int = Field(
        default=90,
        description="Ventana de cancelación antes del dispatch "
                    "de Nivel 3 (contactar) — más larga que la de "
                    "Nivel 4 porque Nivel 3 no pasa por Paso 3.",
    )
    auto_call_enabled: bool = True
    do_not_disturb_start: Optional[time] = None
    do_not_disturb_end: Optional[time] = None


class UserPreferencesUpdate(BaseModel):
    alert_sensitivity: Optional[AlertSensitivity] = None
    cancel_timer_seconds: Optional[int] = None
    contact_cancel_timer_seconds: Optional[int] = None
    auto_call_enabled: Optional[bool] = None
    do_not_disturb_start: Optional[time] = None
    do_not_disturb_end: Optional[time] = None


# ============================================================
# CONVERSATIONS (Chat / Natural Interaction)
# ============================================================

class ChatMessage(BaseModel):
    """Un mensaje individual dentro de conversations.messages (JSONB)."""
    role: str = Field(description="'user' o 'assistant'")
    content: str
    timestamp: datetime


class Conversation(BaseModel):
    """Tabla: conversations"""
    id: UUID
    user_id: UUID
    messages: list[ChatMessage] = Field(default_factory=list)
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Contexto reciente inyectado en cada respuesta "
                    "(threads recientes, etc.) — no es historial de "
                    "chat, es contexto de estado del hogar.",
    )


# ============================================================
# ACTIVITY LOG
# ============================================================

class ActivityLogEntry(BaseModel):
    """
    Tabla: activity_log
    Registro de eventos para el feed de Activity / Living Memory.
    Distinto de `threads`: un thread es la unidad de análisis de
    IA, un activity_log entry es la unidad de presentación en UI
    (puede incluir eventos que no vienen de un thread, ej. "cámara
    reconectada").
    """
    id: UUID
    user_id: UUID
    thread_id: Optional[UUID] = None
    event_type: EventType
    title: str
    description: str
    location: Optional[str] = Field(
        default=None, description="Nombre del space, ej. 'living room'"
    )
    image_url: Optional[str] = Field(
        default=None,
        description="SOLO para imágenes subidas explícitamente por "
                    "el usuario (ej. 'Attach' en el chat, foto de "
                    "referencia del perro). NUNCA un frame de "
                    "cámara.",
    )
    timestamp: datetime


# ============================================================
# DISPATCH LOGS (Paso 4 — auditoría de Twilio)
# ============================================================

class DispatchLog(BaseModel):
    """
    Tabla: dispatch_logs
    Auditoría de cada llamada/mensaje individual de Twilio durante
    un dispatch de Nivel 3 o 4. Un thread puede generar varias filas
    en secuencia (ej: call_user -> call_contacts -> call_911).

    Retención: 5 años (relevancia legal ante reclamos — ver
    ARTEMISA_02_ARQUITECTURA.md sección 6, nota legal pendiente).
    """
    id: UUID
    thread_id: UUID
    user_id: UUID
    action: str = Field(
        description="'call_user' | 'call_contacts' | 'call_911'"
    )
    twilio_sid: str
    status: str = Field(
        description="Espejo del status de Twilio, más 'cancelled' "
                    "si el usuario canceló dentro de la ventana."
    )
    created_at: datetime
