import { createClient, type SupabaseClient } from '@supabase/supabase-js';

/**
 * Cliente de Supabase para server components / route handlers. Usa la
 * service key — NUNCA importar este archivo desde un componente
 * marcado 'use client' (esa key nunca debe llegar al browser).
 *
 * Inerte hasta que existan SUPABASE_URL y SUPABASE_SERVICE_KEY reales
 * — ver .env.local.example. Sin esas env vars, devuelve null en vez
 * de tirar, igual que backend/clients/store.py cae a InMemoryStore
 * cuando faltan las mismas credenciales del lado Python.
 */
export function getSupabaseServerClient(): SupabaseClient | null {
  const url = process.env.SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_KEY;

  if (!url || !serviceKey) return null;
  return createClient(url, serviceKey, { auth: { persistSession: false } });
}
