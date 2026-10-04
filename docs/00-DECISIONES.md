# 00. Registro de decisiones

Las decisiones posteriores al 22/9/2026, con su fecha. **Al 27/9/2026 todas las
de abajo ya están integradas en los documentos 01 a 10**, así que no debería
haber contradicciones. Si aparece una, gana lo más nuevo y se avisa. Si algo no
está claro, se pregunta; no se resuelve inventando.

Para la idea completa, leé `00-INTRO.md`.

---

## 2026-09-27

### 1. El dispositivo tiene un solo nombre

- En la interfaz, el copy y el código, la caja de la casa se llama **Cloud
  Bridge** (ver punto 7). En texto corrido, "el bridge". El software que corre
  adentro también se llama bridge en el código.
- Afecta a esta clave de `02-PRODUCTO.md`, que queda así:

| Clave | en | es-AR |
|---|---|---|
| `connect.errorHelp` | Make sure the camera is on and on the same network as your bridge. | Fijate que la cámara esté encendida y en la misma red que tu bridge. |

- Hardware de referencia (propuesta, no bloquea la Fase 0): caja blanca al lado
  del router, luz de estado (blanca: mirando · ámbar: sin internet · roja:
  alerta), sirena integrada, Ethernet + USB-C, QR de emparejamiento abajo. La
  sirena y la luz roja **no se construyen** hasta que haya diseño y fase
  asignada.

### 2. Privacidad: la nube nunca guarda imágenes; el bridge sí graba, cifrado

Cambia la promesa de "zero-video" absoluto por esta:

- **La nube sigue sin guardar nada visual.** Todas las reglas de zero-video
  para la API, el worker, el relay, Supabase, logs y Sentry siguen vigentes
  sin cambios. Un frame en la nube vive en memoria y se descarta.
- **El bridge graba localmente, cifrado, y solo el usuario puede verlo.**
- **Fase:** Fase 1. En la Fase 0 (laboratorio) **no se construye grabación**.
  La Fase 0 no cambia.

**Diseño técnico: propuesta, confirmar antes de implementar.**

- El teléfono genera un par de claves al emparejar el bridge. La privada queda
  en el llavero del teléfono (`expo-secure-store`); la pública va al bridge.
- El bridge graba segmentos cortos, cifra cada uno con una clave simétrica al
  azar y guarda esa clave envuelta con la pública del usuario. El bridge no
  puede descifrar lo que grabó.
- Para ver una grabación, la app pide el segmento cifrado por el canal del
  bridge (vía relay), lo descifra en el teléfono y lo reproduce. La nube solo
  pasa bytes cifrados, sin guardarlos.
- Consecuencia honesta: si el usuario pierde el teléfono sin respaldo de la
  clave, pierde las grabaciones. Hay que resolver respaldo o multi-dispositivo.

**Preguntas abiertas (bloquean la implementación, no la Fase 0):**

1. ¿Grabación continua, solo clips de momentos (`attention`/`emergency`), o las
   dos?
2. ¿Cuántos días se guardan y en qué almacenamiento (microSD, SSD)?
3. ¿Respaldo de la clave y varios teléfonos por casa?
4. Diseño de las pantallas para ver grabaciones.

**Textos que dejan de ser verdad** y se reescriben antes de la Fase 1 (hasta
entonces no se tocan en la Fase 0, que no graba):

- `live.privacy` ("Artemisa doesn't record it")
- `connect.privacy` ("never keeps the images")
- La regla de `02-PRODUCTO.md` sobre "See now" vs "Watch" se mantiene para los
  threads; ver grabaciones será una acción nueva con su propio texto.
- `01-INTRODUCCION.md`, "Qué no es Artemisa: no es un grabador" deja de valer
  en la Fase 1.

### 3. Llamada al 911: bloqueada

- Se mantiene la Fase 2b **bloqueada**. La cuenta regresiva de 10 s para
  llamar al 911 está decidida como producto, pero **no se escribe ni una línea**
  hasta tener opinión legal. Nada de flags apagados ni código "preparado".

### 4. Qué es "terminar la beta"

- Orden: **Fase 0 (laboratorio) → Fase 1 (beta cerrada)**. No se saltea el
  laboratorio.
- Seguimiento del avance: `PROGRESS.md` en la raíz del repo.

### 5. Sistema de diseño y dependencias aprobadas

- El sistema de diseño vive en `09-DISENO.md` y `design/tokens.json`.
  Monocromático; el color solo indica estado; el rojo es exclusivo de
  `emergency`. Negro, blanco y gris en todo: app, web y marca.
- Dependencias de la app aprobadas además de las de `07-APP.md`:
  `@expo-google-fonts/instrument-serif`, `@expo-google-fonts/inter`,
  `expo-font`, `expo-splash-screen`, `lucide-react-native`,
  `react-native-svg` (lo pide Lucide).
