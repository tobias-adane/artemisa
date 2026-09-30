# 02. Producto

## La experiencia en una frase

Abrís la app y leés tu día como una línea: qué pasó en tu casa, cuándo, y qué
hizo Artemisa al respecto. Si querés, mirás en vivo. Si tenés una duda, le
preguntás.

---

## Superficies del producto

El producto tiene dos superficies distintas que no hay que confundir:

**Eventos (threads).** Pasado. Tienen hora. Son lo que Artemisa entendió. Es lo
que abre la app.

**Feed en vivo.** Presente. No tiene hora. Es la cámara ahora mismo, con lo que
Artemisa dice de lo que ve. El usuario llega ahí solo si quiere mirar.

---

## Mapa de pantallas

El diseño visual es la fuente de verdad de **cómo se ve** cada pantalla y vive
exportado en `design/`, una imagen por pantalla o estado. Este documento define
**qué hace** cada pantalla y **qué dice**: el texto visible sale de la tabla de
textos de este documento, no de las imágenes. Si una imagen muestra un texto
distinto (un placeholder, una versión vieja de un botón, contenido de ejemplo),
gana este documento.

**El canvas de Claude Design.** Hay un canvas "Artemisa" en Claude Design con
la dirección visual más nueva (Inicio, Actividad, Espacios, Espacio,
Configuración, Onboarding). Es la referencia de cómo se ve el producto, pero
una pantalla del canvas se construye recién cuando está en esta lista, con su
imagen exportada en `design/` y sus textos en la tabla. Si una pantalla del
canvas muestra algo bloqueado (llamadas, contactos de emergencia, el 911) o un
texto que contradice este documento, gana este documento.

### Pantallas diseñadas

| Pantalla | Archivo de diseño | Fase |
|---|---|---|
| Home (línea del día) | `design/home.png` | 0 |
| Detalle de un thread | `design/thread-detail.png` | 0 |
| Feed en vivo | `design/live-feed.png` | 0 |
| Conectar cámara | `design/connect-camera.png` | 0 |
| Conectar cámara, error | `design/connect-camera-error.png` | 0 |

### Pantallas y estados pendientes de diseño

Son necesarios pero no están diseñados. **No se construyen sin diseño.** Si
hace falta uno para avanzar, se pregunta.

| Pantalla o estado | Por qué hace falta | Fase |
|---|---|---|
| Chat (respuesta a "Ask anything" y "Ask something") | Sin esto el input no tiene dónde responder | 0 |
| Escuchando (voz activa en el input) | Feedback mientras el usuario habla | 0 |
| Feed en vivo: conectando y error | El stream tarda unos segundos o puede fallar | 0 |
| Estado de emergencia (thread, encabezado, notificación) | El pipeline puede clasificar `emergency` desde la Fase 0 | 0 |
| Enseñale tu casa (custom instructions) | Es el insumo más importante del sistema | 1 |
| Iniciar sesión | Cuentas reales | 1 |
| Emparejar el Cloud Bridge (escanear el QR de la caja) | Conectar la casa con la cuenta | 1 |
| Elegir las cámaras que encontró el Cloud Bridge | Conectar una cámara sin escribir su dirección | 1 |
| Menú (spaces, tu casa, preferencias, cerrar sesión) | Gestión mínima | 1 |
| Cámara sin conexión (en la lista de spaces) | Una cámara se puede caer | 1 |
| Primer día sin threads | La línea vacía no puede decir "sin eventos" | 1 |
| Días anteriores (control de día) | Navegar la memoria por día | 1 |
| Perfil (avatar) | Cuenta del usuario | 1 |
| Borrar historial y borrar cuenta | Control del usuario sobre sus datos | 1 |
| Ver grabaciones (las que guarda el Cloud Bridge) | La grabación local cifrada es de la Fase 1 (ver `00-DECISIONES.md`) | 1 |

---

## Home

La pantalla principal. Abre siempre en el día de hoy.

### Encabezado

Arriba, de izquierda a derecha: botón de menú, la marca de Artemisa centrada, y
el avatar del usuario.

Debajo, dos líneas:

