"""
Paso 2b — Clasificación de Thread (Groq).

Contiene la lógica de continuidad de threads y la decisión de qué
modelo de Groq usar — ambas deliberadamente SIN LLM (chequeos baratos),
per backend/CLAUDE.md: "chequeo de keywords/embedding barato ANTES de
decidir escalar, no una decisión del modelo chico".
"""

from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from artemisa_models import AlertLevel, ActionLevel, Classification, ThreadCreate, resolve_action_level
from clients.classification_client import ClassificationClient
from clients.store import Store

NIGHT_START = time(23, 0)
NIGHT_END = time(6, 0)

# Umbral de confidence de Paso 2b bajo el cual `attention` escala a Paso 3
# (verificación) en vez de resolverse directo — ver backend/CLAUDE.md Paso 3.
ATTENTION_ESCALATION_CONFIDENCE = 0.6


def is_night_hours(now: datetime, *, start: time = NIGHT_START, end: time = NIGHT_END) -> bool:
    t = now.time()
    if start <= end:
        return start <= t <= end
    return t >= start or t <= end  # ventana que cruza medianoche (23:00-06:00)


def mentions_custom_instructions(layer_descriptions: list[str], custom_instructions: str) -> bool:
    """
    Chequeo barato de keywords: ¿alguna palabra significativa de
    custom_instructions aparece en las descripciones del batch? Esto
    decide si escalar a Llama 70B, sin gastar una llamada de embeddings
    ni dejarle la decisión al modelo chico.
    """
    if not custom_instructions:
        return False
    stopwords = {"el", "la", "los", "las", "un", "una", "de", "del", "en", "a", "y", "o", "que", "no", "se", "su"}
    keywords = {w.strip(".,").lower() for w in custom_instructions.split() if len(w) > 3 and w.lower() not in stopwords}
    text = " ".join(layer_descriptions).lower()
    return any(k in text for k in keywords)


def descriptions_are_ambiguous(layer_descriptions: list[str]) -> bool:
    """
    Heurística barata de "contradictorio/ambiguo": layers del mismo
    batch que mencionan estados opuestos (alguien entra Y alguien sale,
    puerta abierta Y cerrada, etc.) en la misma ventana.
    """
    text = " ".join(layer_descriptions).lower()
    opposite_pairs = [
        ("entr", "sal"),
        ("abr", "cerr"),
        ("lleg", "se fue"),
        ("prende", "apaga"),
    ]
    return any(a in text and b in text for a, b in opposite_pairs)


def should_use_large_model(
    *,
    layer_descriptions: list[str],
    custom_instructions: str,
    now: datetime,
) -> bool:
    return (
        descriptions_are_ambiguous(layer_descriptions)
        or mentions_custom_instructions(layer_descriptions, custom_instructions)
        or is_night_hours(now)
    )


def summarize_recent_threads(threads) -> str:
    """One-liner por thread reciente — nunca la narrativa completa (ver backend/CLAUDE.md)."""
    if not threads:
        return ""
    return "; ".join(f"{t.classification.value}: {t.narrative[:60]}" for t in threads)


def run_step2b(
    *,
    store: Store,
    classification_client: ClassificationClient,
    space_id: UUID,
    layer_ids: list[UUID],
    layer_descriptions: list[str],
    space_name: str,
    custom_instructions: str,
    other_spaces_state: str,
    now: datetime,
):
    """
    Corre la clasificación para un batch de layers ya cerrado y
    persiste el thread (nuevo o extendido). Devuelve el Thread
    resultante. `alert_level`/`action` quedan resueltos YA si la
    clasificación no requiere Paso 3; si requiere Paso 3
    (emergency, o attention con confidence baja), quedan en su valor
    "provisorio" (Nivel 2/3 degradado) hasta que step3_verification
    los reescriba — el llamador (orchestrator) es responsable de
    invocar Paso 3 cuando corresponda.
    """
    existing = store.get_open_thread(space_id, now=now)
    recent = store.recent_threads_for_space(space_id, limit=5)

    result = classification_client.classify(
        space_name=space_name,
        layer_descriptions=layer_descriptions,
        custom_instructions=custom_instructions,
        recent_threads_summary=summarize_recent_threads(recent),
        other_spaces_state=other_spaces_state,
        use_large_model=should_use_large_model(
            layer_descriptions=layer_descriptions, custom_instructions=custom_instructions, now=now
        ),
        now=now,
    )
    classification = Classification(result.classification)

    needs_step3 = classification == Classification.EMERGENCY or (
        classification == Classification.ATTENTION and result.confidence < ATTENTION_ESCALATION_CONFIDENCE
    )

    if needs_step3:
        # Nivel provisorio: nunca Nivel 4 sin que Paso 3 lo confirme.
        alert_level, action = resolve_action_level(classification, result.severity_score, severity_high=False)
    else:
        alert_level, action = resolve_action_level(classification, result.severity_score)

    if existing is not None:
        thread = store.extend_thread(existing.id, new_layer_ids=layer_ids, narrative=result.narrative)
    else:
        thread = store.create_thread(
            ThreadCreate(
                space_id=space_id,
                layers=layer_ids,
                narrative=result.narrative,
                classification=classification,
                confidence=result.confidence,
                severity_score=result.severity_score,
                reasoning=result.reasoning,
                start_time=now,
                end_time=None,
            ),
            alert_level=alert_level,
            action=action,
        )

    return thread, needs_step3
