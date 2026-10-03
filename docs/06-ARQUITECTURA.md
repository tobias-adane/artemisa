# 06. Arquitectura

## Topología

```
┌─────────────────────── CASA (red local) ───────────────────────┐
│                                                                 │
│   Cámaras IP ────▶  CLOUD BRIDGE (cajita al lado del router)    │
│   o un DVR/NVR       · go2rtc: habla con cada marca             │
│                      · entrega un frame por segundo por cámara  │
│                      · guarda las credenciales de cámaras       │
│                      · publica el stream en vivo a pedido       │
│                      · no analiza nada                          │
│                      · graba cifrado en la casa (Fase 1)        │
│                              │  solo conexiones SALIENTES       │
└──────────────────────────────┼──────────────────────────────────┘
                               │ HTTPS (frames)   WSS (control)   SRT/RTSP (vivo)
                               ▼
┌──────────────────────────── NUBE ──────────────────────────────┐
│                                                                 │
│   API (FastAPI)        WORKER               RELAY (MediaMTX)    │
│   · recibe frames      · Paso 2b            · recibe el vivo    │
│   · Paso 1 y 2a        · Paso 3             · sirve HLS         │
│   · sesionización      · Paso 4               desde memoria     │
│   · lectura en vivo    · salud de cámaras                       │
│   · chat, voz          · retención                              │
│   · canal del bridge                                            │
│          │                    │                    │            │
│          └──────┬─────────────┘                    │            │
│                 ▼                                  │            │
│   SUPABASE (Postgres + tiempo real)                │            │
│                 │                                  │            │
│   Proveedores: OpenAI (visión, razonamiento, voz), Groq (texto),│
│   Expo Push, Twilio (Fase 2)                       │            │
└─────────────────┼──────────────────────────────────┼────────────┘
                  │ tiempo real + lecturas            │ HLS
                  ▼                                   ▼
            ┌──────────────── APP (Expo) ────────────────┐
            │ Home · Detalle · Feed en vivo · Chat · Voz │
            └────────────────────────────────────────────┘
```

---

## Cloud Bridge: la cajita de la casa

**Decisión.** En la primera versión, todas las cámaras se conectan a Artemisa a
través del **Cloud Bridge**: un dispositivo dedicado que se enchufa al lado del
router. No hay otro camino. Artemisa no fabrica hardware: la cajita se arma con
un equipo que se compra hecho, con el software de Artemisa ya grabado. En el
código y en estos documentos, su software se llama **bridge**.

### Por qué hace falta algo en la casa

**Las cámaras viven en la red privada.** Una cámara en `192.168.0.14` no es
alcanzable desde un servidor en la nube. Abrir puertos es inseguro, es fricción
para el usuario, y con CGNAT (común en conexiones domésticas) directamente no
funciona. El Cloud Bridge está adentro de la red y solo abre conexiones hacia
afuera, que funcionan en cualquier casa.

**Las credenciales no salen de la casa.** Las direcciones RTSP incluyen el
usuario y la contraseña de la cámara. Viven solo en el Cloud Bridge.

**Compatibiliza.** Cada marca habla su propio idioma. El Cloud Bridge los
traduce todos a uno solo con go2rtc (ver go2rtc adentro), incluido el de un DVR
o NVR que la casa ya tenga: es la única forma de llegar a cámaras analógicas
viejas, que no tienen IP propia.

**Es un puente, no una computadora.** El Cloud Bridge no analiza: lee las
cámaras y le entrega a la nube un frame por segundo de cada una, reducido. Todo
el análisis, incluido el Paso 1, corre en la nube. Por eso el hardware es
liviano y barato, y el algoritmo se mejora sin tocar las cajas. El costo de esta
decisión es tráfico: la casa sube frames todo el tiempo. Cuánto, y por qué
canal, se define antes de la Fase 1 (ver `00-DECISIONES.md`).

### Por qué una cajita y no "tu computadora"

Una computadora de uso general se apaga para ahorrar luz, se reinicia para
actualizarse, se desenchufa, y muchas no vuelven a encenderse solas después de
un corte. Cada una de esas veces, Artemisa queda ciega sin que nadie lo sepa.

Un dispositivo dedicado no se toca, arranca solo cuando vuelve la energía y se
actualiza solo. Es lo mismo que el hub de las lamparitas inteligentes o el panel
de una alarma: nadie lo encuentra raro porque tiene una sola función.

### El dispositivo

