# ARTEMISA

Artemisa es una app mobile que entiende lo que pasa en tu casa. Se conecta a las
cámaras IP que la familia ya tiene a través del **Cloud Bridge**, una cajita
que se enchufa al router y hace de puente: no procesa, todo el análisis corre en
la nube. Convierte lo que ven las cámaras en texto, entiende la rutina de ese
hogar, y actúa cuando pasa algo que importa. La nube nunca guarda video ni
imágenes.

Para entender la idea completa en cinco minutos: `docs/00-INTRO.md`.

Proyecto nuevo. Se construye desde cero. Fundador: Tob (solo founder).

---

## Fase actual

**Fase 0: Laboratorio.** Paso actual y siguiente: `PROGRESS.md`.

Construí solo lo que `docs/08-CONSTRUCCION.md` incluye en la fase actual. Nada
de fases posteriores se deja preparado ni comentado. Esta línea la cambia Tob
cuando se pasa de fase.

---

## Cómo trabajar en cada sesión (importante: el presupuesto es chico)

1. Leé `PROGRESS.md`. Ahí está el paso en curso.
2. Leé `docs/00-DECISIONES.md` (corto; registro de decisiones, ya integradas
   en los demás docs).
3. Leé **solo** los docs que la tabla de abajo asigna a ese paso. No leas los
   documentos enteros si el paso no los necesita.
4. Antes de escribir código, proponé un plan de 3 a 6 líneas y esperá el OK.
5. Hacé un paso por sesión. Al terminar: tests y chequeos, actualizá
   `PROGRESS.md`, commit.
6. Si algo está trabado más de 2 intentos, frená y preguntá. No gastes vueltas.

### Qué leer en cada paso de la Fase 0

| Paso | Qué es | Docs |
|---|---|---|
| 1 | Esqueleto, herramientas, CI | 08 (Estructura), 05 (Guardas) |
| 2 | Supabase de laboratorio, migraciones, seed | 05, 02 (Día de demo) |
| 3 | Registro de modelos, proveedores, costo, `pipeline_runs` | 04, 05 (`pipeline_runs`) |
| 4 | Bridge: go2rtc, lector, entrega de frames, canal de control, `VIDEO_SOURCE` | 03 (Paso 1: lectura y entrega), 06 (Bridge) |
| 5 | Paso 1 y Paso 2a en la API: endpoint de frames, movimiento y descripción | 03 (Paso 1 y 2a), 04 (`describe`), 06 (Subida de frames) |
| 6 | Sesionización y composing | 03 (Sesionización), 05 (`threads`) |
| 7 | LISTEN/NOTIFY, scheduler, Paso 2b | 03 (Paso 2b), 04 (`analyze`), 06 (Worker) |
| 8 | Paso 3 con refuerzo | 03 (Paso 3), 04 (`reason`) |
| 9 | Paso 4, `dispatches`, salud de caja y cámaras | 03 (Paso 4, Estado de la casa), 02 (Niveles), 06 (Notificaciones) |
| 10 | `artemisa-lab report` | 08 (Instrumentación) |
| 11 | App: init con RN Reusables, tokens, fuentes, i18n, modo lab | 07, 09 (Implementación), `design/tokens.json`, `docs/i18n/*.json` |
| 12 | App: Home en tiempo real | 07 (Home, Datos), 03 (Línea de estado), 09, `design/home.png` |
| 13 | App: Detalle | 07 (Detalle), 05 (What I did), 09, `design/thread-detail.png` |
| 14 | App: Feed en vivo + lectura en vivo | 07, 06 (Stream en vivo), 03 (Lectura en vivo), 09, `design/live-feed.png` |
| 15 | App: voz y chat (**pedir el diseño del chat antes**) | 07 (Voz), 03 (Chat), 04 (`chat`), 09 |
| 16 | App: Conectar cámara | 07, 06 (Agregar una cámara), 09, `design/connect-camera*.png` |
| 17 | Correr el laboratorio | 08 (Criterios de éxito) |

---

## Documentos

