# Artemisa — Frontend (Next.js)

## Qué es esto

Artemisa es una plataforma de inteligencia para el hogar. Se conecta
a cámaras IP existentes del usuario, analiza la actividad en tiempo
real mediante un pipeline de IA, y ejecuta acciones automatizadas
(notificaciones, llamadas, emergencia). **No almacena video, imágenes
ni audio. Nunca.**

Beta lanza en Argentina — **toda la UI en español rioplatense** (voseo:
"tenés", "podés", no "tienes"/"puedes"). Prefijo de teléfono default
en Onboarding/Settings: `+54`.

**Fuente de verdad del schema:** `docs/ARTEMISA_03_DATOS.md` y
`frontend/lib/types/artemisa-types.ts`. Si algo acá contradice esos
dos archivos, ganan ellos.

**Referencia visual:** `frontend/design-reference/*.dc.html` — los
mockups aprobados (formato Claude Design). Sirven como especificación
de layout/interacción para traducir a componentes reales, no se
importan ni se ejecutan tal cual.

---

## Stack

```
Framework:   Next.js 14 (App Router, TypeScript)
UI:          shadcn/ui — style: "maia", preset: bbVJxce, baseColor: neutral, cssVariables: true
AI Elements: @ai-elements/attachments (Vercel AI SDK components)
Icons:       lucide-react — stroke-width: 2, stroke: currentColor, fill: none
Auth:        Clerk (useUser, useAuth, middleware)
DB:          Supabase (PostgreSQL + real-time subscriptions)
Hosting:     Vercel
Errors:      Sentry
```

### Inicialización del proyecto (una sola vez)

```bash
npx shadcn@latest init --preset bbVJxce --template next
npx shadcn@latest add @ai-elements/attachments
```

### `components.json`

```json
{
  "style": "maia",
  "tailwind": {
    "baseColor": "neutral",
    "cssVariables": true,
    "chartColor": "neutral"
  },
  "iconLibrary": "lucide"
}
```

---

## Tokens CSS oficiales de Artemisa (shadcn)

**No modificar sin decisión explícita de diseño.**

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
  --chart-1: oklch(0.87 0 0);
  --chart-2: oklch(0.556 0 0);
  --chart-3: oklch(0.439 0 0);
  --chart-4: oklch(0.371 0 0);
  --chart-5: oklch(0.269 0 0);
  --radius: 0.875rem;  /* xl — usar siempre esta variable */
  --sidebar: oklch(0.985 0 0);
  --sidebar-foreground: oklch(0.145 0 0);
  --sidebar-primary: oklch(0.205 0 0);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.97 0 0);
  --sidebar-accent-foreground: oklch(0.205 0 0);
  --sidebar-border: oklch(0.922 0 0);
  --sidebar-ring: oklch(0.708 0 0);
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
  --chart-1: oklch(0.87 0 0);
  --chart-2: oklch(0.556 0 0);
  --chart-3: oklch(0.439 0 0);
  --chart-4: oklch(0.371 0 0);
  --chart-5: oklch(0.269 0 0);
  --sidebar: oklch(0.205 0 0);
  --sidebar-foreground: oklch(0.985 0 0);
  --sidebar-primary: oklch(0.488 0.243 264.376);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.269 0 0);
  --sidebar-accent-foreground: oklch(0.985 0 0);
  --sidebar-border: oklch(1 0 0 / 10%);
  --sidebar-ring: oklch(0.556 0 0);
}
```

**Tokens de estado de Artemisa** (agregar a globals.css):

```css
:root {
  --status-normal:     #22c55e;
  --status-attention:  #d08700;
  --status-emergency:  #dc2626;
  --status-offline:    #737373;
}
```

⚠️ Los mockups en `design-reference/` usan `#34c759` / `#ffcc00` como
placeholders de active/alert — **no son los tokens oficiales.** Al
traducir a componentes reales, usar siempre los 4 de arriba.

---

## Componentes — reglas de uso

### Regla principal: shadcn primero, siempre

```
✅ Siempre usar componentes de shadcn/ui:
   Button, Card, Input, Badge, Dialog, Sheet, Tabs, Avatar, etc.

✅ Si necesitás un componente que shadcn no tiene:
   → Construirlo COMPONIENDO primitivos de shadcn + tokens CSS del tema
   → Nunca crear estilos desde cero con clases hardcodeadas

✅ Para el chat y adjuntos:
   → Usar @ai-elements/attachments (npx shadcn@latest add @ai-elements/attachments)

❌ NUNCA:
   → Instalar otra librería de componentes (MUI, Chakra, Radix directo, etc.)
   → Usar colores hardcodeados en JSX — siempre variables CSS o clases Tailwind del tema
   → Crear un componente visual desde cero si ya existe en shadcn
```

### Menú / navegación

- **Estilo:** `default` / `solid`
- **Accent:** `subtle` (usar `--accent` / `--accent-foreground`, no `--primary`)
- Sidebar usa los tokens `--sidebar-*` exclusivamente

