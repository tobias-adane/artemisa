# ARTEMISA — 02 · ARQUITECTURA E INTELIGENCIA

*Precios de modelos verificados a agosto 2026.*

---

## 1. EL EMBUDO DE 4 PASOS

Cada paso filtra al anterior. Solo el último tiene consecuencias
reales en el mundo.

Mismo principio que un centro de monitoreo con guardias humanos: la
atención cara (humana o de IA) se activa recién cuando hay una razón
concreta. Nadie mira fijo una cámara vacía con atención completa
24/7.

```
┌─────────────────────────────────────────────────────────────┐
│  PASO 1 — MOVIMIENTO                          (gratis, 24/7) │
│  OpenCV compara frame actual vs. anterior, sin IA.            │
│  ¿Cambió algo? NO → no pasa nada, sigue mirando.               │
└─────────────────────────────────────────────────────────────┘
                          │ SÍ cambió algo
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 2a — DESCRIPCIÓN (GPT-4o mini vision)                   │
│  Describe el frame, puramente factual. NUNCA clasifica.       │
└─────────────────────────────────────────────────────────────┘
                          │ cada ~60s / batch
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 2b — ANÁLISIS (Groq Llama)                              │
│  Agrupa layers en threads → clasifica contra la rutina del    │
│  hogar → calcula confidence y severity_score.                  │
│  ¿Se ve anormal? NO → se guarda como thread normal, listo.     │
└─────────────────────────────────────────────────────────────┘
                          │ SÍ se ve anormal / confidence baja
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 3 — RAZONAMIENTO PROFUNDO           (GPT-4.1 mini)      │
│  Más contexto, más historial, multi-espacio. Sube la          │
│  frecuencia de frames temporalmente.                           │
│  ¿Confirma que es real? NO → se guarda como "attention".      │
└─────────────────────────────────────────────────────────────┘
                          │ SÍ confirma
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 4 — ACCIÓN (Nivel 1-4, ver doc 01 sección 5)            │
│  Twilio: usuario, contactos, 911. Ventana de cancelación.     │
└─────────────────────────────────────────────────────────────┘
```

**Idea central:** la mayoría de los frames no pasan del Paso 1. La
mayoría de los movimientos no pasan del Paso 2b. Solo una fracción
mínima llega al Paso 3, y menos todavía al Paso 4.

Por eso el Paso 3 puede darse el lujo de usar el modelo más caro
disponible: se activa tan poco que "gastar" en inteligencia ahí es
prácticamente gratis en el agregado.

---

## 2. PASO 1 — MOVIMIENTO (gratis, sin IA)

Antes de que un frame llegue a cualquier modelo, el servicio Python
hace un chequeo local con OpenCV: compara el frame actual contra el
último procesado (frame differencing). Si no hay cambio
significativo, no se llama a ningún modelo.

**Por qué es gratis:** no usa IA. Es matemática simple — restar
valores de píxeles de dos imágenes y ver si la diferencia supera un
umbral. Corre en la CPU que ya se paga en Railway, sin llamadas a
APIs externas, sin tokens.

```
Frecuencia de chequeo:   cada 1-2 segundos, siempre activo
Umbral de cambio:        configurable por espacio (una cocina con
                          más tránsito necesita umbral más alto que
                          un dormitorio)
Heartbeat en calma:      si no hubo cambio en X minutos, se manda
                          igual 1 frame al Paso 2a como chequeo de
                          salud. Empezar en 5 min fijo, dejar el
                          gancho para volverlo adaptativo
```

**Este paso es lo que hace viable económicamente todo lo demás.**
Sin él, el costo de IA se dispara ~12x.

---

## 3. PASO 2a — DESCRIPCIÓN (Layer generation)

### Qué hace
Se activa solo cuando el Paso 1 detectó movimiento real. Convierte
cada frame en una oración de texto factual — sin interpretar si es
normal o preocupante. **Nunca clasifica** — ver sección 4 para el
porqué económico de esta separación.

### Modelo
**GPT-4o mini (vision)** — $0.15 / 1M input, $0.60 / 1M output

No hace falta un modelo más grande: acá se necesita velocidad y
descripción factual barata, no razonamiento.