| Archivo | Qué tiene |
|---|---|
| `docs/00-INTRO.md` | **La idea completa**, para cualquier sesión de Claude (Code, Design o chat) |
| `docs/00-DECISIONES.md` | Registro de decisiones con fecha. Leer siempre: dice qué cambió último |
| `docs/01-INTRODUCCION.md` | Qué es, la idea, el problema, la promesa de privacidad, glosario |
| `docs/02-PRODUCTO.md` | Pantallas, estados, niveles de acción, voz y copy, **tabla de Textos**, datos de demo |
| `docs/03-ALGORITMO.md` | Pipeline completo con pseudocódigo y **todas las constantes** |
| `docs/04-MODELOS.md` | Modelos por rol, prompts, esquemas, costos |
| `docs/05-DATOS.md` | Schema, enums, RLS, tiempo real, tipos |
| `docs/06-ARQUITECTURA.md` | Casa, nube y app; bridge; API; stream; auth; secretos |
| `docs/07-APP.md` | Expo, RN Reusables, estructura, pantallas, datos, voz, notificaciones |
| `docs/08-CONSTRUCCION.md` | Fases, orden de construcción, criterios de éxito, riesgos |
| `docs/09-DISENO.md` | **Sistema de diseño**: color, tipografía, radios, íconos, movimiento |
| `docs/10-NEGOCIO.md` | Contexto de negocio y marca. No se implementa |
| `docs/i18n/` | `en.json` y `es-AR.json` generados de la tabla de Textos (app), y `server.*.json` |
| `design/` | Una imagen por pantalla (fuente de verdad visual) y `tokens.json` |
| `server/artemisa/core/models.yaml` | Registro de modelos, ya cargado desde `04-MODELOS.md` |
| `server/artemisa/core/prompts/` | Prompts de cada rol, ya cargados desde `04-MODELOS.md` |

El aparato se llama **Cloud Bridge**; en texto corrido, "el bridge". El software
que corre adentro también se llama bridge en el código.

---

## Reglas

### 1. El diseño manda

Antes de construir una pantalla o un componente, abrí su imagen en `design/`.
Los documentos dicen qué hace; la imagen dice cómo se ve. Si se contradicen en
algo visual, gana la imagen.

**El texto es la excepción.** Todo texto visible sale de la tabla de Textos de
`docs/02-PRODUCTO.md` (con los cambios de `00-DECISIONES.md`).

Si no hay imagen para lo que necesitás, **preguntá**. No lo inventes.

### 2. No agregues nada que no esté pedido

Es la regla más importante del proyecto. Si algo falta o quedaría mejor, frená
y proponelo en una línea. Esperá la respuesta.

Siempre se pregunta antes de:

- instalar una dependencia que no está en `docs/07-APP.md` o `docs/08-CONSTRUCCION.md`;
- crear una pantalla, ruta, componente o carpeta que no está en la estructura;
- agregar un estado de interfaz que no está en `design/`;
- agregar o cambiar una columna, tabla o enum;
- cambiar un prompt, un modelo o una constante de `docs/03-ALGORITMO.md`;
- escribir un texto visible que no está en `docs/02-PRODUCTO.md`.

### 3. Componé con primitivas y tokens

La interfaz se construye con primitivas de React Native Reusables. Viven en
`mobile/components/ui/` y **no se editan**: se envuelven en
`mobile/components/artemisa/`.

El sistema de diseño está en `docs/09-DISENO.md`. En corto:

- **Monocromático.** Ningún color literal en componentes: solo tokens. Nada de
  azul ni acentos nuevos: negro, blanco y gris.
- **Color = estado.** Verde `normal`, ámbar `attention`, rojo `emergency`, gris
  sin señal. Solo en puntos, badges y bordes.
- **El rojo es exclusivo de `emergency`.** Nunca para errores ni para borrar.
- **Instrument Serif solo en headings** (máx. 2 por pantalla). Todo lo demás, Inter.
- **Radios grandes:** tarjetas 28, hojas 34, botones de acción en píldora.
- **Lucide** con `strokeWidth` 2. Animaciones solo de `transform` y `opacity`,
  menos de 300 ms, respetando "reducir movimiento".

### 4. La nube nunca guarda imágenes

- Ninguna tabla tiene columnas binarias ni columnas para imágenes, frames,
  video o credenciales. Un test lo verifica.
- Un frame en la nube existe en memoria mientras se analiza y se descarta.
  Nunca a disco, base, log, Sentry ni caché. Vale también para el frame por
  segundo que el bridge entrega para el Paso 1.
