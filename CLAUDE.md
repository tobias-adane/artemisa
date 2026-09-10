# ARTEMISA — CLAUDE.md
# Contexto maestro para builds con Claude Code

---

## 1. QUÉ ES

**Artemisa no analiza cámaras. Comprende lo que ocurre en tu hogar.**

Capa de inteligencia que se conecta a las cámaras IP que la familia ya tiene.
Convierte video en texto, construye contexto sobre la rutina de ese hogar
específico, y actúa automáticamente cuando detecta algo que realmente importa.
**No almacena video, imágenes ni audio. Nunca.**

> **Propuesta de valor: "Artemisa hace que las familias dejen de preocuparse."**

Regla de producto: si una feature no ayuda a que la respuesta sea más rápida
o más clara, no es prioritaria. Es una app de reacción, no de vigilancia pasiva.

### Los 8 principios (ethos)

1. **Comprender antes de actuar** — detectar algo no significa entenderlo
2. **La tranquilidad antes que las notificaciones** — reducir ansiedad, no producirla
3. **La privacidad por defecto** — la información del hogar pertenece al hogar
4. **La incertidumbre es válida** — Artemisa nunca inventa certeza
5. **Contexto antes que eventos aislados** — un evento tiene significado en una historia
6. **Inteligencia donde importa** — el cómputo se usa para resolver problemas reales
7. **Acción con propósito** — toda acción existe porque mejora seguridad o tranquilidad
8. **Tecnología invisible** — el usuario no necesita entender cómo funciona

### Principio de decisión ante cualquier duda

1. ¿Esto ayuda a que la respuesta sea más rápida o más clara? → prioridad alta
2. ¿Le habla a la familia con ambos padres trabajando y la casa sola? → cliente de v1
3. ¿El copy suena a alguien preocupado por proteger, o a una empresa vendiendo miedo?
4. ¿Agrega complejidad sin acercar al usuario a sentir "si algo pasa, habrá respuesta"?
5. ¿La acción es proporcional al nivel de certeza real? → nunca Nivel 4 con evidencia de Nivel 2

### Los 4 niveles de acción

| Nivel | Nombre | Qué hace |
|---|---|---|
| 1 | **Informar** | Relevante pero no urgente. Se registra en Activity, sin interrumpir |
| 2 | **Alertar** | Requiere atención ahora. Alert card simple, sin dispatch |
| 3 | **Contactar** | Llamadas/mensajes a contacto de confianza (no 911) |
| 4 | **Emergencia** | Protocolo completo — 911 + contactos, vía Twilio |

**Regla de oro:** cuanto mayor el impacto de una acción, mayor el nivel de
certeza requerido. Nivel 4 SOLO si `classification == emergency` Y Paso 3
confirmó `severityHigh`.

---

## 2. STACK

### Frontend
```
Framework:    Next.js 14 (App Router, TypeScript)
Componentes:  shadcn/ui — style: "maia", preset: bbVJxce, baseColor: neutral, cssVariables: true
Icons:        lucide-react — stroke-width: 2, stroke: currentColor, fill: none
Auth:         Clerk (useUser, useAuth, middleware)
Hosting:      Vercel
Errores:      Sentry
```

### Backend (servicio separado — Railway)
```
Pipeline:     Python
Visión:       OpenCV (Paso 1 — motion diff), FFmpeg
Base de datos: Supabase (PostgreSQL + real-time subscriptions)
```

### IA
```
Paso 2 — Descripción:   GPT-4o mini (vision), detail: low
Paso 2 — Análisis:      Groq Llama 3.1 8B / 3.3 70B
Paso 3 — Razonamiento:  GPT-4.1 mini
Chat:                   Groq Llama 3.3 70B
```

### Comunicaciones
```
Twilio — llamadas + WhatsApp (Niveles 3 y 4)
```

**El frontend Next.js lee/escribe contra Supabase y llama endpoints propios.
NO reconstruye el pipeline de IA.**

---

## 3. EL PIPELINE DE 4 PASOS