| | |
|---|---|
| **Hardware** | Se compra hecho. Como no analiza, alcanza con una placa chica. Mínimo: Linux ARM64 o x86-64, 2 GB de RAM, puerto Ethernet, arranque automático al recibir energía, y almacenamiento para la grabación (Fase 1). Referencia: una placa de formato Raspberry Pi (85 × 56 mm). Se elige por disponibilidad y precio en Argentina; el software no depende del modelo. |
| **Forma** | Caja blanca de 120 × 120 × 34 mm, al lado del router. Arriba, el logo y una línea de luz de estado; atrás, red, corriente por USB-C, memoria y reset; abajo, el QR de emparejamiento. La sirena integrada y la luz roja **no se construyen** hasta que haya diseño y fase asignada. |
| **Conexión** | Por cable al router. El Wi-Fi queda para después: una caja sin pantalla necesita un proceso propio para configurarlo. |
| **Energía** | Arranca sola cuando vuelve la luz. Un servicio del sistema levanta el agente y un watchdog lo reinicia si se cuelga. |
| **Software** | La imagen del Cloud Bridge: un Linux mínimo, go2rtc y el agente de Artemisa (lectura de cámaras, entrega de frames, canal de control, salud y, desde la Fase 1, grabación cifrada). |
| **Actualizaciones** | Automáticas y remotas, con vuelta atrás si una versión nueva no arranca. Obligatorio desde la Fase 1: nadie va a actualizar una caja a mano. |
| **Capacidad** | Objetivo: 4 cámaras por caja. Como la caja no analiza, el límite es leer y reducir los frames, y la subida de la casa. Se mide en la Fase 0 y en la beta. |
| **Luz de estado** | Blanca fija: mirando. Blanca con parpadeo lento: arrancando. Ámbar con parpadeo lento: sin internet. Apagada: en pausa o sin corriente. Roja (alerta): pendiente de fase. |

**Recomendación al usuario, opcional:** una UPS chica para el router, las
cámaras y la caja. Sin ella, un corte de luz deja a Artemisa ciega, como a
cualquier sistema de cámaras, y Artemisa lo avisa (ver `03-ALGORITMO.md`).

### go2rtc adentro

go2rtc (licencia MIT) es la capa que habla el idioma de cada marca: RTSP,
ONVIF, Hikvision, Tapo, Xiaomi, DVR genéricos y más. Se conecta a cada cámara
con su protocolo y la vuelve a exponer como un stream RTSP local, dentro de la
caja.

El agente de Artemisa **solo lee de go2rtc**, nunca directo de la cámara. Así
existe una única forma de leer cámaras, sea cual sea la marca, y sumar una marca
nueva es configurar go2rtc, no escribir código en el agente.

**Las contraseñas no quedan en disco.** go2rtc guarda en su archivo de
configuración cada cámara que se le agrega por su API, con la dirección
completa. Por eso ese archivo vive en un sistema de archivos en memoria
(tmpfs), con permisos solo para el usuario del servicio: al arrancar, el bridge
descifra la lista de cámaras del almacenamiento cifrado y escribe ahí la
configuración de go2rtc; lo que go2rtc guarde después también queda en memoria.
Al reiniciar la caja, la configuración se vuelve a armar desde el archivo
cifrado. La API de go2rtc solo escucha en `127.0.0.1`. En el laboratorio, lo
mismo con un volumen tmpfs de Docker. Se verifica que go2rtc no escriba nada
fuera de ese tmpfs.

---

## Servicios

| Servicio | Corre en | Tecnología | Responsabilidad |
|---|---|---|---|
| Cloud Bridge | La casa | Linux, go2rtc, Python, OpenCV, FFmpeg | Cámaras, entrega de frames, stream en vivo, grabación (Fase 1) |
| API | Railway | Python, FastAPI | Entrada de frames, Paso 1, Paso 2a, sesionización, canal del bridge, lectura en vivo, chat, voz, endpoints de la app |
| Worker | Railway | Python | Scheduler (Paso 2b), Paso 3, Paso 4, salud de cajas y cámaras, retención |
| Relay | Railway u otro hosting | MediaMTX | Recibe el stream del bridge y lo sirve a la app |
| Base de datos | Supabase | Postgres + Realtime | Datos y tiempo real |
| App | iOS y Android | Expo | La experiencia |
| Push | Expo | Expo Push Service | Notificaciones |
| Llamadas | Twilio | | Fase 2a y 2b |
| Errores | Sentry | | App, API, worker y bridge |

