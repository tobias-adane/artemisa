'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { es } from './es';
import { en } from './en';
import type { Dictionary } from './es';

export type Locale = 'es' | 'en';

const DICTIONARIES: Record<Locale, Dictionary> = { es, en };
const STORAGE_KEY = 'artemisa_locale';

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  dict: Dictionary;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>('es');

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'es' || stored === 'en') setLocaleState(stored);
    } catch {
      // localStorage inaccesible (SSR/privado) — se queda en español.
    }
  }, []);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // No hay dónde persistir — el cambio igual aplica para esta sesión.
    }
  }, []);

  const value = useMemo<I18nContextValue>(
    () => ({ locale, setLocale, dict: DICTIONARIES[locale] }),
    [locale, setLocale]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n debe usarse dentro de <I18nProvider>');
  return ctx;
}

/** Interpolación simple de `{variable}` en strings del diccionario. */
export function format(template: string, vars: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (_, key) => vars[key] ?? `{${key}}`);
}
