"""
Entrypoint del servicio — `python -m uvicorn main:app --reload`.

Arranca siempre, con o sin credenciales reales: sin
SUPABASE_URL/SUPABASE_SERVICE_KEY cae a InMemoryStore (ver
clients/store.get_store), que además se siembra con los mismos datos
de ejemplo que frontend/lib/mock-data.ts para que ambos lados del
proyecto se puedan probar juntos sin backend real todavía.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router, get_store_dep
from artemisa_models import EmergencyContact, ContactRelationship, Space, SpaceStatus, User, UserPreferences
from clients.store import InMemoryStore, get_store
from config import get_settings

settings = get_settings()
store = get_store(settings)

# Usuario de demo fijo — sin Clerk todavía no hay auth real, así que el
# frontend lo resuelve vía GET /me en vez de tener este UUID hardcodeado
# en dos lugares. Solo existe cuando corremos sobre InMemoryStore.
DEMO_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

if isinstance(store, InMemoryStore):
    _demo_user_id = DEMO_USER_ID
    store.seed(
        users=[
            User(
                id=_demo_user_id,
                email="tomas@artemisa.app",
                name="Tomás Vidal",
                has_children=True,
                custom_instructions="La mucama viene los martes a las 10am. Nadie debería estar en casa después de las 23hs entre semana.",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ],
        prefs=[UserPreferences(id=uuid4(), user_id=_demo_user_id)],
        spaces=[
            Space(
                id=uuid4(),
                user_id=_demo_user_id,
                name="Living",
                camera_url="rtsp://demo.local/living",
                status=SpaceStatus.ACTIVE,
                last_update=datetime.now(timezone.utc),
            )
        ],
        contacts=[
            EmergencyContact(
                id=uuid4(),
                user_id=_demo_user_id,
                name="Valentina Vidal",
                phone="+5491122334455",
                relationship=ContactRelationship.SPOUSE_PARTNER,
                priority=1,
                confirmed=True,
            )
        ],
    )

app = FastAPI(title="Artemisa Backend")

# Dev/demo únicamente: permite que el Next.js en localhost:3000 (u otro
# origen configurado) llame a este servicio directo desde el browser.
# Sin Clerk todavía no hay sesión real que autorizar — cuando exista,
# esto se reemplaza por la validación de sesión, no por abrir CORS a
# cualquier origen.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.dependency_overrides[get_store_dep] = lambda: store


@app.get("/health")
def health():
    return {
        "status": "ok",
        "store": type(store).__name__,
        "openai_configured": settings.has_openai,
        "groq_configured": settings.has_groq,
        "twilio_configured": settings.has_twilio,
        "supabase_configured": settings.has_supabase,
    }


@app.get("/me", response_model=User)
def me():
    """
    Sin Clerk todavía no hay sesión real — esto devuelve el usuario de
    demo sembrado en InMemoryStore para que el frontend tenga un
    user_id con el que llamar al resto de los endpoints. No existe en
    modo Supabase (ahí la identidad viene de la sesión real).
    """
    if not isinstance(store, InMemoryStore):
        raise HTTPException(501, "GET /me solo está disponible en modo demo (InMemoryStore) — requiere auth real con Supabase.")
    user = store.get_user(DEMO_USER_ID)
    if user is None:
        raise HTTPException(404, "No hay usuario de demo sembrado.")
    return user
