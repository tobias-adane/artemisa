# Artemisa — Backend (Python / Railway)

## Qué es esto

Artemisa es una plataforma de inteligencia para el hogar. Este
servicio Python ejecuta el pipeline de análisis de cámaras IP en
tiempo real. **No almacena video, imágenes ni audio. Nunca. Bajo
ninguna circunstancia.**

Beta lanza en Argentina — español rioplatense en todo el copy
generado (narrativas, reasoning, mensajes de Twilio).

**Fuente de verdad del schema:** `docs/ARTEMISA_03_DATOS.md` y
`backend/artemisa_models.py`. Si algo acá contradice esos dos
archivos, ganan ellos.

---

## Stack

```
Runtime:      Python 3.11+
Hosting:      Railway
CV:           OpenCV (captura y detección de movimiento por diferencia de frames)
Visión IA:    OpenAI GPT-4o mini (descripción de frames — Paso 2a)
Análisis:     Groq Llama 3.1 8B / 3.3 70B (clasificación de threads — Paso 2b)
Razonamiento: OpenAI GPT-4.1 mini (verificación Nivel 4 — Paso 3)
Dispatch:     Twilio (llamadas + SMS/WhatsApp — Paso 4)
DB:           Supabase (PostgreSQL via supabase-py + real-time)
Validación:   Pydantic v2
Errors:       Sentry
```

---

## Pipeline — los 4 pasos

### Paso 1 — Detección de movimiento (OpenCV, gratuito)

```python
# Diferencia de frames consecutivos.
# Si el cambio supera el threshold -> capturar frame.
# El frame NUNCA se escribe a disco ni a base de datos.
# Se pasa en memoria al Paso 2a.
# Heartbeat en calma: si no hubo cambio en 5 min, se manda 1 frame
# igual como chequeo de salud (adaptativo a futuro — ver doc 02 #9).
```

Threshold de movimiento ajustado por espacio (sensibilidad en
Settings, vía `user_preferences.alert_sensitivity`).

### Paso 2a — Generación de Layer (OpenAI GPT-4o mini)

```python
# Input:  frame en memoria (base64 inline en el prompt), detail: low
# Output: descripción textual del evento — SOLO texto, SIN clasificación
# El frame se descarta INMEDIATAMENTE después del call a OpenAI.
# NUNCA guardar el frame. NUNCA.
```

**Por qué Layer no clasifica:** ver `docs/ARTEMISA_03_DATOS.md`
sección 3. Meter `classification` acá obligaría a inyectar contexto
completo (rutina, threads recientes, otros espacios) en la llamada
más frecuente del pipeline (~93.600/mes por cámara) para terminar
reclasificando en Paso 2b de todos modos. La clasificación vive una
sola vez, amortizada sobre el batch.

```python
# artemisa_models.py
class LayerCreate(BaseModel):
    space_id: UUID
    description: str
    confidence: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### Paso 2b — Clasificación de Thread (Groq Llama)

```python
# Input:  layers recientes del batch + custom_instructions + resumen
#         comprimido de los últimos 3-5 threads del espacio (one-liner,
#         no narrativa completa) + hora/día + estado de otros espacios.
# Output: ThreadCreate — narrative, classification, confidence,
#         severity_score, reasoning.
# Groq recibe SOLO texto. Nunca imágenes.
```

**Continuidad de threads:** antes de correr el modelo, chequeo
barato (sin LLM) de si hay un thread abierto (`end_time=None`) para
este espacio dentro de la ventana de silencio (2-3 min). Si sí, el
batch nuevo extiende ese thread; si no, abre uno nuevo. Evita
fragmentar una sola visita en eventos desconectados.

**Escala a Llama 3.3 70B cuando:**
- Las descripciones del batch son contradictorias o ambiguas
- El batch toca algo de `custom_instructions` — chequeo de
  keywords/embedding barato ANTES de decidir escalar, no una
  decisión del modelo chico
- Es horario nocturno (11pm-6am default) — chequeo de reloj, no de LLM

Después de escribir el `ThreadCreate`, resolver `alert_level` y
`action` con `resolve_action_level()` (ver más abajo) — nunca
asignarlos a mano ni dejar que el modelo de Groq los invente.

### Paso 3 — Verificación de Emergencia (GPT-4.1 mini)

```python
# Triggers (los 4, ver ARTEMISA_02_ARQUITECTURA.md sección 5):
#   1. attention con confidence < 0.6
#   2. emergency — SIEMPRE se re-verifica acá antes de tocar Twilio
#   3. fast-path liviano detectó algo urgente sin esperar el ciclo de 60s
#   4. patrón de persona no reconocida repitiéndose en poco tiempo
#
# Output: EmergencyVerification { severity_high, reasoning, confidence }
# reasoning acá es INTERNO — nunca se muestra en la UI tal cual.
```

Al terminar Paso 3, **reescribir** `Thread.reasoning` con una síntesis
en voz humana del resultado (nunca volcar el `reasoning` técnico de
`EmergencyVerification` directo a la UI — ver
`docs/ARTEMISA_03_DATOS.md` sección 4).

### Paso 4 — Dispatch (Twilio)

```python
# Nivel 3 (contactar) — puede venir de attention (severity_score alto)
#   o de emergency degradado (Paso 3 no confirmó severity_high):
#   1. Ventana de cancelación: user_preferences.contact_cancel_timer_seconds
#      (default 90s) — vía push/WhatsApp con opción de cancelar.
#   2. Si no cancela -> llamar/mensaje al contacto de confianza de
#      mayor prioridad que tenga confirmed=True.
#
# Nivel 4 (emergencia) — SOLO si Paso 3 confirma severity_high == True:
#   1. Llamada IVR al usuario. Ventana: cancel_timer_seconds (default 30s).
#   2. Si no cancela -> llamar a contactos de emergencia confirmados.
#   3. Si persiste -> llamar al 911.
#
# ⚠️  El paso de "llamar al 911" está IMPLEMENTADO pero APAGADO por
#     default: Settings.enable_911_autodial (env ENABLE_911_AUTODIAL)
#     es False mientras no se resuelva la opinión legal sobre
#     legalidad del autodial en jurisdicción argentina. Con el flag
#     en False, dispatch_client.call_911() sigue lanzando
#     Dispatch911Blocked igual que antes — no cambia el comportamiento
#     en producción hasta que alguien prenda el flag a propósito.
#     Nivel 3 (contactar a persona de confianza, no 911) no depende
#     de este flag.