### Paso 1 — Movimiento (gratis, 24/7, sin IA)
- OpenCV compara frame actual vs. anterior (frame differencing)
- Si no hay cambio: no se llama a ningún modelo
- Chequeo cada 1-2s; heartbeat de salud cada 5 min si no hubo movimiento
  → **heartbeat adaptativo desde el día 1** (escalar a 15 min en horarios tranquilos)
- **Es lo que hace viable económicamente todo el pipeline**

### Paso 2 — Descripción (Layer generation)
- Activa solo cuando Paso 1 detectó movimiento real
- GPT-4o mini vision → convierte frame en 1 oración factual (`layers.description`)
- Frame descartado de memoria inmediatamente después del retorno — nunca a disco
- Cada ~60s: Groq Llama agrupa layers → narrativa → clasifica contra rutina del hogar

Contexto inyectado al modelo de análisis:
1. Layers del batch actual
2. `users.custom_instructions` (rutina enseñada por el usuario)
3. Resumen de los últimos 3-5 threads de ese espacio
4. Hora del día + día de la semana
5. Estado de otros espacios de la casa

Escala a Llama 3.3 70B cuando:
- Descripciones contradictorias o ambiguas
- El batch toca `custom_instructions`
- Horario nocturno (11pm-6am, configurable)

### Paso 3 — Razonamiento profundo (GPT-4.1 mini)
Se activa solo si:
1. Paso 2 clasificó `attention` con confidence < 0.6
2. Paso 2 clasificó `emergency` — **SIEMPRE se re-verifica antes de disparar Twilio**
3. Fast-path detectó algo que amerita escalar sin esperar el ciclo de 60s
4. Patrón de persona no reconocida apareciendo repetidamente

### Paso 4 — Acción (Twilio)
- Niveles 1-2: solo escritura en Supabase → frontend via real-time
- Niveles 3-4: dispatch Twilio (llamada + WhatsApp)
- El dispatch corre **server-side** — no depende de que la app esté abierta
- Ventana de cancelación en la llamada misma (IVR) y en WhatsApp
- El paso "llamar al 911" (dentro de Nivel 4) está **implementado**, pero
  apagado por default vía `Settings.enable_911_autodial` (env
  `ENABLE_911_AUTODIAL=false`) hasta resolver la consulta legal sobre
  autodial en Argentina — ver `backend/CLAUDE.md`. Nivel 3 (contactar a
  persona de confianza) no depende de este flag.

### Cuándo Artemisa interrumpe proactivamente vs. solo registra

| Caso | Comportamiento |
|---|---|
| `attention` | Alert card simple, sin pregunta |
| Patrón nuevo recurrente | Pregunta de aprendizaje activa |
| `emergency` confirmada | Nunca pregunta — acción directa al Paso 4 |
| `normal` | Solo va al feed de Activity |
| Durante Quiet hours | Silenciado, salvo `emergency` |

---

## 4. DESIGN SYSTEM

### Setup (una sola vez)
```bash
npx shadcn@latest init --preset bbVJxce --template next
npx shadcn@latest add @ai-elements/attachments
```

`components.json`:
```json
{
  "style": "maia",
  "tailwind": { "baseColor": "neutral", "cssVariables": true, "chartColor": "neutral" },
  "iconLibrary": "lucide"
}
```

### Tokens CSS — globals.css