### Agregar componentes

```bash
npx shadcn@latest add <nombre>
npx shadcn@latest add @ai-elements/attachments
```

---

## Tipografía

| Rol      | Familia                              | Cuándo                                    |
|----------|---------------------------------------|-------------------------------------------|
| Headings | `'Instrument Serif', Georgia, serif` | SOLO títulos de pantalla. Máximo 1-2 por pantalla. |
| Todo lo demás | `'Inter', -apple-system, sans-serif` | Labels, botones, inputs, nav, body, descripciones |

```css
body {
  font-family: 'Inter', -apple-system, sans-serif;
}

.heading-display {
  font-family: 'Instrument Serif', Georgia, serif;
  font-weight: 400;
}
```

**Instrument Serif nunca en:** botones, labels, badges, navegación,
inputs, body text.

---

## Border radius

`--radius: 0.875rem` (= `rounded-xl`) es la base.

```
rounded-sm  (8px)   → chips, badges pequeños
rounded-xl  (14px)  → inputs, botones, items de lista
rounded-2xl (24px)  → cards contenedoras
rounded-3xl (30px)  → cards grandes, modales, drawers
rounded-full        → pills de estado, avatares
```

**Nunca usar `rounded` (4px) ni `rounded-sm` en cards o containers.**

---

## Colores de estado — los únicos acentos permitidos

```
Normal:    #22c55e / var(--status-normal)    → dots, pills "Todo bien"
Attention: #d08700 / var(--status-attention) → badges Nivel 2/3
Emergency: #dc2626 / var(--status-emergency) → EXCLUSIVO Nivel 4
Offline:   #737373 / var(--status-offline)   → cámaras/espacios offline
```

### ⚠️ REGLA DEL ROJO — CRÍTICA

`#dc2626` es **exclusivo de Emergency / Nivel 4**.

```
❌ NUNCA rojo para:
   - Botones "Eliminar" / "Remover" / acciones destructivas genéricas
   - Botón "Cancelar alerta" (es la acción SEGURA — usar outline/secondary)
   - El destructive de shadcn por defecto — no asumir que aplica acá

✅ SOLO rojo para:
   - Cards con estado Emergency activo (Nivel 4)
   - Indicador dot de clasificación "emergency"
   - Badge de nivel de alerta = 4
```

Nivel 3 (contactar) usa el color `attention` (`#d08700`), no rojo —
no llama al 911, aunque sí dispare Twilio hacia un contacto de
confianza.

Para acciones destructivas genéricas (eliminar contacto, etc.) usar
`variant="outline"` con texto en `--muted-foreground`. No rojo.

---

## Estructura de carpetas (App Router)

```
app/
  (auth)/          login, signup, forgot-password, verify-email
  (onboarding)/    steps 1-6
  (app)/
    home/          dashboard principal (desktop: incluye el chat como estado, no ruta aparte)
    chat/          SOLO mobile — send() navega acá en vez de expandir el chat inline en Home. Construido (lib/use-chat.ts).
    activity/      historial de eventos
    spaces/        lista de espacios (MVP: 1 space = 1 cámara)
    spaces/[id]/   detalle de espacio
    settings/      cuenta, plan, contactos de emergencia
  api/             route handlers
components/
  ui/              shadcn primitives (auto-generados por CLI)
  artemisa/        componentes del producto — compuestos de shadcn
lib/
  supabase/        client, server, middleware helpers
  types/           artemisa-types.ts — sincronizado con backend Python
```

---

## Tipos TypeScript

Ver `frontend/lib/types/artemisa-types.ts` — es el archivo completo y
autoritativo. No lo dupliques acá.

**RTSP:** `Space.camera_url` nunca debe llegar al cliente. Cualquier
query de Supabase desde el frontend usa el shape `SpacePublic`
(`Omit<Space, 'camera_url'>`), proyectando columnas explícitamente —
nunca `select('*')` sobre `spaces`.

---

## Pantallas — estado del diseño

Referencia visual en `frontend/design-reference/`:
`Auth · Onboarding · Home (incluye Chat) · Activity · Spaces · Space
· Settings · AvatarMenu`.

### Estados sin mockup propio — ya construidos siguiendo el estilo maia

Ninguno de estos existe en los `.dc.html` (no había mockup de referencia), pero ya
están implementados en el código real:

1. **Alert card Nivel 2 (Attention)** — `components/artemisa/alert-banner.tsx`.
   Card blanca simple: ícono de estado + título + descripción. Sin dispatch, sin
   llamada. En Home/Activity.
2. **Estado de fallo en test de conexión de cámara** (Onboarding) — `idle /
   testing / ok / error`, con reintento sin perder el resto del formulario. Wireado
   contra el backend real (`POST /spaces/test-connection`) con fallback simulado si
   el servicio Python no está corriendo.
