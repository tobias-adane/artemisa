# 04. Modelos

## Principio: un registro, no nombres sueltos

Ningún nombre de modelo aparece en la lógica del pipeline. El código pide un
**rol** (`describe`, `analyze`, `reason`…) y un registro de configuración
resuelve qué proveedor, qué modelo y qué parámetros usar. Los proveedores
retiran modelos y cambian precios con frecuencia; con el registro, cambiar un
modelo es editar un archivo, no tocar código.

Los precios viven en el mismo registro, con la fecha en que se verificaron. El
costo de cada llamada se calcula con el `usage` real que devuelve el proveedor,
nunca con estimaciones.

---

## Modelos por rol

Verificados el **21 de septiembre de 2026**. Precios en USD por millón de
tokens.

| Rol | Proveedor | Modelo | Entrada | Salida | Para qué |
|---|---|---|---|---|---|
| `describe` | OpenAI | `gpt-4.1-nano` | 0.10 (0.025 cacheado) | 0.40 | Paso 2a: una oración por frame |
| `describe_fallback` | OpenAI | `gpt-4.1-mini` | 0.40 (0.10 cacheado) | 1.60 | Paso 2a si el modelo por defecto falla |
| `analyze` | Groq | `openai/gpt-oss-20b` | 0.075 | 0.30 | Paso 2b por defecto |
| `analyze_hard` | Groq | `openai/gpt-oss-120b` | 0.15 | 0.60 | Paso 2b en casos difíciles |
| `analyze_fallback` | OpenAI | `gpt-4.1-mini` | 0.40 | 1.60 | Paso 2b si Groq no responde |
| `reason` | OpenAI | `gpt-4.1-mini` | 0.40 | 1.60 | Paso 3 |
| `reason_fallback` | Groq | `openai/gpt-oss-120b` | 0.15 | 0.60 | Paso 3 si OpenAI no responde |
| `live_read` | OpenAI | `gpt-4.1-mini` | 0.40 | 1.60 | Lectura en vivo (con imagen) |
| `chat` | Groq | `openai/gpt-oss-120b` | 0.15 | 0.60 | Chat |
| `chat_fallback` | OpenAI | `gpt-4.1-mini` | 0.40 | 1.60 | Chat si Groq no responde |
| `tts` | OpenAI | `tts-1` | a verificar | | Voz de Artemisa |
| Movimiento | Nube | OpenCV en la API | 0 | 0 | Paso 1, sin modelo |
| Voz a texto | Local | Reconocimiento del teléfono | 0 | 0 | Entrada de voz |

### Por qué cada uno

**Describir es el volumen.** Es la llamada que más se repite (decenas de miles
por cámara por mes), así que manda el costo por imagen. `gpt-4.1-nano` cobra
las imágenes por tamaño real y permite controlar el costo reduciendo el frame en
la casa. Describir una escena en una oración no requiere un modelo grande.

**Analizar es texto y es frecuente.** Groq corre modelos abiertos muy rápido y
barato. `gpt-oss-20b` alcanza para narrar y clasificar momentos comunes;
`gpt-oss-120b` entra cuando el caso es difícil.

**Razonar es raro, así que el costo casi no importa.** El Paso 3 decide si
alguien recibe una llamada. El punto de partida es `gpt-4.1-mini`, de otro
proveedor que el análisis (una segunda opinión independiente) y con esquemas de
salida estrictos. No es un modelo de razonamiento, y no se asume que sea el
mejor para este paso: como el Paso 3 se activa unas veinte veces por mes, en la
Fase 0 se compara contra `gpt-oss-120b` y contra modelos más grandes, y se elige
por calidad de decisión, no por precio. Si OpenAI no responde cuando se necesita
el Paso 3, el respaldo es `gpt-oss-120b` en Groq.

**La lectura en vivo la lee una persona mirando su casa.** Es poco frecuente y
la calidad de la prosa importa más que el costo.