- El endpoint de frames lee el cuerpo crudo en memoria (`await request.body()`).
- Si describir un frame falla, el frame se pierde. No hay cola de reintento.
- Las direcciones RTSP y contraseñas de cámaras viven solo en el bridge,
  cifradas. Los logs redactan `rtsp://`. La config de go2rtc vive en tmpfs.
- El stream en vivo existe en memoria del relay, unos segundos. No se graba.
- El botón para mirar dice "See now". Nunca "Watch" ni "replay".
- **En la Fase 0 el bridge tampoco graba.** La grabación local cifrada es Fase 1
  y tiene preguntas abiertas (`00-DECISIONES.md`).
- Única excepción: `DEBUG_SAVE_FRAMES`, solo en `server/artemisa/lab/`, apagada
  por defecto, desaparece antes de la Fase 1.

### 5. Proporción

- Ninguna acción por encima de `informar` sin pasar por el Paso 3.
- `emergencia` solo con `classification = emergency` y `severity_high = true`.
  La base también lo impide.
- Nunca se repite un aviso. Solo se actúa de nuevo si el nivel sube.
- **Nada de llamadas, contactos de emergencia ni 911.** Fase 2b bloqueada.

### 6. Honestidad en lo que dice Artemisa

- "What I did" se arma con `dispatches`, nunca con el nivel teórico.
- La incertidumbre se dice. Artemisa siempre dice qué puede ver.
- Palabras prohibidas en la interfaz: AI, model, detected, motion, person
  detected, no events, processing, replay (lista completa en `02-PRODUCTO.md`).
- El aparato se llama Cloud Bridge. Ningún texto dice "No new hardware".
- Todo texto visible sale de las traducciones, en `en` y `es-AR`.

### 7. Modelos por registro

- Ningún nombre de modelo en la lógica. El código pide un rol;
  `server/artemisa/core/models.yaml` resuelve.
- Costo con el `usage` real. Toda llamada escribe en `pipeline_runs`, sin
  contenido. Toda salida se valida con su esquema.

### 8. Tipos

- TypeScript estricto, sin `any`. Tipos de la base generados desde Supabase.
- Python con `mypy` estricto. Test que compara enums de Python con Postgres.

### 9. Secretos

La app solo tiene claves publicables. Nunca commitees `.env`. Nunca pegues
claves en el código ni en el chat.

---

## Stack

```
Casa:       Cloud Bridge: Linux, go2rtc y el agente (Python). No analiza.
App:        Expo + Expo Router, TypeScript, React Native Reusables (NativeWind),
            TanStack Query, supabase-js, expo-video, expo-notifications,
            expo-speech-recognition, expo-audio, i18next, Sentry, Clerk (Fase 1)
Servidor:   Python 3.12, FastAPI, asyncpg, OpenCV, FFmpeg, uv, ruff, mypy, pytest
Base:       Supabase (Postgres + Realtime)
Relay:      MediaMTX
Modelos:    OpenAI (visión, razonamiento, voz) y Groq (texto), vía registro,
            a través de Vercel AI Gateway (un solo cliente, SDK de openai)
Diseño:     Prototipos en Claude Design con shadcn web (preset bbVJxce). Solo
            para diseñar: la app es Expo.
Push:       Expo Push Service
Hosting:    Railway (API, worker, relay), EAS (builds de la app)
```

## Comandos

```bash
# Servidor (desde server/)
uv sync
uv run ruff check . && uv run ruff format --check .
uv run mypy artemisa
uv run pytest

# App (desde mobile/)
npx tsc --noEmit

# Laboratorio (desde la raíz)
docker compose -f infra/docker-compose.lab.yml up
```

---

## Antes de cada commit

- [ ] Solo lo que incluye la fase actual.
- [ ] Coincide con su imagen en `design/` y usa primitivas de RN Reusables.
- [ ] Solo tokens de `09-DISENO.md`; rojo solo en `emergency`.
- [ ] Nada agregado sin preguntar.
- [ ] Ningún frame a disco, base, logs ni caché.
- [ ] Ninguna dirección RTSP ni contraseña de cámara fuera del bridge.
- [ ] Ningún nombre de modelo fuera del registro; toda llamada en `pipeline_runs`.
- [ ] Textos por traducciones, en los dos idiomas, con la voz de Artemisa.
- [ ] "What I did" sale de `dispatches`.
- [ ] Tests, `tsc`, `mypy` y `ruff` limpios.
- [ ] `PROGRESS.md` actualizado.
