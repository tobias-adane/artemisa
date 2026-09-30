# 05. Datos

## Principios

**Solo texto.** Ninguna tabla tiene columnas binarias (`bytea`) ni columnas que
guarden imágenes, frames, video, audio o referencias a archivos de cámara. Esto
se impone en el schema y además se verifica con un test (ver Guardas). La
grabación de la Fase 1 vive en el Cloud Bridge, cifrada; la base no guarda nada
de ella.

**Las credenciales de las cámaras no están en la base.** Las direcciones RTSP,
con su usuario y contraseña, viven solo en el Cloud Bridge, dentro de la casa. La
base de datos no tiene ninguna columna para ellas.

**El id del usuario es el id de Clerk.** Todas las tablas usan `user_id text`
con el id que emite Clerk (`user_...`). Así las políticas de seguridad comparan
directo contra el token, sin subconsultas.

**Los enums viven en Postgres.** Se definen como tipos `enum` en la base. Los
tipos de TypeScript se generan desde ahí y los de Python se verifican contra ahí.
Una sola fuente.

**Cada tabla y columna nace en su fase.** Lo que pertenece a fases posteriores
se agrega con una migración nueva en esa fase. **Única excepción:** los enums de
`dispatches` declaran desde la Fase 0 todo su vocabulario (llamadas, contactos,
servicios de emergencia), porque son el idioma del registro de acciones y
agregarlos de a poco no aporta nada. Declararlos no autoriza a escribir el
código que los usa antes de su fase.

**Supabase** es la base (PostgreSQL) y el canal de tiempo real hacia la app.

---

## Enums (Fase 0)

```sql
create type classification     as enum ('normal', 'attention', 'emergency');
create type action_level       as enum ('informar', 'alertar', 'contactar', 'emergencia');
create type thread_status      as enum ('composing', 'active', 'closed');
create type space_status       as enum ('pending', 'active', 'offline');
create type bridge_status      as enum ('online', 'offline');
create type layer_flag         as enum ('person_on_floor', 'smoke_or_fire', 'glass_broken',
                                        'door_forced', 'weapon_visible', 'water_leak');
create type dispatch_channel   as enum ('push', 'call', 'whatsapp');
create type dispatch_target    as enum ('owner', 'contact', 'emergency_services');
create type dispatch_status    as enum ('queued', 'sent', 'delivered', 'opened',
                                        'answered', 'no_answer', 'failed', 'cancelled');
create type push_interruption  as enum ('passive', 'time_sensitive', 'critical');
create type alert_sensitivity  as enum ('low', 'balanced', 'high');
create type home_type          as enum ('apartment', 'house', 'small_business');
create type pipeline_step      as enum ('describe', 'state', 'analyze', 'reason',
                                        'live_read', 'chat', 'tts');
create type message_role       as enum ('user', 'assistant');
```

---

## Tablas de la Fase 0

### `users`

```sql
create table users (
  id                  text primary key,              -- id de Clerk
  email               text,
  first_name          text,
  locale              text not null default 'en' check (locale in ('en', 'es-AR')),
  timezone            text not null default 'America/Argentina/Buenos_Aires',
  home_type           home_type,
  custom_instructions text not null default '',
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
```

`custom_instructions` es texto libre: la rutina de la casa que el usuario le
enseña a Artemisa. Es el insumo más importante del análisis. Sin esto, el Paso
2b clasifica a ciegas.

### `user_preferences`

```sql
create table user_preferences (
  user_id           text primary key references users(id) on delete cascade,
  alert_sensitivity alert_sensitivity not null default 'balanced',
  voice_enabled     boolean not null default true,
  quiet_hours_start time,                         -- null = sin quiet hours
  quiet_hours_end   time,
  night_start       time not null default '23:00',
  night_end         time not null default '06:00',
  updated_at        timestamptz not null default now()
);
```

### `bridges`

Una fila por Cloud Bridge. `user_id` es nulo desde que la caja se prepara hasta
que alguien la reclama (Fase 1).

```sql
create table bridges (
  id               uuid primary key default gen_random_uuid(),
  user_id          text references users(id) on delete cascade,
  name             text not null default 'Home',
  status           bridge_status not null default 'offline',
  version          text,
  last_seen_at     timestamptz,      -- último mensaje recibido por el canal de control
  connected_at     timestamptz,      -- última vez que abrió el canal (hello)
  offline_since    timestamptz,      -- desde cuándo no se la ve; null si está online
  offline_notified boolean not null default false,  -- se avisó push.homeBlind
  created_at       timestamptz not null default now()
);
```