**El chat** necesita conversar bien con contexto largo, rápido.

**Voz a texto en el teléfono:** cero costo, cero latencia de red, y el audio no
viaja a ningún servidor de Artemisa.

---

## Trampas conocidas

**No usar `gpt-4o-mini` para describir imágenes.** Su texto es barato, pero
cuenta cada imagen de baja resolución como 2.833 tokens de entrada (`gpt-4o`
cuenta 85 por la misma imagen). En dólares, describir un frame con `gpt-4o-mini`
cuesta unos USD 0,00048, más de seis veces lo que cuesta con la configuración de
este documento. Con el volumen previsto serían más de USD 20 por cámara por mes
solo en descripciones. Es la diferencia entre un producto viable y uno que no.

**Los Llama 3.x de Groq ya no existen.** `llama-3.1-8b-instant` y
`llama-3.3-70b-versatile` se apagaron el 16 de agosto de 2026. Groq recomienda
`openai/gpt-oss-20b` y `openai/gpt-oss-120b` como reemplazos.

**Los `gpt-oss` son modelos de razonamiento.** Generan tokens de razonamiento
antes de responder y esos tokens se cobran como salida. Siempre se configura el
esfuerzo de razonamiento de forma explícita (bajo para `analyze` y `chat`, medio
para `analyze_hard`) y se fija un máximo de tokens de salida que contemple el
razonamiento. El razonamiento no se muestra ni se guarda.

**`whisper-1` está en retiro** (se apaga el 26 de febrero de 2027). Artemisa no
lo usa: la voz a texto corre en el teléfono.

**El cacheo de prompts tiene tamaño mínimo.** Los proveedores cachean prefijos
de prompt largos y repetidos. El prompt de descripción es corto, así que no se
beneficia: su palanca es el tamaño de la imagen. Los prompts de análisis,
razonamiento y chat sí: por eso el texto fijo va siempre primero y el contexto
variable al final.

**Los nombres exactos de parámetros cambian entre proveedores** (esfuerzo de
razonamiento, formato de respuesta, nivel de detalle de imagen). Se verifican
contra la documentación de cada proveedor al implementar su cliente.

---

## Tokens de imagen

Los modelos de la familia `gpt-4.1` cobran las imágenes por parches de 32 × 32
píxeles:

```
parches = ceil(ancho / 32) × ceil(alto / 32)
tokens  = parches × multiplicador        (nano: 2.46 · mini: 1.62)
```

| Frame enviado | Parches | Tokens nano | Tokens mini |
|---|---|---|---|
| 512 × 288 | 144 | ≈ 354 | ≈ 233 |
| 384 × 216 | 84 | ≈ 207 | ≈ 136 |
| 320 × 180 | 60 | ≈ 148 | ≈ 97 |

Por eso el bridge reduce el frame antes de subirlo (`UPLOAD_MAX_WIDTH`). En la
Fase 0 se registran los tokens de imagen que el proveedor realmente cobra y se
comparan con esta tabla.

---

## Registro

`server/artemisa/core/models.yaml`:

```yaml
verified_at: 2026-09-21

roles:
  describe:
    provider: openai
    model: gpt-4.1-nano
    temperature: 0.2
    max_output_tokens: 80
    image_detail: low
    timeout_s: 8
    fallback: describe_fallback
  describe_fallback:
    provider: openai
    model: gpt-4.1-mini
    temperature: 0.2
    max_output_tokens: 80
    image_detail: low
    timeout_s: 8
  analyze:
    provider: groq
    model: openai/gpt-oss-20b
    reasoning_effort: low
    temperature: 0.3
    max_output_tokens: 800
    timeout_s: 10
    fallback: analyze_fallback
  analyze_hard:
    provider: groq
    model: openai/gpt-oss-120b
    reasoning_effort: medium
    temperature: 0.3
    max_output_tokens: 1200
    timeout_s: 15
    fallback: analyze_fallback
  analyze_fallback:
    provider: openai
    model: gpt-4.1-mini
    temperature: 0.3
    max_output_tokens: 400
    timeout_s: 10
  reason:
    provider: openai
    model: gpt-4.1-mini
    temperature: 0.2
    max_output_tokens: 600
    timeout_s: 20
    fallback: reason_fallback
  reason_fallback:
    provider: groq
    model: openai/gpt-oss-120b
    reasoning_effort: medium
    temperature: 0.2
    max_output_tokens: 1500
    timeout_s: 20
  live_read:
    provider: openai
    model: gpt-4.1-mini
    temperature: 0.6
    max_output_tokens: 250
    image_detail: low
    timeout_s: 10
  chat:
    provider: groq
    model: openai/gpt-oss-120b
    reasoning_effort: low
    temperature: 0.5
    max_output_tokens: 800
    stream: true
    timeout_s: 5            # hasta el primer token
    fallback: chat_fallback
  chat_fallback:
    provider: openai
    model: gpt-4.1-mini
    temperature: 0.5
    max_output_tokens: 400
    stream: true
    timeout_s: 5
  tts:
    provider: openai
    model: tts-1
    voice: nova
    format: mp3
    timeout_s: 10

prices_usd_per_1m:
  openai/gpt-4.1-nano:   { input: 0.10,  cached_input: 0.025, output: 0.40 }
  openai/gpt-4.1-mini:   { input: 0.40,  cached_input: 0.10,  output: 1.60 }
  groq/openai/gpt-oss-20b:  { input: 0.075, output: 0.30 }
  groq/openai/gpt-oss-120b: { input: 0.15,  output: 0.60 }
  openai/tts-1: { per_1m_characters: null }   # verificar antes de la Fase 0
```

---

## Prompts

Los prompts viven en `server/artemisa/core/prompts/`, uno por archivo, y se
versionan con el código. Están en inglés; lo que el usuario lee sale en su
idioma porque cada prompt recibe `{language}`.

### `describe` (Paso 2a)

**Sistema:**

```
You describe one frame from a home camera. No image is ever kept, so your sentence is the only record of this moment.

Write ONE present-tense sentence, at most 20 words, about what is visible and happening: people (how many, clothing color, what they carry), what they are doing, animals, vehicles, open or closed doors, lights on or off.
Be factual. Do not guess identity, intent, or emotion. Do not judge whether it is normal. Do not use the words "detected", "motion", or "suspicious".
If nothing is happening, describe the scene plainly: "The living room is empty, lights off."
Write the sentence in {language}.

flags: include only if clearly visible: person_on_floor, smoke_or_fire, glass_broken, door_forced, weapon_visible, water_leak.

Answer with JSON: {"description": string, "flags": string[], "people_count": integer}
```

**Usuario:** la imagen y una línea de texto:

```
Space: {space_name}. Local time: {hh:mm}.
```

### `analyze` y `analyze_hard` (Paso 2b)

**Sistema:**

