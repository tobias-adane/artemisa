'use client';

import { createClient, type SupabaseClient } from '@supabase/supabase-js';

/**
 * Cliente de Supabase para componentes de cliente — real-time
 * subscriptions (ver frontend/CLAUDE.md, sección Supabase) y queries
 * de solo lectura sobre columnas públicas (nunca `select('*')` sobre
 * `spaces` — ese proyecta explícitamente SpacePublic).
 *
 * Inerte hasta que existan NEXT_PUBLIC_SUPABASE_URL y
 * NEXT_PUBLIC_SUPABASE_ANON_KEY reales — ver .env.local.example. Sin
 * esas env vars, `getSupabaseBrowserClient()` devuelve null en vez de
 * tirar, para que el resto de la UI pueda seguir funcionando contra
 * frontend/lib/mock-data.ts o el backend Python (ver lib/api.ts).
 */
let cached: SupabaseClient | null | undefined;

export function getSupabaseBrowserClient(): SupabaseClient | null {
  if (cached !== undefined) return cached;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  cached = url && anonKey ? createClient(url, anonKey) : null;
  return cached;
}
