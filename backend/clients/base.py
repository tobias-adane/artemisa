"""Errores compartidos por los clientes de servicios externos."""

from __future__ import annotations


class NotConfiguredError(RuntimeError):
    """
    Se lanza cuando el código intenta una llamada real a un servicio
    externo (OpenAI/Groq/Twilio/Supabase) sin la env var correspondiente
    configurada. Nunca se usa para degradar silenciosamente — el llamador
    decide qué hacer (ej. el orquestador del pipeline corre en modo mock
    y loggea en vez de propagar, ver pipeline/orchestrator.py).
    """

    def __init__(self, service: str, env_var: str):
        super().__init__(
            f"{service} no está configurado — falta la variable de entorno {env_var}. "
            f"Ver backend/CLAUDE.md sección 'Variables de entorno requeridas'."
        )
        self.service = service
        self.env_var = env_var
