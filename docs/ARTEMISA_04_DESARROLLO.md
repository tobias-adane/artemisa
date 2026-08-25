# ARTEMISA — 04 · STACK, DISEÑO Y ESTADO DEL BUILD

---

## 1. STACK

### Frontend
```
Framework:    Next.js 14 (App Router), TypeScript
Componentes:  shadcn/ui — style "maia"
Auth:         Clerk
Hosting:      Vercel
```

### Backend
```
Pipeline:     Python en Railway
Visión:       OpenCV (Paso 1 — motion diff), FFmpeg
Base de datos: Supabase (PostgreSQL + real-time)
Errores:      Sentry
```

### IA
```
Paso 2a (descripción):  OpenAI GPT-4o mini (vision)
Paso 2b (análisis):     Groq Llama 3.1 8B / 3.3 70B
Paso 3 (razonamiento):  OpenAI GPT-4.1 mini
Chat:                   Groq Llama 3.3 70B
```

### Comunicaciones
```
Twilio — llamadas + WhatsApp (Niveles 3 y 4)
```

**Nota:** el backend Python es un servicio separado. El frontend
Next.js lee/escribe contra Supabase y llama endpoints propios — no
reconstruye el pipeline de IA.

---

## 2. DESIGN SYSTEM

Ver `frontend/CLAUDE.md` — es la fuente de verdad completa (tokens
CSS, tipografía, radius, color, motion, checklist de commit). No se
duplica acá para evitar que los dos diverjan otra vez.

Resumen de lo no negociable:
- Monocromático estricto, sin azul/navy/acentos nuevos
- Rojo (`#dc2626`) exclusivo de Emergency / Nivel 4
- Instrument Serif solo en headings, Inter en todo lo demás
- Radius grande e intencional (parte del estilo maia)
- Todo en español rioplatense (voseo) — beta Argentina

---

## 3. PANTALLAS — ESTADO DEL DISEÑO

Mockups aprobados en `frontend/design-reference/*.dc.html` (formato
Claude Design), listos como especificación visual para traducir a
Next.js + shadcn real:

| Pantalla | Qué contiene |
|---|---|
| **Auth** | Login/signup — Google, Apple, email/password. Falta forgot password y verificación por código (ver frontend/CLAUDE.md) |
| **Onboarding** | Flujo completo: nombre, hogar, safety concerns, custom instructions, contactos de emergencia, conectar cámara. Falta el estado de error en test de conexión |
| **Home** | Saludo contextual, chat input (el chat vive como estado dentro de Home, no como ruta separada), chips de acceso rápido, grid de espacios |
| **Activity** | Timeline por día — Living Memory. Falta el bloque "Por qué importó" |
| **Spaces** | Grid de todos los espacios, estado por cámara. Falta la card completa de "Offline" con Reconectar |
| **Space** | Vista individual de un espacio. Mismo faltante que Spaces |
| **Settings** | Planes, "What's worth an alert", Quiet hours. El pricing actual está desactualizado — ver frontend/CLAUDE.md punto 7 |
| **AvatarMenu** | Profile, Subscription, Spaces, Family, System Instructions, Interactive Memory, Language |

La lista completa y verificada de qué falta construir (con el
detalle de qué se buscó y no se encontró en cada mockup) vive en
`frontend/CLAUDE.md`, sección "Pantallas — estado del diseño". No se
duplica acá para que no queden dos listas desincronizadas.

### Explícitamente descartado — no construir

**Emergency Overlay de pantalla completa con countdown animado.**
El dispatch real corre server-side vía Twilio, independiente de si
la app está abierta. Un alert card simple alcanza para el
reconocimiento in-app.

---

## 4. ORDEN DE BUILD DEL BACKEND

```
FASE 1 — Paso 1: Motion detection
  Servicio Python + OpenCV, conexión RTSP, frame differencing,
  heartbeat adaptativo (construir desde el día 1)

FASE 2 — Paso 2a: Descripción
  GPT-4o mini vision, detail: low, frame descartado en memoria
  inmediatamente, escritura en `layers` (sin classification)

FASE 3 — Paso 2b: Análisis
  Job cada ~60s, contexto comprimido inyectado, Groq Llama,
  output estructurado con confidence + severity_score, escritura
  en `threads`, resolve_action_level() para alert_level/action

FASE 4 — Paso 3: Razonamiento
  GPT-4.1 mini, los 4 triggers de activación, contexto extendido
  multi-espacio, determina severity_high final

FASE 5 — Paso 4: Acción / Twilio
  ⚠️ Sesión de trabajo SEPARADA — es la parte de mayor
  responsabilidad legal del producto (específicamente el autodial
  al 911 de Nivel 4). Nivel 3 (contactar a persona de confianza) no
  está bloqueado por la consulta legal y puede programarse antes.
  Requiere testing dedicado y la consulta legal resuelta antes de
  programar el 911 automatizado.
```

---

## 5. TENSIONES ABIERTAS (decisiones pendientes)

**1. Scope del MVP no está acotado explícitamente.**
El documento fundacional lista como parte del MVP: perfiles de
habitantes, identificación contextual, memoria, threads, layers,
clasificación, conversación, acciones configurables. Eso es más
ambicioso que el recorte original de 12 semanas / $10k. Falta una
lista explícita de qué entra y qué queda post-beta.

**2. Legalidad del dispatch automatizado al 911.**
Sin resolver con abogado argentino. Si la respuesta es restrictiva,
cambia la arquitectura del Nivel 4 (no del Nivel 3). Resolver
**antes** de programar el 911 automatizado de la Fase 5.

**3. Economía de unidad no cierra.**
Costo de IA (~$4.70/mes por hogar) supera el pricing de beta. Las 3
palancas de optimización están identificadas pero no construidas.

**4. Precisión del reconocimiento por patrón descriptivo.**
La decisión de evitar biometría es correcta legalmente, pero falta
validar si la fidelidad alcanza para que el usuario sienta que
Artemisa "reconoce" a su familia de forma creíble. Solo la beta
real lo va a contestar.

### Resueltas en esta ronda de reconciliación

- ~~Modelo de cámaras~~ → confirmado 1 espacio = 1 cámara para el
  MVP, sin tabla `Camera` separada.
- ~~Tablas faltantes del schema~~ → `users`, `activity_log`,
  `conversations` y `user_preferences` confirmadas como parte del
  schema desde ya, no como recorte.
- ~~Separación Layer/Thread~~ → `Layer` nunca clasifica; la
  clasificación vive una sola vez en `Thread` (Paso 2b).
- ~~Ambigüedad Nivel 2 vs Nivel 3 dentro de `attention`~~ →
  resuelto con el criterio `severity_score >= 0.7` y una ventana de
  cancelación propia de 90s para Nivel 3 (no requiere Paso 3).
- ~~Idioma de la beta~~ → español rioplatense, Argentina, `+54`
  como prefijo default de teléfono.

Ver `docs/ARTEMISA_03_DATOS.md` para el detalle completo de cada una.
