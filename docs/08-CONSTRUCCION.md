# 08. Construcción

## Fases

| Fase | Objetivo | Estado |
|---|---|---|
| **0. Laboratorio** | Probar que los algoritmos funcionan, en una casa real, con la app | Se construye primero |
| **1. Primer producto** | Beta cerrada con usuarios reales | Después de cumplir la Fase 0 |
| **2a. Llamadas al usuario** | Artemisa llama al titular | Requiere revisión legal |
| **2b. Terceros y emergencias** | Contactos de emergencia y servicios de emergencia | **Bloqueada** hasta resolver la consulta legal |
| **3. Después** | Aprendizaje, familia, describir en la casa, fabricante socio, A tu Alrededor | Sin fecha |

Se construye solo la fase actual. Lo de fases posteriores no se deja
"preparado" ni comentado en el código.

Dos cosas se documentan completas aunque se implementen por partes, para que se
entienda el diseño entero: la función de acción (`act()` en `03-ALGORITMO.md`) y
la de "What I did" (`whatIDid()` en `05-DATOS.md`). De cada una se escriben solo
las ramas de la fase actual. Y los enums de `dispatches` declaran todo su
vocabulario desde la Fase 0 (ver `05-DATOS.md`); declararlos no autoriza a
escribir el código que los usa.

---

## Estructura del repositorio

```
artemisa/
  CLAUDE.md
  PROGRESS.md               paso en curso y siguiente
  docs/                     estos documentos, e i18n/ con los textos generados
  design/                   una imagen por pantalla o estado, y tokens.json
  mobile/                   app Expo (ver 07-APP.md)
  server/                   Python: bridge, API, worker, laboratorio
    pyproject.toml
    artemisa/
      core/                 config, models.py, schemas.py, models.yaml, prompts/, costs.py
      providers/            gateway.py, expo_push.py, twilio.py (SMS en la Fase 0, llamadas en la 2a)
      bridge/               go2rtc.py, reader.py, uploader.py, control.py, stream.py,
                            secrets.py, discovery.py (Fase 1), recorder.py (Fase 1)
      pipeline/             motion.py, describe.py, sessionize.py, context.py, analyze.py,
                            reason.py, act.py, live_read.py, chat.py, tts.py
      api/                  app.py, auth.py, bridge_hub.py, routes/
      worker/               main.py, scheduler.py, health.py, receipts.py, retention.py
      lab/                  main.py, report.py, seed_demo.py, eval.py
    tests/
  supabase/
    migrations/
    lab_only/               solo para el proyecto de laboratorio
  infra/
    docker-compose.lab.yml
    mediamtx.yml
    go2rtc.yml              configuración base, sin cámaras ni contraseñas
  box/                      Fase 1: imagen del Cloud Bridge, servicio, watchdog,
                            actualizaciones y script de preparación
```

**Herramientas del servidor:** Python 3.12, `uv` para dependencias, `ruff`,
`mypy` en modo estricto y `pytest`. El CI incluye un servicio de Postgres
(`postgres:15.19`) para los tests de la base.

**Dependencias del servidor:** `fastapi`, `uvicorn`, `httpx`, `websockets`,
`pydantic`, `pydantic-settings`, `asyncpg`, `opencv-python-headless`, `numpy`,
`openai`, `pyyaml`, `pyjwt` (Fase 1), `cryptography` (archivo cifrado
del bridge), `sentry-sdk`, `tzdata` (solo en Windows). Nada más sin preguntar.

**Binarios externos:** go2rtc (licencia MIT), en la caja y en el laboratorio,
con la versión fijada. FFmpeg para publicar el vivo.

**Puntos de entrada:** `artemisa-bridge`, `artemisa-api`, `artemisa-worker`,
`artemisa-lab`.

---

## Fase 0. Laboratorio

### Objetivo

Contestar con datos una sola pregunta:

> ¿El pipeline produce descripciones y clasificaciones que se sienten como
> comprensión, y no como un registro de movimiento?

Y producir tres números que hoy no existen: cuánto ruido genera el Paso 1 en una
casa real, cuánto cuesta de verdad una hora de cámara, y cuántas veces escala al
Paso 3 y si tenía razón.

### Alcance

