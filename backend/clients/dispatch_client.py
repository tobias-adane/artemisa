"""
Paso 4 — Dispatch (Twilio).

Ejecuta las llamadas/SMS reales. La lógica de A QUIÉN y CUÁNDO llamar
(ventanas de cancelación, orden de contactos, el bloqueo legal de 911)
vive en pipeline/step4_dispatch.py — este módulo solo sabe hablar con
Twilio.
"""

from __future__ import annotations

from config import Settings
from clients.base import NotConfiguredError


class Dispatch911Blocked(RuntimeError):
    """
    Ver backend/CLAUDE.md, Paso 4: el autodial al 911 está apagado por
    default (`Settings.enable_911_autodial = False`) hasta resolver la
    consulta legal sobre legalidad del autodial en jurisdicción
    argentina. Esta excepción es intencional y no debe silenciarse ni
    recibir un try/except que la ignore — si esto se dispara, el flujo
    correcto es notificar a un humano, no reintentar.
    """


class DispatchClient:
    def __init__(self, settings: Settings):
        self._settings = settings

    def _require_twilio(self):
        if not self._settings.has_twilio:
            raise NotConfiguredError("Twilio (dispatch, Paso 4)", "TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER")
        from twilio.rest import Client

        return Client(self._settings.twilio_account_sid, self._settings.twilio_auth_token)

    def call_ivr(self, *, to_phone: str, twiml_url: str) -> str:
        """Nivel 4 — llamada IVR al usuario mismo, primer paso antes de escalar a contactos."""
        client = self._require_twilio()
        call = client.calls.create(to=to_phone, from_=self._settings.twilio_from_number, url=twiml_url)
        return call.sid

    def call_contact(self, *, to_phone: str, twiml_url: str) -> str:
        """Nivel 3 (contactar) o Nivel 4 degradado a contactos — llama a un contacto de confianza confirmado."""
        client = self._require_twilio()
        call = client.calls.create(to=to_phone, from_=self._settings.twilio_from_number, url=twiml_url)
        return call.sid

    def send_sms(self, *, to_phone: str, body: str) -> str:
        client = self._require_twilio()
        msg = client.messages.create(to=to_phone, from_=self._settings.twilio_from_number, body=body)
        return msg.sid

    def call_911(self, *, to_phone: str, twiml_url: str) -> str:
        if not self._settings.enable_911_autodial:
            raise Dispatch911Blocked(
                "El autodial al 911 está implementado pero apagado por default "
                "(ENABLE_911_AUTODIAL=false) — ver backend/CLAUDE.md, Paso 4. "
                "Requiere opinión legal sobre legalidad del autodial en Argentina "
                "antes de habilitarse."
            )
        client = self._require_twilio()
        call = client.calls.create(to=to_phone, from_=self._settings.twilio_from_number, url=twiml_url)
        return call.sid
