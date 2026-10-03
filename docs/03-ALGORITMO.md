# 03. Algoritmo

## Vista general

El mismo principio que un centro de monitoreo con guardias: la atención cara se
activa recién cuando hay una razón concreta. Nadie mira fijo una cámara vacía
con atención completa las 24 horas.

```
CASA (Cloud Bridge)                        NUBE (API + worker)
───────────────────                        ───────────────────
Lee cada cámara a través de go2rtc         PASO 1  Movimiento
y le entrega a la nube un frame            OpenCV sobre esos frames, sin IA.
por segundo, reducido. No analiza.  ─────▶  ¿Cambió algo que importe?
Desde la Fase 1 guarda además la             NO → el frame se descarta.
grabación, cifrada, en la casa.              SÍ ↓
                                           PASO 2a  Descripción
                                           Un modelo de visión convierte el
                                           frame en una oración. Se descarta
                                           el frame. Se escribe un layer.
                                                    │
                                           SESIONIZACIÓN
                                           Los layers de un space se agrupan
                                           en threads. Nace "composing".
                                                    │
                                           PASO 2b  Análisis
                                           Un modelo de texto arma la
                                           narrativa y clasifica contra la
                                           rutina de la casa.
                                             normal → queda en la línea
                                             dudoso o serio ↓
                                           PASO 3  Razonamiento profundo
                                           Otro modelo, más contexto,
                                           observaciones nuevas. Confirma,
                                           baja o sube la clasificación.
                                                    │
                                           PASO 4  Acción
                                           Nivel 1 a 4, según la fase.
```

La mayoría de los segundos no pasan del Paso 1. La mayoría de los movimientos no
pasan del Paso 2. Solo una fracción mínima llega al Paso 3, y por eso puede
darse el lujo de un modelo más caro y cuidadoso: se activa tan poco que su
costo en el total es despreciable.

Además del embudo hay tres caminos que inicia el usuario: la **lectura en
vivo**, el **chat** y la **voz**. Están al final de este documento.

Todas las constantes están en la tabla del final. Ningún valor numérico se
escribe directo en el código: se leen de configuración.

**Dónde corre cada cosa.** El Cloud Bridge es un puente: lee las cámaras a
través de go2rtc y entrega frames a la nube. **No analiza nada** (ver
`06-ARQUITECTURA.md`). El Paso 1, el Paso 2a y la sesionización corren en la
API. El Paso 2b, el Paso 3 y el Paso 4 corren en el worker. La API y el worker
se avisan cosas a través de Postgres (`signal_worker`, `signal_api`); el
mecanismo está en `06-ARQUITECTURA.md`.

**En la Fase 0** todo corre en la misma notebook, en un solo proceso: el lector
del bridge y el Paso 1 comparten memoria. **Antes de la Fase 1** se define cómo
viajan los frames del bridge a la nube: canal, tamaño, frecuencia y costo de
tráfico (ver `00-DECISIONES.md`). Hasta entonces, el camino es la subida de
frames de `06-ARQUITECTURA.md`.

---

## Paso 1. Movimiento (nube)

Corre en la API, sobre los frames que entrega el bridge. No usa IA ni llama a
ningún modelo: es aritmética sobre píxeles en la CPU del servidor. Este paso es
lo que hace viable la economía de todo lo demás: sin él, cada segundo de cada
cámara costaría una llamada a un modelo.

Cada space tiene **un único loop de movimiento**, porque el fondo que compara
vive en memoria. Con varias instancias de la API, los frames de un bridge se
fijan a la instancia de su canal (ver `06-ARQUITECTURA.md`, Escala).

### Lectura del stream (en el bridge)

- Se prefiere el **substream** de la cámara (la versión de baja resolución que
  casi todas las cámaras IP ofrecen). Es suficiente para detectar movimiento y
  cuesta una fracción de CPU y red.
- RTSP sobre TCP, no UDP: menos artefactos en redes domésticas.
- **Un hilo lector por cámara que lee continuamente y guarda solo el frame más
  reciente.** OpenCV acumula frames en un buffer; si se lee una vez por segundo
  de un stream a 25 fps sin este hilo, se reciben frames de hace varios segundos
  y todo el sistema llega tarde.
- Cada `CAPTURE_INTERVAL_S`, el bridge toma el último frame de cada cámara, lo
  reduce a `UPLOAD_MAX_WIDTH`, lo comprime en memoria y lo entrega a la nube.
  Nunca lo escribe a disco.
- Si el stream se corta: reconexión con espera creciente (1, 2, 4, 8… hasta
  `RECONNECT_BACKOFF_MAX_S`).

### Entrega del frame (en el bridge)

```python
# bridge/uploader.py
def deliver(space, frame, captured_at):
    img = resize(frame, max_width=UPLOAD_MAX_WIDTH)      # mantiene proporción
    jpeg = encode_jpeg(img, quality=JPEG_QUALITY)         # en memoria, sin EXIF
    upload(space.id, captured_at, frame_id=uuid4(), body=jpeg)
    del img, jpeg
```

El `frame_id` permite que la nube descarte duplicados si una subida se
reintenta. El resize ocurre en la casa: sale menos información, se usa menos
red, y el modelo de visión cobra por tamaño de imagen. Si la nube no responde,
el frame se pierde: el bridge no guarda frames para mandar después.

### Detección (en la nube)

Comparación contra un fondo que se adapta despacio, para que los cambios
graduales de luz (el sol moviéndose) no cuenten como movimiento.

`inbox` es el último frame que entregó el bridge para ese space, en memoria.

