# 07. App

## Stack

| Qué | Con qué |
|---|---|
| Framework | Expo, versión estable actual del SDK, con Expo Router |
| Lenguaje | TypeScript en modo estricto |
| Componentes | React Native Reusables (shadcn/ui para React Native) sobre NativeWind |
| Datos del servidor | TanStack Query |
| Base y tiempo real | `@supabase/supabase-js` |
| Autenticación | `@clerk/clerk-expo` (Fase 1) |
| Video en vivo | `expo-video` |
| Escanear el QR del Cloud Bridge | `expo-camera` (Fase 1) |
| Notificaciones | `expo-notifications`, `expo-device` |
| Voz a texto | `expo-speech-recognition` |
| Audio | `expo-audio` |
| Degradado del input | `expo-linear-gradient` |
| Fuentes | `@expo-google-fonts/instrument-serif`, `@expo-google-fonts/inter`, `expo-font`, `expo-splash-screen` |
| Íconos | `lucide-react-native` (con `react-native-svg`) |
| Idiomas | `i18next`, `react-i18next`, `expo-localization` |
| Errores | `@sentry/react-native` |
| Builds | EAS |

No se instala nada fuera de esta lista sin preguntar.

---

## Setup

### 1. Crear el proyecto con React Native Reusables

El proyecto se inicializa con la CLI de React Native Reusables, eligiendo la
plantilla con **NativeWind**. No se crea con `create-expo-app` por separado ni
se configura NativeWind a mano.

```bash
npx @react-native-reusables/cli@latest init
npx @react-native-reusables/cli@latest doctor
```

`doctor` verifica que la configuración quedó bien. Los comandos exactos se
confirman contra la documentación oficial de React Native Reusables al momento
de ejecutarlos.

### 2. Agregar primitivas

```bash
npx @react-native-reusables/cli@latest add button text card badge separator skeleton input avatar
```

Si `add` falla, la alternativa es instalar el componente desde el registro:

```bash
npx shadcn@latest add https://reactnativereusables.com/r/nativewind/<componente>.json
```

Se usa `npm`/`npx`. Hay problemas conocidos del comando `add` con Yarn.

### 3. Dependencias

```bash
npx expo install expo-video expo-notifications expo-device expo-audio \
  expo-linear-gradient expo-localization expo-speech-recognition
npm install @tanstack/react-query @supabase/supabase-js i18next react-i18next
npx expo install @sentry/react-native
npx expo install @expo-google-fonts/instrument-serif @expo-google-fonts/inter \
  expo-font expo-splash-screen react-native-svg
npm install lucide-react-native
# Fase 1:
npx expo install @clerk/clerk-expo expo-secure-store expo-camera
```

Para el cliente de Supabase en React Native se sigue la guía oficial de
Supabase para Expo (incluye cualquier polyfill que haga falta).

### 4. Build de desarrollo

La app usa módulos nativos (reconocimiento de voz, notificaciones), así que **no
corre en Expo Go**. Desde el primer día se trabaja con un build de desarrollo:

```bash
npx expo run:ios          # o run:android, local
eas build --profile development --platform ios
```

---

## Regla de composición

Todo componente propio se construye con primitivas de React Native Reusables.
Antes de escribir un `View` con clases, se busca la primitiva que hace ese
trabajo.

| En el diseño | Primitiva |
|---|---|
| Cualquier texto | `Text` |
| "See now", "Ask something", "Connect", "Try again" | `Button` (variantes del diseño) |
| Píldora de hora, etiqueta "Live" | `Badge` |
| Contenedor de la línea del día | `Card` |
| Líneas grises de composing, carga del vivo | `Skeleton` |
| Separadores del detalle | `Separator` |
| Campo de dirección de la cámara, input del chat | `Input` |
| Avatar del usuario | `Avatar` |
| Menú (Fase 1) | `DropdownMenu` |
| Preferencias (Fase 1) | `Switch`, `Label` |

- Las primitivas viven en `components/ui/` y **no se editan.** Si hace falta
  otro comportamiento, se envuelven en un componente de `components/artemisa/`.
- Si falta una primitiva, se agrega con la CLI. Si React Native Reusables no la
  tiene, se pregunta antes de escribirla.
- Los estilos y variantes visuales salen del diseño en `design/` y de los
  tokens de `09-DISENO.md` (`design/tokens.json`).
- **Prototipos en Claude Design:** ahí se usa shadcn web con el preset del
  proyecto (`npx shadcn@latest init --preset bbVJxce --template next`), con los
  mismos tokens. Es solo para diseñar: nada de ese código entra a `mobile/`.

---

## Estructura

