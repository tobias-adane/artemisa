"""
Paso 3 — Verificación de emergencia (OpenAI GPT-4.1 mini).

Se ejecuta SIEMPRE que classification == emergency, y también cuando
attention tiene confidence < 0.6. Nunca decide Nivel 4 por sí solo — el
resultado (severity_high) alimenta resolve_action_level() en
artemisa_models.py, que es la única función autorizada a fijar
alert_level/action.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from config import Settings
from clients.base import NotConfiguredError
from artemisa_models import EmergencyVerification

VERIFICATION_PROMPT_TEMPLATE = (
    "Verificá si la siguiente situación detectada en {space_name} es realmente\n"
    "una emergencia que requiere contactar servicios de emergencia.\n\n"
    "Thread: {narrative}\n"
    "Layers de soporte: {layer_descriptions}\n"
    "Historial del espacio: {recent_activity}\n\n"
    "Respondé con severity_high: true SOLO si estás altamente confiado\n"
    "de que hay una emergencia real. En caso de duda, severity_high: false.\n"
    "Este reasoning es interno — no se muestra en la UI tal cual.\n\n"
    'Respondé SOLO con JSON: {{"severity_high": bool, "reasoning": str, "confidence": float}}'
)


class VerificationClient:
    def __init__(self, settings: Settings):
        self._settings = settings

    def verify(
        self,
        *,
        space_name: str,
        narrative: str,
        layer_descriptions: list[str],
        recent_activity: str,
    ) -> EmergencyVerification:
        if not self._settings.has_openai:
            raise NotConfiguredError("OpenAI (verificación de emergencia, Paso 3)", "OPENAI_API_KEY")

        from openai import OpenAI

        client = OpenAI(api_key=self._settings.openai_api_key)
        prompt = VERIFICATION_PROMPT_TEMPLATE.format(
            space_name=space_name,
            narrative=narrative,
            layer_descriptions="; ".join(layer_descriptions),
            recent_activity=recent_activity or "sin antecedentes recientes",
        )

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            return EmergencyVerification.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"OpenAI devolvió un JSON inválido para verificación: {raw!r}") from exc