- **Saludo:** según la hora local del usuario y su nombre. "Good night, Alexander".
- **Estado de la casa:** una frase en la voz de Artemisa que resume cómo está la
  casa ahora. "Everything feels right at home." Se calcula de forma
  determinística a partir del estado real (ver `03-ALGORITMO.md`, Estado de la
  casa). Nunca contradice lo que muestra la línea: si hubo algo que merece
  atención hoy, el encabezado no dice que todo está bien. Y si Artemisa no puede
  ver la casa, el encabezado lo dice (ver Artemisa siempre dice qué puede ver,
  más abajo).

### La línea del día

Una tarjeta con el rótulo "Threads" y un control de día ("Today"). Adentro, la
línea: un riel vertical con una píldora de hora por cada thread.

**Orden:** del más reciente al más viejo. Lo último que pasó está arriba.

Cada thread muestra:

- **Píldora de hora** sobre el riel, con un punto de estado (normal, atención,
  emergencia). La hora se formatea según el idioma del usuario.
- **Narrativa**, el texto principal.
- **Space**, como línea chica debajo ("Front Door").
- **Acciones**, alineadas a la derecha.

### Estados de un thread en la línea

**Composing.** El thread ya tiene observaciones pero Artemisa todavía no terminó
de entender el momento. Muestra "Artemisa is composing the moment…", dos líneas
grises animadas con un brillo suave, y el space. Solo tiene la acción "See now",
porque todavía no hay nada sobre qué preguntar. Es el estado que hace visible
que el producto está pensando en este momento.

**Activo.** El momento está en curso y ya tiene narrativa. La narrativa puede
actualizarse mientras siga pasando algo.

**Cerrado.** El momento terminó. Se ve igual que el activo.

Composing pasa a activo en el mismo lugar, sin saltos: la narrativa reemplaza a
las líneas grises.

### Acciones de cada thread

**See now.** Abre el feed en vivo del space de ese thread. El nombre es
deliberado: un botón debajo de algo que pasó hace cuatro horas no puede decir
"Watch", porque promete reproducir el pasado. "See now" dice exactamente lo que
hace. Ver una grabación (Fase 1) va a ser una acción aparte, con su propio
diseño y su propio texto.

**Ask something.** Abre el chat con ese thread como contexto. La pregunta del
usuario se responde sobre ese momento específico.

**Tocar el cuerpo del thread** abre su detalle.

### Input fijo

Abajo, flotando sobre la línea: un botón `+`, el campo "Ask anything", y el botón
de voz. El contenido de la línea se desvanece detrás.

- El campo abre el chat general sobre la casa.
- El botón de voz permite hablarle en lugar de escribir.
- El contenido del menú `+` está **pendiente de definir.** La propuesta es:
  adjuntar una foto al chat, y más adelante "A tu Alrededor". Mientras tanto se
  muestra como en el diseño y no hace nada.

---

## Detalle de un thread

Se abre al tocar un thread. Es la misma línea vista de cerca.

De arriba hacia abajo:

- **Meta:** hora y space. "Today, 7:42 PM · Front Door".
- **Narrativa**, como título.
- **Why I'm telling you:** el razonamiento. Explica por qué el momento importa o
  por qué no, apoyándose en la rutina de la casa.
- **What I did:** qué hizo Artemisa, en primera persona. Se genera a partir del
  registro real de acciones, nunca del nivel teórico (ver Textos). Si Artemisa
  decidió no hacer algo, lo dice: "I didn't contact anyone else."
- **What I saw:** las observaciones que formaron el momento, cada una con su
  hora al segundo. La precisión de segundos es parte de lo que el producto
  demuestra: la respuesta es inmediata.

**Pendiente de diseño:** si el detalle muestra también "See now" y "Ask
something", y cómo se indica que Artemisa miró dos veces (cuando el thread pasó
por el Paso 3). La propuesta es una línea chica: "I took a second, closer
look."

---

## Feed en vivo

Se abre desde "See now". Es presente puro: **no hay ninguna hora en esta
pantalla.**

- **Video en vivo** del space, grande, con un botón para volver y una etiqueta
  "Live" encima.