`offline_since` en nulo con `status = 'offline'` quiere decir que la caja nunca
se conectó todavía: no es una casa sin señal (ver `03-ALGORITMO.md`).

### `bridge_secrets`

Los hashes que autentican a cada caja viven aparte, en una tabla que la app no
puede leer. `bridges` está en tiempo real y el usuario la lee; si los hashes
estuvieran ahí, viajarían a la app con cada cambio de estado.

```sql
create table bridge_secrets (
  bridge_id  uuid primary key references bridges(id) on delete cascade,
  token_hash text                    -- sha256 del token del bridge
);
```

### `spaces`

En la primera versión un space es exactamente una cámara.

```sql
create table spaces (
  id                uuid primary key default gen_random_uuid(),
  user_id           text not null references users(id) on delete cascade,
  bridge_id         uuid references bridges(id) on delete set null,
  name              text not null,
  status            space_status not null default 'pending',
  motion_threshold  real not null default 0.02
                    check (motion_threshold > 0 and motion_threshold < 1),
  state_description text,              -- lo último que se vio, en texto
  state_updated_at  timestamptz,
  people_present    boolean,           -- null = no se sabe
  last_motion_at    timestamptz,
  last_health_at    timestamptz,       -- solo reportes de salud positivos
  offline_since     timestamptz,
  offline_notified  boolean not null default false,
  created_at        timestamptz not null default now()
);
-- No hay columna para la dirección RTSP. Vive solo en el Cloud Bridge.
```

### `threads`

Un momento de un space en el tiempo. Es lo que la app muestra en la línea.

```sql
create table threads (
  id                     uuid primary key default gen_random_uuid(),
  user_id                text not null references users(id) on delete cascade,
  space_id               uuid not null references spaces(id) on delete cascade,
  status                 thread_status not null default 'composing',
  narrative              text,               -- null mientras está en composing
  classification         classification,     -- null mientras está en composing
  confidence             real check (confidence between 0 and 1),
  reasoning              text,               -- "Why I'm telling you"
  escalated_to_reasoning boolean not null default false,
  severity_high          boolean,            -- solo lo escribe el Paso 3
  action                 action_level,       -- nivel más alto al que se actuó
  people_present         boolean,
  unfamiliar_person      boolean not null default false,
  analysis_failures      int not null default 0,
  start_time             timestamptz not null,
  end_time               timestamptz,        -- el thread terminó: ya no recibe layers
  last_layer_at          timestamptz not null,
  last_analyzed_at       timestamptz,
  last_reasoned_at       timestamptz,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now(),

  constraint narrated_unless_composing
    check (status = 'composing' or (narrative is not null and classification is not null)),
  constraint closed_has_end
    check (status <> 'closed' or end_time is not null)
);

-- Como máximo un thread abierto por space, garantizado por la base.
create unique index threads_one_open_per_space
  on threads (space_id)
  where status in ('composing', 'active') and end_time is null;

create index threads_user_time on threads (user_id, start_time desc);
create index threads_unfinished on threads (status) where status in ('composing', 'active');
```

#### Reglas de acción, en la base

Un trigger valida cada vez que cambia `action`:

- el nivel solo sube;
- todo nivel por encima de `informar` requiere que el thread haya pasado por el
  Paso 3;
- `emergencia` requiere además `classification = emergency` y
  `severity_high = true`.

```sql
create function action_rank(a action_level) returns int
language sql immutable as $$
  select case a when 'informar' then 1 when 'alertar' then 2
                when 'contactar' then 3 when 'emergencia' then 4 else 0 end
$$;

create function enforce_action_rules() returns trigger
language plpgsql as $$
declare
  previous action_level;
begin
  if tg_op = 'UPDATE' then
    previous := old.action;
  end if;
  if new.action is distinct from previous then
    if action_rank(new.action) < action_rank(previous) then
      raise exception 'action level cannot decrease';
    end if;
    if action_rank(new.action) > 1 and new.escalated_to_reasoning is not true then
      raise exception 'actions above informar require reasoning';
    end if;
    if new.action = 'emergencia' and not (
         new.classification is not distinct from 'emergency'
         and new.severity_high is true) then
      raise exception 'emergencia requires emergency classification and severity_high';
    end if;
  end if;
  return new;
end $$;

create trigger threads_action_rules
  before insert or update on threads
  for each row execute function enforce_action_rules();
```

