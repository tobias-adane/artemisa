"""
Paso 2a — Cliente de visión (OpenAI GPT-4o mini).

Recibe UN frame en memoria (base64), lo manda inline con detail:"low",
y devuelve solo texto. El frame nunca toca disco ni se persiste acá ni
en el llamador — ver pipeline/step2a_vision.py, que descarta el frame
inmediatamente después de este call.
"""

from __future__ import annotations

from config import Settings
from clients.base import NotConfiguredError

VISION_SYSTEM_PROMPT = (
    "Describí en una oración lo que ocurre en esta imagen del espacio "
    "{space_name}.\n"
    "Contexto del hogar: {home_context}\n"
    "Respondé en español. Sé específico sobre personas, objetos y acciones.\n"
    "No emitas juicio sobre si es normal o preocupante — eso se decide después.\n"
    "No menciones la cámara ni el análisis. Solo describí el evento."
)


class VisionClient:
    def __init__(self, settings: Settings):
        self._settings = settings

    def describe_frame(self, frame_b64: str, *, space_name: str, home_context: str) -> str:
        """
        `frame_b64` es un JPEG/PNG en memoria, codificado base64 — nunca
        un path de archivo. El llamador es responsable de no haberlo
        escrito a disco antes de pasarlo acá (ver Paso 1 en
        pipeline/step1_motion.py).
        """
        if not self._settings.has_openai:
            raise NotConfiguredError("OpenAI (visión, Paso 2a)", "OPENAI_API_KEY")

        # Import diferido: el SDK de OpenAI no es una dependencia dura del
        # servicio si todavía no se configuró la key (permite instalar y
        # correr el resto del pipeline/tests sin el paquete instalado).
        from openai import OpenAI

        client = OpenAI(api_key=self._settings.openai_api_key)
        prompt = VISION_SYSTEM_PROMPT.format(space_name=space_name, home_context=home_context or "sin contexto adicional")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}", "detail": "low"},
                        },
                    ],
                }
            ],
            max_tokens=120,
        )
        return (response.choices[0].message.content or "").strip()