**Entra:** los cuatro pasos completos (el Paso 1 en la nube, sobre los frames
que entrega el bridge; el Paso 4 solo con notificaciones, con sus tres niveles
de interrupción), la sesionización con composing, la salud de la caja y de las
cámaras con sus avisos, la lectura en vivo, el chat, la voz, los dos idiomas,
Sentry, la instrumentación, y en la app: Home, Detalle, Feed en vivo, Conectar
cámara y el chat (cuando esté su diseño).

**No entra:** cuentas, la imagen del Cloud Bridge, su preparación y
emparejamiento, las actualizaciones remotas, la búsqueda de cámaras en la red,
onboarding completo, menú, llamadas, contactos de emergencia, retención de
datos, deploy en la nube (salvo Supabase), la grabación en el bridge, la
sirena y la luz roja.

**La app sí sigue el diseño.** Home, Detalle, Feed en vivo y Conectar cámara ya
están diseñados; se construyen fieles a sus imágenes desde la Fase 0.

### Cómo se monta

- Una notebook en la casa, en la misma red que la cámara, hace de Cloud Bridge
  y de nube a la vez. Corre `artemisa-lab` (bridge, API y worker en un solo
  proceso), go2rtc como en la caja, y MediaMTX como relay local. Todo con
  `docker compose -f infra/docker-compose.lab.yml up`.
- Un proyecto de Supabase **solo para el laboratorio**, con las migraciones más
  `supabase/lab_only/`.
- El usuario es fijo: `user_lab`. El bridge se autentica contra la API local con
  `LAB_BRIDGE_TOKEN`, por el mismo camino que en producción.
- La app corre como build de desarrollo en un teléfono en la misma Wi-Fi, con
  `EXPO_PUBLIC_LAB_MODE=true`.
- La dirección de la cámara se configura desde la pantalla Conectar cámara. En
  el laboratorio se guarda en un archivo cifrado en un volumen de Docker, con la
  clave en `LAB_SECRETS_KEY`.
- La capacidad se mide aparte: el bridge corre en el equipo candidato del
  Cloud Bridge contra varias cámaras, o varias copias del video de referencia,
  y se mira CPU, memoria, temperatura y si la entrega de frames se atrasa.
  También se mide cuánto sube la casa por cámara (tráfico).

### Orden de construcción

1. Esqueleto del repositorio, herramientas y CI: chequeo de tipos, lint y tests
   (incluidas las guardas de `05-DATOS.md`).
2. Proyecto de Supabase de laboratorio: migraciones, `lab_only`, y
   `seed_demo.py`.
3. Registro de modelos, clientes de proveedores, cálculo de costo y escritura en
   `pipeline_runs`. El registro y los prompts ya están en `server/artemisa/core/`
   y se usan tal cual.
4. Bridge: go2rtc con su configuración en tmpfs, hilo lector, entrega de un
   frame por segundo por cámara, canal de control con latido, y modo archivo
   (`VIDEO_SOURCE`).
5. Paso 1 y Paso 2a en la API: endpoint de frames con sus garantías, loop de
   movimiento por space, descripción, estado del space.
6. Sesionización y threads en composing.
7. Señales entre API y worker (`LISTEN` / `NOTIFY`), scheduler y Paso 2b.
8. Paso 3 con refuerzo.
9. Paso 4 con notificaciones y `dispatches`; salud de la caja y de las cámaras,
   con sus avisos. Se prueba desenchufando la notebook.
10. `artemisa-lab report`.
11. App: inicialización con React Native Reusables, tokens de
    `design/tokens.json`, fuentes, textos de `docs/i18n/`, layout y modo
    laboratorio.
12. App: Home en tiempo real. Se puede empezar contra los datos de demo en
    paralelo a los pasos 4 a 9.
13. App: Detalle.
14. App: Feed en vivo con el relay local, y lectura en vivo.
15. App: input con voz y chat. El chat necesita su diseño: se pide antes de
    empezar este paso.
16. App: Conectar cámara.
17. Correr el laboratorio (ver Criterios de éxito).

### La cámara: límite de tiempo

Conectarse a una cámara es la parte más frágil de todo el sistema: protocolos,
códecs, timeouts, formatos de autenticación, streams que se cortan. go2rtc
resuelve la mayor parte, pero no es un problema interesante de pelear en la
Fase 0.

**Límite: 3 horas.** Si en ese tiempo el stream no entra limpio por go2rtc, se
cambia la fuente a un archivo, que el bridge lee directo, sin go2rtc:

```
VIDEO_SOURCE=/ruta/a/video.mp4
```

Una sola variable; el resto del pipeline no se entera. Esto separa dos
problemas: "¿funciona el algoritmo?" y "¿anda esta cámara?". El primero decide
si el producto existe. El segundo es plomería.

**Se graba el video de todas formas.** De 20 a 30 minutos con el celular
apoyado en algún lugar de la casa, en un horario con movimiento real. Es el set
de referencia de la evaluación (ver `04-MODELOS.md`): un archivo es repetible,
así que se puede cambiar un prompt, correr el mismo video, y saber si mejoró.

### Escenas actuadas

Un día normal no produce momentos de atención ni emergencias, y el laboratorio
tiene que probarlos. Se graban escenas actuadas, sin riesgo, en la casa:
alguien desconocido que se acerca a la puerta y vuelve, alguien que prueba el
picaporte, una persona que se queda en el piso, una puerta que queda abierta con
la casa vacía. Cada escena tiene la clasificación esperada anotada.

### Ver los frames durante el laboratorio

Para saber si el modelo describe bien, hace falta ver el frame al lado de su
descripción. Solo en el laboratorio existe:

```
DEBUG_SAVE_FRAMES=false     # por defecto
```

Con `true`, el laboratorio guarda cada frame descripto en
`server/debug_frames/`, con el id del layer como nombre. Condiciones, todas
obligatorias:

- `server/debug_frames/` está en `.gitignore`.
- Nunca se escribe a Supabase ni se muestra en la app.
- El código que lo hace vive solo en `artemisa/lab/` y no forma parte del bridge
  que se distribuye.
- Se borra la carpeta y se elimina la opción antes de empezar la Fase 1.

Es una herramienta de laboratorio en una máquina de desarrollo, no una grieta
en la arquitectura.

### Instrumentación

`artemisa-lab report` lee `pipeline_runs` y muestra, para un período:

- Frames recibidos por tipo, y cuántos se describieron.
- Threads creados, por clasificación.
- Pasos 3 activados, y por qué disparador.
- Costo total, costo por hora de cámara, y su proyección a un mes.
- Latencia del primer frame a la narrativa (p50 y p95).
- Tokens de imagen reales por descripción.

`artemisa-lab eval` corre el pipeline sobre el video de referencia con una
configuración de modelos dada y compara contra las etiquetas del titular.

### Criterios de éxito

La Fase 0 termina cuando se puede contestar esto con datos. Los umbrales son
iniciales y se pueden discutir.

| Pregunta | Umbral inicial |
|---|---|
| **Ruido.** ¿Cuántos threads por hora son movimiento sin importancia para una persona? | Menos de 2 por hora de actividad |
| **Descripción.** Leyendo solo los layers, ¿se entiende qué pasó? | Promedio de 4 sobre 5 o más |
| **Clasificación.** ¿Coincide con lo que diría el titular? | 85% o más de acuerdo en 30 momentos |
| **Emergencias actuadas.** ¿Llegan a `emergency`? | Todas, sin excepción |
| **Escaladas.** ¿Los pasos 3 estaban justificados? | 70% o más |
| **Velocidad.** Del primer frame a la narrativa | p95 de 60 segundos o menos |
| **Costo.** Proyección mensual por cámara | Conocida, y comparada con `04-MODELOS.md` |
| **Capacidad.** En el equipo candidato del Cloud Bridge, ¿cuántas cámaras lee y entrega a un frame por segundo sin atrasarse? | 4 o más |
| **Tráfico.** ¿Cuánto sube una casa por cámara por mes? | Conocido, para decidir el canal de subida antes de la Fase 1 |
| **La apuesta.** ¿Leer y escuchar a Artemisa se siente como que alguien entendió? | El titular y al menos tres personas más, leyendo un día, lo describen como comprensión y no como reporte |

Las primeras nueve se miden. La última decide el producto.

---

## Fase 1. Primer producto

### Antes de empezar

- La Fase 0 cumplió sus criterios.
- Están diseñadas: iniciar sesión, emparejar el Cloud Bridge, elegir cámaras,
  enseñale tu casa, chat, menú, estado de emergencia, cámara sin conexión,
  primer día, días anteriores, perfil.
- Se eligió el equipo del Cloud Bridge (por disponibilidad y precio en
  Argentina), cómo se actualiza a distancia, y quién paga la caja en la beta.
