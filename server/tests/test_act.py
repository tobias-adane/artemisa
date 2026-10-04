"""Paso 4 y SMS sin Postgres: quiet hours, niveles, un solo segmento, modo de prueba y tope."""

import asyncio
import logging
from datetime import time
from urllib.parse import parse_qs

import httpx
import pytest

from artemisa.core.models import ActionLevel, PushInterruption
from artemisa.pipeline.act import in_quiet_hours, interruption_for, thread_text
from artemisa.providers import twilio
from artemisa.providers.twilio import (
    SMS_GSM_MAX_CHARS,
    SMS_LIVE_MAX_PER_HOUR,
    SMS_UCS2_MAX_CHARS,
    LogSms,
    TwilioSms,
    one_segment,
    sms_from_env,
)

SECRET_TOKEN = "twilio-secret-token-xyz"
PHONE = "+5491100000000"


# Quiet hours y niveles


@pytest.mark.parametrize(
    ("start", "end", "local", "quiet"),
    [
        (None, None, time(3, 0), False),
        (time(23, 0), None, time(23, 30), False),
        (time(23, 0), time(7, 0), time(23, 30), True),
        (time(23, 0), time(7, 0), time(6, 59), True),
        (time(23, 0), time(7, 0), time(7, 0), False),
        (time(23, 0), time(7, 0), time(14, 0), False),
        (time(13, 0), time(15, 0), time(14, 0), True),
    ],
)
def test_quiet_hours_cross_midnight(
    start: time | None, end: time | None, local: time, quiet: bool
) -> None:
    assert in_quiet_hours(start, end, local) is quiet


P, T, C = PushInterruption.passive, PushInterruption.time_sensitive, PushInterruption.critical


@pytest.mark.parametrize(
    ("level", "quiet", "expected"),
    [
        (ActionLevel.informar, False, P),
        (ActionLevel.informar, True, None),  # queda en la línea, sin aviso
        (ActionLevel.alertar, False, T),
        (ActionLevel.alertar, True, P),  # en quiet hours se manda igual
        (ActionLevel.contactar, False, T),
        (ActionLevel.contactar, True, T),  # nunca se silencia
        (ActionLevel.emergencia, False, C),
        (ActionLevel.emergencia, True, C),
    ],
)
def test_interruption_follows_03(
    level: ActionLevel, quiet: bool, expected: PushInterruption | None
) -> None:
    assert interruption_for(level, quiet, None) == expected


def test_the_fallback_notice_keeps_its_interruption_in_quiet_hours() -> None:
    assert interruption_for(ActionLevel.informar, True, T) == T


# Un solo segmento


def test_a_short_text_is_left_alone() -> None:
    assert one_segment("Front Door: Someone left a box.") == "Front Door: Someone left a box."


def test_gsm_text_fits_160_and_cuts_on_a_word() -> None:
    text = one_segment("Front Door: " + "word " * 60)
    assert len(text) <= SMS_GSM_MAX_CHARS and text.endswith("word...")


def test_accents_mean_70_characters() -> None:
    text = one_segment(
        "Puerta: Alguien dejó una caja en la puerta, tocó el timbre y después se fue."
    )
    assert len(text) <= SMS_UCS2_MAX_CHARS
    assert text == "Puerta: Alguien dejó una caja en la puerta, tocó el timbre y..."


def test_the_text_is_never_empty() -> None:
    text = one_segment("x" * 500)
    assert text == "x" * (SMS_GSM_MAX_CHARS - 3) + "..."
    assert one_segment("   ") == ""  # nada que mandar: lo decide quien llama


def test_the_thread_sms_is_space_and_narrative() -> None:
    assert thread_text("Front Door", "Someone left a box.") == "Front Door: Someone left a box."


# Modo de prueba


def test_log_mode_sends_nothing_and_logs_no_text(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        assert asyncio.run(LogSms().send("Front Door: secreto de la familia")) is True
    assert "secreto" not in caplog.text and "SMS not sent (test mode" in caplog.text


def test_log_is_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMS_MODE", raising=False)
    assert isinstance(sms_from_env(httpx.AsyncClient()), LogSms)


def test_live_refuses_to_start_without_every_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMS_MODE", "live")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", SECRET_TOKEN)
    monkeypatch.delenv("TWILIO_FROM_NUMBER", raising=False)
    monkeypatch.delenv("LAB_SMS_TO", raising=False)
    with pytest.raises(SystemExit) as stop:
        sms_from_env(httpx.AsyncClient())
    message = str(stop.value)
    assert "TWILIO_FROM_NUMBER" in message and "LAB_SMS_TO" in message
    assert SECRET_TOKEN not in message and "TWILIO_AUTH_TOKEN" not in message


def test_an_unknown_mode_refuses_to_start(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMS_MODE", "yes")
    with pytest.raises(SystemExit):
        sms_from_env(httpx.AsyncClient())


# Envío real (con transporte simulado)


def twilio_with(status: int, seen: list[httpx.Request], clock: list[float]) -> TwilioSms:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json={"sid": "SM1"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TwilioSms(client, "AC123", SECRET_TOKEN, "+15550001111", PHONE, lambda: clock[0])


def test_live_posts_to_the_rest_api(caplog: pytest.LogCaptureFixture) -> None:
    seen: list[httpx.Request] = []
    sms = twilio_with(201, seen, [0.0])
    with caplog.at_level(logging.DEBUG):
        assert asyncio.run(sms.send("Front Door: hola")) is True
    (request,) = seen
    assert str(request.url) == "https://api.twilio.com/2010-04-01/Accounts/AC123/Messages.json"
    form = parse_qs(request.content.decode())
    assert form == {"From": ["+15550001111"], "To": [PHONE], "Body": ["Front Door: hola"]}
    assert request.headers["authorization"].startswith("Basic ")
    for secret in (SECRET_TOKEN, PHONE, "hola"):
        assert secret not in caplog.text


@pytest.mark.parametrize("status", [400, 401, 500])
def test_an_error_answer_is_a_failed_sms(status: int) -> None:
    assert asyncio.run(twilio_with(status, [], [0.0]).send("x")) is False


def test_a_network_error_is_a_failed_sms() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    sms = TwilioSms(client, "AC123", SECRET_TOKEN, "+1", PHONE)
    assert asyncio.run(sms.send("x")) is False


def test_at_most_five_real_sms_per_hour() -> None:
    seen: list[httpx.Request] = []
    clock = [0.0]
    sms = twilio_with(201, seen, clock)

    async def burst() -> list[bool]:
        return [await sms.send("x") for _ in range(SMS_LIVE_MAX_PER_HOUR + 3)]

    results = asyncio.run(burst())
    assert results == [True] * SMS_LIVE_MAX_PER_HOUR + [False] * 3
    assert len(seen) == SMS_LIVE_MAX_PER_HOUR  # los de más ni siquiera salen
    clock[0] = 3599.0
    assert asyncio.run(sms.send("x")) is False
    clock[0] = 3600.0
    assert asyncio.run(sms.send("x")) is True


def test_the_cap_is_five() -> None:
    assert twilio.SMS_LIVE_MAX_PER_HOUR == 5
