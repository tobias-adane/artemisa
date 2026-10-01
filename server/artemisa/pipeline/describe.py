"""Paso 2a: descripción, en la API (03-ALGORITMO.md, Paso 2a).

Convierte el frame en una oración factual y el frame deja de existir. En el
paso 5 solo actualiza el estado del space: los layers y threads llegan con la
sesionización (paso 6) y el aviso al worker con el paso 7.
"""

import asyncio
import base64
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from artemisa.core.costs import Executor
from artemisa.core.models import PipelineStep
from artemisa.core.schemas import DescribeOut
from artemisa.pipeline.motion import FrameKind, InboxFrame
from artemisa.providers.gateway import Completion, ModelCallFailed, RunContext

DESCRIBE_RETRIES = 2
RETRY_WAIT_S = 1.0  # espera corta entre intentos

PROMPTS = Path(__file__).resolve().parents[1] / "core" / "prompts"
SYSTEM_PROMPT = (PROMPTS / "describe.system.txt").read_text(encoding="utf-8").strip()
USER_PROMPT = (PROMPTS / "describe.user.txt").read_text(encoding="utf-8").strip()

# 04-MODELOS.md, Prompts: users.locale → {language}.
LANGUAGES = {"en": "English", "es-AR": "Argentine Spanish"}

log = logging.getLogger(__name__)


class Models(Protocol):
    """Lo que el Paso 2a usa del gateway (providers/gateway.py)."""

    async def complete[T: BaseModel](
        self,
        role: str,
        messages: list[ChatCompletionMessageParam],
        schema: type[T],
        context: RunContext,
    ) -> Completion[T]: ...


@dataclass(frozen=True)
class SpaceInfo:
    id: UUID
    user_id: str
    bridge_id: UUID | None
    name: str
    motion_threshold: float
    locale: str
    timezone: str


def messages_for(
    space: SpaceInfo, jpeg: bytes, captured_at: datetime, detail: str | None
) -> list[ChatCompletionMessageParam]:
    """El prompt de describe tal cual, con la imagen en memoria (data URL)."""
    local = captured_at.astimezone(ZoneInfo(space.timezone))
    text = USER_PROMPT.replace("{space_name}", space.name).replace(
        "{hh:mm}", local.strftime("%H:%M")
    )
    image: dict[str, Any] = {"url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()}
    if detail is not None:
        image["detail"] = detail
    user: Any = {
        "role": "user",
        "content": [{"type": "text", "text": text}, {"type": "image_url", "image_url": image}],
    }
    system = SYSTEM_PROMPT.replace("{language}", LANGUAGES[space.locale])
    return [{"role": "system", "content": system}, user]


async def describe(
    models: Models,
    space: SpaceInfo,
    kind: FrameKind,
    jpeg: bytes,
    captured_at: datetime,
    detail: str | None,
) -> DescribeOut | None:
    """Hasta 1 + DESCRIBE_RETRIES intentos, solo si la llamada falla o no valida.

    Cada intento (y cada fallback del gateway) queda en pipeline_runs.
    """
    step = PipelineStep.describe if kind == "motion" else PipelineStep.state
    context = RunContext(step=step, user_id=space.user_id, space_id=space.id)
    messages = messages_for(space, jpeg, captured_at, detail)
    try:
        for attempt in range(1 + DESCRIBE_RETRIES):
            try:
                return (await models.complete("describe", messages, DescribeOut, context)).output
            except ModelCallFailed:
                if attempt < DESCRIBE_RETRIES:
                    await asyncio.sleep(RETRY_WAIT_S)
        return None
    finally:
        del messages


async def on_frame(
    models: Models,
    db: Executor,
    space: SpaceInfo,
    kind: FrameKind,
    frame: InboxFrame,
    detail: str | None,
) -> None:
    """Describe y actualiza el estado del space. Si falla, el frame se pierde: no hay cola."""
    captured_at = frame.captured_at
    out = await describe(models, space, kind, frame.jpeg, captured_at, detail)
    del frame  # a partir de acá el frame no se usa más
    if out is None:
        log.warning("space %s: description failed, frame dropped", space.id)
        return
    await db.execute(
        """update spaces set state_description = $2, people_present = $3,
             state_updated_at = $4,
             last_motion_at = case when $5 then $4 else last_motion_at end
           where id = $1""",
        space.id,
        out.description,
        out.people_count > 0,
        captured_at,
        kind == "motion",
    )
    log.info("space %s: state updated (%s, people: %d)", space.id, kind, out.people_count)
