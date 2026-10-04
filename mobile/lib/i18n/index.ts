import { getLocales } from 'expo-localization';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './en.json';
import esAR from './es-AR.json';

export type Locale = 'en' | 'es-AR';

// Sin usuario todavía: el idioma del teléfono. Cualquier español usa es-AR.
export function deviceLocale(): Locale {
  const code = getLocales()[0]?.languageCode;
  return code === 'es' ? 'es-AR' : 'en';
}

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    'es-AR': { translation: esAR },
  },
  lng: deviceLocale(),
  fallbackLng: 'en',
  interpolation: { prefix: '{', suffix: '}', escapeValue: false },
  returnNull: false,
});

export default i18n;
