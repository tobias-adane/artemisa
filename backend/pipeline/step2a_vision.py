"""
Paso 2a — Genera un Layer a partir de un frame en memoria.

El frame vive en esta función y en VisionClient.describe_frame — nunca
más allá. No hay parámetro de "guardar frame" porque no debe existir:
ver backend/CLAUDE.md regla absoluta #1.
"""

from __future__ import annotations

from uuid import UUID

from artemisa_models import LayerCreate
from clients.store import Store
from clients.vision_client import VisionClient


def run_step2a(
    *,
    store: Store,
    vision_client: VisionClient,
    space_id: UUID,
    frame_b64: str,
    space_name: str,
    home_context: str,
):
    description = vision_client.describe_frame(frame_b64, space_name=space_name, home_context=home_context)
    # `frame_b64` sale de scope acá — el llamador no debe retenerlo.
    layer = store.create_layer(LayerCreate(space_id=space_id, description=description))
    return layer