Las reglas se validan **en el momento de actuar**. Si después el Paso 3 baja la
clasificación de un thread en el que ya se actuó, la base lo permite: lo que se
hizo queda en `action` y en `dispatches`. Se usa `is true` y `is not distinct
from` a propósito: comparar contra un `null` con operadores simples da `null`, y
una condición en `null` deja pasar exactamente el caso que se quiere impedir.

### `layers`

Una observación factual de un frame. Es lo que la app muestra en "What I saw".

```sql
create table layers (
  id          uuid primary key default gen_random_uuid(),
  user_id     text not null references users(id) on delete cascade,
  thread_id   uuid not null references threads(id) on delete cascade,
  space_id    uuid not null references spaces(id) on delete cascade,
  description text not null check (length(description) <= 200),
  flags       layer_flag[] not null default '{}',
  captured_at timestamptz not null,       -- hora del frame, al segundo
  created_at  timestamptz not null default now()
);

create index layers_thread_time on layers (thread_id, captured_at);
```

### `dispatches`

Cada intento concreto de avisar a alguien sobre un thread. Es la fuente de "What
I did" y el registro auditable de lo que hizo Artemisa. Los avisos de sistema
(cámara sin conexión) no son dispatches.

```sql
create table dispatches (
  id           uuid primary key default gen_random_uuid(),
  user_id      text not null references users(id) on delete cascade,
  thread_id    uuid not null references threads(id) on delete cascade,
  level        action_level not null,
  channel      dispatch_channel not null,
  target       dispatch_target not null,
  interruption push_interruption,           -- solo para push
  status       dispatch_status not null default 'queued',
  provider_ref text,                        -- id del proveedor (push o llamada)
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create index dispatches_thread on dispatches (thread_id, created_at);
```

### `devices`

```sql
create table devices (
  id              uuid primary key default gen_random_uuid(),
  user_id         text not null references users(id) on delete cascade,
  expo_push_token text not null unique,
  platform        text not null check (platform in ('ios', 'android')),
  last_seen_at    timestamptz not null default now(),
  created_at      timestamptz not null default now()
);
```

### `conversations` y `messages`

```sql
create table conversations (
  id         uuid primary key default gen_random_uuid(),
  user_id    text not null references users(id) on delete cascade,
  thread_id  uuid references threads(id) on delete set null,  -- chat sobre un thread
  created_at timestamptz not null default now()
);

create table messages (
  id              uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references conversations(id) on delete cascade,
  user_id         text not null references users(id) on delete cascade,
  role            message_role not null,
  content         text not null,
  spoken          boolean not null default false,   -- la pregunta se hizo por voz
  created_at      timestamptz not null default now()
);

create index messages_conversation_time on messages (conversation_id, created_at);
```

### `pipeline_runs`

Instrumentación. **Solo métricas**: nunca prompts, respuestas ni imágenes.

```sql
create table pipeline_runs (
  id                  bigint generated always as identity primary key,
  user_id             text references users(id) on delete cascade,
  space_id            uuid references spaces(id) on delete set null,
  thread_id           uuid references threads(id) on delete set null,
  step                pipeline_step not null,
  role                text not null,      -- rol del registro de modelos
  provider            text not null,
  model               text not null,
  input_tokens        int,
  cached_input_tokens int,
  visual_tokens       int,                -- tokens cobrados por la imagen
  output_tokens       int,
  reasoning_tokens    int,
  cost_usd            numeric(12, 8),
  latency_ms          int,
  ok                  boolean not null,
  error               text,
  created_at          timestamptz not null default now()
);

create index pipeline_runs_time on pipeline_runs (created_at);
```

### `updated_at`

```sql
create function set_updated_at() returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

create trigger users_updated_at      before update on users            for each row execute function set_updated_at();
create trigger prefs_updated_at      before update on user_preferences for each row execute function set_updated_at();
create trigger threads_updated_at    before update on threads          for each row execute function set_updated_at();
create trigger dispatches_updated_at before update on dispatches       for each row execute function set_updated_at();
```

---

## Migraciones de fases posteriores

### Fase 1: preparación y emparejamiento del Cloud Bridge

```sql
alter table bridge_secrets
  add column registration_secret_hash text,  -- sha256 del secreto que recibe la caja al prepararse; se borra al entregar el token
  add column pairing_code_hash        text;  -- sha256 del código del QR de la etiqueta; se borra al reclamarla

alter table bridges
  add column claimed_at timestamptz;
```

