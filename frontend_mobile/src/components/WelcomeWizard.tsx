// frontend_mobile/src/components/WelcomeWizard.tsx
// v1.2 - RITO DI INIZIAZIONE (BABEL READY)
// Gestisce il primo avvio, la scelta della lingua, l'identità e la voce.
// FIX: Sincronizzazione stato iniziale con TranslationContext.
// FIX: Risolto ReferenceError su serverUrl durante il test vocale.

import { useState, useEffect, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { UserProfile, AvailableLanguages, ServerConfig } from "@/types";
import { Loader2, Globe, User, Mic, Sparkles, Play, Check, ChevronRight, ChevronLeft } from "lucide-react";
import { toast } from "sonner";
import { getBaseUrl, getHeaders } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/contexts/TranslationContext";

interface WelcomeWizardProps {
  open: boolean;
  onComplete: (profile: UserProfile) => void;
  serverConfig: ServerConfig | null;
}

export const WelcomeWizard = ({ open, onComplete, serverConfig }: WelcomeWizardProps) => {
  const { t: t_legacy, changeLanguage, currentLang } = useTranslation(); // Alias per evitare conflitti se necessario
  const [step, setStep] = useState(0);
  
  // --- [FIX CRITICO] SINCRONIZZAZIONE STATO INIZIALE ---
  // Inizializziamo con currentLang invece di 'it' hardcodato
  const [uiLang, setUiLang] = useState<string>(currentLang || 'it'); 
  const [ttsLang, setTtsLang] = useState<string>(currentLang || 'it'); 
  
  // Form State
  const [name, setName] = useState("");
  const [gender, setGender] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [ttsEngine, setTtsEngine] = useState("vibevoice"); // Default a VibeVoice
  const [voiceId, setVoiceId] = useState("");
  
  // Data State
  const [languages, setLanguages] = useState<AvailableLanguages>({});
  const [uiLanguages, setUiLanguages] = useState<{code: string, label: string}[]>([]);
  const [isLoadingLangs, setIsLoadingLangs] = useState(false);
  const [isLoadingVoices, setIsLoadingVoices] = useState(false);
  const [isPlayingPreview, setIsPlayingPreview] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Helper traduzione (usiamo t_legacy per accedere al JSON unificato)
  const t = (key: string, params?: Record<string, string | number>) => t_legacy(`welcome_wizard.${key}`, params);

  // --- [FIX CRITICO] AGGIORNAMENTO STATO SE LA LINGUA CAMBIA ESTERNAMENTE ---
  useEffect(() => {
      if (currentLang) {
          setUiLang(currentLang);
          setTtsLang(currentLang);
      }
  }, [currentLang]);

  // Caricamento lingue UI dal server
  useEffect(() => {
    if (open && serverConfig) {
      setIsLoadingLangs(true);
      const serverUrl = getBaseUrl(serverConfig);
      const headers = getHeaders();

      fetch(`${serverUrl}/api/translations/languages`, { headers })
        .then((res) => res.json())
        .then((data) => {
          if (data.languages && Array.isArray(data.languages)) {
            setUiLanguages(data.languages);
          }
          setIsLoadingLangs(false);
        })
        .catch((err) => {
          console.error("Errore nel caricamento delle lingue:", err);
          // Fallback di sicurezza
          setUiLanguages([{code: 'en', label: 'English 🇬🇧'}, {code: 'it', label: 'Italiano 🇮🇹'}]);
          setIsLoadingLangs(false);
        });
    }
  }, [open, serverConfig]);

  // Helper robusto per l'URL del server (Bypass Trappola Localhost)
  const getSafeServerUrl = () => {
      // Se siamo in dev mode (Vite) su desktop, punta al backend locale
      if (window.location.port === '5173' || window.location.port === '3000') {
          return 'http://127.0.0.1:8080';
      }
      // In produzione (incluso mobile/ngrok), usa l'origine corrente
      return window.location.origin;
  };

  // Caricamento voci dal server (Dinamico in base al motore)
  useEffect(() => {
    if (open) {
      setIsLoadingVoices(true);
      const safeServerUrl = getSafeServerUrl();
      const headers = getHeaders();

      fetch(`${safeServerUrl}/api/tts/languages?engine=${ttsEngine}`, { headers })
        .then((res) => res.json())
        .then((data: AvailableLanguages) => {
          setLanguages(data);
          // Auto-seleziona la prima voce disponibile per la lingua corrente se esiste
          if (data[ttsLang] && data[ttsLang].voices.length > 0) {
              setVoiceId(data[ttsLang].default_voice || data[ttsLang].voices[0].id);
          } else {
              setVoiceId("");
          }
          setIsLoadingVoices(false);
        })
        .catch((err) => {
          console.error(t("err_load_voices"), err);
          setIsLoadingVoices(false);
        });
    }
  },[open, serverConfig, ttsEngine, ttsLang]); // Aggiunto ttsLang alle dipendenze per aggiornare la voce di default

  // Sincronizza lingua TTS con lingua UI quando viene scelta
  const handleUiLangSelect = (lang: string) => {
      setUiLang(lang);
      setTtsLang(lang); // Pre-imposta la lingua TTS
      changeLanguage(lang); // Aggiorna la lingua dell'interfaccia in tempo reale
      setStep(1);
  };

  // Gestione cambio lingua TTS (Step 2)
  const handleTtsLangChange = (code: string) => {
      setTtsLang(code);
      // Reset voce se cambia lingua
      const langData = languages[code];
      if (langData && langData.voices.length > 0) {
          setVoiceId(langData.default_voice);
      } else {
          setVoiceId("");
      }
  };

  const handlePreviewVoice = async () => {
      if (!voiceId) return;
      
      // Ferma eventuale audio in riproduzione
      if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current.currentTime = 0;
      }

      setIsPlayingPreview(true);
      toast.info(t("toast_preview_loading"));
      
      const testText = uiLang === 'it' ? t("preview_text_it") : t("preview_text_en");
      const safeServerUrl = getSafeServerUrl();
      
      try {
          const res = await fetch(`${safeServerUrl}/api/tts/preview`, {
              method: 'POST',
              headers: { ...getHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify({
                  text: testText,
                  voice: voiceId,
                  engine: ttsEngine,
                  lang_code: ttsLang
              })
          });

          if (!res.ok) throw new Error("Preview generation failed");
          
          const data = await res.json();
          if (data.url) {
              // --- [FIX CRITICO] REFERENCE ERROR RISOLTO E CACHE BUSTER AGGIUNTO ---
              const audio = new Audio(`${safeServerUrl}${data.url}?t=${Date.now()}`);
              audioRef.current = audio;
              
              audio.onended = () => setIsPlayingPreview(false);
              audio.onerror = (e) => {
                  console.error("Audio playback error:", e);
                  setIsPlayingPreview(false);
                  toast.error(t("err_preview_failed"));
              };
              
              await audio.play();
          }
      } catch (error) {
          console.error("Preview error:", error);
          toast.error(t("err_preview_failed"));
          setIsPlayingPreview(false);
      }
  };

  const handleFinish = async () => {
      // Salva la scelta del motore vocale nel backend prima di completare
      if (serverConfig) {
          try {
              const serverUrl = getBaseUrl(serverConfig);
              await fetch(`${serverUrl}/api/settings/tts`, {
                  method: 'POST',
                  headers: { ...getHeaders(), 'Content-Type': 'application/json' },
                  body: JSON.stringify({ 
                      active_engine: ttsEngine, 
                      vibevoice_url: "http://localhost:8880" // Default URL
                  })
              });
          } catch (e) {
              console.error("Failed to save TTS engine choice:", e);
          }
      }

      const profile: UserProfile = {
          name,
          gender,
          birthDate,
          preferredLanguage: ttsLang, // Salva la lingua TTS scelta
          preferredVoice: voiceId,
          email: "", // Opzionali, modificabili dopo
          mobileNumber: "",
          bio: ""
      };
      onComplete(profile);
  };

  // Validazione Step
  const isStep1Valid = name.trim().length > 0 && gender.length > 0;
  const isStep2Valid = ttsLang.length > 0 && voiceId.length > 0;

  const currentVoices = languages[ttsLang]?.voices || [];

  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent className="sm:max-w-md border-primary/20 shadow-2xl bg-background/95 backdrop-blur-xl flex flex-col h-[85dvh] sm:h-[600px] max-h-[100dvh] sm:max-h-[90dvh]" onPointerDownOutside={(e) => e.preventDefault()} onEscapeKeyDown={(e) => e.preventDefault()}>
        
        {/* HEADER DINAMICO */}
        <DialogHeader>
          <div className="flex items-center justify-center mb-4">
              <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary animate-pulse">
                  {step === 0 && <Globe className="w-6 h-6" />}
                  {step === 1 && <User className="w-6 h-6" />}
                  {step === 2 && <Mic className="w-6 h-6" />}
                  {step === 3 && <Sparkles className="w-6 h-6" />}
              </div>
          </div>
          <DialogTitle className="text-center text-xl">
              {step === 0 && t("step0_title")}
              {step === 1 && t("step1_title", { nome_pg: name || "Creatore" })}
              {step === 2 && t("step2_title")}
              {step === 3 && t("step3_title")}
          </DialogTitle>
          <DialogDescription className="text-center">
              {step === 0 && t("step0_desc")}
              {step === 1 && t("step1_desc")}
              {step === 2 && t("step2_desc")}
              {step === 3 && t("step3_desc")}
          </DialogDescription>
        </DialogHeader>

        {/* CONTENUTO STEP */}
        <div className="relative flex-1 min-h-0 my-2">
            <div className="absolute inset-0 overflow-y-auto custom-scrollbar px-2 py-4">
            
            {/* STEP 0: LINGUA */}
            {step === 0 && (
                <div className="grid grid-cols-2 gap-4">
                    {isLoadingLangs ? (
                        <div className="col-span-2 flex justify-center py-8">
                            <Loader2 className="animate-spin text-primary w-8 h-8" />
                        </div>
                    ) : (
                        uiLanguages.map((lang) => (
                            <Button 
                                key={lang.code}
                                variant={uiLang === lang.code ? "default" : "outline"} 
                                className={cn(
                                    "h-24 flex flex-col gap-2 transition-all whitespace-normal text-center",
                                    uiLang === lang.code ? "border-primary bg-primary/20" : "hover:border-primary hover:bg-primary/5"
                                )}
                                onClick={() => handleUiLangSelect(lang.code)}
                            >
                                <span className="font-semibold text-base sm:text-lg leading-tight">{lang.label}</span>
                            </Button>
                        ))
                    )}
                </div>
            )}

            {/* STEP 1: IDENTITÀ */}
            {step === 1 && (
                <div className="space-y-4 animate-in fade-in slide-in-from-right-4">
                    <div className="space-y-2">
                        <Label className="text-primary">{t("label_name")}</Label>
                        <Input 
                            value={name} 
                            onChange={(e) => setName(e.target.value)} 
                            placeholder={t("name_placeholder")}
                            className="text-lg"
                            autoFocus
                        />
                    </div>
                    <div className="space-y-2">
                        <Label className="text-primary">{t("label_gender")}</Label>
                        <Select value={gender} onValueChange={setGender}>
                            <SelectTrigger><SelectValue placeholder={t("select_placeholder")} /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="Male">{t("gender_male")}</SelectItem>
                                <SelectItem value="Female">{t("gender_female")}</SelectItem>
                                <SelectItem value="Non-binary">{t("gender_nonbinary")}</SelectItem>
                                <SelectItem value="Other">{t("gender_other")}</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-2">
                        <Label>{t("label_birthdate")}</Label>
                        <Input 
                            type="date" 
                            value={birthDate} 
                            onChange={(e) => setBirthDate(e.target.value)} 
                        />
                    </div>
                </div>
            )}

            {/* STEP 2: VOCE */}
            {step === 2 && (
                <div className="space-y-4 animate-in fade-in slide-in-from-right-4">
                    <div className="space-y-2">
                        <Label className="text-primary">{t("label_engine")}</Label>
                        <Select value={ttsEngine} onValueChange={setTtsEngine}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="vibevoice">{t("engine_vibevoice")}</SelectItem>
                                <SelectItem value="kokoro">{t("engine_kokoro")}</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {isLoadingVoices ? (
                        <div className="flex justify-center py-8"><Loader2 className="animate-spin text-primary w-6 h-6" /></div>
                    ) : (
                        <>
                            <div className="space-y-2">
                                <Label className="text-primary">{t("label_lang")}</Label>
                                <Select value={ttsLang} onValueChange={handleTtsLangChange}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        {Object.entries(languages).map(([code, info]) => (
                                            <SelectItem key={code} value={code}>{info.name}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label className="text-primary">{t("label_voice")}</Label>
                                <Select value={voiceId} onValueChange={setVoiceId}>
                                    <SelectTrigger><SelectValue placeholder={t("select_placeholder")} /></SelectTrigger>
                                    <SelectContent>
                                        {currentVoices.map(v => (
                                            <SelectItem key={v.id} value={v.id}>
                                                {v.name} ({v.gender})
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            
                            <Button 
                                variant="secondary" 
                                size="sm" 
                                className="w-full mt-4 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20" 
                                onClick={handlePreviewVoice} 
                                disabled={!voiceId || isPlayingPreview}
                            >
                                {isPlayingPreview ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Play className="w-4 h-4 mr-2" />}
                                {t("preview_voice")}
                            </Button>
                        </>
                    )}
                </div>
            )}

            {/* STEP 3: RIEPILOGO */}
            {step === 3 && (
                <div className="space-y-4 animate-in fade-in slide-in-from-right-4 text-center">
                    <div className="p-4 bg-muted/30 rounded-lg border border-border space-y-2">
                        <p><span className="text-muted-foreground">{t("summary_name")}</span> <span className="font-bold text-lg">{name}</span></p>
                        <p><span className="text-muted-foreground">{t("summary_gender")}</span> <span className="font-medium">{gender}</span></p>
                        <p><span className="text-muted-foreground">{t("summary_lang")}</span> <span className="font-medium">{languages[ttsLang]?.name}</span></p>
                        <p><span className="text-muted-foreground">{t("summary_voice")}</span> <span className="font-medium">{voiceId}</span></p>
                    </div>
                    <p className="text-xs text-muted-foreground italic">
                        {t("pact_text")}
                    </p>
                </div>
            )}

            </div>
        </div>

        {/* FOOTER NAVIGAZIONE */}
        <DialogFooter className="flex justify-between sm:justify-between gap-2 mt-2">
            {step > 0 && (
                <Button variant="ghost" onClick={() => setStep(step - 1)}>
                    <ChevronLeft className="w-4 h-4 mr-1" /> {t("btn_back")}
                </Button>
            )}
            
            <div className="flex-1"></div>

            {step === 1 && (
                <Button onClick={() => setStep(2)} disabled={!isStep1Valid}>
                    {t("btn_next")} <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
            )}
            {step === 2 && (
                <Button onClick={() => setStep(3)} disabled={!isStep2Valid}>
                    {t("btn_next")} <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
            )}
            {step === 3 && (
                <Button onClick={handleFinish} className="bg-primary hover:bg-primary/90 text-white w-full sm:w-auto">
                    <Sparkles className="w-4 h-4 mr-2" /> {t("btn_finish")}
                </Button>
            )}
        </DialogFooter>

      </DialogContent>
    </Dialog>
  );
};