```css
:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.145 0 0);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.97 0 0);
  --secondary-foreground: oklch(0.205 0 0);
  --muted: oklch(0.97 0 0);
  --muted-foreground: oklch(0.556 0 0);
  --accent: oklch(0.97 0 0);
  --accent-foreground: oklch(0.205 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  --border: oklch(0.922 0 0);
  --input: oklch(0.922 0 0);
  --ring: oklch(0.708 0 0);
  --radius: 0.875rem;
  --sidebar: oklch(0.985 0 0);
  --sidebar-foreground: oklch(0.145 0 0);
  --sidebar-primary: oklch(0.205 0 0);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.97 0 0);
  --sidebar-accent-foreground: oklch(0.205 0 0);
  --sidebar-border: oklch(0.922 0 0);
  --sidebar-ring: oklch(0.708 0 0);

  /* Status tokens — únicos acentos de color permitidos */
  --status-normal:    #22c55e;
  --status-attention: #d08700;
  --status-emergency: #dc2626;
  --status-offline:   #737373;
}

.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  --card: oklch(0.205 0 0);
  --card-foreground: oklch(0.985 0 0);
  --popover: oklch(0.205 0 0);
  --popover-foreground: oklch(0.985 0 0);
  --primary: oklch(0.922 0 0);
  --primary-foreground: oklch(0.205 0 0);
  --secondary: oklch(0.269 0 0);
  --secondary-foreground: oklch(0.985 0 0);
  --muted: oklch(0.269 0 0);
  --muted-foreground: oklch(0.708 0 0);
  --accent: oklch(0.269 0 0);
  --accent-foreground: oklch(0.985 0 0);
  --destructive: oklch(0.704 0.191 22.216);
  --border: oklch(1 0 0 / 10%);
  --input: oklch(1 0 0 / 15%);
  --ring: oklch(0.556 0 0);
  --sidebar: oklch(0.205 0 0);
  --sidebar-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.269 0 0);
  --sidebar-accent-foreground: oklch(0.985 0 0);
  --sidebar-border: oklch(1 0 0 / 10%);
  --sidebar-ring: oklch(0.556 0 0);
}
```

### Tipografía

| Rol | Familia | Cuándo |
|---|---|---|
| Headings | `'Instrument Serif', Georgia, serif` | SOLO títulos de pantalla. Máx 1-2 por pantalla. Weight 400 |
| Body/UI | `'Inter', -apple-system, sans-serif` | Todo lo demás |

Instrument Serif **NUNCA** en: botones, labels, badges, nav, inputs, body text.

Google Fonts en `layout.tsx`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
```

### Border radius

```
rounded-sm    8px    → chips, badges pequeños
rounded-xl   14px    → inputs, botones, items de lista
rounded-2xl  24px    → cards internas / contenedoras
rounded-3xl  30px    → cards grandes, modales, drawers
rounded-full        → pills de estado, avatares, bottom nav
```

### REGLA DEL ROJO — CRÍTICA

`#dc2626` / `var(--status-emergency)` es **EXCLUSIVO de Emergency / Nivel 4**.

```
❌ NUNCA rojo para:
   - Botones "Eliminar" / "Remover" / acciones destructivas genéricas
   - Botón "Cancelar alerta" — es la acción SEGURA, no el peligro
   - El destructive de shadcn por defecto — no asumir que aplica

✅ SOLO rojo para:
   - Cards con estado Emergency activo (Nivel 4)
   - Dot de clasificación "emergency"
   - Badge de alert_level == 4
```

Para acciones destructivas genéricas: `variant="outline"` con texto en `--muted-foreground`.

### Motion

```
Solo animar: transform + opacity
  (excepciones: clip-path, height en accordions)

Nunca: transition: all | scale(0) | ease-in en UI

Curvas:
  --ease-out:    cubic-bezier(.23,1,.32,1)
  --ease-in-out: cubic-bezier(.77,0,.175,1)
  --ease-drawer: cubic-bezier(.32,.72,0,1)

Duración siempre < 300ms:
  press 100-160ms · dropdown 150-250ms · modal/drawer 200-500ms

Stagger 30-80ms cuando entran varios elementos juntos.
Siempre respetar prefers-reduced-motion.
```

### Componentes — regla principal

SIEMPRE shadcn/ui primero. Si no existe en shadcn, componer con primitivos + tokens CSS.
NUNCA instalar otra librería de componentes.

```bash
npx shadcn@latest add <nombre>
```

### Bottom nav

Pill flotante, `rounded-full`, fondo `--card`, `shadow-sm`.
Íconos Lucide: Home | LayoutGrid | Activity | Settings.
Activo: `--foreground`. Inactivo: `--muted-foreground`. Sin labels de texto.

---

## 5. ARQUITECTURA ZERO-VIDEO — RESTRICCIÓN CRÍTICA

- Frames procesados en memoria, descartados inmediatamente
- `layers` y `threads` en Supabase: **NUNCA** columnas blob/bytea/imagen
- `rtsp_url`: **SOLO** en el backend Python, **nunca** en el cliente
- `activity_log.image_url`: solo para imágenes que sube el usuario explícitamente (chat attach), **nunca** un frame de cámara