El código del QR no vence (ver `06-ARQUITECTURA.md`, Preparación de cada caja).
Por eso no hay columna de vencimiento, el código es largo y el reclamo tiene
límite de intentos.

### Fase 2b: contactos y emergencias

```sql
create type contact_relationship as enum ('spouse_partner', 'parent', 'sibling',
                                          'friend', 'neighbor', 'other');

create table emergency_contacts (
  id                   uuid primary key default gen_random_uuid(),
  user_id              text not null references users(id) on delete cascade,
  name                 text not null,
  phone                text not null check (phone ~ '^\+[1-9][0-9]{7,14}$'),  -- E.164
  relationship         contact_relationship not null,
  priority             int not null check (priority >= 1),   -- 1 = primero
  consent_confirmed_at timestamptz,   -- el contacto aceptó recibir llamadas de Artemisa
  created_at           timestamptz not null default now(),
  unique (user_id, priority)
);

alter table dispatches
  add column contact_id uuid references emergency_contacts(id) on delete set null;

alter table user_preferences
  add column cancel_timer_seconds int not null default 30
    check (cancel_timer_seconds between 10 and 120);
```

Los teléfonos van en formato E.164 (`+5491122334455`), que es el que exige el
proveedor de llamadas. La app valida el formato antes de guardar.

---

## Seguridad a nivel de fila (RLS)

Todas las tablas tienen RLS activo. La app se autentica con el token de Clerk
(Supabase lo acepta como proveedor de autenticación externo) y el id del usuario
se lee de `auth.jwt()->>'sub'`.

La API y el worker usan la clave de servicio y no pasan por RLS.

```sql
alter table users            enable row level security;
alter table user_preferences enable row level security;
alter table bridges          enable row level security;
alter table bridge_secrets   enable row level security;
alter table spaces           enable row level security;
alter table threads          enable row level security;
alter table layers           enable row level security;
alter table dispatches       enable row level security;
alter table devices          enable row level security;
alter table conversations    enable row level security;
alter table messages         enable row level security;
alter table pipeline_runs    enable row level security;

-- Lectura de lo propio
create policy own_read on users            for select to authenticated using (id = auth.jwt()->>'sub');
create policy own_read on user_preferences for select to authenticated using (user_id = auth.jwt()->>'sub');
create policy own_read on bridges          for select to authenticated using (user_id = auth.jwt()->>'sub');
create policy own_read on spaces           for select to authenticated using (user_id = auth.jwt()->>'sub');
create policy own_read on threads          for select to authenticated using (user_id = auth.jwt()->>'sub');
create policy own_read on layers           for select to authenticated using (user_id = auth.jwt()->>'sub');
create policy own_read on dispatches       for select to authenticated using (user_id = auth.jwt()->>'sub');
create policy own_read on conversations    for select to authenticated using (user_id = auth.jwt()->>'sub');
create policy own_read on messages         for select to authenticated using (user_id = auth.jwt()->>'sub');

-- Escritura acotada: solo lo que el usuario edita directo desde la app
create policy own_update on users for update to authenticated
  using (id = auth.jwt()->>'sub') with check (id = auth.jwt()->>'sub');
revoke update on users from authenticated;
grant update (first_name, locale, timezone, home_type, custom_instructions)
  on users to authenticated;

create policy own_update on user_preferences for update to authenticated
  using (user_id = auth.jwt()->>'sub') with check (user_id = auth.jwt()->>'sub');
revoke update on user_preferences from authenticated;
grant update (alert_sensitivity, voice_enabled, quiet_hours_start, quiet_hours_end,
              night_start, night_end)
  on user_preferences to authenticated;

-- devices, pipeline_runs y bridge_secrets: sin políticas para authenticated. Solo la API.
-- threads, layers, spaces, dispatches, messages: solo la API escribe.
```

Todo lo demás (crear spaces, registrar dispositivos, chatear, emparejar el
Cloud Bridge) pasa por la API, que valida y escribe con la clave de servicio.

### Laboratorio (Fase 0)

La Fase 0 corre sin cuentas. Usa **un proyecto de Supabase separado del de
producción**, con un usuario fijo (`user_lab`) y una migración adicional en
`supabase/lab_only/`:

- políticas de lectura con la clave anónima solo para ese usuario;
- la fila del usuario de laboratorio, sus preferencias, y un bridge, con el
  hash de `LAB_BRIDGE_TOKEN` en su fila de `bridge_secrets`.

