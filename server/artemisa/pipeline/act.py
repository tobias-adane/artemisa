"""Paso 4: acción, en el worker (03-ALGORITMO.md, Paso 4), y avisos de sistema.

En la Fase 0 cada nivel es un aviso al titular, por SMS (00-DECISIONES.md, 11).
Llamadas: Fase 2a. Contactos y servicios de emergencia: Fase 2b, bloqueada.

Cada aviso de un thread se registra en dispatches antes de enviarse: "What I
did" se arma con esa tabla. Los avisos de sistema (casa sin señal, casa de
vuelta, cámara sin conexión) no pertenecen a un thread y no se registran ahí.
"""

import logging
from collections.abc import Callable
from datetime import datetime, time
from typing import Any, Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

from artemisa.core.models import ActionLevel, PushInterruption
from artemisa.pipeline.analyze import Thread, server_text, utcnow
from artemisa.providers.twilio import Sms, one_segment

log = logging.getLogger(__name__)

LEVEL_RANK = {None: 0, "informar": 1, "alertar": 2, "contactar": 3, "emergencia": 4}


class Db(Protocol):
    async def execute(self, query: str, *args: object) -> object: ...
    async def fetchrow(self, query: str, *args: object) -> Any: ...
    async def fetchval(self, query: str, *args: object) -> Any: ...


def in_quiet_hours(start: time | None, end: time | None, local: time) -> bool:
    """Sin quiet hours si falta alguno de los dos extremos. Pueden cruzar medianoche."""
    if start is None or end is None or start == end:
        return False
    if start < end:
        return start <= local < end
    return local >= start or local < end


def interruption_for(
    level: ActionLevel, quiet: bool, interruption: PushInterruption | None
) -> PushInterruption | None:
    """El nivel de interrupción de 03, o None si en quiet hours no se avisa.

    El SMS no tiene niveles: se guarda en dispatches.interruption.
    """
    if level == ActionLevel.informar:
        if interruption is not None:
            return interruption  # el aviso de resguardo
        return None if quiet else PushInterruption.passive
    if level == ActionLevel.alertar:
        return PushInterruption.passive if quiet else PushInterruption.time_sensitive
    if level == ActionLevel.contactar:
        return PushInterruption.time_sensitive
    return PushInterruption.critical


def clock_time(when: datetime, zone: ZoneInfo) -> str:
    return when.astimezone(zone).strftime("%H:%M")


def thread_text(space_name: str, narrative: str) -> str:
    """El SMS de un thread: "{space}: {narrativa}", en un solo segmento."""
    return one_segment(f"{space_name}: {narrative}")


class Actions:
    def __init__(self, sms: Sms, clock: Callable[[], datetime] = utcnow) -> None:
        self.sms = sms
        self.clock = clock

    async def act(
        self,
        db: Db,
        th: Thread,
        level: ActionLevel,
        interruption: PushInterruption | None = None,
        ignore_quiet: bool = False,
    ) -> None:
        # Nunca repite, nunca baja. La condición va en el update; la base valida el nivel 4.
        raised = await db.fetchval(
            """update threads set action = $2
               where id = $1 and action_rank(action) < action_rank($2::action_level)
               returning id""",
            th.id,
            level.value,
        )
        if raised is None:
            return
        home = await db.fetchrow(
            """select u.timezone, p.quiet_hours_start, p.quiet_hours_end, s.name as space_name,
                      t.narrative
               from threads t
               join users u on u.id = t.user_id
               join user_preferences p on p.user_id = t.user_id
               join spaces s on s.id = t.space_id
               where t.id = $1""",
            th.id,
        )
        local = self.clock().astimezone(ZoneInfo(home["timezone"])).time()
        quiet = not ignore_quiet and in_quiet_hours(
            home["quiet_hours_start"], home["quiet_hours_end"], local
        )
        chosen = interruption_for(level, quiet, interruption)
        if chosen is None:
            log.info("thread %s: %s in quiet hours, no SMS", th.id, level.value)
            return
        dispatch_id: UUID = await db.fetchval(
            """insert into dispatches (user_id, thread_id, level, channel, target, interruption)
               values ($1, $2, $3, 'sms', 'owner', $4) returning id""",
            th.user_id,
            th.id,
            level.value,
            chosen.value,
        )
        ok = await self.sms.send(thread_text(home["space_name"], home["narrative"] or ""))
        status = "sent" if ok else "failed"
        await db.execute("update dispatches set status = $2 where id = $1", dispatch_id, status)
        log.info("thread %s: %s, dispatch %s %s", th.id, level.value, dispatch_id, status)

    async def notice(self, db: Db, user_id: str, key: str, **values: datetime | str) -> bool:
        """Un aviso de sistema con su texto de core/locales, en el idioma y la hora del usuario.

        Son textos fijos y aprobados (02-PRODUCTO.md): no se recortan, aunque alguno
        ocupe dos segmentos. El tope de un segmento es para la narrativa.
        """
        user = await db.fetchrow("select locale, timezone from users where id = $1", user_id)
        zone = ZoneInfo(user["timezone"])
        text = server_text(user["locale"], key)
        for name, value in values.items():
            shown = clock_time(value, zone) if isinstance(value, datetime) else value
            text = text.replace("{" + name + "}", shown)
        ok = await self.sms.send(text)
        log.info("system notice %s for %s: %s", key, user_id, "sent" if ok else "failed")
        return ok
