-- Simula lo mínimo de Supabase que pide la migración; solo para el CI, no se usa fuera de él.
do $$
begin
  if not exists (select from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
  if not exists (select from pg_publication where pubname = 'supabase_realtime') then create publication supabase_realtime; end if;
end $$;
create schema if not exists auth;
create or replace function auth.jwt() returns jsonb language sql stable
  as $$ select coalesce(nullif(current_setting('request.jwt.claims', true), ''), '{}')::jsonb $$;