```sql
create policy lab_read on threads for select to anon using (user_id = 'user_lab');
-- idem para bridges, spaces, layers, dispatches, messages, conversations, users, user_preferences
```

La carpeta `supabase/lab_only/` nunca se aplica en el proyecto de producción.

---

## Tiempo real

```sql
alter publication supabase_realtime add table threads, layers, spaces, dispatches, bridges;
```

La app escucha **INSERT y UPDATE** en `threads` (un thread nace en composing y se
actualiza al tener narrativa), UPDATE en `spaces` (estado de las cámaras) y
UPDATE en `bridges` (si el Cloud Bridge tiene señal).
Mientras el detalle de un thread está abierto, escucha INSERT en `layers` e
**INSERT y UPDATE** en `dispatches` de ese thread (una llamada pasa de enviada a
atendida o no atendida). Los eventos respetan RLS: cada usuario recibe solo lo
suyo.

---

## Tipos en TypeScript

Los tipos de la base se generan, no se escriben a mano:

```bash
npx supabase gen types typescript --project-id <id> > mobile/lib/types/db.ts
```

Encima, un archivo de tipos de dominio:

```ts
// mobile/lib/types/domain.ts
import type { Database } from "./db";

type Row<T extends keyof Database["public"]["Tables"]> =
  Database["public"]["Tables"][T]["Row"];
type Enum<T extends keyof Database["public"]["Enums"]> =
  Database["public"]["Enums"][T];

export type Classification = Enum<"classification">;
export type ActionLevel = Enum<"action_level">;
export type ThreadStatus = Enum<"thread_status">;
export type SpaceStatus = Enum<"space_status">;
export type BridgeStatus = Enum<"bridge_status">;

export type Thread = Row<"threads">;
export type Layer = Row<"layers">;
export type Space = Row<"spaces">;
export type Bridge = Row<"bridges">;
export type Dispatch = Row<"dispatches">;
export type Message = Row<"messages">;

export type ComposingThread = Thread & {
  status: "composing"; narrative: null; classification: null;
};
export type NarratedThread = Thread & {
  status: "active" | "closed"; narrative: string; classification: Classification;
};

export const isComposing = (t: Thread): t is ComposingThread =>
  t.status === "composing";
```

### "What I did" en la app

Se arma **solo** a partir de `dispatches`. Si el nivel era `contactar` pero en
esta fase solo se mandó una notificación, dice que se mandó una notificación.
Las claves de texto están en `02-PRODUCTO.md`.

Esta es la función completa. En las Fases 0 y 1 solo se implementan las ramas de
notificaciones; las de llamadas se agregan en la Fase 2a y las de contactos y
emergencias en la Fase 2b.

```ts
// mobile/lib/what-i-did.ts
const RANK: Record<ActionLevel, number> =
  { informar: 1, alertar: 2, contactar: 3, emergencia: 4 };

export function whatIDid(dispatches: Dispatch[], t: TFunction,
                         time: (iso: string) => string): string[] {
  const ds = [...dispatches].sort((a, b) => a.created_at.localeCompare(b.created_at));
  const lines: string[] = [];

  for (const d of ds) {
    if (d.status === "queued" || d.status === "cancelled") continue;
    if (d.channel === "push") {
      if (d.status === "failed") lines.push(t("did.pushFailed"));
      else lines.push(d.interruption === "passive"
        ? t("did.pushQuiet")
        : t("did.pushAlert", { time: time(d.created_at) }));
    } else if (d.channel === "call" && d.target === "owner") {          // Fase 2a
      if (d.status === "answered") lines.push(t("did.calledYou", { time: time(d.created_at) }));
      if (d.status === "no_answer") lines.push(t("did.calledYouNoAnswer", { time: time(d.created_at) }));
    } else if (d.target === "contact" && d.status !== "failed") {       // Fase 2b
      lines.push(d.channel === "call"
        ? t("did.calledContact", { name: contactName(d) })
        : t("did.messagedContact", { name: contactName(d) }));
    } else if (d.target === "emergency_services" && d.status !== "failed") {  // Fase 2b
      lines.push(t("did.emergencyServices", { time: time(d.created_at) }));
    }
  }

  const cancelled = ds.find(d => d.status === "cancelled");
  if (cancelled) lines.push(t("did.cancelled", { time: time(cancelled.updated_at) }));

  if (lines.length === 0) return [t("did.nothing")];

  const reached = ds.filter(d => !["queued", "failed", "cancelled"].includes(d.status));
  const maxLevel = Math.max(0, ...reached.map(d => RANK[d.level]));
  const reachedOthers = reached.some(d => d.target !== "owner");
  if (maxLevel >= RANK.alertar && !reachedOthers && !cancelled) {
    lines.push(t("did.noOneElse"));
  }
  return [...new Set(lines)];
}
```

