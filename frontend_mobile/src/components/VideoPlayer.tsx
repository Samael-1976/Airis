// frontend_mobile/src/components/VideoPlayer.tsx
// v119.2 - GHOST CURSOR VISUALIZATION (MODULO B)
// ADD: Rendering del Ghost Cursor (cerchio rosso semitrasparente) su trigger visualEffect.
// FIX: Ottimizzazione animazione ripple per visibilità immediata.
// MANTENUTO: Video Watchdog, Ripple Effect logic, Audio-Video Sync, Immortal Video.
// LEGGE A0099: Invarianza strutturale garantita.

import { useEffect, useRef, useState } from "react";
import { Loader2, AlertCircle } from "lucide-react";
import { useTranslation } from "@/contexts/TranslationContext";

// Definizione locale per l'effetto visivo (in attesa di aggiornamento types)
interface VisualEffectData {
  type: string;
  x: number;
  y: number;
  timestamp: number;
}

interface VideoPlayerProps {
  intent: string | null;
  videoUrl: string | null;
  loop: boolean;
  isConnected: boolean;
  onVideoEnd: (intent: string, interrupted?: boolean) => void;
  shouldWait?: boolean;
  playSignal?: number;
  preloadUrl?: string | null;
  idleStates: string[]; // Lista dinamica degli stati interrompibili (Idle)
  visualEffect?: VisualEffectData | null; // Trigger per effetti visivi (Ghost Cursor)
  forceInterrupt?: boolean;
}

interface VideoCommand {
  url: string;
  loop: boolean;
  intent: string;
  shouldWait: boolean;
}

interface Ripple {
  id: number;
  x: number;
  y: number;
  type: string;
}

