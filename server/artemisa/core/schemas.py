"""Esquemas de salida de los modelos. Generado desde docs/04-MODELOS.md."""
from enum import Enum
from pydantic import BaseModel, Field

class Classification(str, Enum):
    normal = "normal"
    attention = "attention"
    emergency = "emergency"

class Flag(str, Enum):
    person_on_floor = "person_on_floor"
    smoke_or_fire = "smoke_or_fire"
    glass_broken = "glass_broken"
    door_forced = "door_forced"
    weapon_visible = "weapon_visible"
    water_leak = "water_leak"

class DescribeOut(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    flags: list[Flag] = []
    people_count: int = Field(ge=0, le=50)

class AnalysisOut(BaseModel):
    narrative: str = Field(min_length=1, max_length=240)
    classification: Classification
    confidence: float = Field(ge=0, le=1)
    reasoning: str = Field(min_length=1, max_length=500)
    escalate: bool
    escalate_reason: str | None = None
    people_present: bool | None = None
    unfamiliar_person: bool = False

class ReasoningOut(BaseModel):
    classification: Classification
    severity_high: bool
    reasoning: str = Field(min_length=1, max_length=500)
    narrative: str = Field(min_length=1, max_length=240)

class LiveReadOut(BaseModel):
    headline: str = Field(min_length=1, max_length=80)
    body: str = Field(min_length=1, max_length=400)
