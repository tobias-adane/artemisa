# ARTEMISA — 03 · MODELOS Y DATOS

> **Nota de reconciliación:** este documento reemplaza la versión anterior.
> `CLAUDE_backend.md` y `CLAUDE_frontend.md` habían divergido del modelo
> original (`Layer` con `classification`, `Thread` sin `reasoning`, mapeo
> de acción ambiguo, tabla `Camera` separada, faltaban `users` /
> `activity_log` / `conversations` / `user_preferences`). Las decisiones
> de esta reconciliación quedan resueltas acá — este doc es ahora la
> única fuente de verdad del schema. `artemisa_models.py` (backend) y
> `artemisa-types.ts` (frontend) lo espejan 1:1.

Los modelos en código están sincronizados campo por campo:
- `backend/artemisa_models.py` — Pydantic, para el servicio Python
- `frontend/lib/types/artemisa-types.ts` — TypeScript, para Next.js

**Si cambia el schema, se tocan los dos archivos a la vez** + las
migraciones de Supabase + este documento.

---

## 1. SCHEMA DE SUPABASE

```sql
users (
  id, email, name, timezone, account_type, home_type,
  area_type, has_children, custom_instructions,
  created_at, updated_at
)

spaces (
  id, user_id, name, camera_url, camera_type, status,
  last_frame, last_update
)
-- MVP: 1 usuario -> 1 space -> 1 cámara. La cámara vive embebida
-- en spaces (camera_url, camera_type), no como tabla separada.
-- No introducir una tabla `cameras` hasta que el producto soporte
-- multi-cámara por espacio explícitamente (fuera de scope del MVP).

layers (
  id, space_id, description, confidence, timestamp, metadata
)
-- SIN classification. Paso 2a (visión) solo describe — nunca
-- clasifica. Ver sección 3 para el porqué.

threads (
  id, space_id, layers, narrative, classification, confidence,
  severity_score, reasoning, alert_level, action,
  escalated_to_reasoning, start_time, end_time
)

emergency_contacts (
  id, user_id, name, phone, relationship, priority, confirmed
)

user_preferences (
  id, user_id, alert_sensitivity, cancel_timer_seconds,
  contact_cancel_timer_seconds, auto_call_enabled,
  do_not_disturb_start, do_not_disturb_end
)

conversations (
  id, user_id, messages JSONB, context JSONB
)

activity_log (
  id, user_id, thread_id, event_type, title, description,
  location, image_url, timestamp
)

dispatch_logs (
  id, thread_id, user_id, action, twilio_sid, status, created_at
)
-- Auditoría de cada llamada/mensaje individual de Twilio durante
-- un dispatch de Nivel 3 o 4. Un solo thread puede generar varias
-- filas (ej: call_user -> call_contacts -> call_911 en secuencia).
-- Retención larga por relevancia legal — ver sección 7.
```

### Restricción de schema no negociable

**`layers` y `threads` nunca tienen columnas de tipo blob/bytea para
contenido de cámara.** Solo texto y metadata. Esto está impuesto a
nivel de schema, no solo de política.

`activity_log.image_url` existe **solo** para imágenes que el
usuario sube explícitamente (feature "Attach" del chat, foto de
referencia de una mascota). **Nunca** un frame de cámara.

`spaces.camera_url` (URL RTSP) **nunca se expone al frontend**. Ver
sección 8.

---

## 2. ENUMS

### Classification
Resultado del Paso 2b (análisis) o Paso 3 (razonamiento).
```
normal | attention | emergency
```

### AlertLevel
Los 4 niveles de acción, como entero — para badges/orden en UI.
```
1 | 2 | 3 | 4
```

### ActionLevel
El nombre de la acción correspondiente a cada AlertLevel.
```
informar | alertar | contactar | emergencia
```

### SpaceStatus
```
active | offline | pending
```

### CameraType
```
rtsp    (único soportado en v1)
```

### ContactRelationship
```
spouse_partner | parent | sibling | friend | neighbor | other
```

### HomeType
```
apartment | house | small_business
```

### EventType
Para agrupar/filtrar en el feed de Activity.
```
thread_logged | dispatch_triggered | dispatch_cancelled |
space_connected | space_went_offline | space_reconnected
```

### AlertSensitivity
Afecta los dos umbrales del pipeline (ver sección 3): cuándo
`attention` escala a Paso 3, y el punto de corte de `severity_score`
entre Nivel 2 y Nivel 3.
```
low | balanced | high
```

---

## 3. LAYER VS THREAD — POR QUÉ LAYER NO CLASIFICA

Esta es la decisión de reconciliación más importante del documento.

