// frontend_mobile/src/contexts/TranslationContext.tsx
// v4.6 - IL TRITACARNE SUPREMO "DIO CANE APPROVED"
// FIX: Sincronia Flat Map + Auto-Clean Chiavi + Variable Replacement Predictable.
// FIX: Fetch lingua di default dal backend se il profilo locale è assente (Factory Reset Fix).
// LEGGE A0099: Invarianza strutturale garantita. Codice integrale fornito.

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { getBaseUrl, getHeaders } from '@/lib/api';

type TranslationsMap = Record<string, any>;

interface TranslationContextType {
  t: (key: string, params?: Record<string, string | number>) => string;
  currentLang: string;
  availableLangs: string[];
  changeLanguage: (lang: string) => Promise<void>;
  isLoading: boolean;
}

const TranslationContext = createContext<TranslationContextType | undefined>(undefined);

export const TranslationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [translations, setTranslations] = useState<TranslationsMap>({});
  const [flattenedMap, setFlattenedMap] = useState<Record<string, string>>({});
  const [currentLang, setCurrentLang] = useState<string>('en');
  const [availableLangs, setAvailableLangs] = useState<string[]>(['en']);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isInitialLoad, setIsInitialLoad] = useState<boolean>(true);

  // [TRITACARNE] Helper per appiattire l'oggetto delle traduzioni in modo normalizzato
  const flattenTranslations = useCallback((obj: any, prefix = '') => {
    let items: Record<string, string> = {};
    if (!obj || typeof obj !== 'object') return items;

    for (const key in obj) {
      // Normalizziamo la chiave: minuscolo e senza spazi
      const cleanKey = key.toLowerCase().trim();
      const newKey = prefix ? `${prefix}.${cleanKey}` : cleanKey;

      if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
        Object.assign(items, flattenTranslations(obj[key], newKey));
      } else {
        items[newKey] = String(obj[key]);
      }
    }
    return items;
  }, []);

  // Fetch delle lingue disponibili all'avvio
  useEffect(() => {
    const fetchAvailableLanguages = async () => {
      try {
        const response = await fetch(`${getBaseUrl(null)}/api/translations/languages`, {
          headers: { ...getHeaders(), "Content-Type": "application/json" }
        });
        if (response.ok) {
          const data = await response.json();
          if (data && data.languages) {
            setAvailableLangs(data.languages);
          }
        }
      } catch (error) {
        console.error("Errore fetch lingue:", error);
      }
    };
    fetchAvailableLanguages();
  }, []);

  // Funzione per cambiare lingua e rigenerare il Tritacarne
  const changeLanguage = async (lang: string) => {
    setIsLoading(true);
    try {
      // [FIX CACHE] Aggiunto timestamp per forzare il browser a scaricare sempre il JSON aggiornato
      const response = await fetch(`${getBaseUrl(null)}/api/translations/frontend?lang=${lang}&t=${Date.now()}`, {
        headers: { ...getHeaders(), "Content-Type": "application/json", "Cache-Control": "no-cache" }
      });
      if (response.ok) {
        const data = await response.json();
        if (data) {
          // Se il JSON è avvolto nella chiave lingua (es. { "it": { ... } }), lo sbucciamo
          const cleanData = (data[lang] && Object.keys(data).length === 1) ? data[lang] : data;
          
          setTranslations(cleanData);
          setFlattenedMap(flattenTranslations(cleanData));
          setCurrentLang(lang);
          console.log(`[TRITACARNE] Lingua ${lang} caricata. Chiavi indicizzate:`, Object.keys(flattenTranslations(cleanData)).length);
        }
      }
    } catch (error) {
      console.error(`Errore caricamento lingua ${lang}:`, error);
    } finally {
      setIsLoading(false);
      setIsInitialLoad(false);
    }
  };

  // Carica la lingua dal profilo utente al mount o dal backend se assente
  useEffect(() => {
    const initLanguage = async () => {
      try {
        // --- [FIX CRITICO] FACTORY RESET SYNC ---
        // Interroghiamo PRIMA il backend per sapere qual è la lingua di default (letta da lang.cfg)
        const res = await fetch(`${getBaseUrl(null)}/api/user_profile`, { headers: getHeaders() });
        if (res.ok) {
            const data = await res.json();
            // Se il backend dice che è il first_run, ignoriamo il localStorage e usiamo la lingua del prompt
            if (data.first_run) {
                await changeLanguage(data.preferredLanguage || 'it');
            } else {
                // Altrimenti usiamo il localStorage o il dato del backend
                const storedProfile = localStorage.getItem("airis_user_profile");
                if (storedProfile) {
                    const lang = JSON.parse(storedProfile).preferredLanguage || 'it';
                    await changeLanguage(lang);
                } else {
                    await changeLanguage(data.preferredLanguage || 'it');
                }
            }
        } else {
            await changeLanguage('it');
        }
      } catch (e) {
        await changeLanguage('it');
      }
    };
    initLanguage();
  }, []);

  // Navigazione ad albero standard (Case-Insensitive)
  const resolveValue = (key: string, data: any): any => {
    const keys = key.split('.');
    let current = data;
    for (const k of keys) {
      if (current && typeof current === 'object') {
        const actualKey = Object.keys(current).find(
          (objKey) => objKey.toLowerCase() === k.toLowerCase().trim()
        );
        if (actualKey) {
          current = current[actualKey];
        } else {
          return null;
        }
      } else {
        return null;
      }
    }
    return current;
  };

  // Funzione di traduzione [TRITACARNE v4.5]
  const t = useCallback((key: string, params?: Record<string, string | number>): string => {
    if (!key) return "";

    // 1. BONIFICA CHIAVE (Rimuove parentesi quadre e spazi)
    let cleanKey = key.trim();
    if (cleanKey.startsWith('[') && cleanKey.endsWith(']')) {
      cleanKey = cleanKey.slice(1, -1).trim();
    }
    const lowerKey = cleanKey.toLowerCase();

    let value: any = null;

    // 2. TENTATIVO: Risoluzione ad albero esatta
    value = resolveValue(cleanKey, translations);

    // 3. TENTATIVO: Lookup su Mappa Piatta (Tritacarne)
    if (!value || typeof value !== 'string') {
      if (flattenedMap[lowerKey]) {
        value = flattenedMap[lowerKey];
      }
    }

    // 4. TENTATIVO: Ricerca per Suffisso (es. "human" trova "rpg.races.human")
    if (!value || typeof value !== 'string') {
      const suffixKey = Object.keys(flattenedMap).find(k => k.endsWith(`.${lowerKey}`));
      if (suffixKey) {
        value = flattenedMap[suffixKey];
      }
    }

    // 5. FALLBACK FINALE
    if (!value || typeof value !== 'string') {
      return `[${cleanKey}]`;
    }

    // 6. SOSTITUZIONE VARIABILI BULLETPROOF (Tritacarne Mode Assoluto)
    let translatedString = value;
    if (params) {
      for (const[paramKey, paramValue] of Object.entries(params)) {
        // 6.1 Pulizia brutale della chiave parametro (rimuove spazi accidentali passati dal dev)
        const cleanParamKey = paramKey.trim();
        
        // 6.2 Escape dei caratteri speciali per non far esplodere la RegExp
        const safeParamKey = cleanParamKey.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        
        // 6.3 Regex Onnivora: 
        // - \\{{1,2} e \\}{1,2} cattura sia {var} che {{var}}
        // - \\s* cattura infiniti spazi prima e dopo la variabile
        // - 'gi' ignora totalmente maiuscole e minuscole (es. {{ SuMmArY }})
        const regex = new RegExp(`\\{{1,2}\\s*${safeParamKey}\\s*\\}{1,2}`, 'gi');
        
        // 6.4 Sostituzione sicura forzando il valore a stringa
        translatedString = translatedString.replace(regex, String(paramValue));
      }
    }

    return translatedString;
  }, [translations, flattenedMap]);

  return (
    <TranslationContext.Provider value={{ t, currentLang, availableLangs, changeLanguage, isLoading }}>
      {isInitialLoad ? (
        <div style={{ display: 'flex', height: '100vh', width: '100%', alignItems: 'center', justifyContent: 'center', backgroundColor: 'black' }}>
          <style>{`
            @keyframes airis-spin { 100% { transform: rotate(360deg); } }
            .airis-loader { border: 4px solid rgba(255,255,255,0.1); border-left-color: #ec4899; border-radius: 50%; width: 40px; height: 40px; animation: airis-spin 1s linear infinite; }
          `}</style>
          <div className="airis-loader"></div>
        </div>
      ) : (
        children
      )}
    </TranslationContext.Provider>
  );
};

export const useTranslation = (): TranslationContextType => {
  const context = useContext(TranslationContext);
  if (!context) {
    // Fallback estremo per evitare crash se il context non è ancora pronto
    return {
      t: (key: string) => key,
      currentLang: 'it',
      availableLangs: ['it', 'en'],
      changeLanguage: async () => {},
      isLoading: false
    };
  }
  return context;
};