---

## Modelos en Python

`server/artemisa/core/models.py` define modelos Pydantic para las filas que el
backend escribe, y los enums espejo de los de Postgres:

```python
from enum import Enum

class Classification(str, Enum):
    normal = "normal"
    attention = "attention"
    emergency = "emergency"

class ActionLevel(str, Enum):
    informar = "informar"
    alertar = "alertar"
    contactar = "contactar"
    emergencia = "emergencia"

class ThreadStatus(str, Enum):
    composing = "composing"
    active = "active"
    closed = "closed"
# ...un enum por cada tipo de Postgres
```

Un test compara cada enum de Python con los valores reales del tipo en Postgres
(`select unnest(enum_range(null::classification))`) y falla si difieren.

### Resolución del nivel de acción

Vive solo en el servidor. La app nunca decide niveles.

```python
def resolve_action_level(c: Classification, severity_high: bool) -> ActionLevel | None:
    match c:
        case Classification.normal:
            return None
        case Classification.attention:
            return ActionLevel.alertar if severity_high else ActionLevel.informar
        case Classification.emergency:
            return ActionLevel.emergencia if severity_high else ActionLevel.contactar
    raise AssertionError(f"classification sin manejar: {c}")
```

Un test recorre la tabla completa: 3 clasificaciones × 2 valores de severidad.

---

## Qué no se guarda nunca en la nube

- Frames, imágenes, video, clips, miniaturas. Tampoco los frames que el bridge
  entrega cada segundo para el Paso 1: viven en memoria hasta que llega el
  siguiente.
- La grabación de la Fase 1: queda en el Cloud Bridge, cifrada, y solo se ve
  en el teléfono del dueño.
- Direcciones RTSP y credenciales de cámaras (viven solo en el Cloud Bridge).
- Las cámaras que el Cloud Bridge encuentra en la red.
- Segmentos del stream en vivo (existen en memoria del relay, segundos).
- Audio del micrófono (la voz a texto corre en el teléfono).
- Audio generado por la voz de Artemisa (se cachea en memoria).
- Prompts, respuestas crudas y razonamiento interno de los modelos. Solo se
  guarda lo que se convierte en layers, threads o mensajes.

La única excepción es la herramienta de laboratorio `DEBUG_SAVE_FRAMES`, que
existe solo en el código de `artemisa/lab/`, solo en la máquina del laboratorio,
y desaparece antes de la Fase 1 (ver `08-CONSTRUCCION.md`).

### Guardas

- Un test lee todas las migraciones y falla si aparece `bytea`, o una columna
  cuyo nombre contenga `image`, `frame`, `video`, `clip`, `snapshot`, `jpeg`,
  `rtsp` o `password`.
- Un test de la API verifica que el endpoint de frames no escribe nada a disco:
  corre con el sistema de archivos de solo lectura (salvo el directorio de logs)
  y revisa que ningún log contenga bytes de imagen. Corre sobre la API, que no
  incluye el código de laboratorio.

---

## Retención

**Propuesta, a confirmar con asesoría legal:**

| Dato | Se conserva |
|---|---|
| `layers` | 90 días |
| `threads`, `dispatches` | 12 meses |
| `messages` | 12 meses |
| `pipeline_runs` | 180 días |

A partir de la Fase 1, un job diario del worker borra lo vencido. El usuario
puede borrar todo el historial de su casa en cualquier momento (pantalla
pendiente de diseño). Borrar la cuenta borra todo en cascada.

---

## Datos de demo

`server/artemisa/lab/seed_demo.py` carga el hogar de demo relativo al día de
hoy, en la zona horaria del usuario:

- Usuario `user_lab`, nombre "Alexander", idioma `en`, con las custom
  instructions de ejemplo de `02-PRODUCTO.md`.
- Spaces: Kitchen, Driveway, Living Room, Front Door.
- Los 13 threads del día de demo de `02-PRODUCTO.md`, todos `closed` y `normal`,
  con su narrativa y un razonamiento breve.
- Los 3 layers del thread de las 11:20 AM, con sus segundos exactos.
- Opcional, con un flag del script: el thread de las 3:35 PM como `attention`.