### "Ver momento" — stream proxeado

El botón "Ver momento" llama a `app/api/camera/[id]/stream/route.ts` →
el backend hace proxy del RTSP vía ffmpeg → el cliente recibe HLS/MJPEG →
la `rtsp_url` nunca llega al cliente.

**Siempre "Ver momento", nunca "Ver video".** Artemisa no grabó nada — está
abriendo la cámara ahora, en el instante del evento.

---

## 6. SCHEMA DE SUPABASE

```sql
users (
  id, email, name, timezone, account_type, home_type,
  area_type, has_children, custom_instructions,
  created_at, updated_at
)

spaces (
  id, user_id, name, camera_url, camera_type, status,
  last_frame, last_update
)

layers (
  id, space_id, description, confidence, timestamp, metadata
)

threads (
  id, space_id, layers, narrative, classification, confidence,
  severity_score, reasoning, alert_level, action, start_time, end_time,
  escalated_to_reasoning
)

emergency_contacts (
  id, user_id, name, phone, relationship, priority
)

user_preferences (
  id, user_id, alert_sensitivity, cancel_timer_seconds,
  auto_call_enabled, do_not_disturb_start, do_not_disturb_end
)

conversations (
  id, user_id, messages JSONB, context JSONB
)

activity_log (
  id, user_id, thread_id, event_type, title, description,
  location, image_url, timestamp
)
```

**`layers` y `threads` nunca tienen columnas blob/bytea. Impuesto a nivel de schema.**

`activity_log.thread_id` es nullable: hay entradas de actividad sin thread
(cámara reconectada, dispatch cancelado, etc.).

### Enums

```
Classification:      normal | attention | emergency
ActionLevel:         informar | alertar | contactar | emergencia
SpaceStatus:         active | offline | pending
CameraType:          rtsp
ContactRelationship: spouse_partner | parent | sibling | friend | neighbor | other
HomeType:            apartment | house | small_business
EventType:           thread_logged | dispatch_triggered | dispatch_cancelled |
                     space_connected | space_went_offline | space_reconnected
AlertSensitivity:    low | balanced | high
```

### Mapeo Classification → Action

```
normal     → alert_level 1 → action: informar   (solo se registra)
attention  → severity_score < 0.7  → alert_level 2 → action: alertar
           → severity_score >= 0.7 → alert_level 3 → action: contactar
emergency  → severity_high == True  → alert_level 4 → action: emergencia
           → severity_high == False → alert_level 3 → action: contactar (degradado)
```

`severity_score` (Paso 2b, Groq) decide Nivel 2 vs Nivel 3 dentro de `attention` —
es distinto de `confidence`. `severity_high` lo decide el modelo de razonamiento
(Paso 3, GPT-4.1 mini) y solo es relevante cuando `classification == emergency`,
que siempre escala a Paso 3 antes de resolver la acción.

Implementado como función determinística `resolve_action_level()` /
`resolveActionLevel()` con exhaustiveness check — ver
`backend/artemisa_models.py` y `frontend/lib/types/artemisa-types.ts`
(ya sincronizados entre sí; esta tabla los espeja, no al revés).

### Teléfonos
`emergency_contacts.phone` usa formato **E.164**: `+5491122334455`. Validar en frontend antes de guardar.

---

## 7. TIPOS TYPESCRIPT

Sincronizados con el backend Python. **Si cambia el schema, actualizar ambos + migración Supabase.**