3. **Estado "Offline" completo** en Spaces/Space — card con botón "Reconectar"
   cuando una cámara activa se cae. Tono calmo: una cámara caída no es una
   emergencia.
4. **"Por qué importó"** ("Why this mattered") — bloque colapsable bajo la
   descripción en Activity, ahora con el `ReasoningThread` de 4 nodos completo
   (no solo el texto de `Thread.reasoning`).
5. **Empty state "Día 1"** — Home/Activity cuando terminó el onboarding pero
   todavía no hay threads (`lib/day1.ts`, flag por sessionStorage seteado al
   terminar Onboarding).
6. **Auth — flujos secundarios** — forgot password completo, verificación por
   código.
7. **Pricing en Settings** — ARS, tiers Founding / Premium, sin ninguna mención a
   clips/grabación.

### Explícitamente descartado — no construir

**Emergency Overlay de pantalla completa con countdown animado.** El
dispatch real corre server-side vía Twilio, independiente de si la
app está abierta. Un alert card simple alcanza para el reconocimiento
in-app.

---

## Copy — reglas duras

```
❌ NUNCA en la UI:
   "AI" / "inteligencia artificial" / "modelo" / "vision model"
   "Movimiento detectado en cámara 3"
   "Persona detectada"
   "Sin eventos registrados"
   "Procesando..." (en tono técnico)

✅ Siempre voz humana de Artemisa, en español rioplatense (voseo):
   "Tu hija llegó hace 15 minutos. Está en su habitación."
   "Llegó tu marido."
   "No pasó nada importante desde que te fuiste."
```

### Copy validado (traducción del set aprobado — usar estas versiones, no el inglés)

```
"Buen día, [nombre] — Todo está en orden en casa."
"Tu casa está sola ahora mismo. Todo tranquilo."
"Un día tranquilo."
"La puerta de entrada está cerrada. Todo en calma."
"Preguntá lo que quieras sobre tu casa"
"¿Cómo está mi familia?" / "¿Qué está pasando en casa?" / "Actividad reciente"
```

---

## Backend Python — conexión real

`lib/api.ts` es el cliente HTTP contra `backend/` (ver `backend/api/routes.py`).
Cada función devuelve `{ok, data} | {ok:false, error}` en vez de tirar — el caller
decide si cae a `lib/mock-data.ts` cuando el fetch falla (backend no levantado,
CORS, etc.). `lib/use-backend-user.ts` resuelve el `user_id` vía `GET /me` (usuario
de demo fijo sembrado en `InMemoryStore` — no hay sesión de Clerk real todavía).
Wireado en Onboarding (test de cámara), Spaces, Space detail y Settings →
Contactos. Ver `NEXT_PUBLIC_ARTEMISA_API_URL` en `.env.local.example`.

---

## Supabase — real-time

```typescript
const channel = supabase
  .channel('threads')
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'threads',
    filter: `space_id=eq.${spaceId}`,
  }, (payload) => {
    // actualizar estado local
  })
  .subscribe();

return () => { supabase.removeChannel(channel); };
```

---

## Clerk — auth

```typescript
// Server components
import { auth, currentUser } from '@clerk/nextjs/server';

// Client components
import { useUser, useAuth } from '@clerk/nextjs';
```

**No wireado todavía.** `@clerk/nextjs` no está instalado ni hay
provider/middleware — sin `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` /
`CLERK_SECRET_KEY` reales, el middleware de Clerk tira en cada
request y tumba la app entera (a diferencia de Supabase, acá no hay
fallback posible). Login/Onboarding son pantallas propias sin
autenticación real por ahora — `lib/use-backend-user.ts` resuelve un
usuario de demo fijo en su lugar (ver sección "Backend Python" arriba).

---

## Checklist antes de hacer un commit

- [ ] ¿Todos los componentes nuevos están construidos con shadcn primitivos?
- [ ] ¿No hay ninguna librería de UI nueva instalada?
- [ ] ¿Instrument Serif SOLO en headings (máx 1-2 por pantalla)?
- [ ] ¿El rojo solo aparece si hay Emergency / Nivel 4 activo?
- [ ] ¿Ningún color hardcodeado fuera de los tokens CSS del tema (ni los del mockup viejo)?
- [ ] ¿El radius usa `--radius` o las clases `rounded-xl/2xl/3xl`?
- [ ] ¿Los íconos son Lucide con `stroke-width={2}`?
- [ ] ¿El copy está en español rioplatense (voseo) y suena humano, no técnico?
- [ ] ¿Los tipos TypeScript están sincronizados con `artemisa_models.py` y con `docs/ARTEMISA_03_DATOS.md`?
- [ ] ¿`spaces.camera_url` no llega al cliente en ningún query/response?

---

## Comandos frecuentes

```bash
npm run dev
npm run build
npm run lint
npx shadcn@latest add <component>
npx shadcn@latest add @ai-elements/attachments
```

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