El backend es un solo proyecto de Python con varios puntos de entrada
(`artemisa-bridge`, `artemisa-api`, `artemisa-worker`, `artemisa-lab`). La
estructura está en `08-CONSTRUCCION.md`.

---

## Bridge (el software del Cloud Bridge)

### Responsabilidades

- Mantener la configuración de las cámaras de la casa, con sus credenciales
  cifradas localmente.
- Leer cada cámara a través de go2rtc (preferentemente el substream).
- Entregar a la API un frame por cámara cada `CAPTURE_INTERVAL_S`, reducido a
  `UPLOAD_MAX_WIDTH` (ver `03-ALGORITMO.md`, Paso 1). No analiza nada.
- Reportar la salud de cada cámara.
- Recibir comandos por el canal de control.
- Publicar el stream en vivo de un space cuando se le pide, y cortarlo.
- Desde la Fase 1, grabar lo que ven las cámaras, cifrado (ver Grabación).

### Lo que nunca hace

- Analizar lo que ve: eso es trabajo de la nube.
- Escribir a disco los frames que entrega a la nube. La grabación de la Fase 1
  es otra cosa, cifrada, y nunca se sube.
- Abrir puertos de entrada.
- Mandar credenciales de cámaras a la nube.
- Guardar frames para reenviarlos si la conexión falla.

### Dónde guarda las credenciales

En un archivo cifrado dentro de la caja, con una clave derivada del secreto que
recibe la caja al prepararse, y con permisos solo para el usuario del servicio.
La caja no tiene llavero de sistema operativo.

Una aclaración honesta: sin un chip de seguridad, alguien que se lleve la caja
podría llegar a leer las credenciales, porque la clave vive en el mismo equipo.
La garantía real es que no salen de la casa. Si el equipo elegido tiene TPM o un
elemento seguro, la clave se guarda ahí; es un punto a favor al elegirlo.

**En la Fase 0** el laboratorio corre en contenedores. Las credenciales van a un
archivo cifrado en un volumen de Docker, con la clave en la variable
`LAB_SECRETS_KEY`.

### Preparación de cada caja (Fase 1)

Antes de entregarla, un script de preparación:

1. Graba la imagen del Cloud Bridge.
2. Registra la caja con `POST /v1/bridges/provision` (autenticación de
   administrador, con `PROVISION_ADMIN_TOKEN`). Recibe un `bridge_id`, un
   **secreto de registro**, que se graba en la caja, y un **código de
   emparejamiento** largo (`PAIRING_CODE_LENGTH` caracteres, al azar), que no se
   graba en la caja. La base guarda solo los hashes del secreto y del código.
3. Imprime el QR del código (`artemisa://pair?code=...`) en una etiqueta que se
   pega en la caja.

El código no vence: sirve hasta que alguien reclama la caja. Por eso es largo,
y el endpoint de reclamo tiene límite de intentos.

### Emparejamiento (Fase 1)

La caja no tiene pantalla, así que el emparejamiento lo hace el QR de la
etiqueta:

1. El usuario enchufa la caja al router y a la corriente.
2. En la app escanea el QR de la etiqueta: `POST /v1/bridges/claim`. La API
   asocia la caja al usuario y borra el hash del código.
3. La caja consulta `GET /v1/bridges/pairing-status` presentando su secreto de
   registro. Cuando ya fue reclamada, la API **genera en ese momento** su token,
   guarda el hash, borra el hash del secreto de registro, y devuelve el token.
   Solo se entrega una vez.
4. La caja guarda el token cifrado y abre el canal de control con él.

**En la Fase 0** no hay emparejamiento: el laboratorio corre bridge y API en el
mismo proceso, y el bridge se autentica contra la API local con
`LAB_BRIDGE_TOKEN`, cuyo hash carga la migración de laboratorio. Así se ejercita
el mismo camino de código que en producción.

### Agregar una cámara

1. La app envía nombre y dirección RTSP: `POST /v1/spaces`.
2. La API crea el space en `pending` y reenvía la dirección al bridge del
   usuario por el canal de control. **La dirección existe en la API solo en
   memoria durante esta request.** Nunca se guarda ni se loguea: los logs
   tienen un filtro que redacta cualquier `rtsp://`.
3. El bridge agrega la cámara a go2rtc y prueba leer un frame a través de
   go2rtc, con un límite de `CAMERA_TEST_TIMEOUT_S`. Si funciona, guarda la
   dirección cifrada y empieza a entregar sus frames. Si no, la saca de
   go2rtc.
