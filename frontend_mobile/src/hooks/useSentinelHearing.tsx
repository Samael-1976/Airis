// frontend_mobile/src/hooks/useSentinelHearing.tsx
// v1.0 - CLIENT-SIDE VAD (VOICE ACTIVITY DETECTION)
// Permette ai dispositivi Sentinel di ascoltare l'ambiente e registrare automaticamente
// quando rilevano la voce umana, ignorando i rumori di fondo e la voce dell'AI stessa.

import { useState, useEffect, useRef, useCallback } from "react";
import { toast } from "sonner";
import { useTranslation } from "@/contexts/TranslationContext";

interface UseSentinelHearingProps {
  enabled: boolean;           // Se l'ascolto è attivo (Toggle UI)
  isAiSpeaking: boolean;      // Se l'AI sta parlando (per evitare auto-trigger)
  onAudioCaptured: (audioBlob: Blob) => void; // Callback per inviare l'audio
  onSpeechStart?: () => void; // [NUOVO] Callback innescato appena l'utente inizia a parlare
  silenceThreshold?: number;  // Soglia di volume (0-255) per considerare "voce"
  silenceDuration?: number;   // Ms di silenzio prima di tagliare la registrazione
}

export const useSentinelHearing = ({
  enabled,
  isAiSpeaking,
  onAudioCaptured,
  onSpeechStart, // [NUOVO]
  silenceThreshold = 25, // Soglia empirica per ambiente domestico
  silenceDuration = 1500 // 1.5 secondi di silenzio per chiudere la frase
}: UseSentinelHearingProps) => {
  const { t } = useTranslation();
  
  const [isListening, setIsListening] = useState(false); // Il sistema è pronto e monitora
  const [isRecording, setIsRecording] = useState(false); // Il sistema sta effettivamente registrando
  const [volumeLevel, setVolumeLevel] = useState(0);     // Per feedback visivo (opzionale)

  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  
  // Ref per accedere allo stato corrente dentro il loop di animazione
  const stateRef = useRef({
    isRecording: false,
    isAiSpeaking: false,
    silenceStartTime: 0 as number | null,
    hasInterrupted: false // [NUOVO] Previene lo spam del trigger di interruzione
  });

  // Sincronizza i ref con le props
  useEffect(() => {
    stateRef.current.isAiSpeaking = isAiSpeaking;
    // Se l'AI smette di parlare (naturalmente o per interruzione), resettiamo il flag
    if (!isAiSpeaking) {
        stateRef.current.hasInterrupted = false;
    }
  }, [isAiSpeaking]);

  const stopHearing = useCallback(() => {
    if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }

    audioContextRef.current = null;
    analyserRef.current = null;
    mediaRecorderRef.current = null;
    streamRef.current = null;
    
    setIsListening(false);
    setIsRecording(false);
    stateRef.current.isRecording = false;
  }, []);

  const startHearing = useCallback(async () => {
    if (!enabled) return;
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { 
            echoCancellation: true, 
            noiseSuppression: true, 
            autoGainControl: true 
        } 
      });
      
      streamRef.current = stream;
      
      // Setup Audio Context per Analisi
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);
      
      analyser.fftSize = 256;
      source.connect(analyser);
      
      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      // Setup Media Recorder per Cattura
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        audioChunksRef.current = [];
        
        // Invia solo se il blob ha una dimensione sensata (evita click vuoti)
        if (audioBlob.size > 1000) {
            console.log(t("camera_manager.toast.sentinel_audio_captured"));
            onAudioCaptured(audioBlob);
        }
      };

      setIsListening(true);
      analyzeLoop();
      
    } catch (error) {
      console.error(t("camera_manager.error.sentinel_mic_denied_log"), error);
      toast.error(t("camera_manager.error.sentinel_mic_denied"));
      stopHearing();
    }
  }, [enabled, onAudioCaptured]);

  const startRecording = () => {
    if (!mediaRecorderRef.current || stateRef.current.isRecording) return;
    
    console.log(t("camera_manager.toast.sentinel_voice_detected"));
    audioChunksRef.current = [];
    mediaRecorderRef.current.start();
    setIsRecording(true);
    stateRef.current.isRecording = true;
  };

  const stopRecording = () => {
    if (!mediaRecorderRef.current || !stateRef.current.isRecording) return;
    
    console.log(t("camera_manager.toast.sentinel_silence_detected"));
    mediaRecorderRef.current.stop();
    setIsRecording(false);
    stateRef.current.isRecording = false;
    stateRef.current.silenceStartTime = null;
  };

  const analyzeLoop = () => {
    if (!analyserRef.current) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);

    // Calcola volume medio
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i];
    }
    const average = sum / dataArray.length;
    setVolumeLevel(average);

    // LOGICA VAD (Voice Activity Detection) - FULL DUPLEX
    
    if (average > silenceThreshold) {
        // L'utente sta parlando o c'è rumore forte

        // 1. LOGICA DI INTERRUZIONE (Se l'AI sta parlando)
        if (stateRef.current.isAiSpeaking && !stateRef.current.hasInterrupted) {
            console.log("[VAD] Interruzione rilevata! L'utente sta parlando sopra l'AI.");
            stateRef.current.hasInterrupted = true;
            if (onSpeechStart) {
                onSpeechStart(); // Innesca il kill dell'audio nel frontend
            }
        }

        // 2. AVVIO REGISTRAZIONE
        if (!stateRef.current.isRecording) {
            startRecording();
        }
        // Resetta timer silenzio
        stateRef.current.silenceStartTime = null;
    } 
    else {
        // C'è silenzio
        if (stateRef.current.isRecording) {
            if (!stateRef.current.silenceStartTime) {
                stateRef.current.silenceStartTime = Date.now();
            } else {
                const silenceDurationCurrent = Date.now() - stateRef.current.silenceStartTime;
                if (silenceDurationCurrent > silenceDuration) {
                    stopRecording();
                }
            }
        }
    }

    animationFrameRef.current = requestAnimationFrame(analyzeLoop);
  };

  // Gestione ciclo di vita
  useEffect(() => {
    if (enabled) {
      startHearing();
    } else {
      stopHearing();
    }
    return () => stopHearing();
  }, [enabled, startHearing, stopHearing]);

  return {
    isListening,
    isRecording,
    volumeLevel
  };
};