- Se midió en la Fase 0 cuántas cámaras aguanta el equipo elegido y cuánto
  tráfico sube una casa.
- Se definió cómo viajan los frames del bridge a la nube: canal, tamaño,
  frecuencia y costo (ver `06-ARQUITECTURA.md`, Subida de frames).
- La grabación tiene respuesta a sus preguntas abiertas y sus pantallas
  diseñadas, y se reescribieron los textos que dejan de ser verdad
  (`live.privacy`, `connect.privacy` y el prompt de `chat`).
- Se pidió a OpenAI retención cero (o monitoreo modificado) y se revisaron los
  términos de Groq.
- Política de privacidad y términos redactados, con los proveedores declarados,
  y revisados por un abogado.
- Se pidió a Apple el permiso de avisos críticos (opcional; sin él, `critical`
  se envía como `time_sensitive`).
- `DEBUG_SAVE_FRAMES` y `server/debug_frames/` ya no existen.
- Proyecto de Supabase de producción, separado del laboratorio.

### Alcance

- Cuentas con Clerk.
- **Cloud Bridge:** la imagen (Linux mínimo, go2rtc, el bridge como servicio,
  watchdog, arranque solo al volver la luz), las actualizaciones remotas con
  vuelta atrás, el script de preparación con su etiqueta QR, el emparejamiento,
  y la búsqueda de cámaras en la red.
- **Grabación** local cifrada en el Cloud Bridge y la pantalla para verla, según
  lo que se decida (ver `06-ARQUITECTURA.md`, Grabación).
- Beta con 10 a 20 cajas preparadas a mano.
- Onboarding completo, menú y las pantallas diseñadas para esta fase.
- RLS de producción, relay en la nube, API y worker desplegados.
- Job de retención, borrado de historial y de cuenta.

---

## Fase 2a. Llamadas al usuario

**Requisito:** revisión legal sobre llamadas automáticas al titular de la cuenta,
y los requisitos regulatorios para tener un número de Twilio en el país.

**Alcance:** llamada al titular para `alertar` (si no abrió el aviso en
`ALERT_CALL_DELAY_S`), `contactar` y `emergencia`; webhooks de estado de
llamadas hacia `dispatches`; textos de "What I did" para llamadas.

---

## Fase 2b. Terceros y emergencias

**Bloqueada** hasta tener una opinión legal sobre:

- el contacto automatizado a servicios de emergencia en Argentina;
- llamar a terceros en nombre del usuario;
- el consentimiento de los contactos de emergencia para recibir esas llamadas;
- responsabilidad y términos de servicio.

Si la respuesta es restrictiva, cambia la arquitectura del nivel 4 entero.

**Alcance, si se habilita:** tabla y pantallas de contactos de emergencia (con su
consentimiento registrado), cadena de contactos por prioridad, protocolo de
emergencia con ventana de cancelación en la llamada y en WhatsApp, auditoría
completa en `dispatches`.

---

## Fase 3. Después

Sin orden ni fecha:

- **Aprender de la conversación:** que el chat proponga cambios a las custom
  instructions ("that's the plumber, he comes on Tuesdays") y el usuario los
  confirme. Y las preguntas proactivas de aprendizaje.
- **Familia:** varios miembros en una misma casa.
- **Varias cámaras por space.**
- **Describir en la casa:** un modelo de visión chico en el Cloud Bridge, con una
  caja de más capacidad. Costo del Paso 2a en cero e imágenes que nunca salen
  de la casa. Va en contra del bridge liviano de hoy: se evalúa a largo plazo.
- **Sirena y luz roja** del Cloud Bridge, cuando tengan diseño y fase.
- **Fabricante socio:** integrar sus cámaras según el modelo que se acuerde
  (ver Decisiones abiertas). Algunas marcas ya saben registrarse solas hacia
  afuera (Hikvision ISUP, Dahua Auto Register), lo que permitiría conectar esas
  cámaras sin caja.
- **Cámaras propias con firmware abierto** (OpenIPC), si el socio no aparece.
- **Conectores de nube** para marcas sin RTSP (Tuya, EZVIZ, Imou), con el costo
  por tráfico de cada proveedor.
- **Wi-Fi en el Cloud Bridge**, con su propio proceso de configuración.
- **Filtro de escena** por hash perceptual en el Paso 1.
- **Video en vivo de baja latencia** con WebRTC.
- **A tu Alrededor**, después de su propia consulta legal.