4. El bridge responde con éxito o con un código de error: `unreachable`,
   `auth_failed`, `unsupported_codec`, `timeout`.
5. Con éxito, la API pasa el space a `active`. Con error, lo borra y devuelve el
   código a la app, que muestra el estado de error (en la primera versión, un
   único mensaje para todos los códigos).

**Desde la Fase 1**, el camino principal es elegir una cámara que la caja
encontró en la red (ver Encontrar las cámaras): la app envía el id de la cámara
encontrada con su usuario y contraseña en lugar de una dirección, y la caja arma
la dirección del stream. El usuario y la contraseña siguen las mismas reglas que
una dirección RTSP: cruzan la API una sola vez, en memoria, y viven solo en el
Cloud Bridge.

### Canal de control

WebSocket saliente desde el bridge (`WSS /v1/bridges/connect`), autenticado con
el token del bridge. Mensajes JSON:

**De la nube al bridge:**

| Mensaje | Campos | Efecto |
|---|---|---|
| `add_camera` | `request_id, space_id, rtsp_url` (o, desde la Fase 1, `discovered_id, username, password`) | Probar, guardar y empezar a mirar |
| `remove_camera` | `space_id` | Dejar de mirar y borrar credenciales |
| `start_stream` | `space_id, publish_url` | Publicar el vivo al relay |
| `stop_stream` | `space_id` | Cortar el vivo |
| `discover` | `request_id` | Buscar cámaras en la red local (Fase 1) |

**Del bridge a la nube:**

| Mensaje | Campos |
|---|---|
| `hello` | `bridge_id, version, space_ids` |
| `heartbeat` | (sin campos; cada `BRIDGE_HEARTBEAT_S`, aunque no haya cámaras) |
| `health` | `space_id, ok, fps, error` (cada `HEALTH_PING_S` por cámara; solo `ok: true` cuenta como señal de vida) |
| `camera_result` | `request_id, ok, error_code` |
| `stream_result` | `space_id, ok, error_code` |
| `discovered` | `request_id, cameras: [{discovered_id, ip, manufacturer, model}]` (Fase 1) |

La API anota `last_seen_at` de la caja con **cada** mensaje que recibe. Así el
worker sabe si el Cloud Bridge está vivo mirando solo la base, aunque la conexión
parezca abierta (ver `03-ALGORITMO.md`, Artemisa nunca finge que ve).

Si el canal se corta, el bridge reconecta con espera creciente. Mientras está
desconectado no entrega nada: no hay cola de frames. La grabación de la Fase 1
sigue en la casa.

### Subida de frames

El bridge entrega un frame por cámara cada `CAPTURE_INTERVAL_S` con
`POST /v1/frames`, con el JPEG como **cuerpo crudo** y los metadatos en headers:

```
Authorization: Bearer <token del bridge>
Content-Type: image/jpeg
X-Space-Id: <uuid>
X-Frame-Id: <uuid>
X-Captured-At: 2026-09-21T19:42:11.482Z
```

La API descarta duplicados por `X-Frame-Id`, guarda el frame **en memoria**
como el último de ese space (el `inbox` del Paso 1) y lo suelta al llegar el
siguiente. **También lo suelta si el space deja de mandar:** pasados
`STALE_FRAME_S` sin un frame nuevo, el `inbox` queda vacío. El Paso 1 decide si
pasa al Paso 2a; la lectura en vivo usa el último.

**Pendiente antes de la Fase 1:** si una request por frame alcanza o hace falta
un canal continuo (WebSocket o stream), a qué tamaño y frecuencia, y cuánto
cuesta el tráfico por casa. En la Fase 0 este es el camino, dentro de la red
local.

### Grabación (Fase 1)

**En la Fase 0 no se graba nada.** Desde la Fase 1, el Cloud Bridge graba en su
memoria (microSD o SSD), cifrado, y solo el dueño puede verlo. La nube no guarda
nada visual; las reglas de zero-video de la nube no cambian.

Diseño técnico propuesto, a confirmar antes de implementar:

- El teléfono genera un par de claves al emparejar el bridge. La privada queda
  en el llavero del teléfono (`expo-secure-store`); la pública va al bridge.
- El bridge graba segmentos cortos, cifra cada uno con una clave simétrica al
  azar y guarda esa clave envuelta con la pública del usuario. El bridge no
  puede descifrar lo que grabó.