- **Nombre del space** como rótulo.
- **Titular:** una frase sobre el estado de la casa entera. "Your home's empty
  right now. All secure."
- **Lectura en vivo:** dos o tres oraciones sobre lo que se ve en este space
  ahora, que cierran en una observación concreta. "Your living room is quiet.
  It's that calm stretch of the evening when the light comes through the windows
  just right. Nothing's moved in about an hour."
- **Línea de privacidad**, con un candado: "You're watching this live. Artemisa
  doesn't record it."
- El mismo input fijo que el Home.

La etiqueta "Live" y la línea de privacidad son obligatorias. Sin ellas, un
usuario que ve una imagen grande de su living asume que Artemisa la guarda, y el
producto pierde exactamente lo que lo diferencia. El texto actual de la línea de
privacidad vale para la Fase 0; en la Fase 1, cuando el bridge graba, se
reescribe (ver Textos).

Cuando el usuario sale de la pantalla, el stream se corta.

---

## Primer uso

### Conectar cámara (diseñada)

La marca, un título, una explicación corta, un campo para la dirección de la
cámara con `rtsp://` como placeholder, una ayuda sobre dónde encontrar la
dirección, una línea de privacidad al pie, y el botón para conectar. Los textos
están en la tabla.

**Error de conexión (diseñado):** el campo se marca, aparece el mensaje de error
con una ayuda adicional, un enlace secundario "Can't find the address?", y el
botón "Try again". **La dirección que el usuario escribió no se borra.** La URL
RTSP es la mayor fricción real del onboarding; perder lo tipeado la empeora.

El tratamiento visual del error sale del diseño. Regla de producto: el
tratamiento exclusivo de emergencia nunca se usa para errores.

### El resto del primer uso (Fase 1, pendiente de diseño)

El orden previsto:

1. Iniciar sesión.
2. Enchufar el Cloud Bridge al router y a la corriente, y escanear el QR de la
   caja.
3. Elegir las cámaras que el Cloud Bridge encontró en la red y escribir el usuario
   y la contraseña de cada una. Si una cámara no aparece, se conecta con su
   dirección desde la pantalla Conectar cámara, que ya está diseñada.
4. Enseñarle la casa a Artemisa.

"Enseñale tu casa" es obligatorio: sin custom instructions, Artemisa clasifica
a ciegas.

---

## Features

**Accessible Protection.** Funciona con las cámaras IP que la familia ya tiene,
de casi cualquier marca. Lo único nuevo en la casa es el Cloud Bridge, una cajita
que se enchufa al router. Sin kits caros, sin instalación en las paredes, sin
cambiar de cámaras.

**Real-Time Understanding.** No son alertas de movimiento. Es comprensión de lo
que pasa mientras pasa, distinguiendo lo cotidiano de lo que necesita atención.

**Contextual Intelligence.** Entiende qué pasó antes, qué pasa ahora y por qué
importa, usando la rutina que el usuario le enseñó. Es lo que termina con la
fatiga de alertas y el diferenciador más importante del producto.

**Living Memory.** En lugar de horas de grabación, una línea de momentos
significativos por día, en texto. La nube nunca guarda video; la grabación,
desde la Fase 1, queda en la casa y es algo que la familia elige mirar.

**Natural Interaction.** Preguntas en lenguaje natural, por texto o voz: "¿quién
vino hoy?", "¿Maya ya llegó?". Las respuestas salen de los threads reales.

**Live View.** Mirar cualquier space en vivo, con la lectura de Artemisa de lo
que se ve. La nube no lo graba.

**Privacy by Design.** "What happens at home stays home." La nube no guarda
nada visual y lo que se graba queda cifrado en la casa. Ver `01-INTRODUCCION.md`.

**Auto Dispatch (por fases).** Cuando pasa algo real, Artemisa avisa de forma
proporcional. En la primera versión avisa solo al usuario con notificaciones.
Las llamadas llegan en la Fase 2a. Contactar a terceros y a servicios de
emergencia es la Fase 2b y está bloqueada hasta resolver la consulta legal.

**A tu Alrededor (beta futura).** Red comunitaria opt-in entre vecinos que usan
Artemisa: las cámaras que miran a la calle comparten análisis en texto, nunca
imágenes, dentro de un radio cercano. Requiere consulta legal propia bajo la Ley
25.326 antes de construirse. No forma parte de la primera versión.