- Los textos de la app ya están generados en `docs/i18n/`. El paso 11 los copia
  a `mobile/lib/i18n/`. Si cambia la tabla de `02-PRODUCTO.md`, se regeneran.
- El registro de modelos y los prompts ya están en `server/artemisa/core/`.
  El paso 3 los usa tal cual; no se reescriben.

### 6. Superado

Cualquier referencia fuera de `docs/` a Next.js, shadcn web, Framer como
frontend, `gpt-4o-mini` para visión o "No new hardware" está superada. Manda
este repo.

### 7. El nombre es "Cloud Bridge"

- El dispositivo se llama **Cloud Bridge** en todos los documentos, el copy y
  el diseño. En texto corrido, después de nombrarlo una vez, alcanza con "el
  bridge". El software que corre adentro se sigue llamando bridge en el
  código.
- La clave `connect.errorHelp` del punto 1 queda igual ("tu bridge").

### 8. El Cloud Bridge es un puente: el análisis corre en la nube

- El bridge **no procesa**. Lee las cámaras vía go2rtc, sube a la nube lo que
  hace falta, guarda la grabación cifrada (punto 2) y las contraseñas de las
  cámaras. Nada más. Por eso su hardware es liviano.
- **El Paso 1 (movimiento) pasa a la nube**, con las mismas constantes de
  `03-ALGORITMO.md`. Donde `03-ALGORITMO.md` y `06-ARQUITECTURA.md` ponen el
  Paso 1 en el bridge, leé "en la nube". El resto de esos documentos sigue
  igual.
- **Fase 0:** no cambia nada. El laboratorio ya corre todo en una notebook.
- **Pendiente antes de la Fase 1** (no se inventa): cómo sube el bridge los
  frames a la nube, a qué tamaño y frecuencia, y cuánto cuesta ese tráfico.
- La promesa de privacidad del punto 2 no cambia: la nube sigue sin guardar
  nada visual.

### 9. shadcn web solo para prototipos

- La app es mobile (Expo + React Native Reusables). El punto 6 sigue vigente.
- El preset de shadcn web (`npx shadcn@latest init --preset bbVJxce --template
  next`) se usa **solo para prototipar pantallas en Claude Design**. Comparte
  los tokens de `09-DISENO.md`. Nada de ese código entra al repo de la app.

---

## 2026-09-30

### 10. Modelos vía Vercel AI Gateway en la Fase 0

- En lugar de claves directas de OpenAI y Groq, un solo cliente con el SDK de
  openai contra `https://ai-gateway.vercel.sh/v1`. La clave va en
  `AI_GATEWAY_API_KEY`.
- El registro usa los ids del gateway, que llevan el prefijo del creador
  (`openai/gpt-4.1-nano`, `openai/gpt-oss-20b`). Cada rol fija quién lo sirve
  con `providerOptions.gateway.only`: `["openai"]` para los modelos de OpenAI y
  `["groq"]` para los `gpt-oss`.
- `providers/` tiene un solo `gateway.py`, junto a `expo_push.py`. La
  dependencia `groq` sale del servidor.
- `tts` queda abierto hasta el paso 15: el gateway no lo sirve por el SDK de
  openai.
- Los precios se verifican contra el gateway. `openai/gpt-oss-20b` queda
  pendiente: el registro dice 0.075 de entrada y Vercel lista 0.08.
- Vercel pasa a ser un intermediario más: se declara en la política de
  privacidad y se verifican sus términos de retención antes de la Fase 1.
- Integrado en `04-MODELOS.md`, `08-CONSTRUCCION.md`, `models.yaml` y
  `CLAUDE.md`.

---

## 2026-10-04

### 11. Avisos por SMS en la Fase 0

- En la Fase 0 los avisos del Paso 4 y los avisos de sistema (casa sin señal,
  casa de vuelta, cámara sin conexión) salen **por SMS**, no por Expo Push: la
  app todavía no existe. **El push vuelve con la app.**
- `dispatch_channel` suma el valor `sms` (`supabase/migrations/0002_dispatch_sms.sql`).
- Proveedor: Twilio, por su API REST con `httpx`, en `providers/twilio.py`, sin
  dependencia nueva. Claves en `server/.env`: `TWILIO_ACCOUNT_SID`,
  `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`.
- El número de destino es `LAB_SMS_TO`, una variable solo del laboratorio. El
  esquema no tiene teléfonos.
- `SMS_MODE=log` por defecto: registra el aviso sin enviarlo. `SMS_MODE=live`
  envía, con un tope duro de envíos por hora.
- La llamada de voz al titular sigue en la Fase 2a. No se escribe nada de ella.