- Para ver una grabación, la app pide el segmento cifrado por el canal del
  bridge (vía relay), lo descifra en el teléfono y lo reproduce. La nube solo
  pasa bytes cifrados, sin guardarlos.
- Si el usuario pierde el teléfono sin respaldo de la clave, pierde las
  grabaciones.

Preguntas abiertas (bloquean la implementación): grabación continua, solo
clips de momentos o las dos; cuántos días y en qué almacenamiento; respaldo de
la clave y varios teléfonos por casa; diseño de las pantallas para ver
grabaciones.

### Encontrar las cámaras (Fase 1)

Después de emparejarse, la app pide `GET /v1/bridges/{id}/discovered`. La API
manda `discover` a la caja, que busca cámaras ONVIF en la red local durante unos
segundos y responde con `discovered`. La API devuelve la lista a la app sin
guardarla. El usuario elige cuáles conectar y solo escribe el usuario y la
contraseña de cada una. Escribir una dirección RTSP a mano queda como camino
alternativo, para cámaras que no se anuncian en la red.

La búsqueda y la conexión las hace go2rtc, que ya las trae: busca cámaras ONVIF
en la subred, y su fuente ONVIF (`onvif://usuario:contraseña@ip`) averigua sola
la dirección del stream. go2rtc tiene que estar en la misma subred que las
cámaras: en la caja corre directo sobre el sistema; si alguna vez corre en un
contenedor, necesita la red del equipo.

### Distribución

En la Fase 0 el bridge corre dentro del proceso de laboratorio, en una notebook.
En la Fase 1, el Cloud Bridge se entrega como caja ya preparada, en dos formas de
venta: sola, para quien ya tiene cámaras, o en un kit con cámaras del fabricante
socio. Es la misma caja preparada igual; el kit solo agrega cámaras ya elegidas
al lado. Para la beta se preparan a mano, de 10 a 20. Cómo se preparan y se
entregan a escala, y quién arma y distribuye el kit, es una decisión abierta
(ver `08-CONSTRUCCION.md`).

---

## API

FastAPI, asincrónica. Un solo proceso en la Fase 1 (ver Escala).

### Autenticación

- **App → API:** el token de sesión de Clerk en `Authorization`. La API lo
  verifica localmente con las claves públicas de Clerk, cacheadas.
- **Bridge → API:** token opaco del bridge. La base guarda solo su hash.
- **Relay → API:** el hook de autenticación de MediaMTX llama a la API para
  validar tokens de publicación y lectura de un solo uso.

### Endpoints

| Método | Ruta | Llama | Qué hace | Fase |
|---|---|---|---|---|
| GET | `/v1/health` | cualquiera | Salud del servicio | 0 |
| POST | `/v1/me` | app | Crea el usuario en el primer inicio de sesión, o lo devuelve | 1 |
| DELETE | `/v1/me` | app | Borra la cuenta y todo su historial | 1 |
| DELETE | `/v1/history` | app | Borra el historial de la casa, conserva la cuenta | 1 |
| POST | `/v1/bridges/provision` | script de preparación | Registra una caja nueva y devuelve su secreto y su código (autenticación de administrador) | 1 |
| POST | `/v1/bridges/claim` | app | Asocia la caja del QR al usuario (con límite de intentos) | 1 |
| GET | `/v1/bridges/pairing-status` | bridge | Entrega el token una vez emparejada | 1 |
| GET | `/v1/bridges/{id}/discovered` | app | Cámaras que la caja encontró en la red | 1 |
| WSS | `/v1/bridges/connect` | bridge | Canal de control (en la Fase 0, con `LAB_BRIDGE_TOKEN`) | 0 |
| POST | `/v1/frames` | bridge | Sube un frame (en la Fase 0, con `LAB_BRIDGE_TOKEN`) | 0 |
| POST | `/v1/spaces` | app | Crea un space con su cámara: dirección RTSP o, desde la Fase 1, cámara encontrada con usuario y contraseña (la prueba ocurre en el bridge) | 0 |
| PATCH | `/v1/spaces/{id}` | app | Renombrar, ajustar umbral | 1 |
| DELETE | `/v1/spaces/{id}` | app | Borrar el space | 1 |
| POST | `/v1/spaces/{id}/stream` | app | Pide el vivo, devuelve URL de HLS firmada | 0 |
| DELETE | `/v1/spaces/{id}/stream` | app | Corta el vivo | 0 |
| POST | `/v1/spaces/{id}/live-read` | app | Lectura en vivo | 0 |
| POST | `/v1/chat` | app | Chat con respuesta en streaming (SSE) | 0 |
| POST | `/v1/tts` | app | Audio mp3 de un texto | 0 |
| POST | `/v1/devices` | app | Registra el token de push | 0 |
| POST | `/v1/dispatches/{id}/opened` | app | Marca una notificación como abierta | 0 |
| POST | `/v1/relay/auth` | relay | Valida tokens del relay | 0 |
| POST | `/v1/webhooks/twilio` | Twilio | Estados de llamadas y cancelaciones | 2a |