---

## Los 4 niveles de acción

No todo lo que importa merece la misma respuesta.

| Nivel | Acción | Significado |
|---|---|---|
| 1 | `informar` | Relevante pero no urgente. Aviso silencioso. |
| 2 | `alertar` | El usuario tiene que saberlo ahora. |
| 3 | `contactar` | Hay que llegar a una persona, aunque no sea una emergencia confirmada. |
| 4 | `emergencia` | Protocolo completo. |

### Qué hace cada nivel según la fase

| Nivel | Fase 0 y 1 | Fase 2a (llamadas al usuario) | Fase 2b (terceros, bloqueada) |
|---|---|---|---|
| `informar` | Notificación silenciosa | Igual | Igual |
| `alertar` | Notificación urgente | + llamada al usuario si no abre la notificación en 2 minutos | Igual |
| `contactar` | Notificación urgente | + llamada al usuario | + llamada y WhatsApp a contactos de emergencia, en orden de prioridad |
| `emergencia` | Notificación crítica | + llamada al usuario | + contactos + servicios de emergencia, con ventana de cancelación |

### Reglas

**Regla de oro.** Cuanto mayor el impacto de una acción, mayor la certeza que
hace falta para tomarla. Toda acción por encima de `informar` requiere que el
momento haya pasado por el razonamiento profundo (Paso 3). `emergencia` solo es
posible si la clasificación es `emergency` y el Paso 3 confirmó severidad alta.

**Nunca se decide al revés.** La acción sale del nivel; el texto que ve el
usuario sale de lo que realmente pasó. Si el nivel era `contactar` pero en esta
fase solo se mandó una notificación, "What I did" dice que se mandó una
notificación.

**Horas de silencio.** Durante las quiet hours del usuario, `informar` no
notifica (queda en la línea), `alertar` se entrega como aviso silencioso y no
dispara llamadas, y `contactar` y `emergencia` no se silencian nunca.

**Una sola escalada por momento.** Si un thread se vuelve a analizar, Artemisa
solo actúa de nuevo si el nivel sube. Nunca repite el mismo aviso.

**El aviso de resguardo.** Si los modelos no responden y un momento trae
señales de riesgo (humo, alguien en el piso, una puerta forzada), Artemisa avisa
igual al usuario, solo a él y con urgencia, sin subir de nivel. Es la única
excepción a la regla de oro, porque es la acción de menor impacto posible y el
silencio sería peor. Detalle en `03-ALGORITMO.md`.

### Cuándo interrumpe Artemisa

| Situación | Comportamiento |
|---|---|
| `normal` | Solo aparece en la línea. No interrumpe. |
| `attention` | Aviso según el nivel. Informativo, sin preguntas. |
| `emergency` confirmada | Nunca pregunta. Actúa según la fase. |
| El Cloud Bridge sin señal durante 2 minutos (corte de luz, corte de internet, alguien lo desenchufó) | Aviso con prioridad, silencioso en quiet hours. Al recuperar la señal, un aviso silencioso con el tiempo que no pudo ver. Los cortes de menos de 2 minutos no se avisan. |
| Una cámara sin señal durante 10 minutos, con el Cloud Bridge conectado | Aviso silencioso y calmo: una cámara caída no es una emergencia. |
| Quiet hours | Ver reglas arriba. |

---

## Artemisa siempre dice qué puede ver

Un sistema de seguridad que está ciego y no lo dice es peor que no tener nada:
la familia cree que está cuidada y no lo está. Por eso:

- Si Artemisa no ve la casa entera, lo avisa, y el encabezado del Home lo dice
  mientras dure. Cuando vuelve a ver, lo avisa y dice cuánto tiempo no pudo ver.
- Si no ve una cámara, lo dice.
- Ningún texto promete lo que Artemisa no puede cumplir. Durante un corte de luz
  Artemisa no ve, como cualquier sistema de cámaras. La diferencia es que lo
  dice.
- Ningún texto dice que no hace falta nada nuevo en la casa ("No new hardware").
  Hace falta el Cloud Bridge, y se dice.