export const VideoPlayer = ({
  intent,
  videoUrl,
  loop,
  isConnected,
  onVideoEnd,
  shouldWait = false,
  playSignal = 0,
  preloadUrl = null,
  idleStates = Array(0),
  visualEffect = null,
  forceInterrupt = false,
}: VideoPlayerProps) => {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // CODA VIDEO: Gestisce la sequenza di riproduzione per evitare sovrapposizioni
  const videoQueue = useRef<VideoCommand[]>([]);
  const currentPlaying = useRef<VideoCommand | null>(null);

  // STATI UI
  const [activeSrc, setActiveSrc] = useState<string | null>(null);
  const [activeLoop, setActiveLoop] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSnapshotVisible, setIsSnapshotVisible] = useState(false); // Il Velo di Maya
  const[hasError, setHasError] = useState(false);
  const [playTrigger, setPlayTrigger] = useState<number>(0); // FIX FREEZE: Forza il reload

  // STATO LOADER RITARDATO: Per evitare flash del loader su caricamenti veloci
  const [showSpinner, setShowSpinner] = useState(false);

  // STATI LOGICI
  const isWaitingForSignal = useRef(shouldWait);
  const isVideoLoaded = useRef(false);
  const lastProcessedSignalRef = useRef<number>(0);
  const pendingPlayRequest = useRef<boolean>(false);

  // Ref per gestire il debounce della rimozione velo (evita flickering)
  const revealTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Ref per la valvola di sicurezza
  const safetyValveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // --- FIX v118.6: REF PER BUFFERING SEGNALE AUDIO ANTICIPATO ---
  const bufferedPlaySignal = useRef<number | null>(null);
  const retryPlayTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // --- [NUOVO v119.1] WATCHDOG REFS ---
  const watchdogIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastTimeRef = useRef<number>(0);
  const stuckCounterRef = useRef<number>(0);

  // --- [NUOVO v119.2] GESTIONE RIPPLES (GHOST CURSOR) ---
  const [ripples, setRipples] = useState<Ripple[]>([]);
  const lastEffectTimestamp = useRef<number>(0);

  // --- PRELOAD LOGIC ---
  // Scarica in anticipo il prossimo video se il backend invia un hint
  useEffect(() => {
    if (preloadUrl) {
      const link = document.createElement("link");
      link.rel = "preload";
      link.as = "video";
      link.href = preloadUrl;
      document.head.appendChild(link);

      // Pulizia dopo 10 secondi per non intasare il DOM
      setTimeout(() => {
        if (document.head.contains(link)) {
          document.head.removeChild(link);
        }
      }, 10000);
    }
  }, [preloadUrl]);

  // ---[FIX CRITICO MOBILE] SBLOCCO VIDEO AL RIENTRO DAL BACKGROUND ---
  // I browser mobile mettono in pausa i video e bloccano il rendering quando l'app è in background.
  // Al rientro, il video rimane freezato e il "Velo di Maya" non cade mai.
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        console.log("[MOBILE FIX] App in foreground. Forzo sblocco video e rimozione velo.");
        
        // 1. Rimuovi il velo se è rimasto incastrato
        setIsSnapshotVisible(false);
        
        // 2. Sblocca lo stato di caricamento infinito
        setIsLoading(false);
        
        // 3. Forza il play se c'è un video caricato e non stiamo aspettando l'audio
        if (videoRef.current && activeSrc && !isWaitingForSignal.current) {
          const playPromise = videoRef.current.play();
          if (playPromise !== undefined) {
            playPromise.catch((e) => {
              console.warn("[MOBILE FIX] Autoplay bloccato al rientro dal background:", e);
              // Se l'OS blocca l'autoplay, skippiamo il video per non freezare il backend
              if (currentPlaying.current && !currentPlaying.current.loop) {
                  onVideoEnd(currentPlaying.current.intent);
                  currentPlaying.current = null;
                  if (videoQueue.current.length > 0) processQueue();
              }
            });
          }
        }
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [activeSrc]);

  // --- LOGICA LOADER RITARDATO ---
  // Mostra lo spinner solo se il caricamento dura più di 500ms
  useEffect(() => {
    let timeout: NodeJS.Timeout;
    if (isLoading) {
      timeout = setTimeout(() => setShowSpinner(true), 500);
    } else {
      setShowSpinner(false);
    }
    return () => clearTimeout(timeout);
  }, [isLoading]);

  // --- HARD MUTE ENFORCER ---
  // Forza il muto a livello DOM per evitare che il video rubi il focus audio al TTS su mobile
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.muted = true;
      videoRef.current.defaultMuted = true;
    }
  }, []); // [FIX CRITICO] Aggiunto array vuoto per evitare reflow continuo e micro-freeze del video ad ogni re-render della chat

  // --- [NUOVO v118.8] PROTOCOLLO Z.3: WATCHDOG ANTI-FREEZE POTENZIATO ---
  // Monitora costantemente se l'interfaccia è bloccata sul "Velo di Maya" o se il video si freeza
  useEffect(() => {
    watchdogIntervalRef.current = setInterval(() => {
        // [FIX CRITICO MOBILE] Rimosso !isLoading. Su mobile, il browser può rimanere
        // incastrato in uno stato di "falso caricamento" infinito al rientro dal background.
        // Il watchdog deve poter intervenire anche se React pensa che stia caricando.
        if (videoRef.current && !isWaitingForSignal.current) {
            const currentTime = videoRef.current.currentTime;
            const isEnded = videoRef.current.ended;
            // readyState < 3 (HAVE_FUTURE_DATA) significa che il video sta scaricando dati dalla rete
            const isBuffering = videoRef.current.readyState < 3;
            
            // Se il tempo non avanza E il video non è finito E NON sta bufferizzando
            if (currentTime === lastTimeRef.current && !isEnded && !isBuffering) {
                stuckCounterRef.current += 1;
            } else {
                stuckCounterRef.current = 0;
                lastTimeRef.current = currentTime;
            }

            // --- [FIX CRITICO] PUNTO CIECO WATCHDOG RISOLTO ---
            // Interviene se il video è bloccato da > 2 secondi (4 tick), INDIPENDENTEMENTE dal velo.
            if (stuckCounterRef.current > 4) {
                if (isSnapshotVisible) {
                    console.warn(t("video_player.watchdog_warning"));
                    setIsSnapshotVisible(false);
                } else if (stuckCounterRef.current === 5) {
                    console.warn(t("video_player.watchdog_stuck_no_veil"));
                }
                
                // Tenta un recupero forzato del play se non siamo in attesa di segnale
                if (!isWaitingForSignal.current && stuckCounterRef.current === 5) {
                    const playPromise = videoRef.current.play();
                    if (playPromise !== undefined) {
                        playPromise.catch(() => {
                            // --- FIX CRITICO MOBILE: SBLOCCO BACKEND DA WATCHDOG ---
                            if (currentPlaying.current && !currentPlaying.current.loop) {
                                // [FIX BUG 01] Passiamo false per ingannare il backend e forzare l'invio di playback_complete
                                onVideoEnd(currentPlaying.current.intent, false); 
                                currentPlaying.current = null;
                                if (videoQueue.current.length > 0) processQueue();
                            }
                        });
                    }
                }
                
                // --- [FIX CRITICO MOBILE] HARD TIMEOUT ---
                // Se il video è bloccato da > 4 secondi (8 tick), forziamo la chiusura del video non-looping
                // per sbloccare definitivamente la coda del backend.
                if (stuckCounterRef.current > 8) {
                    console.warn("Hard timeout: video stuck for > 4s. Forcing end to unblock backend.");
                    if (currentPlaying.current && !currentPlaying.current.loop) {
                        onVideoEnd(currentPlaying.current.intent, false);
                        currentPlaying.current = null;
                        if (videoQueue.current.length > 0) processQueue();
                    }
                    stuckCounterRef.current = 0;
                }
            }
        }
    }, 500);

    return () => {
        if (watchdogIntervalRef.current) clearInterval(watchdogIntervalRef.current);
    };
  }, [isSnapshotVisible, isLoading]);

  // --- [NUOVO v119.2] MANIFESTAZIONE GHOST CURSOR ---
  useEffect(() => {
    if (visualEffect && visualEffect.timestamp > lastEffectTimestamp.current) {
        lastEffectTimestamp.current = visualEffect.timestamp;
        
        const newRipple: Ripple = {
            id: visualEffect.timestamp,
            x: visualEffect.x,
            y: visualEffect.y,
            type: visualEffect.type
        };
        
        setRipples(prev => [...prev, newRipple]);
        
        // Rimuovi il ripple dopo l'animazione (1s) per pulizia DOM
        setTimeout(() => {
            setRipples(prev => prev.filter(r => r.id !== newRipple.id));
        }, 1000);
    }
  }, [visualEffect]);

  // --- 1. GESTIONE INPUT ---
  // Riceve le props dal genitore e popola la coda
  useEffect(() => {
    if (!videoUrl || !intent) return;

    const newCommand: VideoCommand = {
      url: videoUrl,
      loop: loop,
      intent: intent,
      shouldWait: shouldWait,
    };

    // Evita duplicati consecutivi identici
    const lastInQueue = videoQueue.current[videoQueue.current.length - 1];
    if (lastInQueue && lastInQueue.intent === intent && lastInQueue.url === videoUrl) {
      return;
    }

    if (
      currentPlaying.current &&
      currentPlaying.current.intent === intent &&
      currentPlaying.current.url === videoUrl &&
      videoQueue.current.length === 0
    ) {
      return;
    }

    if (forceInterrupt) {
        console.log("[VideoPlayer] Interruzione forzata ricevuta!");
        videoQueue.current =[]; // Svuota la coda
        if (currentPlaying.current) {
            onVideoEnd(currentPlaying.current.intent, true);
            currentPlaying.current = null;
        }
    }

    // LOGICA SALTO DELLA FILA: Se arriva un comando prioritario (non idle), rimuoviamo gli idle pendenti dalla coda
    // Generalizzazione: Controlla se l'intent è nella lista degli idle o inizia con un prefisso idle noto
    const isNewCommandIdle = idleStates.some(idle => intent.startsWith(idle));
    // --- [FIX BUG 01] Corretta la stringa di riconoscimento per i video di thinking dinamici ---
    const isNewCommandThinking = intent.startsWith("state_thinking");

    if (!isNewCommandIdle) {
      // Rimuovi tutti i comandi idle pendenti dalla coda
      videoQueue.current = videoQueue.current.filter((cmd) => !idleStates.some(idle => cmd.intent.startsWith(idle)));

      // Se non è thinking, rimuoviamo anche eventuali thinking pendenti per passare subito all'azione
      if (!isNewCommandThinking) {
        videoQueue.current = videoQueue.current.filter((cmd) => !cmd.intent.startsWith("state_thinking"));
      }
    }

    videoQueue.current.push(newCommand);

    // ---[FIX CRITICO] INTERRUZIONE FORZATA DEL THINKING ---
    // Se stiamo pensando e arriva un'emozione (Intent) o il parlato, dobbiamo interrompere il loop di thinking
    // altrimenti il video di Intent viene accodato e ritardato, causando la desincronizzazione del backend
    // e bruciando il segnale audio prematuramente.
    if (currentPlaying.current && currentPlaying.current.intent.startsWith("state_thinking") && !isNewCommandThinking && !isNewCommandIdle) {
        console.log("Interruzione forzata del thinking per dare priorità a:", intent);
        // Forziamo il passaggio al prossimo video nella coda.
        // Il backend ignorerà il segnale di fine thinking grazie alla blindatura in chat.py
        processQueue();
        return;
    }

    // Se il player è libero, avvia subito
    if (!currentPlaying.current) {
      processQueue();
    }
  },[videoUrl, loop, intent, shouldWait, idleStates, forceInterrupt]);

  // --- 2. PROCESSO DI CODA ---
  const processQueue = () => {
    if (videoQueue.current.length === 0) return;

    const nextCmd = videoQueue.current.shift();
    if (nextCmd) {
      playCommand(nextCmd);
    }
  };

  // --- 3. ESECUZIONE COMANDO ---
  const playCommand = (cmd: VideoCommand) => {
    console.log(t("video_player.log_play", { intent: cmd.intent }));
    setHasError(false);

    // A. CATTURA SNAPSHOT (Velo di Maya)
    // Prima di cambiare video, congeliamo l'ultimo frame valido sul canvas
    // Questo nasconde il nero/loading del prossimo video
    if (videoRef.current && canvasRef.current) {
      const v = videoRef.current;
      const c = canvasRef.current;

      // FIX BLINK: Cattura SEMPRE se c'è un frame valido, anche se il video è finito o in pausa.
      if (v.videoWidth > 0 && v.videoHeight > 0 && !v.error) {
        c.width = v.videoWidth;
        c.height = v.videoHeight;
        const ctx = c.getContext("2d");
        if (ctx) {
          ctx.drawImage(v, 0, 0, c.width, c.height);
          setIsSnapshotVisible(true); // Velo ATTIVO
        }
      }
    }

    // B. AGGIORNAMENTO STATO IMMEDIATO
    // Notifica al backend che il video precedente è finito (sostituito)
    if (currentPlaying.current) {
      onVideoEnd(currentPlaying.current.intent, true); // [FIX BUG 01] Segnala che è stato interrotto
    }

    currentPlaying.current = cmd;
    setIsLoading(true);
    isVideoLoaded.current = false;
    pendingPlayRequest.current = false;
    isWaitingForSignal.current = cmd.shouldWait;

    // --- FIX v118.6: RESET BUFFER SEGNALE ---
    bufferedPlaySignal.current = null;

    // Pulisce eventuali timeout pendenti
    if (revealTimeoutRef.current) {
      clearTimeout(revealTimeoutRef.current);
      revealTimeoutRef.current = null;
    }
    if (safetyValveTimeoutRef.current) {
      clearTimeout(safetyValveTimeoutRef.current);
      safetyValveTimeoutRef.current = null;
    }
    if (retryPlayTimeoutRef.current) {
      clearTimeout(retryPlayTimeoutRef.current);
      retryPlayTimeoutRef.current = null;
    }

    // Imposta i nuovi valori per il tag video
    setActiveLoop(cmd.loop);
    setActiveSrc(cmd.url);
    setPlayTrigger(prev => prev + 1); // FIX FREEZE: Forza l'aggiornamento anche se l'URL è identico
  };

  // --- 4. GESTIONE EVENTI VIDEO ---
  const handleLoadedData = () => {
    setIsLoading(false);
    isVideoLoaded.current = true;

    // FIX FREEZE: Valvola di Sicurezza
    // Se il video è carico, il velo DEVE cadere.
    // Se timeUpdate non scatta entro 125ms, forziamo la rimozione del velo.
    if (safetyValveTimeoutRef.current) {
      clearTimeout(safetyValveTimeoutRef.current);
    }
    safetyValveTimeoutRef.current = setTimeout(() => {
      if (isSnapshotVisible) {
        console.log(t("video_player.log_safety_valve"));
        setIsSnapshotVisible(false);
      }
    }, 125);

    if (videoRef.current) {
      // Re-enforce mute per sicurezza
      videoRef.current.muted = true;
    }

    // --- [NUOVO v118.7] PROTOCOLLO Z.3: VALVOLA DI SICUREZZA ---
    // Se il video è carico, il velo DEVE cadere entro 250ms per evitare il freeze visivo
    if (safetyValveTimeoutRef.current) {
      clearTimeout(safetyValveTimeoutRef.current);
    }
    safetyValveTimeoutRef.current = setTimeout(() => {
      if (isSnapshotVisible) {
        console.log(t("video_player.log_protocol_z3"));
        setIsSnapshotVisible(false);
      }
    }, 125);

    // --- FIX v118.6: GESTIONE DOPPIA MODALITÀ ---
    if (pendingPlayRequest.current) {
      // Il segnale audio era arrivato mentre caricavamo → sblocca subito
      console.log(t("video_player.log_pending_request"));
      isWaitingForSignal.current = false;
      pendingPlayRequest.current = false;
      safePlay();
    } else if (bufferedPlaySignal.current !== null) {
      // Segnale audio arrivato in anticipo ma non ancora processato
      console.log(t("video_player.log_buffered_signal"));
      isWaitingForSignal.current = false;
      bufferedPlaySignal.current = null;
      safePlay();
    } else if (isWaitingForSignal.current) {
      // Dobbiamo aspettare l'audio (Lip-Sync)
      console.log(t("video_player.log_waiting_audio"));
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    } else {
      // Nessuna attesa richiesta (Mute ON o video non-Speaking), vai subito
      console.log(t("video_player.log_no_wait"));
      safePlay();
    }
  };

  const safePlay = () => {
    if (videoRef.current) {
      // --- [NUOVO v118.7] PROTOCOLLO Z.2: RITARDO DI GRAZIA MOBILE ---
      // Su mobile, chiamare play() nello stesso tick di load causa uno stallo.
      // 50ms è il tempo minimo per permettere al thread UI di respirare.
      setTimeout(() => {
        if (!videoRef.current) return; 

        const playPromise = videoRef.current.play();
        if (playPromise !== undefined) {
          playPromise.catch((e) => {
            console.warn(t("video_player.log_autoplay_blocked"), e);
            // Se l'autoplay fallisce, rimuoviamo il velo per mostrare i controlli o l'errore
            setIsSnapshotVisible(false);
            
            // --- FIX CRITICO MOBILE: SBLOCCO BACKEND SE AUTOPLAY NEGATO ---
            // I browser mobile bloccano l'autoplay senza interazione utente.
            // Se il video bloccato è un'azione singola (es. saluto iniziale), 
            // dobbiamo simulare la sua fine per non mandare in deadlock il backend.
            if (currentPlaying.current && !currentPlaying.current.loop) {
                console.warn("Autoplay blocked on non-looping video. Forcing end to unblock backend.");
                // [FIX BUG 01] Passiamo false per garantire l'invio di playback_complete e sbloccare il backend
                onVideoEnd(currentPlaying.current.intent, false); 
                currentPlaying.current = null;
                if (videoQueue.current.length > 0) {
                    processQueue();
                }
            }
          });
        }
      }, 50); // 50ms di respiro
    }
  };

  const handlePlaying = () => {
    // FIX MOBILE: NON rimuovere il velo qui.
    // Su mobile, "playing" scatta prima che il frame sia renderizzato.
    // Se togliamo il velo qui, si vede un flash nero.
    // Ci affidiamo a timeUpdate o alla valvola di sicurezza.
  };

  const handleTimeUpdate = () => {
    // FIX MOBILE: Rimuovi il velo SOLO quando il video ha effettivamente renderizzato frame
    // (>0.05s è una soglia sicura per garantire che il buffer nero sia passato).
    if (videoRef.current && videoRef.current.currentTime > 0.05) {
      if (isSnapshotVisible && !revealTimeoutRef.current) {
        // Cancella la valvola di sicurezza se scatta il timeUpdate (perché è più preciso)
        if (safetyValveTimeoutRef.current) {
          clearTimeout(safetyValveTimeoutRef.current);
        }

        revealTimeoutRef.current = setTimeout(() => {
          requestAnimationFrame(() => {
            setIsSnapshotVisible(false); // Velo RIMOSSO (Sicuro)
          });
          revealTimeoutRef.current = null;
        }, 0);
      }
    }
  };

  const handleEnded = () => {
    console.log(t("video_player.log_ended", { intent: currentPlaying.current?.intent }));

    // Se c'è altro in coda, procedi
    if (videoQueue.current.length > 0) {
      processQueue();
      return;
    }

    // Se è un loop, riavvia
    if (activeLoop && videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current.play().catch(console.error);
    } else {
      // Altrimenti notifica la fine
      if (currentPlaying.current) {
        const endedIntent = currentPlaying.current.intent;
        onVideoEnd(endedIntent, false); //[FIX BUG 01] Fine naturale, non interrotto
        currentPlaying.current = null;

        // --- [NUOVO] PARACADUTE ANTI-FREEZE (AUTO-LOOP DI EMERGENZA) ---
        // Se era un idle o listening, impostiamo un timeout di sicurezza di 0.25 secondi.
        // Se entro 1.5s non è arrivato un nuovo video dal server (il video è fermo o concluso),
        // lo facciamo ripartire in loop localmente invece di lasciare lo schermo congelato su un frame fisso.
        if (endedIntent.startsWith("state_idle") || endedIntent.startsWith("state_listening")) {
            setTimeout(() => {
                if (videoRef.current && (videoRef.current.paused || videoRef.current.ended)) {
                    console.log("[ANTI-FREEZE] Rilevato stallo di rete. Avvio riproduzione locale di emergenza.");
                    videoRef.current.currentTime = 0;
                    videoRef.current.play().catch(() => {});
                }
            }, 250);
        }
      }
    }
  };

  const handleError = (e: any) => {
    console.error(t("video_player.log_error"), e);
    setHasError(true);

    // FIX CRITICO: Pulizia forzata dello stato visivo in caso di errore
    setIsLoading(false);
    setIsSnapshotVisible(false); // Rimuovi il velo per non bloccare la vista anche se c'è errore
    setShowSpinner(false);

    if (safetyValveTimeoutRef.current) {
      clearTimeout(safetyValveTimeoutRef.current);
    }
    if (retryPlayTimeoutRef.current) {
      clearTimeout(retryPlayTimeoutRef.current);
    }

    // Notifica al backend che questo intent è finito (fallito) per sbloccare il flusso
    if (currentPlaying.current) {
      console.log(t("video_player.log_skip_error", { intent: currentPlaying.current.intent }));
      // [FIX BUG 01] Passiamo false per garantire l'invio di playback_complete e sbloccare il backend
      onVideoEnd(currentPlaying.current.intent, false); 
      currentPlaying.current = null;
    }

    // Tenta di processare il prossimo video se esiste
    if (videoQueue.current.length > 0) {
      processQueue();
    } else {
      console.warn(t("video_player.log_empty_queue"));
    }
  };

  // --- 5. GESTIONE SEGNALE AUDIO ---
  useEffect(() => {
    if (playSignal && playSignal !== lastProcessedSignalRef.current) {
      lastProcessedSignalRef.current = playSignal;

      console.log(t("video_player.log_signal_received", { signal: playSignal }));

      // --- FIX CRITICO: GESTIONE SEGNALE ANTICIPATO E PREVENZIONE CONSUMO PREMATURO ---
      if (!isVideoLoaded.current) {
        // Video non ancora pronto → bufferizza il segnale
        console.log(t("video_player.log_buffering"));
        bufferedPlaySignal.current = playSignal;
        pendingPlayRequest.current = true;
        
        // --- FIX v118.6: RETRY AUTOMATICO ---
        if (retryPlayTimeoutRef.current) {
          clearTimeout(retryPlayTimeoutRef.current);
        }
        retryPlayTimeoutRef.current = setTimeout(() => {
          if (isVideoLoaded.current && bufferedPlaySignal.current !== null) {
            console.log(t("video_player.log_retry_timeout"));
            isWaitingForSignal.current = false;
            bufferedPlaySignal.current = null;
            pendingPlayRequest.current = false;
            safePlay();
          } else if (!isVideoLoaded.current) {
            console.warn(t("video_player.log_stuck_loading"));
          }
        }, 500);

        return;
      }

      // Video già pronto. Controlliamo se stava effettivamente aspettando questo segnale.
      if (isWaitingForSignal.current) {
        console.log(t("video_player.log_unlock_play"));

        // ---[NUOVO v118.7] PROTOCOLLO Z.4: PRIORITÀ AUDIO ---
        setIsSnapshotVisible(false);

        if (safetyValveTimeoutRef.current) {
          clearTimeout(safetyValveTimeoutRef.current);
        }

        isWaitingForSignal.current = false;
        safePlay();
      } else {
        // Il video corrente è carico ma NON stava aspettando (es. sta finendo un loop idle o thinking).
        // Questo significa che il segnale audio è arrivato in anticipo per il PROSSIMO video in coda.
        // Dobbiamo bufferizzarlo, altrimenti andrà perso e il prossimo video si freezerà!
        console.log(t("video_player.log_buffering"));
        bufferedPlaySignal.current = playSignal;
        pendingPlayRequest.current = true;
      }
    }
  },[playSignal]); // FIX CRITICO: Rimosso shouldWait dalle dipendenze per evitare trigger spuri

  // --- FIX CRITICO: GESTIONE MANUALE DEL CAMBIO SRC ---
  // Invece di usare key={activeSrc} che distrugge il DOM e rompe l'autoplay mobile,
  // usiamo questo useEffect per caricare il nuovo video mantenendo lo stesso elemento DOM.
  useEffect(() => {
    if (videoRef.current && activeSrc) {
      videoRef.current.load();
      // Non chiamiamo play() qui, ci pensa handleLoadedData o il segnale audio
    }
  }, [activeSrc, playTrigger]); // FIX FREEZE: Aggiunto playTrigger alle dipendenze

  return (
    <div className="relative w-full h-full flex items-center justify-center bg-black overflow-hidden rounded-lg">
      {/* CANVAS SNAPSHOT (Velo di Maya) - Z-Index 20 */}
      <canvas
        ref={canvasRef}
        className={`absolute inset-0 w-full h-full object-cover pointer-events-none transition-opacity ${
          isSnapshotVisible ? "opacity-100 z-20 duration-0" : "opacity-0 z-0 duration-75"
        }`}
      />

      {/* VIDEO PLAYER - Z-Index 10 */}
      {/* FIX CRITICO: Rimossa prop "key". Il tag è immortale. */}
      <video
        ref={videoRef}
        src={activeSrc || undefined}
        muted={true}
        autoPlay={true}
        playsInline
        webkit-playsinline="true"
        loop={false}
        onLoadedData={handleLoadedData}
        onPlaying={handlePlaying}
        onTimeUpdate={handleTimeUpdate} // CRUCIALE: Qui avviene la rimozione sicura del velo
        onEnded={handleEnded}
        onError={handleError}
        className="w-full h-full object-cover z-10"
      />

      {/* LOADER - Z-Index 30 */}
      {showSpinner && !isSnapshotVisible && !hasError && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 backdrop-blur-[2px] z-30">
          <Loader2 className="w-10 h-10 text-primary animate-spin" />
        </div>
      )}

      {/* ERROR INDICATOR - Z-Index 40 */}
      {hasError && (
        <div className="absolute top-2 right-2 z-40 text-red-500 bg-black/50 rounded-full p-1">
          <AlertCircle className="w-6 h-6" />
        </div>
      )}

      {!isConnected && (
        <div className="absolute top-4 right-4 bg-destructive text-destructive-foreground px-3 py-1 rounded-full text-xs font-medium z-50 shadow-md animate-pulse">
          {t("video_player.disconnected")}
        </div>
      )}

      {/* --- [NUOVO v119.2] GHOST CURSOR OVERLAY (RIPPLE ROSSO) - Z-Index 50 --- */}
      {ripples.map(ripple => (
          <div
              key={ripple.id}
              className="fixed w-8 h-8 rounded-full bg-red-500/40 pointer-events-none z-50 animate-ping"
              style={{
                  left: ripple.x,
                  top: ripple.y,
                  transform: 'translate(-50%, -50%)',
                  boxShadow: '0 0 15px 4px rgba(239, 68, 68, 0.6)',
                  border: '2px solid rgba(239, 68, 68, 0.8)'
              }}
          />
      ))}
    </div>
  );
};