```typescript
// lib/types.ts

type AlertLevel = 1 | 2 | 3 | 4;
type Classification = 'normal' | 'attention' | 'emergency';
type ActionType = 'informar' | 'alertar' | 'contactar' | 'emergencia';

interface Layer {
  id: string;
  space_id: string;
  description: string;       // texto factual de visión IA — NUNCA imagen/blob
  confidence: number;
  timestamp: string;         // ISO 8601 con segundos exactos
  metadata?: Record<string, unknown>;
  created_at: string;
}

interface Thread {
  id: string;
  space_id: string;
  narrative: string;         // resumen del evento en voz de Artemisa
  classification: Classification;
  confidence: number;
  reasoning: string | null;  // por qué se llegó a esa clasificación — Paso 3, null si no aplica
  action: ActionType | null;
  start_time: string;
  end_time: string | null;
  escalated_to_reasoning: boolean;
}

interface Space {
  id: string;
  user_id: string;
  name: string;
  cameras: Camera[];
  status: 'active' | 'offline' | 'pending';
  last_frame?: string;
}

interface Camera {
  id: string;
  space_id: string;
  name: string;
  rtsp_url: string;          // NUNCA exponer en el cliente — solo backend
  is_online: boolean;
}

interface EmergencyContact {
  id: string;
  user_id: string;
  name: string;
  phone: string;             // E.164
  relationship: string;
  priority: number;          // 1 = primero
}

interface UserPreferences {
  alert_sensitivity: 'low' | 'balanced' | 'high';
  cancel_timer_seconds: number;  // default 30
  auto_call_enabled: boolean;
  do_not_disturb_start?: string; // HH:MM
  do_not_disturb_end?: string;
}
```

---

## 8. ESTRUCTURA DE CARPETAS

```
app/
  (auth)/
    login/page.tsx
    signup/page.tsx
    forgot-password/page.tsx
    verify-email/page.tsx
  (onboarding)/page.tsx        ← flujo completo (steps 1-6)
  (app)/
    layout.tsx                 ← bottom nav + providers
    home/page.tsx               ← desktop: incluye el chat como estado, no ruta aparte
    chat/page.tsx                ← SOLO se renderiza/navega en mobile — ver nota abajo
    activity/page.tsx
    spaces/page.tsx
    spaces/[id]/page.tsx
    settings/page.tsx
  api/
    chat/route.ts
    camera/[id]/stream/route.ts  ← proxea RTSP, nunca expone la URL

components/
  ui/                            ← shadcn primitives (auto-generados)
  artemisa/
    BottomNav.tsx
    StatusDot.tsx
    ThreadCard.tsx
    ReasoningThread.tsx
    ContextualLayers.tsx
    AlertBanner.tsx
    SpaceCard.tsx
    CameraStatus.tsx

lib/
  supabase/client.ts
  supabase/server.ts
  types.ts
  utils.ts
```

**Chat como ruta separada es exclusivo de mobile.** En desktop, Home ya
incluye el chat como estado interno (no navega a otra pantalla — igual
que `frontend/design-reference/Home.dc.html`, que no tiene un
`Chat.dc.html` separado). En mobile, `send()` navega a `chat/page.tsx`
en vez de expandir el chat inline en Home. Construido — el estado y la
lógica de reply se comparten entre Home y Chat vía `lib/use-chat.ts`.

---

## 9. COMPONENTES CLAVE DEL PRODUCTO

### ReasoningThread ("Cómo llegué a esta decisión")

Thread de 4 nodos conectados por línea vertical.

| Nodo | Label | Dot | Contenido |
|---|---|---|---|
| 1 | "Artemisa notó algo" | Rojo si emergency, gris si attention | `layers[0].description` + timestamp |
| 2 | "Artemisa analizó el contexto" | Gris | `thread.narrative` |
| 3 | "Artemisa verificó dos veces" | Gris | `thread.reasoning` — **OCULTO** si `escalated_to_reasoning == false` o `reasoning == null` |
| 4 | "Artemisa actuó" | Negro | `thread.action` — texto bold |

### ContextualLayers ("Hilo contextual")

Feed cronológico de los layers que construyeron el thread. Cada ítem: `description`,
`timestamp` con segundos exactos, nombre del espacio/cámara. Lista simple, sin procesamiento extra.

### ActionText (helper)

```typescript
function actionText(thread: Thread): string {
  const time = new Date(thread.start_time).toLocaleTimeString('es-AR', {
    hour: '2-digit', minute: '2-digit'
  });
  switch (thread.action) {
    case 'informar':   return 'Te mandé una notificación.';
    case 'alertar':    return `Te llamé a las ${time}.`;
    case 'contactar':  return 'Te llamé. Como no atendiste, llamé a tus contactos de emergencia.';
    case 'emergencia': return 'Te llamé. Llamé a tus contactos. Contacté al servicio de emergencias.';
    default:           return '';
  }
}
```