---

## Identidad sin biometría

Artemisa construye una idea de quién vive en la casa a partir de evidencia
acumulada: rasgos generales, ropa, objetos que alguien suele llevar, horarios,
lugares que frecuenta, y lo que el usuario le contó en sus custom instructions.

La lógica nunca es "es esta cara". Es "la persona observada coincide lo
suficiente con alguien que vive acá". Cuando no alcanza, lo dice: "Looks like
Maya's home, but I'm not completely sure."

**No hay reconocimiento facial biométrico.** Los datos biométricos son datos
sensibles bajo la Ley 25.326. Si alguna vez se agrega, será opt-in explícito por
persona y nunca automático sobre visitantes.

---

## Voz y copy

Artemisa habla como alguien que cuida la casa, no como un sistema que reporta
eventos.

### Reglas

- **Qué pasó, no qué hizo la cámara.** "Everyone's out. The house is empty." y
  nunca "No motion detected".
- **Específica.** Lo que notaría alguien que conoce la casa: "Maya's off to
  school. Her jacket's still on the kitchen chair."
- **La incertidumbre es válida.** "Looks like Maya's home, but I'm not completely
  sure." es mejor que afirmar algo que no sabe.
- **Sin dramatismo y sin falsa tranquilidad.** Nunca exagera, nunca minimiza.
- **Corta.** La línea se lee de un vistazo.
- **Sin guiones largos** en el copy de la interfaz.
- **El aparato se llama Cloud Bridge.** En el copy, después de nombrarlo una
  vez, alcanza con "tu bridge".
- **El sujeto es la familia**, no Artemisa: "protegé a los que querés", no
  "Artemisa protege a tu familia" (ver `10-NEGOCIO.md`).

### Palabras que nunca aparecen en la interfaz

"AI", "artificial intelligence", "model", "vision", "detected", "detection",
"motion", "person detected", "no events", "processing", "Watch" (sobre algo
pasado), "replay", "recording" (salvo para decir que no se graba).

En español: "IA", "inteligencia artificial", "modelo", "detectado", "movimiento
detectado", "persona detectada", "sin eventos registrados", "procesando", "ver
video".

---

## Textos

Esta tabla es la fuente de verdad de todo texto visible. Cada fila es una clave
de traducción: la app la lee de `en.json` y `es-AR.json`, que ya están
generados a partir de esta tabla en `docs/i18n/`. Ningún texto visible se
escribe fuera de estas claves; si hace falta uno nuevo, se pregunta. Si la
tabla cambia, los JSON se regeneran.

### Home

| Clave | en | es-AR |
|---|---|---|
| `home.greeting.morning` (5 a 12 h) | Good morning, {name} | Buen día, {name} |
| `home.greeting.afternoon` (12 a 19 h) | Good afternoon, {name} | Buenas tardes, {name} |
| `home.greeting.evening` (19 a 22 h) | Good evening, {name} | Buenas noches, {name} |
| `home.greeting.night` (22 a 5 h) | Good night, {name} | Buenas noches, {name} |
| `home.state.default` | Everything feels right at home. | Todo se siente bien en casa. |
| `home.state.empty` | Your home's empty right now. All secure. | Tu casa está vacía ahora. Todo en orden. |
| `home.state.attentionOne` | A calm day, with one thing worth telling you about. | Un día tranquilo, con una sola cosa que contarte. |
| `home.state.attentionFew` | A day with a few things worth telling you about. | Un día con algunas cosas para contarte. |
| `home.state.attentionRecent` | There's something I want to tell you about. | Hay algo que quiero contarte. |
| `home.state.offline` | I can't see the {space} right now. Everything else is quiet. | No puedo ver {space} ahora. Todo lo demás está tranquilo. |
| `home.state.blind` | I haven't been able to see your home since {time}. | No puedo ver tu casa desde las {time}. |
| `home.state.day1` | I'm getting to know your home. I'll tell you what I notice. | Estoy conociendo tu casa. Te voy a contar lo que note. |
| `home.state.emergency` | Pendiente de diseño | Pendiente de diseño |
| `home.threads` | Threads | Hilos |
| `home.today` | Today | Hoy |
| `thread.composing` | Artemisa is composing the moment… | Artemisa está componiendo el momento… |
| `thread.seeNow` | See now | Ver ahora |
| `thread.askSomething` | Ask something | Preguntá algo |
| `ask.placeholder` | Ask anything | Preguntá lo que quieras |

