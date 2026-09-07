"""
Orquestador — compone los 4 pasos para un ciclo de batch de un espacio.

Lo que SÍ hace este módulo: dado un batch de layers ya generadas
(Paso 2a corrido frame a frame por el loop de lectura de cámara, fuera
de este archivo), corre clasificación (2b) -> verificación si
corresponde (3) -> arma el plan de dispatch (4), y devuelve todo listo
para que quien orqueste el timing real (ventanas de cancelación, el
loop de lectura RTSP) actúe.

Lo que NO hace: leer la cámara (RTSP) ni bloquear esperando ventanas de
cancelación con sleeps reales — eso es infraestructura que necesita una
cámara real y un scheduler (cola/cron), no algo que se pueda construir
o probar de forma significativa sin ellos. `run_step1_and_step2a` de
abajo es la pieza por-frame que un loop de lectura real invocaría.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

import numpy as np

from artemisa_models import ActionLevel, Classification, EventType, ActivityLogEntry, Thread
from clients.classification_client import ClassificationClient
from clients.store import Store
from clients.verification_client import VerificationClient
from clients.vision_client import VisionClient
from pipeline.step1_motion import MotionState, detect
from pipeline.step2a_vision import run_step2a
from pipeline.step2b_classification import run_step2b
from pipeline.step3_verification import run_step3
from pipeline.step4_dispatch import DispatchPlan, plan_dispatch


def run_step1_and_step2a(
    *,
    store: Store,
    vision_client: VisionClient,
    motion_state: MotionState,
    space_id: UUID,
    space_name: str,
    home_context: str,
    frame_bgr: np.ndarray,
    now: datetime | None = None,
):
    """
    La pieza por-frame: Paso 1 decide si vale la pena describir este
    frame: si no, se descarta acá mismo y no llega a Paso 2a (ni a
    OpenAI). El llamador (el loop de lectura RTSP) le pasa un frame por
    vez; este frame nunca se retiene más allá del alcance de esta
    llamada.
    """
    motion = detect(motion_state, frame_bgr, now=now)
    if not motion.should_emit:
        return None
    frame_b64 = _encode_frame_b64(frame_bgr)
    return run_step2a(
        store=store,
        vision_client=vision_client,
        space_id=space_id,
        frame_b64=frame_b64,
        space_name=space_name,
        home_context=home_context,
    )


def _encode_frame_b64(frame_bgr: np.ndarray) -> str:
    import base64

    import cv2

    ok, buf = cv2.imencode(".jpg", frame_bgr)
    if not ok:
        raise ValueError("No se pudo codificar el frame a JPEG")
    return base64.b64encode(buf).decode("ascii")


@dataclass(frozen=True)
class BatchOutcome:
    thread: Thread
    dispatch_plan: DispatchPlan | None


def run_batch_cycle(
    *,
    store: Store,
    classification_client: ClassificationClient,
    verification_client: VerificationClient,
    space_id: UUID,
    space_name: str,
    user_id: UUID,
    layer_ids: list[UUID],
    layer_descriptions: list[str],
    custom_instructions: str,
    other_spaces_state: str,
    now: datetime,
) -> BatchOutcome:
    """
    Cierra un batch de layers acumuladas para un espacio: clasifica,
    escala a verificación si corresponde, arma el plan de dispatch si
    el resultado lo amerita, y deja un registro en activity_log.

    No ejecuta el dispatch (eso lo hace step4_dispatch.execute_dispatch_step,
    típicamente después de que la ventana de cancelación real haya
    corrido en el llamador).
    """
    thread, needs_step3 = run_step2b(
        store=store,
        classification_client=classification_client,
        space_id=space_id,
        layer_ids=layer_ids,
        layer_descriptions=layer_descriptions,
        space_name=space_name,
        custom_instructions=custom_instructions,
        other_spaces_state=other_spaces_state,
        now=now,
    )

    if needs_step3:
        thread = run_step3(
            store=store,
            verification_client=verification_client,
            thread=thread,
            space_name=space_name,
            layer_descriptions=layer_descriptions,
            recent_activity=other_spaces_state,
        )

    dispatch_plan = None
    if thread.action in (ActionLevel.CONTACTAR, ActionLevel.EMERGENCIA):
        preferences = store.get_preferences(user_id)
        if preferences is not None:
            dispatch_plan = plan_dispatch(thread.action, preferences)

    store.create_activity_log_entry(
        ActivityLogEntry(
            id=uuid4(),
            user_id=user_id,
            thread_id=thread.id,
            event_type=EventType.THREAD_LOGGED,
            title=thread.narrative[:80],
            description=thread.narrative,
            location=space_name,
            image_url=None,
            timestamp=now,
        )
    )

    return BatchOutcome(thread=thread, dispatch_plan=dispatch_plan)