---

## 10. SUPABASE REAL-TIME

```typescript
const channel = supabase
  .channel('threads')
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'threads',
    filter: `space_id=eq.${spaceId}`,
  }, (payload) => { /* actualizar estado */ })
  .subscribe();

return () => { supabase.removeChannel(channel); };
```

---

## 11. COPY — REGLAS DURAS

```
❌ NUNCA en la UI:
   "AI" / "inteligencia artificial" / "modelo" / "vision model" / "chain of thought"
   "Movimiento detectado en cámara 3"
   "Persona detectada"
   "Sin eventos registrados"
   "Ver video" (Artemisa no graba video)
   "Procesando..." (en tono técnico)

✅ Siempre voz humana de Artemisa:
   "Tu hija llegó hace 15 minutos."
   "No pasó nada importante desde que te fuiste."
   "Todo tranquilo en casa."
   "Artemisa está prestando atención."
   "Ver momento" (no "Ver video")
```

Artemisa puede expresar incertidumbre:
- ❌ "Llegó tu hija."
- ✅ "Parece que llegó tu hija, pero no estoy completamente segura."

Copy de estado ya validado:
```
"Good morning, [nombre] — Everything feels right at home."
"Your home's empty right now. All secure."
"A calm, quiet day."
"The front door's locked. All quiet."
"Ask anything about your home"
```

---

## 12. PANTALLAS YA DISEÑADAS (no tocar sin motivo)

8 pantallas en formato `.dc.html` como especificación visual (en
`frontend/design-reference/` — no hay un `Chat.dc.html` separado; el
chat vive dentro de `Home.dc.html` como estado, salvo en mobile — ver
sección 8):

| Pantalla | Contenido |
|---|---|
| **Auth** | Login/signup — Google, Apple, email/password |
| **Onboarding** | Nombre, hogar, safety concerns, custom instructions, contactos, cámara |
| **Home** | Saludo contextual, chat input (incluye la conversación como estado en desktop), chips de acceso rápido, grid de espacios |
| **Activity** | Timeline por día — Living Memory |
| **Spaces** | Grid de todos los espacios, estado por cámara |
| **Space** | Vista individual de espacio |
| **Settings** | Plan, "What's worth an alert", Quiet hours |
| **AvatarMenu** | Profile, Subscription, Spaces, Family, System Instructions, Interactive Memory, Language |

---

## 13. ESTADO DEL FRONTEND

Los 7 gaps priorizados que vivían acá (Alert card Nivel 2, estado de fallo en test de
cámara, Offline completo en Spaces/Space, "Why this mattered", empty state "Día 1",
flujos secundarios de Auth, pricing sin mención a clips) **ya están construidos.**
También: chat de pantalla completa exclusivo de mobile (`app/(app)/chat/page.tsx`),
los componentes nombrados en la sección 8 (`AlertBanner`, `StatusDot`, `ThreadCard`,
`SpaceCard`, `CameraStatus`, `ReasoningThread`, `ContextualLayers`), y una conexión
HTTP real entre el frontend y `backend/` (`frontend/lib/api.ts`) con fallback a
`mock-data.ts` cuando el servicio Python no está corriendo.

### Conexión frontend ↔ backend — estado real

- **Backend Python real**: `frontend/lib/api.ts` le pega directo a `backend/` (`GET
  /me`, `/spaces`, `POST /spaces`, `/spaces/test-connection`, `/activity`,
  `/contacts`) vía `NEXT_PUBLIC_ARTEMISA_API_URL`. Sin sesión de Clerk todavía, `GET
  /me` resuelve el usuario de demo fijo sembrado en `InMemoryStore`
  (`backend/main.py DEMO_USER_ID`). Cada función devuelve `{ok, data}` — el caller
  decide si cae a `mock-data.ts` cuando el fetch falla (backend no levantado, CORS,
  etc.), nunca tira. Wireado en: Onboarding (test de cámara — TCP real), Spaces
  (lista real de spaces), Space detail (busca el space por id en real + mock),
  Settings → Contactos (lista y alta real).