```python
# pipeline/motion.py
def motion_loop(space, inbox):
    background = None
    last_described = last_state = float("-inf")

    while running:
        sleep(CAPTURE_INTERVAL_S)
        now = monotonic()
        latest = inbox.latest                       # (jpeg, frame, captured_at, received_at) o None
        if latest is None or is_stale(latest, STALE_FRAME_S):
            continue                                # la salud la reporta el bridge

        small = resize(latest.frame, width=ANALYSIS_WIDTH)
        gray = gaussian_blur(to_gray(small), BLUR_KERNEL)
        if background is None:
            background = gray.astype("float32")
            continue

        diff = absdiff(gray, background.astype("uint8"))
        mask = dilate(threshold(diff, PIXEL_DIFF_THRESHOLD))
        changed = count_nonzero(mask) / mask.size
        accumulate_weighted(gray, background, BG_LEARNING_RATE)
        boosted = space.boost_until is not None and now < space.boost_until

        if changed >= GLOBAL_CHANGE_RATIO:
            # Luz que se prende o apaga, cambio a infrarrojo, salto de exposición.
            # No es movimiento: se reinicia el fondo y se refresca el estado.
            background = gray.astype("float32")
            if now - last_state >= STATE_MIN_INTERVAL_S:
                handle_frame(space, latest, kind="state")
                last_state = now

        elif changed >= space.motion_threshold or boosted:
            if now - last_described >= describe_interval(space, now):
                handle_frame(space, latest, kind="motion", motion_ratio=changed)
                last_described = now

        elif now - last_state >= STATE_REFRESH_MAX_S:
            handle_frame(space, latest, kind="state")
            last_state = now

        del small, gray                             # nada se escribe a disco, nunca


def describe_interval(space, now) -> float:
    boosted = space.boost_until is not None and now < space.boost_until
    return BOOSTED_INTERVAL_S if boosted else DESCRIBE_MIN_INTERVAL_S
```

`handle_frame` pasa el JPEG al Paso 2a en memoria. Los frames que no pasan el
Paso 1 se descartan al llegar el siguiente.

**El refuerzo.** Cuando el Paso 3 pide mirar de nuevo un space, el worker le
avisa a la API (`signal_api("boost", ...)`) y el loop fija `space.boost_until`.
Mientras dura, pasa un frame `motion` al Paso 2a cada `BOOSTED_INTERVAL_S`
**haya movimiento o no**. Es a propósito: una persona que quedó quieta en el
piso no genera movimiento, y es exactamente lo que hay que volver a mirar.

`space.motion_threshold` es configurable por space. Una cocina con cortinas que
se mueven necesita un umbral más alto que un pasillo.

### Tipos de frame que pasan al Paso 2a

| Tipo | Cuándo | Para qué |
|---|---|---|
| `motion` | Hubo movimiento (como máximo uno cada `DESCRIBE_MIN_INTERVAL_S` por space), o hay un refuerzo activo (uno cada `BOOSTED_INTERVAL_S`) | Crear layers y threads |
| `state` | Cambio global de luz, o nada se movió en `STATE_REFRESH_MAX_S` | Mantener actualizado el estado del space. No crea threads. |

La lectura en vivo no pasa por acá: usa el último frame del `inbox` (ver
Lectura en vivo). El reporte de salud de cada cámara lo manda el bridge y no
lleva imagen: es solo "sigo viendo esta cámara" o "no la estoy viendo".

---

## Paso 2a. Descripción (API)

Se ejecuta en la API cuando el Paso 1 le pasa un frame (`motion` o `state`).
Convierte la imagen en una oración factual y la imagen deja de existir.

```python
# pipeline/describe.py
async def on_frame(space, kind, jpeg: bytes, captured_at, meta):   # lo llama handle_frame
    try:
        out = await describe(jpeg, space, locale=owner_locale(space))  # reintentos: DESCRIBE_RETRIES
        # A partir de acá el frame no se usa más.
        await update_space_state(space.id, description=out.description,
                                 people_present=out.people_count > 0,
                                 at=captured_at)
        if kind == "state":
            return

        await set_last_motion(space.id, captured_at)
        thread = await sessionize(space, captured_at,     # thread y layer, en una transacción
                                  layer=Layer(description=out.description, flags=out.flags))
        if set(out.flags) & URGENT_FLAGS:
            await signal_worker("analyze_now", thread_id=thread.id, fast_path=True)
    finally:
        del jpeg
```

Salida del modelo:

```json
{ "description": "Someone walks up carrying a box.", "flags": [], "people_count": 1 }
```

`flags` es una lista cerrada de hechos observables, nunca juicios:
`person_on_floor`, `smoke_or_fire`, `glass_broken`, `door_forced`,
`weapon_visible`, `water_leak`. Todos ellos son `URGENT_FLAGS`: cualquiera
activa el camino rápido.

El prompt completo y el modelo están en `04-MODELOS.md`.

### Garantías sobre el frame

- El frame llega como **cuerpo crudo de la request** (`Content-Type:
  image/jpeg`) y se lee en memoria. No se usa el manejo de archivos subidos del
  framework, que escribe a un archivo temporal en disco cuando el archivo supera
  cierto tamaño.
- Hay un límite de tamaño de cuerpo (`MAX_FRAME_BYTES`). Lo que lo supera se
  rechaza.
- El frame no se loguea, no se manda a Sentry, no se guarda en ninguna caché.
- Si la descripción falla después de `DESCRIBE_RETRIES` reintentos (y del modelo
  de respaldo), se descarta el frame. **No se puede encolar para después**: un
  frame guardado para reintentar es un frame guardado. Es un costo aceptado de la
  arquitectura.

La descripción ocurre **antes** de la sesionización. Así nunca existe un thread
sin al menos una observación.

---

## Sesionización: cómo nacen y terminan los threads

Un thread es un momento de un space. Los layers se agrupan por cercanía en el
tiempo.

**Thread abierto:** un thread con `status` en `composing` o `active` y
`end_time` vacío. Cada space tiene como máximo uno, y la base lo garantiza.

**Regla:** un layer nuevo se suma al thread abierto del space si el último layer
de ese thread fue hace `THREAD_GAP_S` segundos o menos. Si pasó más, el thread
abierto **termina** (se le pone `end_time`) y nace uno nuevo.

```python
async def sessionize(space, t, layer) -> Thread:
    async with transaction():
        await advisory_lock("space", space.id)       # un solo escritor por space
        current = await get_open_thread(space.id)
        if current and (t - current.last_layer_at) <= THREAD_GAP_S:
            # greatest y least: un frame capturado antes puede terminar de describirse después
            await touch_thread(current.id, last_layer_at=max(current.last_layer_at, t),
                               start_time=min(current.start_time, t))
            thread = current
        else:
            if current:
                # Ya no recibe layers. El worker lo narra si hace falta y lo cierra.
                await set_end_time(current.id, current.last_layer_at)
            thread = await create_thread(space_id=space.id, user_id=space.user_id,
                                         status="composing", start_time=t,
                                         last_layer_at=t)
        await insert_layer(thread.id, space.id, layer)   # en la misma transacción
        return thread
```