### Prompt (system, cacheable)
```
Describí en una oración lo que ocurre en esta imagen del espacio [space_name].
Contexto del hogar: [home_context]
Respondé en español. No emitas juicio sobre si es normal o
preocupante — eso se decide después. Si no hay nada notable, decilo
directamente.
```

### Configuración de imagen
Usar `detail: low` (~85 tokens fijos por imagen). No hace falta leer
texto chico ni detectar detalles finos — alcanza con saber "quién
está y qué está haciendo". Subir a `high` solo si en la práctica se
pierde información crítica.

### Restricción crítica
El frame se descarta **de memoria** inmediatamente después de que la
llamada retorna. Nunca se escribe a disco, nunca se persiste.

### Costo por frame
```
Input:  ~125 tokens (imagen low + prompt)
Output: ~40 tokens
Costo:  ~$0.000043 por frame
```

---

## 4. PASO 2b — ANÁLISIS Y CLASIFICACIÓN

### Qué hace
Cada ~60 segundos (o al acumular suficientes layers), agrupa las
descripciones en una narrativa coherente y la compara contra lo que
es normal para ESA casa. Acá — y solo acá — se decide si algo "se ve
raro" y merece pasar al Paso 3. La clasificación vive en Thread, no
en Layer: ver `docs/ARTEMISA_03_DATOS.md` sección 3 para el
razonamiento completo (meterla en Layer multiplicaría el costo de la
parte más frecuente del pipeline por ~10x sin ganar coherencia).

### Continuidad de threads (evita eventos desordenados)
Un thread queda abierto (`end_time = null`) mientras sigan llegando
layers del mismo espacio dentro de una ventana corta de silencio
(2-3 min). Este chequeo es una comparación de timestamps — cero
tokens — y evita que una sola visita se fragmente en varios eventos
sin relación entre sí.

### Modelo
**Groq Llama 3.1 8B Instant** por default — $0.05 / 1M input,
$0.08 / 1M output.

**Escala a Llama 3.3 70B Versatile** ($0.59 / $0.79) cuando:
- Las descripciones del batch son contradictorias o ambiguas
- El batch toca algo de la lista de atención del usuario
  (`custom_instructions`) — resuelto con un match de
  keywords/embedding barato ANTES de invocar el modelo grande, no
  con una decisión del modelo chico
- Es horario nocturno (11pm-6am por default, configurable) — chequeo
  de reloj, no de LLM

Ambos triggers de escalado son deterministas a propósito: no cuesta
tokens decidir "conviene escalar", solo cuesta tokens el escalado en
sí — y ese ya es raro por diseño.

### Contexto inyectado al modelo

Esto es lo que lo hace *Contextual Intelligence* y no un
clasificador genérico — pero comprimido, para no volar el costo:

```
1. Las descripciones (layers) del batch actual
2. users.custom_instructions — cacheado (prompt caching) porque se
   repite idéntico en cada batch de ese usuario
3. Resumen COMPRIMIDO de los últimos 3-5 threads de ESE espacio:
   {clasificación, hora, narrativa en una línea} — no la narrativa
   completa de UI
4. Hora del día + día de la semana
5. Estado (compacto, no narrativas) de otros espacios de la casa
```

### Output estructurado

```json
{
  "narrative": "Alguien tocó el timbre a las 16:40. Nadie respondió.",
  "classification": "attention",
  "confidence": 0.78,
  "severity_score": 0.35,
  "reasoning": "No hay visitante esperado según custom_instructions.
                No es horario de delivery habitual. Pero tampoco hay
                señal de intento de forzar entrada."
}
```

`confidence` y `severity_score` son ejes distintos: `confidence` es
qué tan segura está la clasificación (dispara escalado a Paso 3 si
`attention` y `< 0.6`); `severity_score` es qué tan grave sería si es
correcta (decide Nivel 2 vs Nivel 3 dentro de `attention` — ver doc
03 sección 4). El pipeline calcula `alert_level` y `action` después,
con `resolve_action_level()` — nunca los pide como output del modelo.

El campo `reasoning` alimenta directamente el bloque *"Por qué
importó"* en la UI de Activity. No es un campo extra a construir
después — es parte nativa del output.

### Costo por batch
```
Input:  ~1,200 tokens · Output: ~150 tokens
Con Llama 3.1 8B:   ~$0.00007 por batch
Con Llama 3.3 70B:  ~$0.00083 por batch
```