En la Fase 0, sin cuentas, la API usa el usuario fijo del laboratorio y los
endpoints de la Fase 1 no existen.

### Límites

- `/v1/frames`: cuerpo máximo `MAX_FRAME_BYTES`, solo `image/jpeg`, leído con
  `await request.body()`. Nunca con el manejo de archivos subidos del framework,
  que escribe a disco los archivos grandes.
- `/v1/chat`, `/v1/tts`, `/live-read`: límites por usuario por minuto
  (`RATE_LIMIT_CHAT_PER_MIN`, `RATE_LIMIT_TTS_PER_MIN`,
  `RATE_LIMIT_LIVE_READ_PER_MIN`).
- `/v1/tts`: texto de hasta `TTS_MAX_CHARS` caracteres.

---

## Worker

Un proceso con varios loops:

| Loop | Frecuencia | Qué hace |
|---|---|---|
| Scheduler | `SCHEDULER_TICK_S` | Decide qué threads analizar, terminar y cerrar (Paso 2b) |
| Salud | `HEALTH_TICK_S` | Detecta cajas y cámaras sin conexión, avisa, y avisa cuando vuelven |
| Recibos de push | `RECEIPTS_POLL_S` | Actualiza el estado de los dispatches |
| Retención (Fase 1) | Diario | Borra datos vencidos |

El Paso 3 y el Paso 4 corren dentro del worker, en las tareas que lanza el
scheduler.

**Locks.** La sesionización y el procesamiento de cada thread toman locks de
Postgres (advisory locks sobre el id del space o del thread), así que son
correctos aunque haya más de un proceso.

### Señales entre la API y el worker

La API y el worker son procesos distintos y no comparten memoria. Se avisan
cosas con `LISTEN` / `NOTIFY` de Postgres, que no suma infraestructura:

| Canal | De → a | Contenido | Uso |
|---|---|---|---|
| `analyze_now` | API → worker | `thread_id`, `fast_path` | El camino rápido de un flag urgente |
| `boost` | worker → API | `space_id`, `interval_s`, `duration_s` | El refuerzo del Paso 3: lo aplica el loop de movimiento de ese space, que vive en la API |

En el código, `signal_worker(...)` y `signal_api(...)` encapsulan esto. Con
varias instancias de la API, todas reciben el `boost` y solo lo aplica la que
tiene el loop de movimiento de ese space (ver Escala). Cuando quien envía y
quien recibe están en el mismo proceso, como en el laboratorio, el mensaje va
directo por memoria.

---

## Stream en vivo

### Flujo

1. La app pide `POST /v1/spaces/{id}/stream`.
2. La API verifica que el space sea del usuario y esté activo, y que el Cloud Bridge tenga señal (si no, responde enseguida con error, sin esperar). Genera
   una ruta aleatoria y tokens de un solo uso para publicar y para leer.
3. La API manda `start_stream` al bridge con la URL de publicación.
4. El bridge corre FFmpeg: lee la cámara desde go2rtc y publica al relay
   **copiando** el video, sin recodificar, para no gastar la CPU de la caja.
5. Cuando el bridge confirma (con un límite de `STREAM_START_TIMEOUT_S`), la API
   devuelve a la app la URL de HLS con el token de lectura y su vencimiento.
6. La app reproduce la URL.
7. Al salir de la pantalla, la app llama a `DELETE /v1/spaces/{id}/stream`. Si
   la app desaparece sin avisar, el bridge y el relay cortan solos a los
   `STREAM_IDLE_TIMEOUT_S` sin lectores.

### Privacidad del stream

- El relay mantiene los segmentos de HLS **en memoria**. No se configura ningún
  directorio en disco para HLS. Se verifica en la configuración.
- La lista de segmentos es corta: existen unos pocos segundos de video a la vez.
- No hay grabación en el relay. Cualquier opción de grabación queda desactivada
  explícitamente.

### Decisiones técnicas