### Detalle

| Clave | en | es-AR |
|---|---|---|
| `detail.today` | Today, {time} | Hoy, {time} |
| `detail.why` | Why I'm telling you | Por qué te lo cuento |
| `detail.did` | What I did | Qué hice |
| `detail.saw` | What I saw | Lo que vi |

### What I did

Se arman a partir de los dispatches del thread (`05-DATOS.md`).

| Clave | Cuándo | en | es-AR |
|---|---|---|---|
| `did.nothing` | No hubo ningún aviso | Nothing. I didn't interrupt you. It's here when you want it. | Nada. No te interrumpí. Está acá cuando lo quieras ver. |
| `did.pushQuiet` | Notificación silenciosa | I sent you a notification. | Te mandé una notificación. |
| `did.pushAlert` | Notificación urgente o crítica | I let you know at {time}. | Te avisé a las {time}. |
| `did.pushFailed` | La notificación falló | I tried to let you know, but the notification didn't go through. | Intenté avisarte, pero la notificación no llegó. |
| `did.calledYou` | Llamada atendida (Fase 2a) | I called you at {time}. | Te llamé a las {time}. |
| `did.calledYouNoAnswer` | Llamada no atendida (Fase 2a) | I called you at {time}. You didn't answer. | Te llamé a las {time}. No atendiste. |
| `did.calledContact` | Llamada a un contacto (Fase 2b) | I called {name}. | Llamé a {name}. |
| `did.messagedContact` | Mensaje a un contacto (Fase 2b) | I messaged {name}. | Le escribí a {name}. |
| `did.emergencyServices` | Servicios de emergencia (Fase 2b) | I contacted emergency services at {time}. | Contacté al servicio de emergencias a las {time}. |
| `did.cancelled` | El usuario canceló (Fase 2b) | You cancelled at {time}. I didn't contact anyone else. | Cancelaste a las {time}. No contacté a nadie más. |
| `did.noOneElse` | Se agrega cuando el nivel fue `alertar` o más y no se contactó a terceros | I didn't contact anyone else. | No contacté a nadie más. |

### Feed en vivo

| Clave | en | es-AR |
|---|---|---|
| `live.badge` | Live | En vivo |
| `live.privacy` | You're watching this live. Artemisa doesn't record it. | Lo estás viendo en vivo. Artemisa no lo graba. |

`live.privacy` vale solo mientras el bridge no graba (Fase 0). Se reescribe
antes de la Fase 1.

### Conectar cámara

| Clave | en | es-AR |
|---|---|---|
| `connect.title` | Let's connect your first camera. | Conectemos tu primera cámara. |
| `connect.body` | Artemisa works with the cameras you already have at home. | Artemisa funciona con las cámaras que ya tenés en casa. |
| `connect.label` | Camera address | Dirección de la cámara |
| `connect.placeholder` | rtsp:// | rtsp:// |
| `connect.help` | You'll find it in your camera's app, under remote access or RTSP. | La encontrás en la app de tu cámara, en la sección de acceso remoto o RTSP. |
| `connect.privacy` | Artemisa understands what it sees and never keeps the images. | Artemisa entiende lo que ve y nunca guarda las imágenes. |
| `connect.submit` | Connect | Conectar |
| `connect.error` | I couldn't connect to that address. Check it and let's try again. | No pude conectarme a esa dirección. Revisala y probemos de nuevo. |
| `connect.errorHelp` | Make sure the camera is on and on the same network as your bridge. | Fijate que la cámara esté encendida y en la misma red que tu bridge. |
| `connect.findAddress` | Can't find the address? | ¿No encontrás la dirección? |
| `connect.retry` | Try again | Probar de nuevo |

`connect.privacy` vale solo mientras el bridge no graba (Fase 0). Se reescribe
antes de la Fase 1.

