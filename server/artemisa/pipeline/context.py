"""El contexto del Paso 2b y el prompt de analyze (03-ALGORITMO.md y 04-MODELOS.md).

Lee de la base lo que el modelo necesita y completa la plantilla de
core/prompts/analyze.user.txt sin cambiar su texto.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

CONTEXT_RECENT_THREADS = 5  # threads anteriores del space que ve el análisis

PROMPTS = Path(__file__).resolve().parents[1] / "core" / "prompts"
SYSTEM_PROMPT = (PROMPTS / "analyze.system.txt").read_text(encoding="utf-8").strip()
USER_PROMPT = (PROMPTS / "analyze.user.txt").read_text(encoding="utf-8").strip()

# 04-MODELOS.md, Prompts: users.locale → {language}.
LANGUAGES = {"en": "English", "es-AR": "Argentine Spanish"}


class Reader(Protocol):
    async def fetch(self, query: str, *args: object) -> list[Any]: ...
    async def fetchrow(self, query: str, *args: object) -> Any: ...


@dataclass(frozen=True)
class Layer:
    description: str
    flags: list[str]
    captured_at: datetime


@dataclass(frozen=True)
class OtherSpace:
    name: str
    state_description: str
    state_updated_at: datetime


@dataclass(frozen=True)
class EarlierThread:
    start_time: datetime
    classification: str
    narrative: str


@dataclass(frozen=True)
class AnalysisContext:
    now: datetime
    space_name: str
    locale: str
    timezone: str
    custom_instructions: str
    sensitivity: str
    night_start: time
    night_end: time
    layers: list[Layer]
    other_spaces: list[OtherSpace]
    earlier: list[EarlierThread]
    previous_narrative: str | None


async def build_analysis_context(
    db: Reader,
    thread_id: UUID,
    user_id: str,
    space_id: UUID,
    previous_narrative: str | None,
    now: datetime,
) -> AnalysisContext:
    home = await db.fetchrow(
        """select u.locale, u.timezone, u.custom_instructions, p.alert_sensitivity,
                  p.night_start, p.night_end, s.name as space_name
           from users u
           join user_preferences p on p.user_id = u.id
           join spaces s on s.user_id = u.id and s.id = $2
           where u.id = $1""",
        user_id,
        space_id,
    )
    if home is None:
        raise LookupError(f"no user, preferences or space for thread {thread_id}")
    layers = await db.fetch(
        """select description, flags::text[] as flags, captured_at from layers
           where thread_id = $1 order by captured_at""",
        thread_id,
    )
    others = await db.fetch(
        """select name, state_description, state_updated_at from spaces
           where user_id = $1 and id <> $2
             and state_description is not null and state_updated_at is not null
           order by name""",
        user_id,
        space_id,
    )
    zone = ZoneInfo(home["timezone"])
    midnight = now.astimezone(zone).replace(hour=0, minute=0, second=0, microsecond=0)
    earlier = await db.fetch(
        """select start_time, classification::text as classification, narrative from threads
           where space_id = $1 and id <> $2 and narrative is not null
             and start_time >= $3 and start_time < $4
           order by start_time desc limit $5""",
        space_id,
        thread_id,
        midnight,
        now,
        CONTEXT_RECENT_THREADS,
    )
    return AnalysisContext(
        now=now,
        space_name=home["space_name"],
        locale=home["locale"],
        timezone=home["timezone"],
        custom_instructions=home["custom_instructions"],
        sensitivity=home["alert_sensitivity"],
        night_start=home["night_start"],
        night_end=home["night_end"],
        layers=[Layer(r["description"], list(r["flags"]), r["captured_at"]) for r in layers],
        other_spaces=[
            OtherSpace(r["name"], r["state_description"], r["state_updated_at"]) for r in others
        ],
        earlier=[
            EarlierThread(r["start_time"], r["classification"], r["narrative"])
            for r in reversed(earlier)  # en orden de hora
        ],
        previous_narrative=previous_narrative,
    )


# El prompt


def render_system(ctx: AnalysisContext) -> str:
    return SYSTEM_PROMPT.replace("{sensitivity}", ctx.sensitivity).replace(
        "{language}", LANGUAGES[ctx.locale]
    )


def render_user(ctx: AnalysisContext) -> str:
    """Completa la plantilla. Una línea con "- " se repite por cada elemento de su lista.

    Una lista vacía deja la sección sin líneas.
    """
    zone = ZoneInfo(ctx.timezone)
    local = ctx.now.astimezone(zone)
    lists = {
        "- {space}:": [
            f"- {s.name}: {s.state_description} ({minutes_ago(s.state_updated_at, ctx.now)} min"
            " ago)"
            for s in ctx.other_spaces
        ],
        "- {time}": [
            f"- {t.start_time.astimezone(zone):%H:%M} [{t.classification}] {t.narrative}"
            for t in ctx.earlier
        ],
        "- {hh:mm:ss}": [
            f"- {layer.captured_at.astimezone(zone):%H:%M:%S} {layer.description}"
            + (f" [{', '.join(layer.flags)}]" if layer.flags else "")
            for layer in ctx.layers
        ],
    }
    values = {
        '{custom_instructions | "(nothing yet)"}': ctx.custom_instructions.strip()
        or "(nothing yet)",
        "{weekday}": f"{local:%A}",
        "{local_time}": f"{local:%H:%M}",
        "{timezone}": ctx.timezone,
        "{space_name}": ctx.space_name,
        '{previous_narrative | "(first look)"}': ctx.previous_narrative or "(first look)",
    }
    lines: list[str] = []
    for line in USER_PROMPT.splitlines():
        prefix = next((key for key in lists if line.startswith(key)), None)
        if prefix is not None:
            lines += lists[prefix]
            continue
        for key, value in values.items():
            line = line.replace(key, value)
        lines.append(line)
    return "\n".join(lines)


def minutes_ago(then: datetime, now: datetime) -> int:
    return max(0, int((now - then).total_seconds() // 60))


# Cuándo se usa analyze_hard


def is_night(ctx: AnalysisContext) -> bool:
    """De night_start a night_end del usuario, en su hora local. Puede cruzar medianoche."""
    clock = ctx.now.astimezone(ZoneInfo(ctx.timezone)).time()
    if ctx.night_start <= ctx.night_end:
        return ctx.night_start <= clock < ctx.night_end
    return clock >= ctx.night_start or clock < ctx.night_end


def words(text: str) -> set[str]:
    """Palabras de 4 letras o más, en minúsculas y sin acentos."""
    plain = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return {w for w in re.findall(r"[^\W\d_]+", plain) if len(w) >= 4}


def mentions_watched(ctx: AnalysisContext) -> bool:
    """Regla simple del laboratorio: alguna palabra de las custom instructions en un layer."""
    watched = words(ctx.custom_instructions)
    return any(watched & words(layer.description) for layer in ctx.layers)