```
mobile/
  app/
    _layout.tsx               providers: Sentry, Query, i18n, Supabase, Clerk (Fase 1)
    index.tsx                 Home
    thread/[id].tsx           Detalle, presentado como hoja sobre el Home
    live/[spaceId].tsx        Feed en vivo, pantalla completa
    chat.tsx                  Chat, pendiente de diseño
    connect-camera.tsx        Conectar cámara
    sign-in.tsx               Fase 1, pendiente de diseño
    pair-bridge.tsx           Fase 1, emparejar el Cloud Bridge con su QR; pendiente de diseño
    choose-cameras.tsx        Fase 1, cámaras que encontró el Cloud Bridge; pendiente de diseño
    teach-home.tsx            Fase 1, pendiente de diseño
    menu.tsx                  Fase 1, pendiente de diseño
  components/
    ui/                       primitivas de React Native Reusables
    artemisa/
      HomeHeader.tsx          menú, marca, avatar, saludo, estado
      DayTimeline.tsx         la línea del día (lista virtualizada)
      TimelineRail.tsx        el riel punteado
      TimePill.tsx            hora + punto de estado
      StatusDot.tsx
      ThreadItem.tsx          composing / activo / cerrado
      ComposingLines.tsx      las líneas grises con brillo
      ThreadActions.tsx       See now, Ask something
      AskBar.tsx              +, campo, voz, degradado
      VoiceButton.tsx
      ThreadMeta.tsx
      DetailSection.tsx       rótulo + contenido
      LayerList.tsx           What I saw
      LiveVideo.tsx
      LiveBadge.tsx
      LiveRead.tsx            titular + lectura
      PrivacyLine.tsx
      CameraAddressForm.tsx
  hooks/
    useTodayThreads.ts
    useThread.ts              thread + layers + dispatches
    useSpaces.ts
    useBridge.ts              estado del Cloud Bridge (con señal o sin señal)
    useRealtime.ts
    useLiveStream.ts
    useLiveRead.ts
    useChat.ts
    useVoiceInput.ts
    useSpeak.ts
  lib/
    supabase.ts
    api.ts                    fetch tipado hacia la API, con el token de sesión
    query-client.ts
    types/db.ts               generado desde Supabase
    types/domain.ts
    what-i-did.ts
    home-state.ts
    time.ts
    push.ts
    i18n/index.ts
    i18n/en.json
    i18n/es-AR.json
```

No se agregan rutas ni carpetas fuera de esta estructura sin preguntar.

---

## Navegación

- **Home** es la raíz.
- **Detalle** (`/thread/[id]`) se presenta como hoja o modal sobre el Home.
- **Feed en vivo** (`/live/[spaceId]`) se abre a pantalla completa con volver.
- **Chat** (`/chat?thread=<id>`) se presenta como hoja o modal. Pendiente de
  diseño.
- **Enlaces profundos:** `artemisa://thread/<id>` (desde una notificación) y
  `artemisa://pair?code=<código>` (Fase 1). El QR de la etiqueta del Cloud
  Bridge es ese enlace: escanearlo con la cámara del teléfono también abre la app
  en el emparejamiento.

---

## Pantallas

### Home (`app/index.tsx`)

```
<HomeHeader />                      saludo + línea de estado (lib/home-state.ts)
<Card>
  rótulo "Threads" + control "Today"
  <DayTimeline>
    <ThreadItem />                  × N, del más reciente al más viejo
  </DayTimeline>
</Card>
<AskBar />                          fijo abajo, con degradado
```

- El botón de menú, el control de día y el botón `+` del input se muestran como
  en el diseño. **En la Fase 0 no hacen nada** hasta que el menú, la navegación
  por días y el contenido del `+` estén definidos.
- `DayTimeline` es una lista virtualizada. Un thread nuevo entra arriba sin
  mover la posición de lectura si el usuario scrolleó hacia abajo.
- `ThreadItem` en composing muestra `ComposingLines` y solo "See now". Cuando
  pasa a activo, la narrativa reemplaza a las líneas con una transición suave,
  en el mismo lugar.
- Tocar el cuerpo abre el detalle. "See now" abre el feed en vivo del space.
  "Ask something" abre el chat con ese thread.

### Detalle (`app/thread/[id].tsx`)

```
<ThreadMeta />                      "Today, 7:42 PM · Front Door"
narrativa (título)
<DetailSection "Why I'm telling you">   thread.reasoning
<DetailSection "What I did">            lib/what-i-did.ts sobre dispatches
<DetailSection "What I saw">            <LayerList /> con segundos
```

Mientras el detalle está abierto, se escuchan en tiempo real los layers y
dispatches de ese thread.

### Feed en vivo (`app/live/[spaceId].tsx`)

