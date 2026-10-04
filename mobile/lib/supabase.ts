import { createClient } from '@supabase/supabase-js';

// Fase 0, modo laboratorio: clave anónima del proyecto de laboratorio, sin
// inicio de sesión (docs/07-APP.md, Modo laboratorio). Sin sesión que guardar.
// Los tipos de la base (lib/types/db.ts) se suman en el paso 12.
const url = process.env.EXPO_PUBLIC_SUPABASE_URL;
const anonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  throw new Error('Missing EXPO_PUBLIC_SUPABASE_URL or EXPO_PUBLIC_SUPABASE_ANON_KEY');
}

export const supabase = createClient(url, anonKey, {
  auth: {
    persistSession: false,
    autoRefreshToken: false,
    detectSessionInUrl: false,
  },
});