**Dos correcciones al pseudocódigo (paso 6).**

- **`last_layer_at` nunca retrocede.** Con varias descripciones en vuelo, un
  frame capturado antes puede terminar de describirse después que uno
  posterior. `touch_thread` usa `greatest(last_layer_at, t)`: el reloj del thread
  no vuelve atrás y no cambia cuándo vence `THREAD_GAP_S`. Por lo mismo,
  `start_time` usa `least(start_time, t)`: un thread no empieza después de su
  primer layer.
- **El thread y su layer se escriben en una sola transacción.** Antes
  `sessionize` creaba el thread y `insert_layer` iba aparte: un fallo entre los
  dos dejaba un thread sin observaciones. Con una transacción existen los dos o
  ninguno, así nunca existe un thread sin al menos una observación.

La API nunca cierra un thread ni lo analiza: solo lo termina. Narrarlo y
cerrarlo es trabajo del worker. Así un thread que terminó sin haber sido
narrado todavía (un momento muy corto) se narra igual antes de cerrarse.

### Estados

```
composing ──primer análisis──▶ active ──termina (end_time)──▶ análisis final ──▶ closed
     └──────────termina sin narrar──────▶ análisis final ─────────────────────────┘
```

- **composing:** tiene layers, no tiene narrativa. La app muestra "Artemisa is
  composing the moment…".
- **active:** tiene narrativa. Puede recibir más layers (si no terminó) y
  reanalizarse.
- **closed:** terminó y está narrado. `end_time` es la hora del último layer.
  Un thread nunca pasa a `closed` sin narrativa.

En la primera versión los threads son por space. Una persona que entra por la
puerta y camina al living produce dos threads. Relacionarlos es tarea del Paso
3, que ve todos los spaces, y queda en su razonamiento.

---

## Paso 2b. Análisis (worker)

Convierte las observaciones de un thread en una narrativa humana y decide si
importa.

### Cuándo se analiza un thread

El scheduler del worker revisa cada `SCHEDULER_TICK_S` todos los threads que no
están `closed`, y lanza una tarea por thread. Las tareas corren en paralelo, con
un máximo de `WORKER_CONCURRENCY_PER_USER` por usuario. Cada tarea toma un lock
del thread, lo vuelve a leer de la base y toma **una sola decisión**:

```python
async def scheduler_tick():
    for th in await get_threads(status_in=("composing", "active")):
        if not is_running(th.id):
            spawn(process_thread(th.id), limit_key=th.user_id)

async def process_thread(thread_id, fast_path=False):
    async with advisory_lock("thread", thread_id):
        th = await load_thread(thread_id)            # siempre datos frescos
        now = utcnow()
        pending = th.last_analyzed_at is None or th.last_layer_at > th.last_analyzed_at
        quiet = now - th.last_layer_at

        if fast_path:
            await analyze(th, fast_path=True)
            return

        if th.end_time is not None or quiet >= THREAD_GAP_S:   # terminó
            if th.end_time is None:
                th = await set_end_time(th.id, th.last_layer_at)
            if pending:
                th = await analyze(th)                # pasada final
            if th.narrative is not None:
                await set_closed(th.id)
            return

        if th.status == "composing":
            if quiet >= SETTLE_S or (now - th.start_time) >= MAX_COMPOSE_S:
                await analyze(th)
        elif pending and (now - th.last_analyzed_at) >= reanalyze_interval(th, now):
            await analyze(th)


def reanalyze_interval(th, now) -> float:
    # Los primeros minutos de un momento se siguen de cerca; después, con calma.
    # Una familia en la cocina durante una hora no necesita una narrativa por minuto.
    if (now - th.start_time) <= REANALYZE_FAST_WINDOW_S:
        return REANALYZE_S
    return REANALYZE_SLOW_S
```

El camino rápido llega por `signal_worker("analyze_now", fast_path=True)` y
ejecuta `process_thread(thread_id, fast_path=True)` sin esperar al tick.

Notas de implementación (paso 7):

- **El lock del thread es de sesión, no de transacción**
  (`pg_advisory_lock` y `pg_advisory_unlock`): el análisis llama a un modelo y
  no conviene una transacción abierta durante segundos.
- **`set_end_time` toma el lock del space**, el mismo de la sesionización, y
  solo termina el thread si sigue sin `end_time` y su último layer tiene más de
  `THREAD_GAP_S`. Si entró un layer entre la lectura y el update, no lo termina
  y decide el próximo tick.

En palabras: un momento corto se narra `SETTLE_S` segundos después de que se
calma. Un momento largo tiene su primera narrativa como máximo a los
`MAX_COMPOSE_S` segundos, se actualiza cada `REANALYZE_S` durante sus primeros
`REANALYZE_FAST_WINDOW_S`, y después cada `REANALYZE_SLOW_S`. Un flag urgente
saltea todos los tiempos.

### Contexto que recibe el modelo

Esto es lo que convierte al análisis en Contextual Intelligence y no en un
clasificador genérico:

1. Los layers del thread, con hora al segundo y flags.
2. `custom_instructions`: la rutina que el usuario enseñó.
3. Los últimos `CONTEXT_RECENT_THREADS` threads de hoy en ese space, con hora,
   narrativa y clasificación.
4. El estado actual de los otros spaces (su última descripción y hace cuánto).
5. Día de la semana, hora local y zona horaria.
6. La sensibilidad elegida por el usuario (`low`, `balanced`, `high`).
7. Si es un reanálisis, la narrativa anterior del mismo thread.
8. El idioma en el que tiene que escribir.

La plantilla exacta está en `04-MODELOS.md`.

### Qué modelo

Por defecto, el rol `analyze`. Se usa `analyze_hard` cuando se cumple cualquiera
de estas condiciones:

- Es horario nocturno (`night_start` a `night_end` del usuario, hora local).
- Algún layer del thread tiene flags.
- Algún layer menciona algo que el usuario pidió vigilar en sus custom
  instructions (coincidencia de palabras clave, sin modelo). Regla simple del
  laboratorio: alguna palabra de 4 letras o más de las custom instructions
  aparece en un layer, comparando en minúsculas y sin acentos.
- El análisis anterior del mismo thread tuvo confianza menor a
  `LOW_CONFIDENCE`.

### Salida

```json
{
  "narrative": "Someone rang the bell at 4:40. Nobody answered.",
  "classification": "attention",
  "confidence": 0.78,
  "reasoning": "You weren't expecting anyone, and it's not when deliveries usually come. But there was no sign of anyone trying to get in.",
  "escalate": false,
  "escalate_reason": null,
  "people_present": false,
  "unfamiliar_person": true
}
```

`reasoning` es parte nativa de la salida, no algo a construir después: es lo que
el usuario lee como "Why I'm telling you".

### Qué pasa después

Si el thread ya pasó por el Paso 3, su clasificación y su razonamiento son los
del Paso 3 y **el análisis rápido no los pisa**: solo actualiza la narrativa. Si
encuentra algo más grave, vuelve a mandar el thread al Paso 3, que es el único
que decide.

```python
async def analyze(th, fast_path=False) -> Thread:
    ctx = await build_analysis_context(th)
    role = "analyze_hard" if needs_hard_model(th, ctx) else "analyze"
    try:
        out = await llm_json(role, ANALYZE_PROMPT, ctx, schema=AnalysisOut)  # con fallback de rol
    except ModelFailure:
        return await on_analysis_failure(th)

    fields = dict(narrative=out.narrative, people_present=out.people_present,
                  unfamiliar_person=th.unfamiliar_person or out.unfamiliar_person,
                  status="active", last_analyzed_at=utcnow(), analysis_failures=0)
    if not th.escalated_to_reasoning:
        fields |= dict(classification=out.classification,
                       confidence=out.confidence, reasoning=out.reasoning)
    th = await update_thread(th.id, **fields)
    if out.people_present is not None:
        await set_space_people_present(th.space_id, out.people_present)

    if needs_reasoning(th, out, fast_path):
        await reason(th, urgent=fast_path or out.classification == "emergency")
    elif not th.escalated_to_reasoning and out.classification == "attention":
        await act(th, "informar")
    # normal: no hay acción. emergency nunca llega a actuar desde acá.
    return await load_thread(th.id)
```

---

## Paso 3. Razonamiento profundo (worker)

El paso reservado para cuando hace falta pensar en serio. Más caro, más lento y,
por diseño, raro.

### Cuándo se activa

Para un thread que todavía no pasó por el Paso 3, se activa si se cumple
cualquiera de estas condiciones. Son explícitas, no "a veces":

1. El análisis clasificó `attention` con confianza menor a `LOW_CONFIDENCE`.
2. El análisis clasificó `emergency`. Siempre se verifica antes de actuar: un
   falso positivo tiene un costo real.
3. El camino rápido: un layer trajo un flag urgente.
4. El análisis pidió `escalate: true`.
5. El análisis marcó `unfamiliar_person` en este thread **y** hubo al menos
   `UNFAMILIAR_REPEAT_COUNT` threads con una persona desconocida dentro de
   `UNFAMILIAR_WINDOW_S`, en cualquier space.

Un thread que ya pasó por el Paso 3 vuelve a pasar solo si el análisis nuevo es
más grave que la clasificación que decidió el Paso 3, o si aparecieron flags
urgentes en layers posteriores a su último razonamiento.

```python
def needs_reasoning(th, out, fast_path) -> bool:
    if th.escalated_to_reasoning:
        return (severity_rank(out.classification) > severity_rank(th.classification)
                or has_urgent_flags_since(th.id, th.last_reasoned_at))
    return (fast_path
            or out.classification == "emergency"
            or (out.classification == "attention" and out.confidence < LOW_CONFIDENCE)
            or out.escalate
            or (out.unfamiliar_person and unfamiliar_person_returning(th.user_id)))
```

### Qué hace distinto

- Otro modelo, de otro proveedor, con esquemas estrictos. La calidad de este paso
  se evalúa en la Fase 0 (ver `04-MODELOS.md`).
- Más contexto: los threads de las últimas `REASON_HISTORY_HOURS` horas de toda
  la casa, no solo de ese space, y el estado de todos los spaces.
- **Mira de nuevo.** Si el thread sigue abierto, pide un refuerzo del Paso 1 en
  ese space por `BOOST_DURATION_S`. Si no es urgente, espera `BOOST_WAIT_S` para
  sumar esas observaciones antes de decidir. Si es urgente, decide ya con lo que
  tiene, y el refuerzo alimenta los reanálisis siguientes.

```python
async def reason(th, urgent: bool):
    if th.end_time is None:
        await signal_api("boost", space_id=th.space_id,
                         interval_s=BOOSTED_INTERVAL_S, duration_s=BOOST_DURATION_S)
        if not urgent:
            await sleep(BOOST_WAIT_S)
    ctx = await build_reasoning_context(await load_thread(th.id))
    try:
        out = await llm_json("reason", REASON_PROMPT, ctx, schema=ReasoningOut)  # con fallback de rol
    except ModelFailure:
        return await on_reasoning_failure(th)

    th = await update_thread(th.id,
        classification=out.classification, severity_high=out.severity_high,
        reasoning=out.reasoning, narrative=out.narrative,
        escalated_to_reasoning=True, last_reasoned_at=utcnow())

    await act(th, resolve_action_level(out.classification, out.severity_high))
```

Notas de implementación (paso 8):

- **Un refuerzo por razonamiento.** `reason` no pide otro refuerzo mientras
  siga vigente el último que pidió ese thread (`last_reasoned_at` +
  `BOOST_DURATION_S`): así los layers del propio refuerzo no encadenan
  refuerzos.
