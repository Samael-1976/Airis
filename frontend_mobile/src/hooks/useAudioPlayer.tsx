import { useRef, useCallback, useEffect } from 'react';
import { useTranslation } from "@/contexts/TranslationContext";

export const useAudioPlayer = () => {
  const { t } = useTranslation();
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const onEndedCallbackRef = useRef<(() => void) | null>(null);
  const onPlayCallbackRef = useRef<(() => void) | null>(null);
  const onErrorCallbackRef = useRef<((error: any) => void) | null>(null);

  // Inizializza l'elemento audio solo una volta
  useEffect(() => {
    if (!audioRef.current) {
      audioRef.current = new Audio();
    }

    const audio = audioRef.current;

    const handleEnded = () => {
      if (onEndedCallbackRef.current) {
        onEndedCallbackRef.current();
        // Importante: pulire il ref per evitare chiamate multiple
        onEndedCallbackRef.current = null;
      }
    };

    const handlePlay = () => {
        if (onPlayCallbackRef.current) {
            onPlayCallbackRef.current();
        }
    };

    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('play', handlePlay);

    return () => {
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('play', handlePlay);
      audio.pause();
      audio.src = "";
    };
  }, []);

  const play = useCallback((
      src: string, 
      onEndedCallback?: () => void, 
      onPlayCallback?: () => void,
      onErrorCallback?: (error: any) => void
    ) => {
    const audio = audioRef.current;
    if (!audio) return;

    // Memorizza i callback correnti
    onEndedCallbackRef.current = onEndedCallback || null;
    onPlayCallbackRef.current = onPlayCallback || null;
    onErrorCallbackRef.current = onErrorCallback || null;
    
    // Se sta già suonando, fermalo e resetta
    if (!audio.paused) {
      audio.pause();
      audio.currentTime = 0;
    }
    
    audio.src = src;

    // Prova a riprodurre l'audio
    const playPromise = audio.play();

    if (playPromise !== undefined) {
      playPromise
        .then(() => {
          // Playback iniziato con successo
        })
        .catch(error => {
          console.error(`${t("main_js.audio_error")} Playback fallito (Autoplay block o errore rete).`, error);
          
          // --- FIX LOGICA AUTOPLAY ---
          // Se abbiamo un gestore errori specifico, usiamo quello.
          // Altrimenti, usiamo il fallback vecchio (chiamare onEnded) per evitare blocchi,
          // ma questo causava il "salto" del video.
          if (onErrorCallbackRef.current) {
              onErrorCallbackRef.current(error);
          } else if (onEndedCallbackRef.current) {
            console.log(t("main_js.audio_fallback_trigger"));
            onEndedCallbackRef.current();
            onEndedCallbackRef.current = null;
          }
        });
    }
  },[]);

  const stop = useCallback(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
      
      // --- [FIX PRO A0034] INTERRUZIONE SILENZIOSA ---
      // Puliamo i callback SENZA eseguirli.
      // Evita che il server riceva un falso segnale di "playback_complete"
      // mentre stiamo inviando un "/stop_generation" per interruzione vocale.
      onEndedCallbackRef.current = null;
      onPlayCallbackRef.current = null;
      onErrorCallbackRef.current = null;
    }
  }, [ /* dipendenze vuote per bypass glitch */ ]);

  // Helper per ottenere la durata (utile per il fallback)
  const getDuration = useCallback(() => {
      return audioRef.current?.duration || 0;
  }, []);

  return { play, stop, getDuration };
};