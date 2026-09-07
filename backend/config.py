"""
Configuración del servicio — todo lo que viene de variables de entorno.

Ningún cliente real (OpenAI/Groq/Twilio/Supabase) se instancia acá. Este
módulo solo lee y valida qué está configurado, para que el resto del
código pueda preguntar `settings.has_openai` etc. sin repetir
`os.environ.get(...)` por todos lados.

Sin ninguna key configurada, el servicio arranca igual: cada cliente en
`clients/` cae a un modo mock explícito (ver `clients/base.py`) en vez de
fallar al importar. Así el pipeline completo es testeable end-to-end sin
credenciales reales — y produce un error claro, recién al intentar la
llamada real, si faltan.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    groq_api_key: str | None
    supabase_url: str | None
    supabase_service_key: str | None
    twilio_account_sid: str | None
    twilio_auth_token: str | None
    twilio_from_number: str | None
    sentry_dsn: str | None

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    @property
    def has_twilio(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_number)


@lru_cache
def get_settings() -> Settings:
    # Carga .env si existe (no falla si python-dotenv no está o si el
    # archivo no existe — las env vars del proceso siempre ganan).
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    return Settings(
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        groq_api_key=os.environ.get("GROQ_API_KEY"),
        supabase_url=os.environ.get("SUPABASE_URL"),
        supabase_service_key=os.environ.get("SUPABASE_SERVICE_KEY"),
        twilio_account_sid=os.environ.get("TWILIO_ACCOUNT_SID"),
        twilio_auth_token=os.environ.get("TWILIO_AUTH_TOKEN"),
        twilio_from_number=os.environ.get("TWILIO_FROM_NUMBER"),
        sentry_dsn=os.environ.get("SENTRY_DSN"),
    )