---

## 5. PASO 3 — RAZONAMIENTO PROFUNDO

El paso reservado para cuando realmente hace falta pensar en serio.
Más caro, más lento, y por diseño, raro.

### Triggers de activación (explícitos, no "a veces")

```
1. El Paso 2b clasificó "attention" con confidence < 0.6
2. El Paso 2b clasificó "emergency" — SIEMPRE se re-verifica acá
   antes de disparar Twilio (un falso positivo tiene costo real:
   llamar al 911 sin necesidad)
3. El fast-path (detector liviano corriendo en paralelo sobre cada
   frame) detectó algo que amerita escalar sin esperar el ciclo de
   60s
4. Patrón de persona no reconocida apareciendo repetidamente en
   poco tiempo
```

### Qué hace distinto del Paso 2b

- Modelo con capacidad real de razonamiento, no solo clasificación
- Más contexto: historial de días (no solo últimos threads), estado
  de TODOS los espacios simultáneamente
- Sube temporalmente la frecuencia de frames de ese espacio mientras
  dura la incertidumbre (fast-path)

### Modelo
**GPT-4.1 mini** — $0.40 / 1M input, $1.60 / 1M output. Contexto de
hasta 1M tokens (permite meter mucho historial). Barato en términos
absolutos porque este paso se usa poco.

Si en producción no alcanza para los casos más ambiguos, la escala
natural es a un modelo de razonamiento explícito (~$2/$8 por 1M).
Empezar con 4.1 mini y medir antes de pagar más.

### Output

```
class EmergencyVerification:
  severity_high: bool
  reasoning: str      # INTERNO — nunca se muestra en UI tal cual
  confidence: float
```

Al terminar, el pipeline reescribe `Thread.reasoning` con una
síntesis en voz humana del resultado — nunca vuelca este `reasoning`
técnico directo a la UI. Ver `docs/ARTEMISA_03_DATOS.md` sección 4.

### Costo
```
Input: ~3,000 tokens · Output: ~300 tokens
Costo por activación: ~$0.0017
Con ~15-20 activaciones/mes por hogar: ~$0.03/mes
```

---

## 6. PASO 4 — ACCIÓN

Ver doc 01 sección 5 para la jerarquía completa de los 4 niveles.

```
Nivel 1 (Informar):
  Solo escritura en threads / activity_log. Sin dispatch.

Nivel 2 (Alertar):
  Alert card + push notification. Sin dispatch.

Nivel 3 (Contactar):
  Dispara Twilio hacia el contacto de confianza de mayor prioridad
  (confirmed=True). Ventana de cancelación: 90s
  (user_preferences.contact_cancel_timer_seconds). Puede originarse
  de attention con severity_score alto, o de una emergency que el
  Paso 3 no confirmó (degradado). No pasa por Paso 3 — no es 911,
  el costo de un falso positivo es mucho menor.

Nivel 4 (Emergencia):
  Dispara Twilio — llamada IVR + WhatsApp. Ventana de cancelación:
  30s (user_preferences.cancel_timer_seconds). SOLO se alcanza si
  Paso 3 confirmó severity_high == True.
```

### Diseño del dispatch

- **El dispatch corre server-side, no depende de que la app esté
  abierta.** Por eso el frontend NO necesita un Emergency Overlay de
  pantalla completa con countdown.
