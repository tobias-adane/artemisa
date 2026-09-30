-- Fase 0: schema completo según docs/05-DATOS.md.

-- Enums

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

-- Tablas

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

create table bridge_secrets (
  bridge_id  uuid primary key references bridges(id) on delete cascade,
  token_hash text                    -- sha256 del token del bridge
);

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

-- Reglas de acción, en la base

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

create table devices (
  id              uuid primary key default gen_random_uuid(),
  user_id         text not null references users(id) on delete cascade,
  expo_push_token text not null unique,
  platform        text not null check (platform in ('ios', 'android')),
  last_seen_at    timestamptz not null default now(),
  created_at      timestamptz not null default now()
);

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

-- Instrumentación. Solo métricas: nunca prompts, respuestas ni imágenes.
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

-- updated_at

create function set_updated_at() returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

create trigger users_updated_at      before update on users            for each row execute function set_updated_at();
create trigger prefs_updated_at      before update on user_preferences for each row execute function set_updated_at();
create trigger threads_updated_at    before update on threads          for each row execute function set_updated_at();
create trigger dispatches_updated_at before update on dispatches       for each row execute function set_updated_at();

-- Seguridad a nivel de fila

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

-- Tiempo real

alter publication supabase_realtime add table threads, layers, spaces, dispatches, bridges;