### Accesibilidad (botones de solo ícono)

| Clave | en | es-AR |
|---|---|---|
| `a11y.menu` | Menu | Menú |
| `a11y.profile` | Your profile | Tu perfil |
| `a11y.more` | More options | Más opciones |
| `a11y.voice` | Talk to Artemisa | Hablale a Artemisa |
| `a11y.back` | Back | Volver |

### Textos que usa el servidor

Los escribe el backend, en el idioma del usuario. Están generados en
`docs/i18n/server.en.json` y `docs/i18n/server.es-AR.json`, y se copian a
`server/artemisa/core/locales/`.

| Clave | Dónde | en | es-AR |
|---|---|---|---|
| `push.homeBlind` | El Cloud Bridge perdió la señal | I lost contact with your home at {time}. It might be a power or internet cut. | Perdí contacto con tu casa a las {time}. Puede ser un corte de luz o de internet. |
| `push.homeBack` | El Cloud Bridge recuperó la señal | I can see your home again. I couldn't see it between {start} and {end}. | Vuelvo a ver tu casa. No pude verla entre las {start} y las {end}. |
| `push.cameraOffline` | Aviso de cámara sin conexión | I can't see the {space} right now. | No puedo ver {space} ahora. |
| `fallback.urgentNarrative` | Narrativa del aviso de resguardo | I saw something at the {space} I want you to look at. | Vi algo en {space} que quiero que mires. |

---

## Idiomas

La interfaz arranca en inglés y soporta español rioplatense (`es-AR`) desde el
primer día. Todos los textos pasan por el sistema de traducciones; ningún texto
visible se escribe directo en un componente.

Lo que generan los modelos (layers, narrativas, razonamientos, lectura en vivo,
respuestas del chat) se escribe en el idioma del usuario, que se pasa como
parámetro en cada llamada.

---

## El día de demo

Datos de ejemplo para desarrollo, seed y demos. Un día normal, sin peligro, con
movimiento real. Todo en `normal`.

| Hora | Space | Narrativa |
|---|---|---|
| 6:40 AM | Kitchen | Kitchen light's on. Someone's up before the alarm. |
| 7:20 AM | Kitchen | Breakfast happening. The usual three. |
| 7:48 AM | Kitchen | Maya's off to school. Her jacket's still on the kitchen chair. |
| 8:35 AM | Driveway | Both cars gone. House is Luna's now. |
| 10:10 AM | Living Room | Luna hasn't moved off the couch in two hours. |
| 11:20 AM | Front Door | A package arrived. It's sitting by the front door. |
| 1:05 PM | Living Room | Quiet stretch. Nothing's moved since noon. |
| 3:35 PM | Front Door | Maya's back, and she brought a friend. |
| 4:20 PM | Kitchen | Both of them in the kitchen. The package made it inside. |
| 5:40 PM | Front Door | Maya's friend headed out. |
| 6:50 PM | Driveway | First car's back in the driveway. |
| 7:25 PM | Kitchen | Everyone's home. |
| 9:40 PM | Living Room | Living room's empty. Looks like the day's done. |

**Detalle de ejemplo, 11:20 AM:**

What I saw:
- 11:19:48 A van stops in front of the house.
- 11:20:12 Someone walks up carrying a box.
- 11:20:31 They set it down by the door and leave.

Why I'm telling you: *Same van that comes most weeks, and they did exactly what
they always do. Nothing worth flagging. I just figured you'd want to know there's
a box outside.*

What I did: *Nothing. I didn't interrupt you. It's here when you want it.*

**Custom instructions de ejemplo:**

```
Alexander and his partner both work 9 to 6 on weekdays.
Maya is 15. She leaves for school around 7:45 and gets home around 5.
Luna is our dog. She stays home and sleeps on the living room couch.
Packages usually come mid-morning in a white van.
Someone comes to clean on Tuesday mornings.
Tell me if anyone I don't know comes to the door at night.
```

Para mostrar el rango de estados en una demo, el thread de las 3:35 PM puede ir
como `attention`: "Maya's back with someone I haven't seen before." Sigue sin
haber peligro y muestra a Artemisa admitiendo lo que no sabe.
