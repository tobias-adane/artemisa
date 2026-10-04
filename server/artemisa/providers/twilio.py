"""SMS por Twilio, con su API REST y httpx (00-DECISIONES.md, 11).

En la Fase 0 todos los avisos salen por SMS al número LAB_SMS_TO. Por defecto
SMS_MODE=log: el aviso se registra y no se envía. Con SMS_MODE=live se envía de
verdad, con un tope duro por hora. Nunca se loguea el texto ni el número.
"""

import logging
import os
import time
from collections import deque
from collections.abc import Callable
from typing import Protocol

import httpx

SMS_LIVE_MAX_PER_HOUR = 5  # tope duro de envíos reales: una prueba nunca manda una ráfaga
SMS_GSM_MAX_CHARS = 160  # un segmento con el alfabeto GSM-7
SMS_UCS2_MAX_CHARS = 70  # un segmento si hay algún carácter fuera de GSM-7 (á, í, ó, ú…)
SMS_TIMEOUT_S = 10
TRUNCATED = "..."

LIVE_VARIABLES = ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER", "LAB_SMS_TO")
API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

# El alfabeto básico de GSM 03.38. Con cualquier otro carácter el SMS va en UCS-2.
GSM7 = frozenset(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)

log = logging.getLogger(__name__)


class Sms(Protocol):
    async def send(self, text: str) -> bool:
        """True si el aviso salió (o quedó registrado, en modo log)."""
        ...


def one_segment(text: str) -> str:
    """Corta el texto para que entre en un solo segmento, en el límite de una palabra.

    Nunca devuelve un texto vacío: si la primera palabra no entra, la corta.
    """
    text = " ".join(text.split())
    limit = SMS_GSM_MAX_CHARS if set(text) <= GSM7 else SMS_UCS2_MAX_CHARS
    if len(text) <= limit:
        return text
    room = limit - len(TRUNCATED)
    cut = text[: room + 1].rsplit(" ", 1)[0] if " " in text[: room + 1] else ""
    cut = cut.rstrip(" ,;:.")
    if not cut:
        cut = text[:room]
    return cut + TRUNCATED


class LogSms:
    """SMS_MODE=log: no envía. El log no lleva el texto ni el número."""

    async def send(self, text: str) -> bool:
        log.info("SMS not sent (test mode, %d chars)", len(text))
        return True


class TwilioSms:
    """SMS_MODE=live: envía por la API REST de Twilio, con tope por hora."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        account_sid: str,
        auth_token: str,
        from_number: str,
        to_number: str,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client = client
        self.url = API.format(sid=account_sid)
        self.auth = (account_sid, auth_token)
        self.from_number = from_number
        self.to_number = to_number
        self.clock = clock
        self.sent: deque[float] = deque()

    async def send(self, text: str) -> bool:
        now = self.clock()
        while self.sent and now - self.sent[0] >= 3600:
            self.sent.popleft()
        if len(self.sent) >= SMS_LIVE_MAX_PER_HOUR:
            log.warning("SMS not sent: %d real SMS in the last hour", SMS_LIVE_MAX_PER_HOUR)
            return False
        self.sent.append(now)  # cuenta el intento, salga o no
        try:
            response = await self.client.post(
                self.url,
                auth=self.auth,
                data={"From": self.from_number, "To": self.to_number, "Body": text},
                timeout=SMS_TIMEOUT_S,
            )
        except httpx.HTTPError as exc:
            log.warning("SMS failed (%s)", type(exc).__name__)
            return False
        if response.status_code >= 300:
            log.warning("SMS failed (http %d)", response.status_code)
            return False
        log.info("SMS sent")
        return True


def sms_from_env(client: httpx.AsyncClient) -> Sms:
    mode = os.environ.get("SMS_MODE", "log")
    if mode == "log":
        return LogSms()
    if mode != "live":
        raise SystemExit("SMS_MODE must be log or live")
    missing = [name for name in LIVE_VARIABLES if not os.environ.get(name)]
    if missing:
        raise SystemExit("SMS_MODE=live needs " + ", ".join(missing) + " in server/.env")
    log.warning("SMS_MODE=live: real SMS, at most %d per hour", SMS_LIVE_MAX_PER_HOUR)
    return TwilioSms(
        client,
        os.environ["TWILIO_ACCOUNT_SID"],
        os.environ["TWILIO_AUTH_TOKEN"],
        os.environ["TWILIO_FROM_NUMBER"],
        os.environ["LAB_SMS_TO"],
    )
