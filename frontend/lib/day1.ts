'use client';

import { useEffect, useState } from 'react';

/**
 * Señal de "Día 1": el usuario terminó el onboarding pero todavía no
 * hubo ningún thread real. Server-driven en producción (mockActivity
 * vacío); acá simulado con sessionStorage porque el frontend corre
 * sobre datos mock — ver onboarding/page.tsx (paso 'done').
 */
const DAY1_KEY = 'artemisa_day1';

export function markDay1() {
  try {
    sessionStorage.setItem(DAY1_KEY, '1');
  } catch {
    // sessionStorage puede no estar disponible (SSR, modo privado) — no es crítico.
  }
}

export function useDay1(): boolean {
  const [day1, setDay1] = useState(false);

  useEffect(() => {
    try {
      setDay1(sessionStorage.getItem(DAY1_KEY) === '1');
    } catch {
      setDay1(false);
    }
  }, []);

  return day1;
}
