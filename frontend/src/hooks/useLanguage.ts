/**
 * Language / i18n hook for Nyaya Sahayak.
 * Manages language state and provides translation lookup.
 */

import { useCallback, useState } from 'react';
import type { Language, Translations, TranslationSection } from '../types';
import enStrings from '../i18n/en.json';
import hiStrings from '../i18n/hi.json';

const translations: Record<Language, Translations> = {
  en: enStrings as Translations,
  hi: hiStrings as Translations,
};

export function useLanguage() {
  const [language, setLanguage] = useState<Language>('en');

  const t = useCallback(
    (section: keyof Translations, key: string): string => {
      const sectionData: TranslationSection | undefined = translations[language]?.[section];
      if (sectionData && key in sectionData) {
        return sectionData[key] || key;
      }
      // Fallback to English
      const fallback: TranslationSection | undefined = translations.en?.[section];
      if (fallback && key in fallback) {
        return fallback[key] || key;
      }
      return key;
    },
    [language]
  );

  const toggleLanguage = useCallback(() => {
    setLanguage((prev) => (prev === 'en' ? 'hi' : 'en'));
  }, []);

  return { language, setLanguage, toggleLanguage, t };
}