```
You are Artemisa, the part of a home that understands what happens in it. You never see images. You receive short factual observations captured in one space of the home during a moment, plus context about the household. Turn them into one short narrative a family member would want to read, and judge whether it matters.

NARRATIVE
- One or two short sentences, at most 25 words. Plain, warm, specific.
- Say what happened in the home, never what a camera or system did. Never use: detected, motion, camera, AI, model, alert, suspicious.
- Notice what someone who knows this home would notice: routines, what's unusual, what was left behind.
- Use a family member's name only when the household context makes it reasonable, and hedge when you are not sure ("Looks like Maya's home, but I'm not completely sure.").
- Never dramatize. Never reassure falsely. Uncertainty is fine; invented certainty is not.

CLASSIFICATION
- normal: ordinary life for this home at this time.
- attention: the owner should know soon, but nothing points to danger. Examples: someone unfamiliar at the door, a routine clearly broken, a door left open while nobody is home.
- emergency: signs of immediate risk to people or property. Examples: forced entry, smoke or fire, someone on the floor not moving, a weapon, water flooding.
The same event can be normal at 5 PM and attention at 3 AM. Use the routine.
Sensitivity is "{sensitivity}": with "low", require more evidence before choosing attention; with "high", require less.

REASONING
One to three sentences in the same voice, explaining why this matters or why it doesn't, pointing to the routine or context you relied on. The owner reads this as "Why I'm telling you". It must never read like a log.

OTHER FIELDS
- confidence: 0 to 1, how sure you are about the classification.
- escalate: true when a more careful look is warranted: ambiguous or contradictory observations, something the owner asked to watch for, an unfamiliar person who keeps returning, anything that could be an emergency.
- escalate_reason: a few words when escalate is true, otherwise null.
- people_present: whether people are in this space at the end of the observations; null if you can't tell.
- unfamiliar_person: true if someone appears who doesn't match anyone described in the household context.

Write narrative and reasoning in {language}. Answer only with JSON matching the schema.
```

**Usuario** (plantilla de contexto):

```
HOUSEHOLD
{custom_instructions | "(nothing yet)"}

NOW
{weekday}, {local_time} ({timezone}). Space: {space_name}.

OTHER SPACES RIGHT NOW
- {space}: {state_description} ({minutes} min ago)

EARLIER TODAY IN THIS SPACE
- {time} [{classification}] {narrative}

PREVIOUS NARRATIVE OF THIS MOMENT
{previous_narrative | "(first look)"}

OBSERVATIONS
- {hh:mm:ss} {description} {flags}
```

### `reason` (Paso 3)

**Sistema:**

```
You are Artemisa taking a second, careful look at a moment in a home. A first pass flagged it. You now see more: every observation of the moment (including fresh ones captured just now), what happened across the whole home in the last {hours} hours, the state of every space, and the household routine.

Decide:
- classification: normal, attention, or emergency. You may lower or raise the first pass's choice.
- severity_high: true only if waiting would plausibly make things worse for people or property.
  For attention: the owner should be reached right now, not later.
  For emergency: the full emergency protocol is justified.
- reasoning: one to three sentences in Artemisa's voice, shown to the owner as "Why I'm telling you". Name the detail that decided it ("It's the handle that changed my mind."). When relevant, say what you decided not to do and why.
- narrative: rewrite it only if the fuller picture changes the story; otherwise return it unchanged.

The stronger the action, the more certainty it needs. Contacting other people or emergency services cannot rest on weak or ambiguous evidence. If the evidence is weak, lower the classification or keep severity_high false, and say so honestly.
Never use: detected, motion, camera, AI, model, alert, suspicious.
Write in {language}. Answer only with JSON matching the schema.
```

**Usuario:** la misma plantilla que `analyze`, más estas secciones:

```
FIRST PASS
[{classification}, confidence {confidence}] {narrative}
Why: {reasoning}
Escalated because: {escalate_reason | trigger}

WHOLE HOME, LAST {hours} HOURS
- {time} {space} [{classification}] {narrative}
```

El Paso 3 no recibe imágenes: recibe las observaciones, incluidas las nuevas que
generó el refuerzo del bridge.

### `live_read`

**Sistema:**

```
You are Artemisa. The owner just opened a live view of one space in their home. Look at the frame and use the context to say what this moment is like, right now.

headline: one short sentence about the whole home, using the other spaces too. At most 10 words. Examples: "Your home's empty right now. All secure." "Everyone's home. All quiet." If you can't see some space right now, never say the whole home is fine or secure.
body: two or three short sentences about this space. What it looks like, how it feels, and end on one concrete observation grounded in the context, like "Nothing's moved in about an hour." Present tense. No clock times.
Only describe what you can see or what the context says. Never invent people, sounds, or smells. Never mention cameras, recording, AI, or detection.
Write in {language}. Answer with JSON: {"headline": string, "body": string}
```

**Usuario:** la imagen y:

```
Space: {space_name}. Local time: {hh:mm}. Nothing has moved here for {minutes} minutes.
HOUSEHOLD: {custom_instructions}
OTHER SPACES: {space}: {state_description}; ...
EARLIER HERE: {time} {narrative}; ...
```

### `chat`

**Sistema:**

```
You are Artemisa. You understand what happens in this home through short observations. You never keep images or video.
Answer the owner using only the context below: today's moments, the current state of each space, and what the owner has told you about the household.
- Be brief: one to three sentences unless they ask for more. Warm, plain, specific.
- If the answer isn't in the context, say you don't know. Never guess about people's identity or safety.
- If they ask to see or replay something from the past, explain that you don't keep recordings, tell them what you saw, and offer "See now" to look live.
- If you can't see the home or a space right now, say so. Never describe the present of a space you can't see.
- Never mention AI, models, or how you work internally.
- Write in {language}.

The owner's name is {first_name}. It is {weekday}, {local_time}.

HOUSEHOLD
{custom_instructions}

TODAY
- {time} {space} [{classification}] {narrative}

SPACES NOW
- {space}: {state_description}
```

Si la casa entera o un space está sin señal, su línea en `SPACES NOW` (y en
`OTHER SPACES` de `live_read`) dice `can't see it since {hh:mm}` en lugar de la
última descripción, que ya no es presente. Artemisa nunca describe como actual
algo que no está viendo (ver `02-PRODUCTO.md`, Artemisa siempre dice qué puede
ver).

**En la Fase 1 este prompt cambia.** Cuando el Cloud Bridge graba, "You never
keep images or video" y la regla de "replay" dejan de ser verdad: existe una
grabación en la casa que solo el dueño ve. El prompt se reescribe antes de la
Fase 1, junto con `live.privacy` y `connect.privacy`.

Si la pregunta es sobre un thread, se agrega:

```
THE MOMENT THEY'RE ASKING ABOUT
{time} {space}: {narrative}
Why: {reasoning}
What you saw:
- {hh:mm:ss} {description}
What you did: {action summary from dispatches}
```

---

## Esquemas de salida

`server/artemisa/core/schemas.py`. Toda salida de modelo se valida contra su
esquema antes de tocar la base de datos.

```python
from enum import Enum
from pydantic import BaseModel, Field

class Classification(str, Enum):
    normal = "normal"
    attention = "attention"
    emergency = "emergency"

class Flag(str, Enum):
    person_on_floor = "person_on_floor"
    smoke_or_fire = "smoke_or_fire"
    glass_broken = "glass_broken"
    door_forced = "door_forced"
    weapon_visible = "weapon_visible"
    water_leak = "water_leak"

class DescribeOut(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    flags: list[Flag] = []
    people_count: int = Field(ge=0, le=50)

class AnalysisOut(BaseModel):
    narrative: str = Field(min_length=1, max_length=240)
    classification: Classification
    confidence: float = Field(ge=0, le=1)
    reasoning: str = Field(min_length=1, max_length=500)
    escalate: bool
    escalate_reason: str | None = None
    people_present: bool | None = None
    unfamiliar_person: bool = False

class ReasoningOut(BaseModel):
    classification: Classification
    severity_high: bool
    reasoning: str = Field(min_length=1, max_length=500)
    narrative: str = Field(min_length=1, max_length=240)

class LiveReadOut(BaseModel):
    headline: str = Field(min_length=1, max_length=80)
    body: str = Field(min_length=1, max_length=400)
```

Cuando el proveedor soporta salidas estructuradas con esquema estricto, se usan.
Cuando solo soporta modo JSON, se pide JSON y se valida igual.

### Validación y reintentos

1. Se parsea y valida con el esquema.
2. Si falla, **un** reintento agregando: "Your previous answer did not match
   the schema: {error}. Answer again with only the JSON."
3. Si vuelve a fallar, se trata como fallo del modelo (ver Fallos y bordes en
   `03-ALGORITMO.md`).