**Layer (Paso 2a) es puramente factual.** No lleva `classification`.
El prompt de GPT-4o mini es explícito: *"No speculation, no emotion,
no judgment... that happens later"* (doc 02). Ponerle clasificación a
Layer no es solo un problema conceptual — es un problema de costo:
Paso 2a corre por cada frame con movimiento (~93.600 llamadas/mes por
cámara, doc 02 sección 9). Paso 2b corre en batches de ~60s, un orden
de magnitud menos. Clasificar en Layer obligaría a inyectar contexto
completo (rutina del hogar, threads recientes, estado de otros
espacios) en la llamada más frecuente del pipeline — multiplicando el
costo de la parte más barata para terminar reconciliando de todos
modos en Paso 2b. Es la peor combinación: más tokens y más eventos
desordenados.

**La clasificación vive una sola vez, en Thread (Paso 2b), amortizada
sobre todo el batch.**

### Continuidad de threads

Para que un thread sea una narrativa coherente y no un corte
arbitrario cada 60 segundos: un thread queda "abierto" (`end_time =
null`) mientras sigan llegando layers del mismo espacio dentro de una
ventana corta de silencio (2-3 min configurable). Si no llega ningún
layer nuevo dentro de esa ventana, el thread se cierra (`end_time` se
completa) y el próximo layer abre un thread nuevo. Esto es una
comparación de timestamps — no cuesta tokens — y evita fragmentar una
sola visita en varios eventos sin relación entre sí.

---

## 4. MAPEO CLASSIFICATION → ALERT_LEVEL / ACTION

Función determinística, implementada en ambos lenguajes
(`resolve_action_level()` en Python, `resolveActionLevel()` en TS).

```
classification: normal
  → alert_level 1 → action: informar
    (solo se registra, sin notificación)

classification: attention
  → severity_score < 0.7  → alert_level 2 → action: alertar
    (push notification, sin dispatch)
  → severity_score >= 0.7 → alert_level 3 → action: contactar
    (dispatch a contacto de confianza vía Twilio, CON ventana de
    cancelación — ver sección 6. No pasa por Paso 3: no es 911.)

classification: emergency
  → SIEMPRE escala a Paso 3 (GPT-4.1 mini) antes de resolver acción
  → severity_high == True  → alert_level 4 → action: emergencia
  → severity_high == False → alert_level 3 → action: contactar
    (degradado — el Paso 3 no confirmó, se trata como Nivel 3)
```

`severity_score` es un campo distinto de `confidence`:
- `confidence` = qué tan segura está la clasificación en sí (dispara
  el trigger #1 de escalado a Paso 3: `attention` con
  `confidence < 0.6`).
- `severity_score` = si la clasificación es correcta, qué tan grave
  es. Decide el corte entre Nivel 2 y Nivel 3 dentro de `attention`.