```
<LiveVideo />  + botón volver + <LiveBadge />
rótulo del space
<LiveRead />                        headline + body
<PrivacyLine />
<AskBar />
```

- Al entrar: `POST /v1/spaces/{id}/stream` y `POST /v1/spaces/{id}/live-read`
  en paralelo. El video y la lectura aparecen cada uno cuando están listos.
- Al salir (o al pasar la app a segundo plano): `DELETE /v1/spaces/{id}/stream`.
- **No se muestra ninguna hora en esta pantalla.**
- Los estados conectando y error están pendientes de diseño.

### Emparejar el Cloud Bridge (`app/pair-bridge.tsx`, Fase 1)

Pendiente de diseño. Qué hace:

- Escanea el QR de la etiqueta con `expo-camera`, o recibe el código por el
  enlace profundo.
- `POST /v1/bridges/claim` con el código.
- Espera a que la caja abra su canal (UPDATE en `bridges` por tiempo real) y
  sigue a Elegir cámaras.

### Elegir cámaras (`app/choose-cameras.tsx`, Fase 1)

Pendiente de diseño. Qué hace:

- `GET /v1/bridges/{id}/discovered` y muestra las cámaras encontradas.
- Por cada cámara elegida: nombre del space, usuario y contraseña, y
  `POST /v1/spaces`. La contraseña no se guarda en el teléfono.
- Si una cámara no aparece, lleva a Conectar cámara para escribir su dirección.

### Conectar cámara (`app/connect-camera.tsx`)

- `CameraAddressForm`: campo, ayuda, botón.
- Al enviar: `POST /v1/spaces`. Mientras espera, el botón muestra que está
  trabajando.
- Con error: el estado de error del diseño. **El campo conserva lo que el
  usuario escribió.**

### Ver grabaciones (Fase 1, pendiente de diseño)

La grabación local cifrada del Cloud Bridge es de la Fase 1 (ver
`06-ARQUITECTURA.md`, Grabación). Todavía no tiene ruta ni diseño: se agregan
cuando estén respondidas sus preguntas abiertas. La clave para descifrar vive en
el llavero del teléfono (`expo-secure-store`) y el video se descifra solo en el
teléfono.

---

## Datos en la app

### Consultas

| Hook | Consulta |
|---|---|
| `useTodayThreads` | `threads` del usuario con `start_time` desde el comienzo del día local o desde hace `HOME_LOOKBACK_HOURS`, lo que sea antes; del más reciente al más viejo, con el nombre del space. La línea muestra los de hoy; el encabezado usa todos |
| `useThread(id)` | el thread, sus `layers` ordenados por `captured_at`, y sus `dispatches` |
| `useSpaces` | `spaces` del usuario |
| `useBridge` | el `bridges` del usuario (una caja por casa en la primera versión) |

Todas son lecturas directas a Supabase con RLS. Las escrituras y todo lo que
involucra modelos o el bridge pasan por `lib/api.ts`.

### Tiempo real

Un solo canal por usuario, abierto en `_layout.tsx`:

```ts
supabase
  .channel(`user:${userId}`)
  .on("postgres_changes",
      { event: "INSERT", schema: "public", table: "threads", filter: `user_id=eq.${userId}` },
      ({ new: row }) => upsertTodayThread(queryClient, row))
  .on("postgres_changes",
      { event: "UPDATE", schema: "public", table: "threads", filter: `user_id=eq.${userId}` },
      ({ new: row }) => upsertTodayThread(queryClient, row))
  .on("postgres_changes",
      { event: "UPDATE", schema: "public", table: "spaces", filter: `user_id=eq.${userId}` },
      ({ new: row }) => upsertSpace(queryClient, row))
  .on("postgres_changes",
      { event: "UPDATE", schema: "public", table: "bridges", filter: `user_id=eq.${userId}` },
      ({ new: row }) => setBridge(queryClient, row))
  .subscribe();
```

- `upsertTodayThread` inserta arriba o reemplaza por id en la caché de
  `useTodayThreads`. No vuelve a pedir la lista entera.
- `setBridge` reemplaza el estado del Cloud Bridge en la caché de `useBridge`.
  El encabezado del Home se recalcula con él (`lib/home-state.ts`).
- El detalle abre su propio canal filtrado por `thread_id`: INSERT en `layers`,
  e INSERT y UPDATE en `dispatches` (una notificación pasa a entregada, una
  llamada a atendida). Lo cierra al salir.
- **Siempre se cierra el canal** en la limpieza del efecto.
- **Al volver de segundo plano** se invalidan las consultas: mientras la app
  estuvo dormida pudo perderse eventos.

---

## Horas