class DispatchLog(BaseModel):
    id: UUID
    thread_id: UUID
    user_id: UUID
    action: str  # 'call_user' | 'call_contacts' | 'call_911'
    twilio_sid: str
    status: str
    created_at: datetime
    # Retención: 5 años (relevancia legal ante reclamos)
```

---

## Modelos Pydantic

Ver `backend/artemisa_models.py` — es el archivo completo y
autoritativo. No lo dupliques acá; si necesitás el detalle de un
campo, andá directo a la fuente.

**Regla de oro:** si cambiás un modelo Pydantic, actualizás
`docs/ARTEMISA_03_DATOS.md`, `frontend/lib/types/artemisa-types.ts`
y la migración de Supabase en el mismo cambio.

---

## Supabase

Ver `docs/ARTEMISA_03_DATOS.md` secciones 1 y 7 para el schema
completo y la política de retención/borrado automático.

Siempre usar RLS (Row Level Security). Cada tabla tiene policy
`user_id = auth.uid()` (para `layers`/`threads`, vía `space_id` ->
`spaces.user_id`).

---

## Variables de entorno requeridas

```bash
# OpenAI
OPENAI_API_KEY=

# Groq
GROQ_API_KEY=

# Supabase
SUPABASE_URL=
SUPABASE_SERVICE_KEY=   # solo backend — NUNCA exponer al frontend

# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=     # número E.164

# Autodial al 911 (Paso 4, Nivel 4) — default false, ver sección Paso 4
ENABLE_911_AUTODIAL=false

# Sentry
SENTRY_DSN=
```

---

## Reglas absolutas

1. **NUNCA almacenar frames, imágenes ni video.** Los frames van en
   memoria, se pasan a OpenAI inline, y se descartan. No disco, no
   Supabase, no S3, no ningún storage.

2. **NUNCA enviar imágenes a Groq.** Groq solo recibe texto (las
   descripciones/layers).

3. **NUNCA exponer `spaces.camera_url` al frontend.** Solo el
   backend accede a las cámaras. Cualquier response hacia el cliente
   proyecta columnas explícitamente (shape `SpacePublic`), nunca un
   `select *`.

4. **NUNCA auto-llamar al 911 sin verificación humana** hasta
   resolver consulta legal — hoy garantizado por
   `Settings.enable_911_autodial = False` (default), no por ausencia
   de código. Nivel 3 (contactar a persona de confianza) sí puede
   automatizarse, con su propia ventana de cancelación de 90s.

5. **El Nivel 4 requiere doble verificación**: Paso 2b clasifica
   `emergency` -> Paso 3 (GPT-4.1 mini) confirma `severity_high: True`
   -> recién ahí se activa Paso 4 con acción `emergencia`.

6. **`Layer` nunca lleva `classification`.** Paso 2a describe, Paso
   2b clasifica. Ver sección de Paso 2a más arriba.

7. **`alert_level` y `action` se calculan siempre con
   `resolve_action_level()`**, nunca a mano ni por el modelo de Groq
   directamente.

8. **Los modelos Pydantic, los tipos TypeScript del frontend y
   `docs/ARTEMISA_03_DATOS.md` deben estar siempre sincronizados.**
   Si modificás uno, modificás los tres.

---

## Prompts del sistema (estructura base)

### Paso 2a — Visión (GPT-4o mini)
```
Describí en una oración lo que ocurre en esta imagen del espacio [space_name].
Contexto del hogar: [home_context]
Respondé en español. Sé específico sobre personas, objetos y acciones.
No emitas juicio sobre si es normal o preocupante — eso se decide después.
No menciones la cámara ni el análisis. Solo describí el evento.
```

### Paso 2b — Clasificación (Groq)
```
Sos el sistema de inteligencia de Artemisa. Analizá estos eventos recientes
del espacio [space_name] y determiná si requieren atención.

Eventos: [layers]
Rutina normal del hogar: [custom_instructions]
Resumen de threads recientes de este espacio: [recent_threads_summary]
Estado de otros espacios: [other_spaces_state]
Horario: [hora_actual], [dia_semana]

Clasificá como: normal | attention | emergency
Asigná confidence (0-1) y severity_score (0-1) por separado.
Generá una narrativa y un reasoning en español, en voz humana —
nunca como log de sistema.
```

### Paso 3 — Verificación (GPT-4.1 mini)
```
Verificá si la siguiente situación detectada en [space_name] es realmente
una emergencia que requiere contactar servicios de emergencia.

Thread: [narrative]
Layers de soporte: [descriptions]
Historial del espacio: [recent_activity]

Respondé con severity_high: true SOLO si estás altamente confiado
de que hay una emergencia real. En caso de duda, severity_high: false.
Este reasoning es interno — no se muestra en la UI tal cual.
```

---

## Comandos frecuentes

```bash
python -m pytest                    # tests
python -m uvicorn main:app --reload # desarrollo local
railway up                          # deploy a Railway
```