---

## Riesgos

De mayor a menor:

| Riesgo | Por qué importa | Mitigación |
|---|---|---|
| Cloud Bridge: costo y logística | Hay que conseguir, preparar y hacer llegar una caja a cada casa, y alguien la paga | Hardware liviano porque no procesa; beta chica preparada a mano; equipo elegido por disponibilidad en Argentina; a escala, el fabricante socio |
| Tráfico de subida | La casa sube un frame por segundo por cámara, todo el día; con conexiones lentas o con límite puede no alcanzar, y el tráfico cuesta | Frame reducido; medirlo en la Fase 0; decidir el canal antes de la Fase 1 |
| Cortes de luz y de internet | Sin energía, Artemisa no ve, como cualquier sistema de cámaras | Avisar siempre al perder y al recuperar la vista; la caja arranca sola; UPS recomendada |
| Actualizaciones remotas | Una versión mala deja cajas sin andar en casas ajenas | Vuelta atrás automática; actualizar de a grupos |
| Calidad de las descripciones | Un modelo chico con una imagen chica puede perder lo importante | Evaluación de la Fase 0; modelo de respaldo; ajustar resolución |
| Economía de unidad | El costo de IA supera el precio de la beta, y el Paso 1 en la nube suma cómputo y tráfico | Palancas de `04-MODELOS.md` |
| Diversidad de cámaras | Protocolos, códecs, autenticación y substreams varían | go2rtc; códigos de error; lista de compatibilidad armada en la beta; guía para configurar H.264 |
| Legal | Dispatch, terceros, personas filmadas que no viven en la casa | Fases bloqueadas hasta resolver |
| Cambios de proveedores | Modelos retirados, precios nuevos | Registro de modelos; revisar las páginas de retiro de cada proveedor cada mes |
| Promesa de privacidad | Los proveedores pueden retener datos, y desde la Fase 1 la casa guarda grabación | Retención cero; la nube no guarda nada visual; grabación cifrada que solo ve el dueño; copy preciso |
| Confiabilidad de las notificaciones | Modos de concentración, ahorro de batería | Niveles de interrupción; llamadas en la Fase 2a |
| Latencia | HLS tarda segundos; composing hasta 45 s | Aceptable en la primera versión; camino rápido para lo urgente; WebRTC después |

---

## Decisiones tomadas

| Fecha | Decisión | Por qué |
|---|---|---|
| 2026-09-22 | **Artemisa es software.** Pone la inteligencia, no las cámaras. El camino para crecer es un fabricante de cámaras socio: ellos venden cámaras, Artemisa pone la inteligencia. | Fabricar cámaras cambia la empresa entera. Un socio aporta el hardware y la distribución. |
| 2026-09-22 | **El primer cliente son las familias, directo.** | Es la cuña que la primera versión tiene que validar (ver `01-INTRODUCCION.md`). |
| 2026-09-22 | **Todas las cámaras se conectan a través del Cloud Bridge**, una caja dedicada que se compra hecha, con go2rtc adentro. No hay otro camino en la primera versión. | Las cámaras viven en redes privadas. Una computadora de uso general no vuelve sola después de un corte y queda ciega sin que nadie lo sepa. Una sola forma de conectar sirve para todas las marcas. |
| 2026-09-22 | **Artemisa siempre dice qué puede ver**, y ningún texto promete "No new hardware". | Un sistema ciego que no lo dice da una confianza falsa. |
| 2026-09-22 | **Se vende de dos formas:** un kit (Cloud Bridge + cámaras del fabricante socio) para quien arranca de cero, y el Cloud Bridge solo para quien ya tiene cámaras IP. | El bridge ya funciona con casi cualquier marca vía go2rtc; vender solo el kit dejaría afuera a las familias que el producto ya sabe atender, y el kit le da al socio algo completo para vender por su propio canal. |
| 2026-09-27 | **El aparato se llama Cloud Bridge.** En texto corrido, "el bridge". | Nombre del producto. |
| 2026-09-27 | **El Cloud Bridge es un puente: no procesa.** Todo el análisis, incluido el Paso 1, corre en la nube. | Hardware liviano y barato, y el algoritmo se mejora sin tocar las cajas. El costo es tráfico de subida. |
| 2026-09-27 | **La nube nunca guarda nada visual; desde la Fase 1, el bridge graba en la casa, cifrado**, y solo el dueño lo ve. | Sirve a familias con DVR o sin él, sin romper la promesa de la nube. |
| 2026-09-27 | **Llamada al 911 bloqueada** hasta tener opinión legal. Ni código preparado. | Fase 2b. |
| 2026-09-27 | **Sistema de diseño monocromático** (`09-DISENO.md`): negro, blanco y gris; el color solo marca estado; rojo solo para `emergency`. shadcn web solo para prototipos en Claude Design. | La emoción es tranquilidad, no vigilancia. La app es Expo. |