**0.7 es un punto de partida, no un valor final** — ajustar con datos
reales de la beta (mismo espíritu que doc 04, tensión #3). Ambos
umbrales (el de escalado a Paso 3 y el de severity_score) se modulan
por `user_preferences.alert_sensitivity`.

**Regla de oro sin cambios:** `emergencia` (Nivel 4) solo se alcanza
si `classification == emergency` **Y** el Paso 3 confirmó
`severity_high`. Nunca se ejecuta un Nivel 4 con evidencia de
Nivel 2. Lo nuevo es que Nivel 3 (`contactar`) ahora también puede
originarse desde `attention` con severidad alta — no solo como
degradación de una `emergency` no confirmada — pero un Nivel 3 nunca
llama al 911, así que el costo de un falso positivo es mucho menor
que el de Nivel 4 y no amerita el modelo de razonamiento completo.

La versión TypeScript incluye exhaustiveness check con `never` — si
se agrega una clasificación nueva sin actualizar la función,
TypeScript falla en compilación en vez de silenciosamente en
runtime.

### Dos "reasoning" distintos — no confundirlos

- `Thread.reasoning`: la explicación en **voz humana**, generada por
  Paso 2b (y reescrita si el thread pasa por Paso 3). Alimenta
  directamente el bloque "Why this mattered" en Activity. Nunca debe
  sonar a log de sistema.
- `EmergencyVerification.reasoning` (Paso 3, ver sección 5): el
  razonamiento técnico crudo de la verificación de emergencia. **Es
  solo para logs internos — nunca se muestra tal cual en la UI.**
  Cuando Paso 3 corre, el pipeline debe sintetizar su resultado y
  **reescribir** `Thread.reasoning` en voz humana antes de persistir
  — nunca volcar el reasoning técnico de Paso 3 directo a la UI.

---

## 5. VERIFICACIÓN DE EMERGENCIA (Paso 3) — output

```
class EmergencyVerification:
  severity_high: bool
  reasoning: str      # interno, nunca UI — ver nota arriba
  confidence: float
```

Se ejecuta solo cuando `classification == emergency` (siempre) o
cuando `attention` tiene `confidence < 0.6` (trigger #1 de doc 02).
El resultado alimenta `resolve_action_level()` (sección 4).

---

## 6. VENTANAS DE CANCELACIÓN

Dos ventanas distintas, ambas viven en `user_preferences`:

```
cancel_timer_seconds          → Nivel 4 (emergencia). Default: 30s.
contact_cancel_timer_seconds  → Nivel 3 (contactar).  Default: 90s.
```

Nivel 3 tiene ventana más larga porque, al no pasar por Paso 3, es la
única red de seguridad contra un falso positivo antes de molestar a
un contacto de confianza. Ambas ventanas son timers, no llamadas a
modelo — no tienen costo de IA.

---

## 7. RETENCIÓN Y BORRADO AUTOMÁTICO

```sql
-- Cron jobs en Supabase
layers:         DELETE WHERE created_at < NOW() - INTERVAL '30 days'
threads:        DELETE WHERE created_at < NOW() - INTERVAL '12 months'
activity_log:   DELETE WHERE created_at < NOW() - INTERVAL '12 months'
conversations:  DELETE WHERE created_at < NOW() - INTERVAL '6 months'
dispatch_logs:  DELETE WHERE created_at < NOW() - INTERVAL '5 years'
-- dispatch_logs tiene retención larga por relevancia legal ante
-- reclamos (ver doc 02 sección 6, nota legal pendiente).
-- users, spaces, emergency_contacts, user_preferences: sin borrado
-- automático — son datos de cuenta activa, se borran solo si el
-- usuario cierra la cuenta.
```

Siempre usar RLS (Row Level Security). Cada tabla tiene policy
`user_id = auth.uid()` (para `layers`/`threads`, vía `space_id` →
`spaces.user_id`).

---

## 8. CAMPOS CLAVE Y SU ROL

| Campo | Rol |
|---|---|
| `users.custom_instructions` | Texto libre acumulativo con la rutina del hogar. Se alimenta en onboarding **y** continuamente vía las preguntas contextuales de Artemisa. Es el input más importante de la Contextual Intelligence |
| `spaces.camera_url` | URL RTSP. **Nunca sale del backend** — ni a Supabase real-time del cliente, ni a ningún response de API. El frontend usa el tipo `SpacePublic` (sin este campo) |
| `spaces.last_frame` | Timestamp del último frame recibido — usado para detectar cámaras offline |
| `layers.description` | La descripción factual generada por GPT-4o mini en Paso 2a — sin clasificación, ver sección 3 |
| `threads.narrative` | La narrativa humana del evento — lo que se muestra en Activity |
| `threads.confidence` | Certeza de la clasificación — dispara escalado a Paso 3 si `attention` y `< 0.6` |
| `threads.severity_score` | Gravedad si la clasificación es correcta — decide Nivel 2 vs Nivel 3 dentro de `attention` |
| `threads.reasoning` | Por qué se llegó a esa clasificación, en voz humana. Alimenta "Why this mattered". Nunca el reasoning técnico crudo de Paso 3 |
| `threads.escalated_to_reasoning` | True si el thread pasó por Paso 3 antes de su clasificación final |
| `emergency_contacts.priority` | Orden de llamado, 1 = primero. El 911 siempre antecede a esta lista, no es una fila acá |
| `emergency_contacts.confirmed` | True solo después de que el contacto confirmó (vía Twilio) que acepta ser contactado en una emergencia — un contacto no confirmado no se llama |
| `user_preferences.cancel_timer_seconds` | Ventana de cancelación antes del dispatch de Nivel 4. Default 30 |
| `user_preferences.contact_cancel_timer_seconds` | Ventana de cancelación antes del dispatch de Nivel 3. Default 90 |
| `conversations.context` | Contexto de estado del hogar inyectado en cada respuesta (threads recientes). **No** es el historial de chat — eso va en `messages` |
| `dispatch_logs.action` | Qué llamada puntual se hizo (`call_user` \| `call_contacts` \| `call_911`) — un thread de Nivel 4 puede generar varias filas en secuencia |

---

## 9. THREADS VS ACTIVITY_LOG

Distinción importante que suele confundirse:

| | `threads` | `activity_log` |
|---|---|---|
| **Qué es** | Unidad de análisis de IA | Unidad de presentación en UI |
| **Origen** | Siempre generado por el pipeline | Puede venir de un thread **o** de eventos del sistema |
| **Ejemplo** | "Alguien tocó el timbre, nadie respondió" | Lo anterior, **más** "cámara reconectada", "dispatch cancelado" |

`activity_log.thread_id` es nullable justamente por esto — hay
entradas de actividad que no vienen de un thread.

---

## 10. FORMATO DE TELÉFONOS

`emergency_contacts.phone` usa formato **E.164**:
```
+5491122334455
```
Requerido por Twilio. La beta lanza en Argentina — el input de
teléfono en Onboarding/Settings usa `+54` como prefijo default,
validando el formato completo en el frontend antes de guardar.
