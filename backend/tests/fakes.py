"""
Dobles de los clientes de LLM/Twilio para tests — mismo shape de
retorno que los clientes reales (clients/*_client.py), sin red ni
credenciales. Cada fake se configura con la respuesta que el test
necesita en vez de llamar a un modelo de verdad.
"""

from __future__ import annotations

from clients.classification_client import ClassificationResult
from artemisa_models import EmergencyVerification


class FakeClassificationClient:
    def __init__(self, result: ClassificationResult):
        self._result = result
        self.last_call_kwargs: dict | None = None

    def classify(self, **kwargs) -> ClassificationResult:
        self.last_call_kwargs = kwargs
        return self._result


class FakeVerificationClient:
    def __init__(self, verification: EmergencyVerification):
        self._verification = verification
        self.last_call_kwargs: dict | None = None

    def verify(self, **kwargs) -> EmergencyVerification:
        self.last_call_kwargs = kwargs
        return self._verification


class FakeDispatchClient:
    """Registra cada intento en vez de llamar a Twilio de verdad."""

    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def call_ivr(self, *, to_phone: str, twiml_url: str) -> str:
        self.calls.append(("call_ivr", to_phone))
        return "CA_fake_ivr"

    def call_contact(self, *, to_phone: str, twiml_url: str) -> str:
        self.calls.append(("call_contact", to_phone))
        return "CA_fake_contact"

    def send_sms(self, *, to_phone: str, body: str) -> str:
        self.calls.append(("sms", to_phone))
        return "SM_fake"

    def call_911(self, *, to_phone: str, twiml_url: str) -> str:
        from clients.dispatch_client import Dispatch911Blocked

        raise Dispatch911Blocked