- **Supabase**: `frontend/lib/supabase/{client,server}.ts` existen y están listos
  (usan `@supabase/supabase-js`), pero inertes — devuelven `null` sin
  `NEXT_PUBLIC_SUPABASE_URL`/`SUPABASE_SERVICE_KEY` reales. Nada los llama todavía;
  la fuente de datos real hoy es el backend Python de arriba, no Supabase directo.
- **Clerk — deliberadamente NO wireado.** Instalar `@clerk/nextjs` y envolver
  `layout.tsx`/middleware sin keys reales tumba la app entera en cada request (a
  diferencia de Supabase, acá no hay fallback posible — es middleware de auth, no
  un cliente de datos). Login/Onboarding siguen siendo pantallas propias sin
  autenticación real hasta que existan `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` /
  `CLERK_SECRET_KEY` — ver `frontend/.env.local.example`.

### Explícitamente descartado

Emergency Overlay de pantalla completa con countdown animado. El dispatch corre
server-side vía Twilio, independiente de si la app está abierta. Un alert card alcanza.

---

## 14. ORDEN DE BUILD DEL BACKEND

```
FASE 1 — Paso 1: Motion detection
  Python + OpenCV, conexión RTSP, frame differencing,
  heartbeat adaptativo — construir desde el día 1

FASE 2 — Paso 2: Descripción
  GPT-4o mini vision, detail: low, frame descartado en memoria
  inmediatamente, escritura en `layers`

FASE 3 — Paso 2: Análisis
  Job cada ~60s, contexto completo inyectado, Groq Llama,
  output JSON estructurado, escritura en `threads`

FASE 4 — Paso 3: Razonamiento
  GPT-4.1 mini, los 4 triggers de activación, contexto extendido
  multi-espacio, determina nivel de acción final

FASE 5 — Paso 4: Acción / Twilio
  ⚠️ Sesión de trabajo SEPARADA — es la parte de mayor
  responsabilidad legal del producto. Requiere testing dedicado
  y la consulta legal resuelta antes de programarse.
```

---

## 15. TENSIONES ABIERTAS

**1. Scope del MVP** — falta una lista explícita de qué entra y qué queda post-beta.

**2. Legalidad del dispatch automatizado al 911** — sin resolver con abogado argentino.
El código ya está implementado (`dispatch_client.call_911()`), gateado por
`Settings.enable_911_autodial = False` por default — no requiere más trabajo de
ingeniería para "prender" el paso, solo la resolución legal. Si la respuesta es
restrictiva, sí puede cambiar la arquitectura del Nivel 4 (ej. sacar el paso
directamente en vez de solo apagarlo).

**3. Economía de unidad** — costo IA (~$4.70/mes por hogar) supera el pricing de beta.
Las 3 palancas están identificadas: heartbeat adaptativo, prompt caching, Batch API.

**4. Precisión del reconocimiento por patrón descriptivo** — solo la beta real lo valida.

---

## 16. CHECKLIST ANTES DE CADA COMMIT

- [ ] Componentes nuevos compuestos con shadcn primitivos
- [ ] No hay librería de UI nueva instalada
- [ ] Instrument Serif solo en headings (máx 1-2 por pantalla)
- [ ] El rojo solo aparece si hay Emergency / Nivel 4 activo
- [ ] Sin colores hardcodeados fuera de los tokens CSS
- [ ] Border radius correcto según escala
- [ ] Íconos Lucide con stroke-width={2}
- [ ] Copy suena humano, no técnico
- [ ] Sin "Ver video" — siempre "Ver momento"
- [ ] Tipos TypeScript sincronizados con backend Python
- [ ] RTSP URLs no llegan al cliente
- [ ] layers y threads sin blob/bytea
- [ ] Teléfonos en formato E.164
- [ ] prefers-reduced-motion respetado en animaciones

---

## Figma

Referencia visual del diseño real: https://www.figma.com/design/oOi3o5nMg4UqxG8UlmLDkO/artemisa?node-id=4006-1035