Todas las horas se muestran en la zona horaria del usuario y con el formato de
su idioma:

| Dónde | en | es-AR |
|---|---|---|
| Píldora de la línea | 7:42 PM | 19:42 |
| What I saw (con segundos) | 7:42:11 PM | 19:42:11 |
| Meta del detalle | Today, 7:42 PM · Front Door | Hoy, 19:42 · Front Door |
| Dentro de frases (What I did) | at 7:42 PM | a las 19:42 |
| Feed en vivo | nunca | nunca |

Todo sale de `lib/time.ts`. Ningún componente formatea horas por su cuenta.

---

## Voz

### Hablarle

- `useVoiceInput` usa `expo-speech-recognition` con el idioma del usuario
  (`en-US` o `es-AR`) y resultados parciales.
- Pide reconocimiento en el dispositivo cuando está disponible.
- Mientras el usuario habla, el texto parcial aparece en el input. Al terminar,
  se envía como mensaje con `spoken: true`.
- Pide permisos de micrófono y de reconocimiento de voz la primera vez que se
  toca el botón, no al abrir la app.

### Escucharla

- `useSpeak` pide el audio a `POST /v1/tts` y lo reproduce con `expo-audio`, en
  una cola para que dos frases no se pisen.
- Habla cuando `voice_enabled` está activo y: la pregunta fue hablada (lee la
  respuesta), o la app está abierta y llega un thread que no es `normal` (lee la
  narrativa).
- Respeta el modo silencioso del teléfono.

---

## Notificaciones

- Al iniciar: crear los canales de Android `quiet`, `alerts` y `urgent`.
- Pedir permiso de notificaciones: en la Fase 0 al primer inicio; en la Fase 1,
  en el momento que defina el diseño del primer uso.
- Obtener el token de Expo Push y registrarlo con `POST /v1/devices`.
- Con la app abierta: mostrar el aviso del sistema solo para `time_sensitive` y
  `critical`. Los `passive` ya se ven en la línea.
- Al tocar una notificación sobre un thread: navegar a `/thread/<thread_id>` y
  llamar a `POST /v1/dispatches/<dispatch_id>/opened` con los ids que vienen en
  los datos de la notificación. Los avisos de sistema (casa sin señal, casa de
  vuelta, cámara sin conexión) no traen esos ids y abren el Home.

---

## Idiomas

- `i18next` con `en.json` y `es-AR.json`. Todo texto visible sale de `t()`.
  Ningún texto se escribe directo en un componente.
- El idioma es `users.locale`. Si todavía no hay usuario, el del teléfono.
- Las variables van entre llaves simples (`{name}`): i18next se configura con
  `interpolation: { prefix: "{", suffix: "}" }`. Detalle en `docs/i18n/README.md`.
- Las claves y los textos de cada idioma están en la sección Textos de
  `02-PRODUCTO.md`. Los dos archivos de traducción se generan a partir de esa
  tabla y tienen exactamente las mismas claves.
- El texto que muestren las imágenes de `design/` no cuenta: manda la tabla.
- Lo que escriben los modelos ya llega en el idioma del usuario; la app no lo
  traduce.

---

## Accesibilidad

- Áreas táctiles de al menos 44 × 44 puntos.
- Etiquetas de accesibilidad en todos los botones de solo ícono: menú, `+`,
  voz, volver.
- Cada thread se lee completo con el lector de pantalla: "7:42 PM, Front Door.
  Someone rang the bell. Nobody answered."
- El texto respeta el tamaño de fuente del sistema, con un tope que no rompa el
  diseño.
- Con "reducir movimiento" activo, las líneas de composing no brillan y las
  transiciones se desactivan.

---

## Modo laboratorio (Fase 0)

Con `EXPO_PUBLIC_LAB_MODE=true`:

- No hay Clerk ni inicio de sesión. El usuario es `EXPO_PUBLIC_LAB_USER_ID`.
- El cliente de Supabase usa la clave anónima del proyecto de laboratorio.
- `lib/api.ts` llama a la API del laboratorio en la red local sin token.
- La app abre directo en el Home, o en Conectar cámara si no hay spaces.

---

## Antes de cada commit en la app

- [ ] El componente se construyó con primitivas de React Native Reusables.
- [ ] Coincide con su imagen en `design/`.
- [ ] No se agregó ninguna pantalla, estado, texto ni dependencia no pedida.
- [ ] Todo texto visible sale de `t()` y existe en los dos idiomas.
- [ ] Ninguna hora se formatea fuera de `lib/time.ts`.
- [ ] Los canales de tiempo real se cierran al desmontar.
- [ ] `npx tsc --noEmit` pasa sin errores.