4. Si el proveedor no responde dentro del `timeout_s` del rol o devuelve error
   de forma sostenida, se usa el rol de `fallback`.

Cada intento, exitoso o no, escribe una fila en `pipeline_runs`.

---

## Costos

### Por llamada (configuración por defecto)

| Llamada | Supuesto | Costo aproximado |
|---|---|---|
| `describe` | Imagen 512 × 288 (≈ 354 tokens), ≈ 220 tokens de texto, ≈ 40 de salida | USD 0,000073 |
| `analyze` | ≈ 1.400 de entrada, ≈ 350 de salida con razonamiento | USD 0,00021 |
| `analyze_hard` | ≈ 1.400 de entrada, ≈ 500 de salida | USD 0,00051 |
| `reason` | ≈ 5.000 de entrada, ≈ 400 de salida | USD 0,0026 |
| Refuerzo del Paso 3 | 40 descripciones extra | USD 0,0029 |
| `live_read` | Imagen (≈ 233 tokens) + ≈ 700 de texto, ≈ 120 de salida | USD 0,00056 |
| `chat` | ≈ 3.000 de entrada, ≈ 250 de salida | USD 0,0006 |

### Por cámara por mes

Supuesto conservador: unas 4 horas de movimiento por día en esa cámara. Es un
número de planificación; la Fase 0 mide el real.

| Componente | Volumen mensual | Costo mensual |
|---|---|---|
| Paso 1 | Continuo, en la nube, sin modelos | Sin costo de IA. Cómputo y tráfico: se miden en la Fase 0 |
| Paso 2a | ≈ 44.000 descripciones | ≈ USD 3,20 |
| Paso 2b | ≈ 2.700 análisis (80% rápido, 20% fuerte) | ≈ USD 0,75 |
| Paso 3 | ≈ 20 activaciones con refuerzo | ≈ USD 0,11 |
| Lectura en vivo | ≈ 150 | ≈ USD 0,08 |
| Chat | ≈ 150 mensajes | ≈ USD 0,09 |
| Voz | ≈ 50.000 caracteres | a verificar |
| **Total IA, sin voz** | | **≈ USD 4,25** |

El pricing previsto para la beta (Founding ≈ USD 2,50 a 2,80 por mes, Premium ≈
USD 3,50 a 3,90) no cubre este costo antes de sumar infraestructura. Tampoco
incluye el Cloud Bridge (quién paga la caja y cómo es una decisión abierta, ver
`08-CONSTRUCCION.md`), ni el cómputo y el tráfico de correr el Paso 1 en la nube
sobre un frame por segundo por cámara. La beta se subsidia por diseño, y estas palancas bajan
el número:

### Palancas, de mayor a menor impacto

1. **Describir en la casa.** Un modelo de visión chico corriendo en el Cloud
   Bridge lleva el Paso 2a a cero y hace que ninguna imagen salga nunca de la
   casa. Es la palanca más grande en costo y la más fuerte en privacidad.
   Requiere una versión de la caja con más capacidad (más memoria o un
   acelerador), y hoy el Cloud Bridge es liviano a propósito porque no procesa.
   Opción de largo plazo, Fase 3.
2. **Frame más chico.** Pasar de 512 a 384 píxeles de ancho baja los tokens de
   imagen alrededor de un 40% y el costo de cada descripción alrededor de un
   20% (el texto del prompt y la salida no cambian), si la calidad se sostiene.
   Se mide en la Fase 0.
3. **Presupuesto de frames.** Pasar `DESCRIBE_MIN_INTERVAL_S` de 10 a 15
   segundos baja el Paso 2a un tercio.
4. **Filtro de escena.** No describir un frame si se parece demasiado al último
   descripto del mismo space (comparación por hash perceptual en el Paso 1, en la nube). Una
   persona sentada que se acomoda en el sillón no necesita una oración nueva.