---

## Decisiones abiertas

Necesitan una respuesta del equipo. Ninguna se resuelve inventando. **Mientras
no haya respuesta, rige lo que dicen estos documentos**; la lista marca qué
puede cambiar.

1. **El Cloud Bridge y el kit.** Qué equipo (como no procesa, alcanza una placa
   chica de formato Raspberry Pi; se elige por disponibilidad y precio en
   Argentina) y si necesita ventilación, cuánto cuesta cada forma de
   venta (la caja sola y el kit con cámaras), quién los paga (se venden, se
   prestan o van incluidos en la suscripción), cómo llegan a cada casa y se
   cambian si fallan, y el nombre comercial del kit.
2. **El fabricante socio.** Quién, y cómo se integra: si arma y vende el kit
   por su propio canal de retail, si solo provee las cámaras y Artemisa arma el
   kit, si sus cámaras se conectan solas a la nube de Artemisa, o si llevan el
   software adentro.
3. **Precio y subsidio.** El costo estimado por cámara supera el precio de la
   beta, y eso sin contar la caja. ¿Cuánto se subsidia y hasta cuándo?
4. **Retención de datos.** Los plazos de `05-DATOS.md` son una propuesta.
5. **"See now".** Las imágenes de diseño muestran "Watch" en los botones; estos
   documentos usan "See now" porque un botón bajo un momento pasado no puede
   prometer reproducirlo. Rige "See now" hasta que se confirme.
6. **El menú `+`** del input: qué contiene. Hasta definirlo, no hace nada.
7. **Personas filmadas que no viven en la casa** (visitas, personal de
   limpieza): aviso y consentimiento. Pregunta para la consulta legal.
8. **Hablar sola.** Hoy Artemisa lee en voz alta los threads nuevos que no son
   `normal` cuando la app está abierta y la voz activada. ¿Se mantiene, o solo
   responde cuando le hablan?
9. **Consultas legales:** quién, cuándo, y en qué orden (dispatch, terceros,
   A tu Alrededor, filmación de terceros).
10. **Subida de frames.** Si alcanza una request por frame o hace falta un canal
    continuo, a qué tamaño y frecuencia, y cuánto cuesta el tráfico por casa.
    Bloquea la Fase 1, no la Fase 0.
11. **Grabación.** Continua, solo clips de momentos o las dos; cuántos días y en
    qué almacenamiento; respaldo de la clave y varios teléfonos por casa;
    pantallas para verla. Bloquea la grabación, no la Fase 0.
12. **Sirena y luz roja.** Cuándo suenan, cómo se desactivan y en qué fase.

---

## Antes de cada commit

- [ ] Se construyó solo lo que incluye la fase actual.
- [ ] La interfaz sale de primitivas de React Native Reusables y coincide con su
      imagen en `design/`.
- [ ] No se agregó nada que no estuviera pedido.
- [ ] Ningún frame se escribe a disco, a la base ni a un log en la nube (la
      grabación de la Fase 1 vive solo en el bridge, cifrada).
- [ ] Ninguna dirección RTSP ni contraseña de cámara sale del Cloud Bridge
      (salvo el tránsito en memoria al agregar una cámara), y la configuración
      de go2rtc vive solo en tmpfs.
- [ ] Ningún nombre de modelo aparece fuera del registro.
- [ ] Toda llamada a un modelo escribe en `pipeline_runs`.
- [ ] Todo texto visible pasa por las traducciones y respeta la voz de Artemisa.
- [ ] "What I did" sale de `dispatches`.
- [ ] Pasan los tests: sincronía de enums, guarda de columnas binarias, tabla de
      `resolve_action_level`, endpoint de frames sin disco.
- [ ] `tsc`, `mypy` y `ruff` limpios.
