import { useState, useEffect } from 'react';
import { getHeaders } from '@/lib/api';

export const useSecureMedia = (src: string | null | undefined) => {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!src) {
      setObjectUrl(null);
      return;
    }

    // Se è già un blob o un data URL, usalo direttamente
    if (src.startsWith('blob:') || src.startsWith('data:')) {
      setObjectUrl(src);
      return;
    }

    let isActive = true;
    setLoading(true);
    setError(false);

    const fetchMedia = async () => {
      try {
        // FIX: Usa la funzione centralizzata per gli headers
        // Questo garantisce che Ngrok non blocchi la richiesta
        const headers = getHeaders();
        
        // Nota: fetch richiede un oggetto HeadersInit, getHeaders restituisce un record string
        // La conversione è implicita o possiamo passarlo direttamente
        const response = await fetch(src, { 
            headers: headers as HeadersInit 
        });
        
        if (!response.ok) throw new Error(`Failed to load media: ${response.status}`);

        const blob = await response.blob();
        
        if (isActive) {
          const url = URL.createObjectURL(blob);
          setObjectUrl(url);
          setLoading(false);
        }
      } catch (err) {
        console.error(t("secure_media.err_loading", { src: String(src) }), err);
        if (isActive) {
          setError(true);
          setLoading(false);
          // Fallback disperato: prova l'URL originale
          setObjectUrl(src); 
        }
      }
    };

    fetchMedia();

    return () => {
      isActive = false;
      if (objectUrl && objectUrl.startsWith('blob:')) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [src]);

  return { url: objectUrl, loading, error };
};