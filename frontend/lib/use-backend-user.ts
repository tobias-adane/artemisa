'use client';

import { useEffect, useState } from 'react';
import { getMe } from '@/lib/api';
import { mockUser } from '@/lib/mock-data';

/**
 * Resuelve el user_id para llamar al backend Python. Sin Clerk todavía
 * no hay sesión real — GET /me devuelve el usuario de demo sembrado en
 * InMemoryStore (ver backend/main.py). Si el backend no está corriendo
 * (deploy solo-frontend, o simplemente no se levantó en dev), cae a
 * mockUser.id y `available: false` para que el caller no intente pegarle
 * al resto de los endpoints y use frontend/lib/mock-data.ts directo.
 */
export function useBackendUser() {
  const [userId, setUserId] = useState(mockUser.id);
  const [available, setAvailable] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getMe().then((res) => {
      if (cancelled) return;
      if (res.ok) {
        setUserId(res.data.id);
        setAvailable(true);
      }
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return { userId, available, loading };
}