5. **Prompt de descripción más corto.** El texto del prompt se cobra en cada
   frame.
6. **Cacheo de prompts** en análisis, razonamiento y chat: texto fijo primero,
   contexto variable al final.
7. **Voz solo cuando el usuario habló.** Leer en voz alta cada thread nuevo es lo
   que más caracteres consume.
8. **Procesamiento por lotes** para trabajo no urgente (resúmenes diarios, si se
   agregan). No aplica al pipeline en vivo.

Con las palancas 2, 3 y 5 aplicadas, el total razonable queda alrededor de USD
2,50 a 3 por cámara por mes. Con la palanca 1, el Paso 2a desaparece del costo.

### Candidatos a evaluar

La generación de modelos cambia rápido. En la Fase 0 vale la pena comparar
`describe` contra los modelos "nano" más nuevos de cada proveedor, midiendo
tokens de imagen reales, calidad de descripción y costo por hora. El registro
permite cambiarlo sin tocar código.

---

## Retención de datos de los proveedores

La nube de Artemisa no guarda frames. Los proveedores tienen sus propios
términos, y el producto tiene que ser honesto con eso.

**OpenAI** (recibe imágenes en `describe` y `live_read`):

- Por defecto conserva registros de monitoreo de abuso hasta 30 días, salvo que
  la ley exija más.
- Ofrece **Zero Data Retention** y **Modified Abuse Monitoring** sujetos a
  aprobación, a pedido a su equipo comercial.
- Aun con retención cero, las imágenes pasan por un clasificador de contenido
  ilegal y una imagen marcada puede retenerse para revisión. Fuera de Estados
  Unidos, el soporte de imágenes con retención cero requiere una aprobación
  adicional.

**Groq** (recibe solo texto): verificar sus términos de retención antes de la
Fase 1.

**Acciones del proyecto:**

- Pedir retención cero (o monitoreo modificado) a OpenAI antes de tener usuarios
  reales.
- Desactivar explícitamente cualquier almacenamiento de respuestas del lado del
  proveedor en cada llamada.
- Declarar a cada proveedor como encargado de tratamiento en la política de
  privacidad.
- Escribir el copy del producto afirmando solo lo que Artemisa controla. En la
  Fase 0, "Artemisa doesn't record it"; desde la Fase 1, cuando el Cloud Bridge
  graba en la casa, el copy dice que la nube no guarda nada y que lo grabado
  queda cifrado en la casa.
- A largo plazo, describir en la casa (palanca 1) vuelve absoluta la promesa.

---

## Evaluación

El modelo es una decisión que se mide, no que se opina.

**Set de referencia.** En la Fase 0 se graba un video de prueba de 20 a 30
minutos en la casa real, en un horario con movimiento. El titular etiqueta a
mano cada momento: qué pasó, qué clasificación le daría, y si hubiera querido
que lo interrumpan. Como el video es un archivo, cada corrida del pipeline es
repetible y comparable.

**Métricas:**

| Métrica | Cómo se mide |
|---|---|
| Fidelidad de las descripciones | El titular puntúa de 1 a 5 si la oración dice lo que pasó |
| Acuerdo de clasificación | Proporción de momentos donde coincide con la etiqueta |
| Falsas atenciones | Momentos `attention` que el titular marcó como normales |
| Atenciones perdidas | Momentos que el titular quería saber y quedaron `normal` |
| Escaladas justificadas | Proporción de pasos 3 que el titular considera razonables |
| Latencia | Del frame a la narrativa, p50 y p95 |
| Costo por hora | Suma de `pipeline_runs` dividida por horas de video |

**Comparaciones previstas:** `describe` con `gpt-4.1-nano` contra
`gpt-4.1-mini`; frames de 512 contra 384 píxeles; `analyze` contra
`analyze_hard` en todos los momentos; `reason` con `gpt-4.1-mini` contra
`gpt-oss-120b` y contra un modelo más grande, sobre las escenas actuadas.