- **Publicación del bridge al relay:** SRT o RTSP sobre TCP. Se elige en la Fase
  1 según cuál atraviesa mejor las redes domésticas de prueba. Si se usa SRT
  (UDP), hay que confirmar que el hosting del relay exponga UDP.
- **Substream por defecto** para el vivo: las conexiones domésticas suelen tener
  poca subida. La opción de alta calidad queda para después.
- **Latencia:** HLS tiene de 2 a 6 segundos de retraso. Es aceptable para "See
  now". Si hace falta menos, MediaMTX también sirve WebRTC, en una fase
  posterior.
- **Códecs:** H.264 pasa sin problemas. H.265 se reproduce en iOS pero no en
  todos los Android; en ese caso se le pide al usuario configurar la cámara en
  H.264, o el bridge recodifica si su CPU lo permite.

---

## Tiempo real

La app se suscribe a cambios de Postgres a través de Supabase Realtime,
autenticada con el token de Clerk. Los eventos respetan RLS. Qué tablas y qué
eventos: ver `05-DATOS.md`.

El backend no le avisa nada a la app directamente: escribe en la base, y la
base le avisa a la app. Así el backend no necesita saber si la app está abierta.

---

## Autenticación

- **Clerk** gestiona cuentas e inicio de sesión (Apple, Google, email).
- **Supabase acepta a Clerk como proveedor de autenticación externo.** Se
  configura la integración en ambos paneles para que el token de Clerk incluya
  el claim de rol que Supabase espera.
- En la app, el cliente de Supabase se crea pasándole una función que devuelve
  el token actual de Clerk en cada request.
- En la base, las políticas comparan `auth.jwt()->>'sub'` con `user_id`.

---

## Notificaciones

- La app registra su token de Expo Push con `POST /v1/devices`.
- El backend envía por Expo Push Service: título con el nombre del space, cuerpo
  con la narrativa, y en los datos el `thread_id` (para abrir el detalle) y el
  `dispatch_id` (para marcarlo como abierto).
- Los avisos de sistema (casa sin señal, casa de vuelta, cámara sin conexión)
  usan el mismo servicio pero no llevan `thread_id` ni `dispatch_id`, y no se
  registran en `dispatches`.
- **Nivel de interrupción:**

| Nivel | iOS | Android (canal) |
|---|---|---|
| `passive` | pasivo, sin sonido | `quiet`, importancia baja |
| `time_sensitive` | sensible al tiempo, atraviesa modos de concentración | `alerts`, importancia alta |
| `critical` | crítico, suena aunque el teléfono esté en silencio | `urgent`, importancia máxima |

- Los avisos críticos en iOS requieren un permiso especial de Apple que hay que
  solicitar. Mientras no esté aprobado, `critical` se envía como
  `time_sensitive`.
- Se verifica cómo expone Expo Push Service el nivel de interrupción de iOS al
  implementar el envío.
- Los recibos de Expo actualizan `dispatches.status`. Al tocar la notificación,
  la app llama a `/v1/dispatches/{id}/opened`.

---

## Secretos y variables de entorno

La app solo contiene claves publicables. Nada que permita escribir en la base,
llamar a un modelo o enviar notificaciones vive en la app.

### App (`mobile/.env`)

```
EXPO_PUBLIC_API_URL=
EXPO_PUBLIC_SUPABASE_URL=
EXPO_PUBLIC_SUPABASE_ANON_KEY=
EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY=      # Fase 1
EXPO_PUBLIC_SENTRY_DSN=
EXPO_PUBLIC_LAB_MODE=true               # solo Fase 0
EXPO_PUBLIC_LAB_USER_ID=user_lab        # solo Fase 0
```

### API y worker (`server/.env`)

```
PHASE=0                                 # 0 | 1 | 2a | 2b
DATABASE_URL=                           # Postgres de Supabase (pooler)
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
CLERK_ISSUER=                           # Fase 1
CLERK_JWKS_URL=                         # Fase 1
AI_GATEWAY_API_KEY=                     # Vercel AI Gateway: todos los modelos
OPENAI_API_KEY=                         # solo si `tts` la necesita, a definir en el paso 15
EXPO_ACCESS_TOKEN=
RELAY_PUBLISH_URL=
RELAY_HLS_PUBLIC_URL=
MODELS_CONFIG=artemisa/core/models.yaml
PROVISION_ADMIN_TOKEN=                  # Fase 1, solo lo usa el script de preparación
SENTRY_DSN=
TWILIO_ACCOUNT_SID=                     # Fase 2a
TWILIO_AUTH_TOKEN=                      # Fase 2a
TWILIO_FROM_NUMBER=                     # Fase 2a
```