- La ventana de cancelación vive en la llamada misma (IVR: "presioná
  1 para cancelar") y/o en el mensaje de WhatsApp — más confiable que
  depender de una notificación push que el usuario puede no ver.
- En Nivel 4, Twilio llama al **dueño de la cuenta también**, no
  solo a los contactos de emergencia y al 911.
- Cada llamada/mensaje individual queda auditado en `dispatch_logs`
  (ver doc 03 sección 8) — un solo thread de Nivel 4 puede generar
  varias filas en secuencia.

### Nota legal pendiente

Falta resolver con abogado argentino: **¿es legal que un sistema
automatizado, sin intervención humana, inicie una llamada a
servicios de emergencia reales?** Si la respuesta es restrictiva,
cambia la arquitectura del Nivel 4 específicamente (podría requerir
confirmación humana antes del 911). Nivel 3 (contactar a una persona
de confianza, no 911) no está bloqueado por esta consulta. Resolver
antes de programar la Fase 5 del backend (ver doc 04 sección 5).

---

## 7. TABLA DE MODELOS

| Paso | Modelo | Input /1M | Output /1M | Uso |
|---|---|---|---|---|
| 1 — Movimiento | OpenCV (local) | — | — | Gratis, siempre activo |
| 2a — Descripción | GPT-4o mini (vision) | $0.15 | $0.60 | En cada movimiento |
| 2b — Análisis | Groq Llama 3.1 8B | $0.05 | $0.08 | Default |
| 2b — Análisis (escalado) | Groq Llama 3.3 70B | $0.59 | $0.79 | Ambigüedad / noche |
| 3 — Razonamiento | GPT-4.1 mini | $0.40 | $1.60 | Raro, solo si Paso 2b no alcanza |
| Chat | Groq Llama 3.3 70B | $0.59 | $0.79 | Bajo volumen |

---

## 8. MENSAJES CONTEXTUALES AL USUARIO

Cuándo Artemisa interrumpe proactivamente vs. solo registra.

**Regla general:** interrumpir cuesta atención del usuario — recurso
escaso. Solo se justifica cuando (a) el usuario necesita saber algo
ahora, o (b) responder ayuda a Artemisa a aprender algo que reduce
falsas alarmas futuras.

### Sí generan mensaje

| Caso | Comportamiento |
|---|---|
| Clasificación `attention`, Nivel 2 | Alert card simple, informativo, sin pregunta |
| Clasificación `attention`, Nivel 3 | Dispatch a contacto de confianza, con ventana de cancelación de 90s |
| Patrón nuevo recurrente detectado | Pregunta activa de aprendizaje |
| Clasificación `emergency` confirmada (Nivel 4) | Nunca pregunta — acción directa al Paso 4 |

Ejemplo de pregunta de aprendizaje:
```
"Noté que alguien con estas características viene los martes
alrededor de las 10am. ¿Sabés quién es, para que no te avise más
por esto?"
```
Esto alimenta `custom_instructions` de forma conversacional continua
— la versión "viva" de lo que el onboarding captura una sola vez.

### No generan mensaje (solo se registran)

- Clasificación `normal` → va al feed de Activity
- Fluctuaciones menores de confianza dentro de lo esperado
- Cualquier evento durante Quiet hours configuradas
  (`do_not_disturb_*`), salvo `emergency`

---

## 9. ECONOMÍA DE UNIDAD

### Costo de IA por hogar (1 cámara), con Paso 1 filtrando

```
Ventana activa (~4h/día, chequeo cada 5s con movimiento):
  ~2,880 llamadas al Paso 2a/día
Ventana en calma (~20h/día, heartbeat cada 5 min):
  ~240 llamadas/día
Total: ~93,600 llamadas/mes por cámara
```

| Componente | Costo/mes |
|---|---|
| Paso 2a — Descripción | ~$4.00 |
| Paso 2b — Análisis | ~$0.65 |
| Paso 3 — Razonamiento | ~$0.03 |
| Chat | ~$0.01 |
| **TOTAL** | **~$4.70/mes por hogar** |

### Riesgo abierto

El pricing de beta definido (Founding ~$2.50-2.80 USD/mes, Premium
~$3.50-3.90 USD/mes, cobrado en ARS al tipo de cambio vigente) **no
cubre este costo** — antes de sumar Twilio, Supabase y Railway. La
beta se subsidia por diseño (cobertura estimada 38-50%), pero el
número real dependerá de datos de uso reales.

### 3 palancas para bajarlo

**1. Heartbeat adaptativo** (mayor impacto) — bajar de 5 min a 15
min en horarios históricamente tranquilos para esa casa. Las 20
horas "en calma" son las que más volumen aportan.
→ **Construir desde el día 1, no como optimización posterior.**

**2. Prompt caching** — OpenAI y Groq dan descuento por contenido
repetido (el system prompt + `custom_instructions`). Baja el costo
de input 50-75%. Ya asumido como parte del diseño del Paso 2b
(sección 4).

**3. Batch API** — para procesamiento no urgente (ej. resúmenes
diarios de Living Memory), 50% más barato. No aplica al pipeline en
vivo.

Con las 3 combinadas: realista bajar a ~$2-2.50/mes por cámara.
