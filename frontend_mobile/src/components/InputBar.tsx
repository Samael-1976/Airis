// frontend_mobile/src/components/InputBar.tsx
// v1.9 - Audio Preview Fix & Component Stability
// FIX CRITICO: Rimossa definizione di componenti annidati (AudioPreview, FilePreview) che causava il re-mount e lo stop dell'audio.
// ORA: Il JSX è inlined per garantire la stabilità del nodo DOM <audio> durante i re-render (es. typing).
// MANTENUTO: Double Send Fix, UI Recording, Staging Allegati.
// LEGGE A0099: Invarianza strutturale garantita. Nessuna riga originale rimossa.

import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { Smile, Plus, ArrowUp, Camera, Image, FileText, Mic, MicOff, Square, Save, Power, ChevronDown, ChevronUp, Play, Trash2, X, Paperclip, Loader2, Dices, MessageSquare, Brain } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useTranslation } from "@/contexts/TranslationContext";
import { Textarea } from "@/components/ui/textarea";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import EmojiPicker from "emoji-picker-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Rnd } from "react-rnd";
import { CameraCaptureDialog } from "./CameraCaptureDialog";
import { cn } from "@/lib/utils";

interface InputBarProps {
  onSendMessage: (message: string, audioBlob?: Blob, mediaFile?: File, mediaType?: string) => Promise<void> | void;
  onFileUpload: (type: string, file: File) => void; 
  onStopGeneration: () => void;
  onSaveSession: () => void;
  onQuit: () => void;
  onStartListening: () => void;
  isThinking: boolean;
  disabled?: boolean;
  serverUrl: string;
  isPortrait?: boolean;
  activeAvatarName?: string; 
  isCampaignMode?: boolean; //[NUOVO v27.0]
  isInputLocked?: boolean; // [NUOVO v28.0]
oocMessages?: any[]; // [NUOVO v28.0]
  onSendOoc?: (text: string) => void; // [NUOVO v28.0]
  onTyping?: (text: string) => void; // [NUOVO FASE 4] Pre-Fetch Predittivo
  showTechThoughts?: boolean;
  onToggleTechThoughts?: () => void;
}