### Bridge

```
ARTEMISA_API_URL=
```

El token del bridge y las credenciales de las cámaras no van en variables de
entorno: van al archivo cifrado de la caja (ver Dónde guarda las credenciales).

### Laboratorio (solo Fase 0)

```
LAB_BRIDGE_TOKEN=                       # token del bridge de laboratorio
LAB_SECRETS_KEY=                        # clave del archivo cifrado de credenciales
VIDEO_SOURCE=                           # ruta a un .mp4 en lugar de la cámara RTSP
DEBUG_SAVE_FRAMES=false                 # ver 08-CONSTRUCCION.md
```

Estas variables las lee solo `artemisa-lab`. El bridge que se distribuye en la
Fase 1 no las conoce.

---

## Qué viaja, adónde y qué queda

| Dato | ¿Sale de la casa? | Adónde va | ¿Se guarda? |
|---|---|---|---|
| Dirección RTSP, o usuario y contraseña de una cámara | Una vez, al agregar la cámara | App → API → Cloud Bridge, en memoria | Solo en el Cloud Bridge, cifrado |
| Cámaras encontradas en la red (IP, marca, modelo) | Sí, al conectar cámaras (Fase 1) | Cloud Bridge → API → app | No |
| Latido de la caja | Cada `BRIDGE_HEARTBEAT_S` | Cloud Bridge → API | Solo la hora del último (`last_seen_at`) |
| Frame de cada cámara | Sí, uno por segundo, reducido | Cloud Bridge → API (Paso 1), en memoria | No. Se descarta al llegar el siguiente |
| Frame con movimiento o de estado | Sí, reducido | API → proveedor de visión | No. El proveedor puede retener según sus términos |
| Frame de lectura en vivo | Sí, reducido | API → proveedor de visión | No. Ídem |
| Grabación (Fase 1) | No | Queda en el Cloud Bridge, cifrada. Para verla, viaja cifrada al teléfono vía relay | Solo en el Cloud Bridge |
| Stream en vivo | Solo mientras alguien mira | Relay → app | No. Memoria, segundos |
| Descripciones, narrativas, razonamientos | Se generan en la nube | Supabase | Sí, según retención |
| Voz del usuario | No | Reconocimiento del teléfono (en el dispositivo cuando está disponible) | No |
| Texto que Artemisa lee en voz alta | Sí | API → proveedor de voz | No |

---

## Observabilidad

- **Sentry** en la app, la API, el worker y el bridge, configurado para no
  enviar cuerpos de requests ni variables locales, con un filtro que descarta
  cualquier campo con una dirección `rtsp://`.
- **Logs** estructurados en JSON con id de request, con el mismo filtro. Nunca
  se loguean cuerpos de frames, prompts ni respuestas de modelos.
- **`pipeline_runs`** registra cada llamada a un modelo con tokens, costo,
  latencia y resultado. `artemisa-lab report` resume costo por hora, volumen
  por paso y latencias.

---

## Escala

En la Fase 1 la API corre como una sola instancia y el worker como otro proceso.
Con varias instancias de API, los comandos al bridge siguen funcionando: todas
reciben el `NOTIFY` y solo la que tiene abierto el canal de ese bridge lo
reenvía. Lo que no escala así es el Paso 1: el fondo que compara cada space y
el último frame (`inbox`) viven en la memoria de una instancia. Por eso los
frames de un bridge se fijan a la instancia de su canal, y la lectura en vivo y
el refuerzo del Paso 3 se atienden en esa misma instancia. No hace falta para la
beta.

---

## Fase 0: todo en una máquina

```
Notebook en la casa (misma red que la cámara)
  docker compose
    lab       bridge + API + worker en un solo proceso (artemisa-lab)
    go2rtc    el mismo que va en la caja; el bridge lee las cámaras de acá
    relay     MediaMTX local
  → cámara RTSP, o un .mp4 grabado (VIDEO_SOURCE)

Supabase: proyecto de laboratorio, separado de producción

Teléfono en la misma Wi-Fi
  build de desarrollo de la app → API en http://<ip-de-la-notebook>:8000
```

Para hablar con la notebook por HTTP en la red local, el build de desarrollo de
iOS necesita permitir redes locales y el usuario tiene que aceptar el permiso de
red local. Eso es solo para la Fase 0.
