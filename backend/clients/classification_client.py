"""
Paso 2b — Cliente de clasificación (Groq Llama).

SOLO recibe texto (las descripciones de layers ya generadas en Paso 2a).
Nunca imágenes — ver backend/CLAUDE.md, regla absoluta #2.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError

from config import Settings
from clients.base import NotConfiguredError

CLASSIFICATION_PROMPT_TEMPLATE = (
    "Sos el sistema de inteligencia de Artemisa. Analizá estos eventos recientes\n"
    "del espacio {space_name} y determiná si requieren atención.\n\n"
    "Eventos: {layers}\n"
    "Rutina normal del hogar: {custom_instructions}\n"
    "Resumen de threads recientes de este espacio: {recent_threads_summary}\n"
    "Estado de otros espacios: {other_spaces_state}\n"
    "Horario: {current_time}, {day_of_week}\n\n"
    "Clasificá como: normal | attention | emergency\n"
    "Asigná confidence (0-1) y severity_score (0-1) por separado.\n"
    "Generá una narrativa y un reasoning en español, en voz humana —\n"
    "nunca como log de sistema.\n\n"
    'Respondé SOLO con JSON: {{"narrative": str, "classification": str, '
    '"confidence": float, "severity_score": float, "reasoning": str}}'
)

# Groq escala de 8B a 70B cuando el batch es ambiguo, toca custom_instructions,
# o es horario nocturno — ver pipeline/step2b_classification.py, que decide
# esto con chequeos baratos (no-LLM) ANTES de llamar acá.
MODEL_SMALL = "llama-3.1-8b-instant"
MODEL_LARGE = "llama-3.3-70b-versatile"


class ClassificationResult(BaseModel):
    narrative: str
    classification: str
    confidence: float
    severity_score: float
    reasoning: str


class ClassificationClient:
    def __init__(self, settings: Settings):
        self._settings = settings

    def classify(
        self,
        *,
        space_name: str,
        layer_descriptions: list[str],
        custom_instructions: str,
        recent_threads_summary: str,
        other_spaces_state: str,
        use_large_model: bool,
        now: datetime | None = None,
    ) -> ClassificationResult:
        if not self._settings.has_groq:
            raise NotConfiguredError("Groq (clasificación, Paso 2b)", "GROQ_API_KEY")

        from groq import Groq

        client = Groq(api_key=self._settings.groq_api_key)
        now = now or datetime.now(timezone.utc)
        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
            space_name=space_name,
            layers="; ".join(layer_descriptions),
            custom_instructions=custom_instructions or "sin instrucciones particulares",
            recent_threads_summary=recent_threads_summary or "sin actividad reciente",
            other_spaces_state=other_spaces_state or "sin información",
            current_time=now.strftime("%H:%M"),
            day_of_week=now.strftime("%A"),
        )

        response = client.chat.completions.create(
            model=MODEL_LARGE if use_large_model else MODEL_SMALL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            return ClassificationResult.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"Groq devolvió un JSON inválido para clasificación: {raw!r}") from exc