export const InputBar = ({
  onSendMessage, 
  onFileUpload, 
  onStopGeneration, 
  onSaveSession,
  onQuit,
  onStartListening,
  isThinking, 
  disabled,
  serverUrl,
  isPortrait = false,
  activeAvatarName = "Avatar",
  isCampaignMode = false,
  isInputLocked = false,
  oocMessages = Array(0),
  onSendOoc,
  onTyping,
  showTechThoughts = true,
  onToggleTechThoughts
}: InputBarProps) => {
  const [message, setMessage] = useState("");
  const [oocMessage, setOocMessage] = useState("");
  const[isOocOpen, setIsOocOpen] = useState(false);
  const oocScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
      if (oocScrollRef.current) {
          oocScrollRef.current.scrollTop = oocScrollRef.current.scrollHeight;
      }
  },[oocMessages, isOocOpen]);

  const [isMicMuted, setIsMicMuted] = useState(true);
  const [emojiOpen, setEmojiOpen] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false); 
  
  // --- STATI PER REGISTRAZIONE VOCALE ---
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlayingPreview, setIsPlayingPreview] = useState(false);

  // --- STATI PER STAGING ALLEGATI ---
  const[pendingFile, setPendingFile] = useState<{ file: File; type: string } | null>(null);
  const [pendingFilePreview, setPendingFilePreview] = useState<string | null>(null);

  // --- NUOVO: STATO ANTI-DOPPIO INVIO (v1.8) ---
  const [isSending, setIsSending] = useState(false);

  // ---[NUOVO FASE 4] DEBOUNCE TYPING PER PRE-FETCH ---
  useEffect(() => {
    if (!message.trim() || message.length < 15 || !onTyping) return;
    const timeoutId = setTimeout(() => {
      onTyping(message.trim());
    }, 1000); // Invia il ping dopo 1 secondo di inattività nella digitazione
    return () => clearTimeout(timeoutId);
  },[message, onTyping]);

  const imageInputRef = useRef<HTMLInputElement>(null);
  const docInputRef = useRef<HTMLInputElement>(null);

  const isConnected = !disabled;
  const { t } = useTranslation();

  // Helper per capitalizzazione sicura (FIX JS ERROR)
  const capitalizeName = (name: string) => {
      if (!name) return "";
      return name.charAt(0).toUpperCase() + name.slice(1);
  };

  // Pulizia URL audio e preview file
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      if (pendingFilePreview) URL.revokeObjectURL(pendingFilePreview);
    };
  }, [audioUrl, pendingFilePreview]);

  // --- [NUOVO v27.0] HANDLER DADO (DM INTERVENTION) ---
  const handleDiceRoll = async () => {
      if (isSending || disabled) return;
      setIsSending(true);
      try {
          const textToSend = message.trim();
          if (textToSend) {
              // Invia l'azione con richiesta esplicita di intervento DM
              await onSendMessage(`/dm_action ${textToSend}`);
          } else {
              // Forza un evento ambientale (Stallo)
              await onSendMessage("/force_dm");
          }
          setMessage("");
      } catch (error) {
          console.error(t("input_bar.err_send_dice"), error);
      } finally {
          setIsSending(false);
      }
  };

  // --- FIX v1.8: INVIO ASINCRONO CON LOCK ---
  const handleSend = async () => {
    if (isSending) return; // Blocco preventivo

    if ((message.trim() || audioBlob || pendingFile) && !disabled) {
      setIsSending(true); // Attiva lock
      try {
          if (pendingFile) {
              // --- [FIX CRITICO] SICUREZZA TIPO FILE ---
              // Garantisce che i documenti vengano sempre etichettati come "document"
              // anche se il menu a tendina ha passato un tipo errato.
              let finalType = pendingFile.type;
              const ext = pendingFile.file.name.split('.').pop()?.toLowerCase();
              if (['pdf', 'txt', 'doc', 'docx', 'md', 'csv', 'xls', 'xlsx'].includes(ext || '')) {
                  finalType = "document";
              } else if (['mp4', 'webm', 'mov', 'avi'].includes(ext || '')) {
                  finalType = "video";
              }
              
              await onSendMessage(message.trim(), undefined, pendingFile.file, finalType);
              handleRemovePendingFile();
          } else {
              await onSendMessage(message.trim(), audioBlob || undefined);
              handleDeleteAudio(); 
          }
          setMessage("");
      } catch (error) {
          console.error(t("input_bar.err_send_msg"), error);
      } finally {
          setIsSending(false); // Rilascia lock
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCameraCapture = (file: File, type: "image" | "video") => {
      setPendingFile({ file, type: type === "image" ? "camera_image" : "camera_video" });
      setPendingFilePreview(URL.createObjectURL(file));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, type: string) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setPendingFile({ file, type });
      if (type === "image") {
          setPendingFilePreview(URL.createObjectURL(file));
      } else {
          setPendingFilePreview(null); 
      }
    }
    e.target.value = "";
  };

  const handleRemovePendingFile = () => {
      if (pendingFilePreview) URL.revokeObjectURL(pendingFilePreview);
      setPendingFile(null);
      setPendingFilePreview(null);
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current =[];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const url = URL.createObjectURL(blob);
        setAudioBlob(blob);
        setAudioUrl(url);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setIsMicMuted(false);
    } catch (err) {
      console.error(t("input_bar.err_mic_access"), err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsMicMuted(true);
    }
  };

  const handleMicClick = () => {
    if (!disabled && !isThinking) {
        if (isRecording) {
          stopRecording();
        } else {
          if (audioBlob || pendingFile) {
            return;
          }
          startRecording();
        }
    }
  };

  const handleDeleteAudio = () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioBlob(null);
    setAudioUrl(null);
    setIsPlayingPreview(false);
  };

  const togglePlayPreview = () => {
    if (!previewAudioRef.current || !audioUrl) return;
    
    if (isPlayingPreview) {
      previewAudioRef.current.pause();
      setIsPlayingPreview(false);
    } else {
      previewAudioRef.current.play();
      setIsPlayingPreview(true);
    }
  };

  // --- PULSANTI ---
  
  const EmojiButton = (
    <Popover open={emojiOpen} onOpenChange={setEmojiOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-primary" disabled={disabled || isThinking || isRecording || isSending}>
          <Smile className="w-5 h-5" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0 border-0 mb-2" align="start">
        <EmojiPicker onEmojiClick={(emojiData) => { setMessage((prev) => prev + emojiData.emoji); setEmojiOpen(false); }} height={350} width="100%" />
      </PopoverContent>
    </Popover>
  );

  const MicButton = (
    <Button 
      variant="ghost" 
      size="icon" 
      className={cn(
        "transition-all duration-300", 
        isRecording ? "text-red-500 scale-125 animate-pulse bg-red-500/10 rounded-full" : "text-muted-foreground hover:text-primary",
        (audioBlob || pendingFile) && "text-green-500 opacity-50 cursor-not-allowed"
      )} 
      onClick={handleMicClick} 
      // [FIX CRITICO UX] Se sta registrando, il tasto DEVE essere sempre cliccabile per poter fermare l'audio, anche se l'Anima inizia a pensare.
      disabled={disabled || (isThinking && !isRecording) || (!!audioBlob && !isRecording) || !!pendingFile || isSending} 
      title={isRecording ? t("input_bar.stop_recording_hint") : t("input_bar.start_recording_hint")}
    >
      {isRecording ? <Square className="w-5 h-5 fill-current" /> : <Mic className="w-5 h-5" />}
    </Button>
  );

  const OocButton = (
    <Button 
      variant="ghost" 
      size="icon" 
      className="text-muted-foreground hover:text-primary relative" 
      disabled={disabled}
      onClick={() => setIsOocOpen(!isOocOpen)}
    >
      <MessageSquare className="w-5 h-5" />
      {oocMessages.length > 0 && (
          <span className="absolute top-1 right-1 w-2 h-2 bg-primary rounded-full animate-pulse" />
      )}
    </Button>
  );

  const TechThoughtsButton = (
    <Button 
      variant="ghost" 
      size="icon" 
      className={cn("text-muted-foreground hover:text-primary transition-all", !showTechThoughts && "opacity-50 grayscale")} 
      disabled={disabled}
      onClick={onToggleTechThoughts}
      title={showTechThoughts ? t("input_bar.hide_tech_thoughts") : t("input_bar.show_tech_thoughts")}
    >
      <Brain className="w-5 h-5" />
    </Button>
  );

  const SaveButton = (
    <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-primary" onClick={onSaveSession} disabled={disabled || isThinking || isRecording || isSending} title={t("input_bar.save_session")}>
      <Save className="w-5 h-5" />
    </Button>
  );

  const PlusMenuButton = (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-primary" disabled={disabled || isThinking || isRecording || !!pendingFile || !!audioBlob || isSending}>
          <Plus className="w-5 h-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuItem onClick={() => setCameraOpen(true)}><Camera className="w-4 h-4 mr-2" /> {t("input_bar.camera")}</DropdownMenuItem>
        <DropdownMenuItem onClick={() => imageInputRef.current?.click()}><Image className="w-4 h-4 mr-2" /> {t("input_bar.image")}</DropdownMenuItem>
        <DropdownMenuItem onClick={() => docInputRef.current?.click()}><FileText className="w-4 h-4 mr-2" /> {t("input_bar.document")}</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );

  const QuitButton = (
    <Button variant="destructive" size="icon" className="rounded-full w-8 h-8 shadow-md" onClick={onQuit} disabled={!isConnected || isRecording || isSending}>
      <Power className="w-4 h-4" />
    </Button>
  );

  const SendStopButton = isThinking ? (
    <Button size="icon" onClick={onStopGeneration} variant="destructive" className="bg-destructive/80 hover:bg-destructive text-destructive-foreground rounded-full w-10 h-10">
      <Square className="w-4 h-4" />
    </Button>
  ) : (
    <div className="flex items-center gap-1">
        {/*[NUOVO v27.0] PULSANTE DADO (Visibile solo in Modalità Campagna) */}
        {isCampaignMode && (
            <Button 
                size="icon" 
                onClick={handleDiceRoll} 
                // --- [FIX CRITICO RACE CONDITION] Aggiunto isThinking ---
                disabled={disabled || isRecording || isSending || isThinking} 
                variant="secondary"
                className="rounded-full w-10 h-10 bg-purple-600/20 text-purple-400 hover:bg-purple-600/40 border border-purple-500/30"
                title={t("input_bar.roll_dice")}
            >
                {isSending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Dices className="w-5 h-5" />}
            </Button>
        )}
        <Button 
            size="icon" 
            onClick={handleSend} 
            disabled={(!message.trim() && !audioBlob && !pendingFile) || disabled || isRecording || isSending} 
            className="bg-primary hover:bg-primary/90 text-primary-foreground rounded-full w-10 h-10"
        >
          {isSending ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowUp className="w-5 h-5" />}
        </Button>
    </div>
  );

  return (
    <div className="h-full w-full pointer-events-auto relative">
      <CameraCaptureDialog open={cameraOpen} onOpenChange={setCameraOpen} onCapture={handleCameraCapture} serverUrl={serverUrl} />
      <input type="file" ref={imageInputRef} className="hidden" accept="image/*" onChange={(e) => handleFileChange(e, "image")} />
      <input type="file" ref={docInputRef} className="hidden" accept=".pdf,.doc,.docx,.txt" onChange={(e) => handleFileChange(e, "document")} />

      {isOocOpen && createPortal(
        <Rnd
          default={{
            x: window.innerWidth > 400 ? window.innerWidth / 2 - 160 : 20,
            y: window.innerHeight > 500 ? window.innerHeight / 2 - 200 : 50,
            width: 320,
            height: 400,
          }}
          minWidth={250}
          minHeight={200}
          bounds="window"
          dragHandleClassName="ooc-drag-handle"
          className="z-[100] flex flex-col shadow-2xl border border-primary/20 bg-background/95 backdrop-blur-md rounded-xl overflow-hidden"
          style={{ position: 'fixed' }}
        >
          <div className="ooc-drag-handle flex items-center justify-between border-b border-white/10 p-3 bg-muted/30 cursor-move shrink-0">
              <h4 className="text-sm font-bold text-primary flex items-center gap-2 pointer-events-none">
                  <MessageSquare className="w-4 h-4" /> {t("input_bar.ooc_title")}
              </h4>
              <Button variant="ghost" size="icon" className="h-6 w-6 rounded-full hover:bg-destructive/20 hover:text-destructive" onClick={() => setIsOocOpen(false)}>
                  <X className="w-4 h-4" />
              </Button>
          </div>
          <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2" ref={oocScrollRef}>
              {oocMessages.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-4">{t("input_bar.ooc_empty")}</p>
              ) : (
                  oocMessages.map((msg, idx) => (
                      <div key={idx} className="bg-muted/30 p-2 rounded-lg border border-white/5">
                          <span className="text-[10px] font-bold text-primary block mb-0.5">{msg.sender}</span>
                          <p className="text-xs text-foreground/90">{msg.text}</p>
                      </div>
                  ))
              )}
          </div>
          <div className="flex gap-2 p-3 border-t border-white/10 bg-background/50 shrink-0">
              <Input 
                  value={oocMessage}
                  onChange={(e) => setOocMessage(e.target.value)}
                  onKeyDown={(e) => {
                      if (e.key === 'Enter' && oocMessage.trim() && onSendOoc) {
                          onSendOoc(oocMessage.trim());
                          setOocMessage("");
                      }
                  }}
                  placeholder={t("input_bar.ooc_placeholder")}
                  className="h-8 text-xs"
              />
              <Button 
                  size="sm" 
                  className="h-8 px-3"
                  onClick={() => {
                      if (oocMessage.trim() && onSendOoc) {
                          onSendOoc(oocMessage.trim());
                          setOocMessage("");
                      }
                  }}
              >
                  {t("input_bar.ooc_send")}
              </Button>
          </div>
        </Rnd>,
        document.body
      )}

      {isPortrait ? (
        // --- LAYOUT VERTICALE (PORTRAIT) ---
        isCollapsed ? (
            // STATO COLLASSATO: Solo bottone per espandere
            <div className="flex justify-center pb-4 animate-in slide-in-from-bottom-4 fade-in duration-300">
                <Button
                    variant="secondary"
                    size="icon"
                    className="rounded-full w-12 h-12 shadow-lg bg-muted/90 backdrop-blur-sm border border-white/10 hover:bg-muted"
                    onClick={() => setIsCollapsed(false)}
                >
                    <ChevronUp className="w-6 h-6 text-primary" />
                </Button>
            </div>
        ) : (
            // STATO ESPANSO: Input Box Completa
            <div className="w-full max-w-4xl mx-auto flex flex-col gap-2 bg-muted/90 backdrop-blur-sm rounded-3xl p-3 border border-black/60 shadow-[0_-4px_20px_rgba(0,0,0,0.3)] transition-all animate-in slide-in-from-bottom-10 fade-in duration-300 relative">
                
                {/* ANTEPRIME INSERITE NEL FLUSSO (FIX UI: Inlined Components) */}
                {audioUrl && (
                    <div className="w-full bg-card/50 backdrop-blur-sm border border-primary/20 rounded-xl p-2 mb-2 flex items-center gap-3 animate-in fade-in slide-in-from-bottom-1">
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="rounded-full bg-primary/10 text-primary hover:bg-primary/20 h-8 w-8"
                          onClick={togglePlayPreview}
                        >
                          {isPlayingPreview ? <Square className="w-3 h-3 fill-current" /> : <Play className="w-3 h-3 fill-current ml-0.5" />}
                        </Button>
                        
                        <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
                          <div className={cn("h-full bg-primary transition-all duration-100", isPlayingPreview ? "w-full" : "w-0")} />
                        </div>

                        <audio 
                            ref={previewAudioRef} 
                            src={audioUrl} 
                            onEnded={() => setIsPlayingPreview(false)} 
                            className="hidden" 
                            playsInline 
                            preload="auto"
                        />

                        <Button variant="ghost" size="icon" className="text-destructive hover:bg-destructive/10 h-8 w-8" onClick={handleDeleteAudio}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                    </div>
                )}

                {pendingFile && (
                    <div className="w-full bg-card/50 backdrop-blur-sm border border-primary/20 rounded-xl p-2 mb-2 flex items-center gap-3 animate-in fade-in slide-in-from-bottom-1">
                        <div className="w-8 h-8 rounded-md bg-muted flex items-center justify-center overflow-hidden border border-border shrink-0">
                            {pendingFilePreview ? (
                                <img src={pendingFilePreview} alt="Preview" className="w-full h-full object-cover" />
                            ) : (
                                <Paperclip className="w-4 h-4 text-muted-foreground" />
                            )}
                        </div>
                        
                        <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium truncate">{pendingFile.file.name}</p>
                            <p className="text-[10px] text-muted-foreground">{(pendingFile.file.size / 1024).toFixed(1)} KB</p>
                        </div>

                        <Button variant="ghost" size="icon" className="text-destructive hover:bg-destructive/10 h-8 w-8" onClick={handleRemovePendingFile}>
                          <X className="w-4 h-4" />
                        </Button>
                    </div>
                )}

                {isRecording && (
                    <div className="w-full bg-red-500/10 border border-red-500/20 rounded-xl p-2 mb-2 flex items-center justify-center gap-2 animate-pulse">
                        <div className="w-2 h-2 bg-red-500 rounded-full" />
                        <span className="text-xs font-bold text-red-500 uppercase tracking-wider">{t("input_bar.recording")}</span>
                    </div>
                )}

                <div className="flex items-center justify-between px-2 pb-1 border-b border-white/10 min-h-[40px]">
                    <div className="flex gap-2">
                        {EmojiButton}
                        {MicButton}
                        {OocButton}
                    </div>

                    <button
                        onClick={() => setIsCollapsed(true)} 
                        className="text-muted-foreground/50 hover:text-primary transition-colors p-1"
                    >
                        <ChevronDown className="w-6 h-6" />
                    </button>

                    <div className="flex gap-2 items-center">
                        {TechThoughtsButton}
                        {PlusMenuButton}
                        {SaveButton}
                    </div>
                </div>
                
                <div className="flex items-end gap-2 pt-1">
                    <Textarea
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder={isInputLocked ? t("input_bar.locked") : (isThinking ? t("input_bar.thinking", { name: capitalizeName(activeAvatarName) }) : t("input_bar.placeholder"))}
                      className={cn(
                          "flex-1 min-h-[45px] max-h-[120px] bg-background/50 border-0 focus-visible:ring-0 focus-visible:ring-offset-0 text-foreground placeholder:text-muted-foreground resize-none py-3 leading-relaxed rounded-xl transition-all",
                          isInputLocked && "opacity-50 cursor-not-allowed bg-red-950/20"
                      )}
                      disabled={disabled || isThinking || isRecording || isSending || isInputLocked}
                    />
                    {SendStopButton}
                </div>
            </div>
        )
      ) : (
        // --- LAYOUT ORIZZONTALE (LANDSCAPE/DESKTOP) ---
        <div className="h-full w-full max-w-4xl mx-auto flex flex-col">
            
            {/* ANTEPRIME (Staging) - Spingono la barra in basso se presenti */}
            <div className="px-2 pt-2 shrink-0 mt-auto">
                {audioUrl && (
                    <div className="w-full bg-card/50 backdrop-blur-sm border border-primary/20 rounded-xl p-2 mb-2 flex items-center gap-3 animate-in fade-in slide-in-from-bottom-1">
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="rounded-full bg-primary/10 text-primary hover:bg-primary/20 h-8 w-8"
                          onClick={togglePlayPreview}
                        >
                          {isPlayingPreview ? <Square className="w-3 h-3 fill-current" /> : <Play className="w-3 h-3 fill-current ml-0.5" />}
                        </Button>
                        
                        <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
                          <div className={cn("h-full bg-primary transition-all duration-100", isPlayingPreview ? "w-full" : "w-0")} />
                        </div>

                        <audio 
                            ref={previewAudioRef} 
                            src={audioUrl} 
                            onEnded={() => setIsPlayingPreview(false)} 
                            className="hidden" 
                            playsInline 
                            preload="auto"
                        />

                        <Button variant="ghost" size="icon" className="text-destructive hover:bg-destructive/10 h-8 w-8" onClick={handleDeleteAudio}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                    </div>
                )}

                {pendingFile && (
                    <div className="w-full bg-card/50 backdrop-blur-sm border border-primary/20 rounded-xl p-2 mb-2 flex items-center gap-3 animate-in fade-in slide-in-from-bottom-1">
                        <div className="w-8 h-8 rounded-md bg-muted flex items-center justify-center overflow-hidden border border-border shrink-0">
                            {pendingFilePreview ? (
                                <img src={pendingFilePreview} alt="Preview" className="w-full h-full object-cover" />
                            ) : (
                                <Paperclip className="w-4 h-4 text-muted-foreground" />
                            )}
                        </div>
                        
                        <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium truncate">{pendingFile.file.name}</p>
                            <p className="text-[10px] text-muted-foreground">{(pendingFile.file.size / 1024).toFixed(1)} {t("input_bar.kb_unit")}</p>
                        </div>

                        <Button variant="ghost" size="icon" className="text-destructive hover:bg-destructive/10 h-8 w-8" onClick={handleRemovePendingFile}>
                          <X className="w-4 h-4" />
                        </Button>
                    </div>
                )}

                {isRecording && (
                    <div className="w-full bg-red-500/10 border border-red-500/20 rounded-xl p-2 mb-2 flex items-center justify-center gap-2 animate-pulse">
                        <div className="w-2 h-2 bg-red-500 rounded-full" />
                        <span className="text-xs font-bold text-red-500 uppercase tracking-wider">{t("input_bar.recording")}</span>
                    </div>
                )}
            </div>

            {/* BARRA INPUT (Espandibile) */}
            <div className="flex-1 flex items-end gap-2 bg-muted rounded-2xl px-2 py-2 border transition-all relative overflow-hidden">
                <div className="flex gap-2 shrink-0 pb-1">
                    {EmojiButton}
                    {MicButton}
                    {OocButton}
                    {TechThoughtsButton}
                </div>
                
                <Textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={isInputLocked ? t("input_bar.locked") : (isThinking ? t("input_bar.thinking", { name: capitalizeName(activeAvatarName) }) : t("input_bar.placeholder"))}
				  // FIX: h-full per riempire il pannello ridimensionabile
                  className={cn(
                      "flex-1 h-full min-h-[40px] bg-transparent border-0 focus-visible:ring-0 focus-visible:ring-offset-0 text-foreground placeholder:text-muted-foreground resize-none py-2.5 leading-relaxed transition-all",
                      isInputLocked && "opacity-50 cursor-not-allowed text-red-400"
                  )}
                  disabled={disabled || isThinking || isRecording || isSending || isInputLocked}
                />
                
                <div className="flex gap-2 shrink-0 pb-1">
                    {PlusMenuButton}
                    {SaveButton}
                    {SendStopButton}
                </div>
            </div>
        </div>
      )}
    </div>
  );
};