- **`unfamiliar_person_returning` cuenta threads distintos:** este thread más
  al menos `UNFAMILIAR_REPEAT_COUNT` − 1 threads más del usuario con un
  desconocido y un layer dentro de `UNFAMILIAR_WINDOW_S`.
- **`{escalate_reason | trigger}`:** si el análisis no dio `escalate_reason`, va
  una frase corta en inglés con la regla que activó el Paso 3. Viven en
  `pipeline/reason.py` y solo las lee el modelo.
- **"WHOLE HOME"** muestra cada thread con día y hora local del usuario
  (`Sat 14:40`).

El Paso 3 **puede bajar** la clasificación (una emergencia que no era, un
`attention` que era normal) o subirla. Si baja después de que Artemisa ya actuó,
lo hecho no se deshace: queda en `dispatches`, `action` sigue guardando el nivel
más alto alcanzado, y el razonamiento nuevo explica el cambio. Su razonamiento
reemplaza al del Paso 2b y menciona el detalle decisivo ("It's the handle that
changed my mind."). Cuando corresponde, dice también qué decidió no hacer.

### Resolución del nivel

Función determinística. Vive solo en el servidor (`05-DATOS.md`); la app nunca
decide niveles.

```
normal     → ninguna acción
attention  → severity_high ? alertar    : informar
emergency  → severity_high ? emergencia : contactar
```

`emergencia` solo es alcanzable con `classification == emergency` y
`severity_high == true`, y `severity_high` solo lo decide el Paso 3. Nunca se
actúa en nivel 4 con evidencia de un análisis rápido. La base de datos lo impide
también (`05-DATOS.md`).

---

## Paso 4. Acción (worker)

Esta es la función completa. **Cada rama se implementa en su fase:** en la Fase
0 y la Fase 1 existen solo las notificaciones; las llamadas se agregan en la
Fase 2a; los contactos y los servicios de emergencia, en la Fase 2b.

```python
LEVEL_RANK = {None: 0, "informar": 1, "alertar": 2, "contactar": 3, "emergencia": 4}

async def act(th, level, *, interruption=None, ignore_quiet=False):
    if LEVEL_RANK[level] <= LEVEL_RANK[th.action]:
        return                                   # nunca repite, nunca baja
    await set_thread_action(th.id, level)        # la base valida el nivel 4
    quiet = (not ignore_quiet) and in_quiet_hours(await get_prefs(th.user_id),
                                                  local_now(th.user_id))

    if level == "informar":
        if interruption or not quiet:
            await push(th, level, interruption or "passive")
    elif level == "alertar":
        await push(th, level, "passive" if quiet else "time_sensitive")
        if PHASE >= "2a" and not quiet:
            schedule(call_owner_if_unopened, th, after=ALERT_CALL_DELAY_S)
    elif level == "contactar":
        await push(th, level, "time_sensitive")
        if PHASE >= "2a":
            await call_owner(th)
        if PHASE >= "2b":
            await contact_chain(th)              # contactos por prioridad
    elif level == "emergencia":
        await push(th, level, "critical")
        if PHASE >= "2a":
            await call_owner(th)
        if PHASE >= "2b":
            await emergency_protocol(th)         # ventana de cancelación primero
```

- `push` primero escribe una fila en `dispatches` (`queued`), después envía la
  notificación con `thread_id` y `dispatch_id` en los datos, y actualiza el
  estado con los recibos del proveedor (entregado, abierto, fallido).
- La notificación lleva como título el nombre del space y como cuerpo la
  narrativa. Al tocarla abre el detalle del thread.
- El dispatch corre en el servidor. No depende de que la app esté abierta.
- En la Fase 2b, la ventana de cancelación dura `cancel_timer_seconds` y vive en
  la llamada misma ("press 1 to cancel") y en el mensaje.
- "What I did" en la app se arma leyendo `dispatches`, no `action`. Ver
  `02-PRODUCTO.md`.
- `dispatches` registra solo acciones sobre threads. El aviso de cámara sin
  conexión es un aviso de sistema: no pertenece a un thread y no se registra
  ahí.

---

## Estado de la casa

### Estado de cada space

Cada frame `motion` o `state` que se describe actualiza en el space:

- `state_description`: la última descripción de lo que se ve.
- `state_updated_at`: cuándo.
- `people_present`: si hay gente, según la descripción o el análisis.
- `last_motion_at`: la hora del último frame de movimiento (solo `motion`).

### Artemisa nunca finge que ve

Es una regla de producto, no un detalle técnico: **Artemisa siempre dice qué
puede ver.** Un producto de seguridad que deja al usuario creyendo que está
cuidado mientras está ciego es peor que no tener nada. Por eso hay dos niveles
de pérdida de señal, y el más grave se avisa rápido.

#### La casa entera sin señal

Si el Cloud Bridge pierde contacto con la nube (corte de luz, corte de internet,
alguien la desenchufó), Artemisa no ve **ninguna** cámara. Es el estado más
importante después de una emergencia.

**La señal de vida es un latido, no la conexión.** Cuando se corta la luz de la
casa, la conexión con la nube no se cierra: del lado del servidor queda abierta,
sin nadie del otro lado, a veces durante minutos. Por eso el bridge manda
`heartbeat` por el canal de control cada `BRIDGE_HEARTBEAT_S`, aunque no tenga
cámaras, y la API anota `last_seen_at` con cada mensaje que recibe. El worker
decide mirando solo la base, así que funciona aunque la API se reinicie.

```python
async def on_bridge_message(bridge, msg):        # API, cada mensaje del canal de control
    await touch_bridge(bridge.id)                # last_seen_at = ahora
    if msg.type == "hello":                      # la caja (re)abrió el canal
        # Atómico: status = online, connected_at = ahora, limpia offline_since
        # y offline_notified. Devuelve cómo estaba antes.
        before = await set_bridge_online(bridge.id)
        if before.status == "offline" and before.offline_notified:
            await push_system_notice(bridge.user_id, key="push.homeBack",
                                     start=before.offline_since, end=utcnow(),
                                     interruption="passive")

async def bridge_tick():                         # worker, cada HEALTH_TICK_S
    # Atómico: las cajas online sin ningún mensaje desde hace más de
    # BRIDGE_OFFLINE_AFTER_S pasan a offline, con offline_since = last_seen_at
    # y offline_notified = true. Devuelve las que cambiaron.
    for b in await mark_silent_bridges_offline(BRIDGE_OFFLINE_AFTER_S):
        await push_system_notice(b.user_id, key="push.homeBlind",
                                 time=b.offline_since,
                                 interruption="time_sensitive")  # passive en quiet hours
```

Con los valores por defecto, el usuario se entera en unos 2 minutos, y vuelve a
enterarse cuando Artemisa recupera la vista. Los cortes de luz pueden ser
frecuentes: son dos avisos por corte, uno al perder la señal y otro al volver.
Los cortes de menos de `BRIDGE_OFFLINE_AFTER_S` no se avisan.

#### Una cámara sin señal

Si la caja está conectada pero una cámara deja de responder, es un problema de
esa cámara, no de la casa.

Solo un reporte de salud **positivo** actualiza `last_health_at`. Los reportes
negativos se registran en logs y no cuentan como señal de vida.

```python
async def on_health(space, ok: bool):            # API, al recibir un reporte
    if not ok:
        return log_camera_problem(space)
    await set_last_health(space.id, utcnow())
    if space.status == "offline":
        await set_active(space.id)               # limpia offline_since y offline_notified

async def health_tick():                         # worker, cada HEALTH_TICK_S
    # Solo cámaras de cajas conectadas: si la casa entera está sin señal, ya
    # avisó bridge_tick, y no se repite cámara por cámara.
    for space in await get_spaces(status_in=("active", "offline"), bridge_status="online"):
        # El silencio se cuenta desde lo más reciente entre el último reporte
        # sano y la última vez que la caja se conectó. Así, al volver de un
        # corte, las cámaras no pasan a offline antes de su primer reporte.
        silent = utcnow() - max(space.last_health_at, space.bridge_connected_at)
        if space.status == "active" and silent > OFFLINE_AFTER_S:
            await set_offline(space.id, since=utcnow())
        elif (space.status == "offline" and not space.offline_notified
              and utcnow() - space.offline_since >= OFFLINE_NOTIFY_AFTER_S):
            await push_system_notice(space.user_id, key="push.cameraOffline",
                                     space=space.name, interruption="passive")
            await mark_offline_notified(space.id)
```

Con los valores por defecto, el aviso llega a los 10 minutos sin señal de la
cámara (`OFFLINE_AFTER_S` + `OFFLINE_NOTIFY_AFTER_S`).

### Línea de estado del encabezado

Se calcula en la app, a partir de los threads, los spaces y el estado del
Cloud Bridge que ya tiene cargados. No llama a ningún modelo. La app carga los
threads desde el comienzo del día local o desde hace `HOME_LOOKBACK_HOURS`, lo
que sea antes (así una emergencia de las 23:30 sigue visible a las 00:30).

```ts
function homeStateKey(s: HomeSnapshot): StateKey {
  if (s.emergencyWithin(HOME_LOOKBACK_HOURS))      return "emergency";   // pendiente de diseño
  if (s.bridge?.status === "offline" && s.bridge.offline_since) return "blind"; // {time} = offline_since
  if (s.threads.length === 0 && s.firstSpaceCreatedWithin(DAY1_WINDOW_S)) return "day1";
  if (s.attentionWithin(ATTENTION_RECENT_HOURS))   return "attentionRecent";
  if (s.attentionToday >= 2)                       return "attentionFew";
  if (s.attentionToday === 1)                      return "attentionOne";
  if (s.offlineSpaces.length > 0)                  return "offline";     // usa el primero
  if (s.activeSpaces.length > 0 &&
      s.activeSpaces.every(sp => sp.people_present === false)) return "empty";
  return "default";
}
```

- `attentionToday` cuenta los threads de hoy con clasificación `attention` o
  `emergency`.
- `attentionWithin(h)` y `emergencyWithin(h)` miran `start_time` de los threads
  cargados.
- El orden importa: el encabezado nunca dice que todo está bien, ni que "todo lo
  demás está tranquilo", si la línea muestra algo que merece atención. Y si el
  Cloud Bridge no tiene señal, el encabezado lo dice antes que cualquier otra
  cosa salvo una emergencia, aunque sea el primer día.
- `blind` exige `offline_since`: una caja recién preparada que todavía no se
  conectó nunca no cuenta como casa sin señal.
- El estado de la caja llega por tiempo real, igual que el de los spaces.

Los textos de cada clave están en `02-PRODUCTO.md`. El saludo sale de la hora
local: 5 a 12 morning, 12 a 19 afternoon, 19 a 22 evening, 22 a 5 night.

---

## Lectura en vivo (API)

Cuando el usuario abre el feed en vivo de un space, Artemisa dice lo que ve
ahora. Es presente y no crea layers ni threads: no es un evento.

```python
async def live_read(user, space) -> LiveRead:
    if await bridge_is_offline(space.bridge_id):
        raise HomeBlind                          # sin frame no hay presente: no se inventa
    cached = live_cache.get(space.id)            # solo texto
    if cached and cached.age < LIVE_READ_CACHE_S:
        return cached
    latest = inbox_for(space.id).latest          # el último frame que entregó el bridge
    if latest is None or is_stale(latest, LIVE_FRAME_TIMEOUT_S):
        raise CameraUnavailable                  # tampoco se inventa
    jpeg = latest.jpeg                           # en memoria
    try:
        ctx = {
            "space": space.name,
            "last_description": space.state_description,
            "minutes_since_motion": minutes_since(space.last_motion_at),
            "recent_threads": await threads_last_hours(space.id, LIVE_READ_HISTORY_HOURS),
            "other_spaces": await other_spaces_state(user.id, space.id),  # ídem
            "local_time": local_now(user.id),
            "household": user.custom_instructions,
            "locale": user.locale,
        }
        out = await llm_json("live_read", LIVE_READ_PROMPT, ctx,
                             image=jpeg, schema=LiveReadOut)
    finally:
        del jpeg
    live_cache.set(space.id, out)
    return out                                   # {"headline": ..., "body": ...}
```

El video en sí no pasa por este camino: va por el relay de streaming (ver
`06-ARQUITECTURA.md`). La lectura usa el último frame que entregó el bridge,
que ya está en memoria de la API y se descarta al llegar el siguiente.

---

## Chat (API)

Responde preguntas sobre la casa. Puede ser general ("Ask anything") o sobre un
thread ("Ask something").

```python
async def chat(user, message, spoken=False, thread_id=None, conversation_id=None):
    conv = await get_or_create_conversation(user.id, thread_id, conversation_id)
    await save_message(conv.id, "user", message, spoken=spoken)
    ctx = {
        "today": await threads_today(user.id),   # hora, space, narrativa, clasificación
        "spaces": await spaces_state(user.id),   # o "sin señal desde" si no se ve
        "household": user.custom_instructions,
        "name": user.first_name,
        "local_time": local_now(user.id),
        "locale": user.locale,
    }
    if thread_id:
        ctx["focus"] = await thread_with_layers_and_dispatches(thread_id)
    history = await last_messages(conv.id, CHAT_HISTORY_MESSAGES)

    text = ""
    async for token in llm_stream("chat", CHAT_PROMPT, ctx, history, message):
        text += token
        yield token                               # SSE hacia la app
    await save_message(conv.id, "assistant", text)
```

Reglas que el prompt impone:

- Responde solo con lo que está en el contexto. Si no sabe, lo dice.
- Si le piden mostrar o reproducir algo del pasado, explica que Artemisa no
  guarda grabaciones, describe lo que vio, y ofrece "See now" para mirar en vivo.
- Breve, en la voz de Artemisa, en el idioma del usuario.

En la primera versión el chat es de solo lectura: no modifica las custom
instructions. Que Artemisa aprenda de la conversación ("that's the plumber, he
comes on Tuesdays") es una fase posterior.

---

## Voz

**Entrada.** El reconocimiento de voz corre en el teléfono, con el idioma del
usuario. El texto parcial aparece en el input mientras el usuario habla; el
resultado final se envía al chat con `spoken: true`. No hay costo de API.

**Salida.** Artemisa habla cuando `voice_enabled` está activo y:

- el usuario hizo la pregunta hablando: se lee la respuesta;
- la app está abierta y llega un thread nuevo que no es `normal`: se lee su
  narrativa.

El audio se genera en el backend (`POST /v1/tts`) para no exponer claves en la
app. Se cachea en memoria por hash del texto y la voz. No se persiste.

---

## Fallos y bordes

| Situación | Comportamiento |
|---|---|
| Falla la descripción | `DESCRIBE_RETRIES` reintentos con espera, después el rol de respaldo. Si todo falla, se descarta el frame. |
| Falla el análisis | Se usa el rol de respaldo. Si también falla, se suma 1 a `analysis_failures` y se reintenta en el próximo tick. |
| El análisis falla `ANALYSIS_MAX_FAILURES` veces seguidas | Si el thread ya tenía narrativa, se deja como está. Si no tenía: con un flag urgente en sus layers, la narrativa pasa a ser el texto de sistema `fallback.urgentNarrative`, la clasificación `attention`, y se ejecuta el **aviso de resguardo**. Sin flags urgentes, la narrativa pasa a ser la última descripción y la clasificación `normal`. |
| Falla el razonamiento (Paso 3) | Se usa el rol de respaldo. Si también falla: si el análisis dijo `emergency` o hay flags urgentes, **aviso de resguardo**; si dijo `attention`, `act(th, "informar")`. El thread no queda marcado como razonado, así que el próximo análisis puede volver a intentarlo. |
| JSON inválido | Un reintento indicando el error. Después, se trata como fallo. |
| El Cloud Bridge sin señal | A los `BRIDGE_OFFLINE_AFTER_S` sin mensajes pasa a sin señal y se avisa una sola vez por toda la casa; al volver, otro aviso con el tiempo que no pudo ver (ver Artemisa nunca finge que ve). No se avisa cámara por cámara. La caja no guarda frames para mandar a la nube después (la grabación de la Fase 1 queda en la casa y no se sube). |
| Frame duplicado | Se descarta por `frame_id`. La API recuerda los ids vistos durante `FRAME_DEDUP_WINDOW_S`. |
| Reloj del bridge desfasado | Si `captured_at` difiere más de `MAX_CLOCK_SKEW_S` de la hora del servidor, se usa la hora de recepción y se registra el desfase. |
| Muchas cámaras con movimiento a la vez | Cada space respeta su propio intervalo de descripción. El worker procesa threads en paralelo, hasta `WORKER_CONCURRENCY_PER_USER` por usuario. |

**Aviso de resguardo.** Es la única forma de interrumpir con urgencia sin un
Paso 3 completo, y existe para cuando los modelos no responden y hay señales de
riesgo: `act(th, "informar", interruption="time_sensitive", ignore_quiet=True)`.
Llega **solo al titular**, con el nivel más bajo (`informar`) y la entrega más
urgente. No llama a nadie ni sube de nivel. Es la acción de menor impacto
posible, y el silencio en ese caso sería peor.

---

## Constantes

Valores iniciales. Todos configurables; varios se ajustan en la Fase 0.

| Constante | Valor | Dónde | Qué controla |
|---|---|---|---|
| `CAPTURE_INTERVAL_S` | 1 | bridge y API | Cada cuánto el bridge entrega un frame por cámara y el Paso 1 evalúa movimiento |
| `STALE_FRAME_S` | 5 | API (Paso 1) | Antigüedad máxima del último frame entregado. Pasada, el Paso 1 lo ignora y el `inbox` lo suelta de memoria |
| `RECONNECT_BACKOFF_MAX_S` | 60 | bridge | Espera máxima entre reconexiones a una cámara o a la nube |
| `ANALYSIS_WIDTH` | 320 px | API (Paso 1) | Ancho de la imagen para detectar movimiento |
| `BLUR_KERNEL` | 21 × 21 | API (Paso 1) | Suavizado antes de comparar |
| `PIXEL_DIFF_THRESHOLD` | 25 (de 255) | API (Paso 1) | Diferencia mínima para que un píxel cuente como cambiado |
| `BG_LEARNING_RATE` | 0.05 | API (Paso 1) | Velocidad de adaptación del fondo |
| `motion_threshold` | 0.02 | por space | Proporción de píxeles cambiados que cuenta como movimiento |
| `GLOBAL_CHANGE_RATIO` | 0.6 | API (Paso 1) | Por encima, es cambio de luz y no movimiento |
| `DESCRIBE_MIN_INTERVAL_S` | 10 | API (Paso 1) | Máximo un frame de movimiento cada tantos segundos por space |
| `BOOSTED_INTERVAL_S` | 3 | API (Paso 1) | Intervalo durante un refuerzo del Paso 3 |
| `STATE_MIN_INTERVAL_S` | 300 | API (Paso 1) | Mínimo entre refrescos de estado por cambio de luz |
| `STATE_REFRESH_MAX_S` | 3600 | API (Paso 1) | Máximo sin refrescar el estado de un space quieto |
| `HEALTH_PING_S` | 60 | bridge | Reporte de salud por cámara |
| `BRIDGE_HEARTBEAT_S` | 30 | bridge | Latido del canal de control, aunque no haya cámaras |
| `UPLOAD_MAX_WIDTH` | 512 px | bridge | Ancho máximo del frame que el bridge entrega a la nube |
| `JPEG_QUALITY` | 70 | bridge | Compresión del frame |
| `CAMERA_TEST_TIMEOUT_S` | 10 | bridge | Límite para probar una cámara nueva |
| `STREAM_IDLE_TIMEOUT_S` | 60 | bridge y relay | Corte del stream sin lectores |
| `MAX_FRAME_BYTES` | 300 KB | API | Tamaño máximo aceptado |
| `FRAME_DEDUP_WINDOW_S` | 300 | API | Memoria de frames vistos |
| `MAX_CLOCK_SKEW_S` | 30 | API | Desfase de reloj tolerado |
| `DESCRIBE_RETRIES` | 2 | API | Reintentos de una descripción |
| `THREAD_GAP_S` | 90 | API y worker | Silencio que termina un thread |
| `LIVE_READ_CACHE_S` | 30 | API | Reutilización de la lectura en vivo |
| `LIVE_FRAME_TIMEOUT_S` | 5 | API | Antigüedad máxima del frame que usa la lectura en vivo |
| `LIVE_READ_HISTORY_HOURS` | 6 | API | Threads recientes que ve la lectura en vivo |
| `STREAM_START_TIMEOUT_S` | 8 | API | Espera máxima a que el bridge empiece a publicar |
| `CHAT_HISTORY_MESSAGES` | 10 | API | Mensajes anteriores que ve el chat |
| `RATE_LIMIT_CHAT_PER_MIN` | 20 | API | Mensajes de chat por usuario por minuto |
| `RATE_LIMIT_TTS_PER_MIN` | 30 | API | Pedidos de voz por usuario por minuto |
| `RATE_LIMIT_LIVE_READ_PER_MIN` | 10 | API | Lecturas en vivo por usuario por minuto |
| `TTS_MAX_CHARS` | 600 | API | Largo máximo de un texto para voz |
| `PAIRING_CODE_LENGTH` | 12 caracteres | preparación | Largo del código de emparejamiento de la etiqueta (Fase 1) |
| `BRIDGE_OFFLINE_AFTER_S` | 120 | worker | Sin mensajes de la caja, el Cloud Bridge pasa a sin señal y se avisa |
| `SETTLE_S` | 20 | worker | Calma antes de narrar un momento |
| `MAX_COMPOSE_S` | 45 | worker | Tiempo máximo en composing |
| `REANALYZE_S` | 60 | worker | Reanálisis de un thread activo en sus primeros minutos |
| `REANALYZE_FAST_WINDOW_S` | 300 | worker | Duración de esos primeros minutos |
| `REANALYZE_SLOW_S` | 300 | worker | Reanálisis de un thread activo largo |
| `SCHEDULER_TICK_S` | 5 | worker | Frecuencia del scheduler |
| `WORKER_CONCURRENCY_PER_USER` | 4 | worker | Threads procesados en paralelo por usuario |
| `CONTEXT_RECENT_THREADS` | 5 | worker | Threads anteriores del space que ve el análisis |
| `LOW_CONFIDENCE` | 0.6 | worker | Debajo, un `attention` se verifica en el Paso 3 |
| `ANALYSIS_MAX_FAILURES` | 3 | worker | Fallos seguidos antes de la narrativa de resguardo |
| `UNFAMILIAR_REPEAT_COUNT` | 2 | worker | Apariciones de un desconocido que activan el Paso 3 |
| `UNFAMILIAR_WINDOW_S` | 3600 | worker | Ventana para contar esas apariciones |
| `REASON_HISTORY_HOURS` | 48 | worker | Historia que ve el Paso 3 |
| `BOOST_DURATION_S` | 120 | worker | Duración del refuerzo |
| `BOOST_WAIT_S` | 6 | worker | Espera del Paso 3 para sumar observaciones nuevas |
| `ALERT_CALL_DELAY_S` | 120 | worker | Fase 2a: espera antes de llamar si no se abrió el aviso |
| `HEALTH_TICK_S` | 30 | worker | Revisión de cajas y cámaras sin conexión |
| `OFFLINE_AFTER_S` | 180 | worker | Sin señal de vida, el space pasa a offline |
| `OFFLINE_NOTIFY_AFTER_S` | 420 | worker | Tiempo offline antes de avisar (10 min en total) |
| `RECEIPTS_POLL_S` | 60 | worker | Consulta de recibos de notificaciones |
| `night_start` / `night_end` | 23:00 / 06:00 | por usuario | Ventana nocturna (`user_preferences`) |
| `HOME_LOOKBACK_HOURS` | 6 | app | Horas hacia atrás que carga el Home, y ventana del estado de emergencia |
| `ATTENTION_RECENT_HOURS` | 2 | app | Ventana de "atención reciente" del encabezado |
| `DAY1_WINDOW_S` | 86400 | app | Ventana del estado de primer día |
| `URGENT_FLAGS` | todos los flags | API y worker | Flags que activan el camino rápido |
