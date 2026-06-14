// frontend_mobile/src/components/ChatArea.tsx
// v13.1 - FILE LINK ROUTING FIX
// FIX: Routing intelligente dei link file.
//      - Export (.zip) -> /download/ (cartella exports)
//      - Asset Generati -> /documents/ (cartella documents)
// MANTENUTO: Ghost Text, Audio Waveform, Smart Icons.
// LEGGE A0099: Invarianza strutturale garantita.

import { useEffect, useRef, useState, useMemo } from "react";
import { ChatMessage } from "@/types";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Copy, Edit, Trash2, RefreshCw, FileText, Loader2, Play, Square, Mic, FileCode, Download, ExternalLink, Ghost, Heart, ShieldAlert, Ban, Eye, X } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useSecureMedia } from "@/hooks/useSecureMedia";
import { useTranslation } from "@/contexts/TranslationContext";
import { Virtuoso, VirtuosoHandle } from "react-virtuoso";
import { CombatEntity } from "@/types"; // [NUOVO v27.0]
import { Progress } from "@/components/ui/progress"; // [NUOVO v27.0]
import dmIcon from "@/images/DMS.png"; // [NUOVO] Icona fissa per il Dungeon Master

interface ChatAreaProps {
  messages: ChatMessage[];
  isThinking: boolean;
  thinkingAction?: "thinking" | "studying";
  activeAvatarName: string;
  pngAvatarUrls: Record<string, string>;
  serverUrl: string;
  userName: string; 
  onEdit: (messageId: string, newContent: string) => void;
  onReRun: (messageId: string) => void;
  onDelete: (messageId: string) => void;
  isPortrait?: boolean;
  // --- [NUOVO v13.0] GHOST PROPS ---
  ghostText?: string;
  ghostStatus?: 'hidden' | 'typing' | 'deleting';
  // ---[NUOVO v27.0] RPG PROPS ---
  combatEntities?: CombatEntity[];
  onAvatarClick?: (characterName: string) => void; // [NUOVO] Prop per click su miniatura
  aiAvatarUrl?: string; // [FIX BUG 1] Prop per l'immagine dell'Avatar principale
}

// --- SUB-COMPONENTS PER CARICAMENTO SICURO ---

const SecureImage = ({ src, alt, className }: { src: string, alt: string, className?: string }) => {
  const { url, loading } = useSecureMedia(src);
  if (loading) return <div className="flex items-center justify-center h-32 w-full bg-muted/20 rounded-lg"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>;
  return <img src={url || ""} alt={alt} className={className} />;
};

const SecureVideo = ({ src, className }: { src: string, className?: string }) => {
  const { url, loading } = useSecureMedia(src);
  if (loading) return <div className="flex items-center justify-center h-32 w-full bg-muted/20 rounded-lg"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>;
  return <video src={url || ""} controls className={className} />;
};

// --- AUDIO MESSAGE BUBBLE (v10.2 - Pink Pill & Stop Icon) ---
const AudioMessageBubble = ({ src, isUser }: { src: string, isUser: boolean }) => {
    const { t } = useTranslation();
    const { url, loading } = useSecureMedia(src);
    const audioRef = useRef<HTMLAudioElement>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);

    useEffect(() => {
        const audio = audioRef.current;
        if (!audio) return;

        const updateTime = () => setCurrentTime(audio.currentTime);
        const updateDuration = () => setDuration(audio.duration);
        const onEnded = () => setIsPlaying(false);

        audio.addEventListener('timeupdate', updateTime);
        audio.addEventListener('loadedmetadata', updateDuration);
        audio.addEventListener('ended', onEnded);

        return () => {
            audio.removeEventListener('timeupdate', updateTime);
            audio.removeEventListener('loadedmetadata', updateDuration);
            audio.removeEventListener('ended', onEnded);
        };
    }, [url]);

    const togglePlay = () => {
        if (!audioRef.current) return;
        if (isPlaying) {
            audioRef.current.pause();
            setIsPlaying(false);
        } else {
            audioRef.current.play();
            setIsPlaying(true);
        }
    };

    const formatTime = (time: number) => {
        if (isNaN(time)) return "0:00";
        const minutes = Math.floor(time / 60);
        const seconds = Math.floor(time % 60);
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    };

    // Generazione barre waveform simulate
    const bars = useMemo(() => Array.from({ length: 20 }, () => Math.floor(Math.random() * 60) + 20), []);

    if (loading) return <div className="flex items-center gap-2 p-2"><Loader2 className="w-4 h-4 animate-spin" /> <span className="text-xs">{t("chat_area.loading_audio")}</span></div>;

    return (
        <div className={cn(
            "flex items-center gap-3 p-2 transition-all shadow-sm",
            isUser 
                ? "bg-primary/90 backdrop-blur-md border border-white/20 rounded-full pr-6 pl-2" 
                : "bg-muted/40 border border-white/10 rounded-xl"
        )}>
            <Button 
                variant="ghost" 
                size="icon" 
                className={cn(
                    "h-10 w-10 rounded-full shrink-0 shadow-md transition-transform active:scale-95", 
                    isUser 
                        ? "bg-white text-primary hover:bg-white/90" 
                        : "bg-white/10 hover:bg-white/20"
                )}
                onClick={togglePlay}
            >
                {/* FIX: Icona Square (Stop) quando suona, Play quando è in pausa */}
                {isPlaying ? <Square className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
            </Button>

            <div className="flex flex-col gap-0.5 flex-1 min-w-0 justify-center">
                {/* Waveform Visualizer */}
                <div className="flex items-center gap-[3px] h-6 w-full overflow-hidden">
                    {bars.map((height, i) => (
                        <div 
                            key={i} 
                            className={cn(
                                "w-1 rounded-full transition-all duration-300",
                                isUser ? "bg-white" : "bg-foreground/50",
                                isPlaying ? "animate-waveform" : "opacity-60" // [FIX] Uso classe CSS dedicata
                            )}
                            style={{ 
                                height: `${height}%`, // [FIX] Altezza base fissa, l'animazione scala in Y
                                animationDelay: `${i * 0.05}s`
                            }} 
                        />
                    ))}
                </div>
                <div className={cn(
                    "flex justify-between text-[10px] font-mono px-1",
                    isUser ? "text-white/90" : "opacity-70"
                )}>
                    <span>{formatTime(currentTime)}</span>
                    <span>{formatTime(duration)}</span>
                </div>
            </div>

            <audio ref={audioRef} src={url || ""} className="hidden" />
        </div>
    );
};

// ---------------------------------------------------------

// ---[FIX CRITICO] FOOTER ESTRATTO PER PREVENIRE UNMOUNT SU MOBILE ---
const ChatFooter = ({ context }: { context: any }) => {
  const { isThinking, thinkingAction, activeAvatarName, thinkingAvatarUrl, t } = context;
  
  // Controllo per l'icona del Dungeon Master
  const isDM = activeAvatarName === "Dungeon Master" || activeAvatarName === "Narrator";
  
  const actionText = thinkingAction === "studying" ? t("chat_area.studying") : t("chat_area.thinking");

  return (
    <div className="flex flex-col gap-2 pb-2">
      {/* THINKING/STUDYING INDICATOR */}
      {isThinking && (
          <div className="flex items-end gap-3 animate-in fade-in py-2 px-4">
              <Avatar className="w-8 h-8 flex-shrink-0 border border-border">
              {isDM ? (
                  <AvatarImage src={dmIcon} alt="DM" className="object-cover" />
              ) : (
                  <AvatarImage src={thinkingAvatarUrl} alt={activeAvatarName} className="object-cover" />
              )}
              <AvatarFallback>{activeAvatarName.charAt(0).toUpperCase()}</AvatarFallback>
              </Avatar>
              <div 
              className="bg-muted text-foreground rounded-2xl px-4 py-2.5 max-w-[85%] sm:max-w-[75%] rounded-bl-none shadow-sm"
              style={{ transform: 'translateZ(0)', backfaceVisibility: 'hidden' }}
              >
              <div className="flex items-center gap-2">
                  <span className="text-sm capitalize font-medium">{activeAvatarName} {actionText}</span>
                  <div className="flex gap-1 items-center h-4">
                  <span className="animate-[bounce_1s_infinite_0.1s] w-1.5 h-1.5 bg-current rounded-full"></span>
                  <span className="animate-[bounce_1s_infinite_0.2s] w-1.5 h-1.5 bg-current rounded-full"></span>
                  <span className="animate-[bounce_1s_infinite_0.3s] w-1.5 h-1.5 bg-current rounded-full"></span>
                  </div>
              </div>
              </div>
          </div>
      )}
      
      {/* SPACER SE NON È ATTIVO */}
      {!isThinking && <div className="h-4" />}
    </div>
  );
};

// // Helper per formattare il testo (Grassetto, Corsivo e Sanitizzazione Variabili)
// AGGIORNAMENTO v11.3: Regex Potenziata per { pg_name }
const renderFormattedText = (text: string, userName: string, t: any) => {
  if (!text) return null;

  // --- FIX FRONTEND MASK: Sostituzione variabili residue ---
  const nameToUse = userName || t("chat_area.creator_fallback");
  
  // Regex aggressiva: cattura {{...}} o {...} con spazi opzionali e case-insensitive
  // Cattura: {{nome_pg}}, {nome_pg}, {{ pg_name }}, { pg_name }, {pg_name}, [nome_pg]
  const pattern = /\{\{\s*(nome_pg|pg_name)\s*\}\}|\{\s*(nome_pg|pg_name)\s*\}|\[\s*(nome_pg|pg_name)\s*\]/gi;
  
  const sanitizedText = text.replace(pattern, nameToUse);

  let cleanedText = sanitizedText.replace(/\r\n/g, '\n');
  cleanedText = cleanedText.replace(/^\s+$/gm, '');
  cleanedText = cleanedText.replace(/\n{3,}/g, '\n\n');
  cleanedText = cleanedText.trim();

  // 1. Split per Protocollo Verbo (<< ... >>)
  const speechParts = cleanedText.split(/(<<[\s\S]*?>>)/g);

  return speechParts.map((speechPart, speechIndex) => {
      // Se è una parte parlata << ... >>
      if (speechPart.startsWith('<<') && speechPart.endsWith('>>')) {
          const content = speechPart.slice(2, -2).trim();
          return (
              // MODIFICA: Solo grassetto, colore ereditato (bianco/foreground)
              <span key={`speech-${speechIndex}`} className="font-bold">
                  {content}
              </span>
          );
      }

      // Se è narrazione/pensiero, applica il parsing Markdown standard (**bold**, *italic*)
      const boldParts = speechPart.split(/(\*\*.*?\*\*)/g);
      return (
          <span key={`narrative-${speechIndex}`}>
              {boldParts.map((part, index) => {
                  if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
                      const content = part.slice(2, -2);
                      return <strong key={index} className="font-bold">{content}</strong>;
                  } else {
                      const italicParts = part.split(/(\*.*?\*)/g);
                      return (
                          <span key={index}>
                              {italicParts.map((subPart, subIndex) => {
                                  if (subPart.startsWith('*') && subPart.endsWith('*') && subPart.length > 2) {
                                      const content = subPart.slice(1, -1);
                                      // MODIFICA: Corsivo con leggera opacità per differenziare, ma senza colore specifico
                                      return <em key={subIndex} className="italic opacity-80">{content}</em>;
                                  }
                                  return subPart;
                              })}
                          </span>
                      );
                  }
              })}
          </span>
      );
  });
};

export const ChatArea = ({ messages, isThinking, thinkingAction, activeAvatarName, pngAvatarUrls, serverUrl, userName, onEdit, onReRun, onDelete, isPortrait = false, ghostText, ghostStatus, combatEntities =[], onAvatarClick, aiAvatarUrl }: ChatAreaProps) => {
  const { t } = useTranslation();
  const virtuosoRef = useRef<VirtuosoHandle>(null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const[editText, setEditText] = useState("");
  
  // --- [NUOVO] STATO GHOST TEXT RIPRISTINATI ---
  const [revealedGhosts, setRevealedGhosts] = useState<Set<string>>(new Set());
  const [isGhostDismissed, setIsGhostDismissed] = useState(false);

  // Resetta lo stato di chiusura quando arriva un nuovo testo fantasma
  useEffect(() => {
    if (ghostText) {
      setIsGhostDismissed(false);
    }
  }, [ghostText]);

  // ---[FIX CRITICO MOBILE] BLINDATURA GHOST TEXT (SELF-DESTRUCT) ---
  const isGhostAlreadyInChat = useMemo(() => {
    return messages && messages.slice(-3).some((m: any) => 
        m.content?.startsWith("[GHOST] ") && 
        ghostText && 
        m.content.includes(ghostText.trim())
    );
  }, [messages, ghostText]);

  const effectiveGhostStatus = isGhostAlreadyInChat ? 'hidden' : ghostStatus;

  // --- FIX: FILTRO VISUALIZZAZIONE E ANTI-DUPLICAZIONE (v10.3) ---
  const filteredMessages = useMemo(() => {
    const seenSignatures = new Set<string>();

    return messages.filter(m => {
      const content = m.content || "";
      const hasMedia = !!m.mediaUrl;
      
      // Filtro comandi tecnici
      if (content.startsWith('/') || content.startsWith('!')) return false;
      
      //// FIX: Filtro messaggi di sistema "brutti"
      if (m.sender === "System") {
          if (content.includes(t("chat_area.gdr_mode"))) return false;
          if (content.includes(t("chat_area.auto_learning"))) return false;
      }

      if (!content.trim() && !hasMedia) return false;

      // --- [FIX CRITICO] SCUDO ANTI-DUPLICAZIONE VISIVA ---
      // Creiamo una firma univoca basata su ruolo e contenuto.
      // Se l'abbiamo già vista in questa sessione di rendering, scartiamo il duplicato.
      const signature = `${m.role}-${content.trim()}`;
      if (seenSignatures.has(signature)) {
          return false;
      }
      seenSignatures.add(signature);

      return true;
    });
  }, [messages]);

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
  };

  const handleEditClick = (message: ChatMessage) => {
    setEditingMessageId(message.id);
    setEditText(message.content || "");
  };

  const handleSaveEdit = () => {
    if (editingMessageId) {
      onEdit(editingMessageId, editText);
      setEditingMessageId(null);
      setEditText("");
    }
  };

  const handleCancelEdit = () => {
    setEditingMessageId(null);
    setEditText("");
  };

  // --- FIX v36.4: SMART ICON LOOKUP (SPAZI -> UNDERSCORE) ---
  const lowerName = activeAvatarName.toLowerCase();
  const underscoreName = lowerName.replace(/ /g, '_');
  let avatarPath = pngAvatarUrls[lowerName] || pngAvatarUrls[underscoreName];

  // --- FIX BUG ICONA THINKING: Ricerca Parziale Intelligente ---
  if (!avatarPath) {
      const matchedKey = Object.keys(pngAvatarUrls).find(k => 
          k.includes(lowerName) || lowerName.includes(k) || k.startsWith(lowerName.split(' ')[0])
      );
      if (matchedKey) {
          avatarPath = pngAvatarUrls[matchedKey];
      }
  }

  //[FIX BUG 1] Se non trova il PNG, usa l'immagine dell'Avatar principale (Gemma)
  const thinkingAvatarUrl = avatarPath 
    ? `${serverUrl}${avatarPath}` 
    : aiAvatarUrl;

  // ---[FIX CRITICO] MEMOIZZAZIONE CONTESTO E COMPONENTI PER VIRTUOSO ---
  const virtuosoContext = useMemo(() => {
    return {
      isThinking,
      thinkingAction,
      activeAvatarName,
      thinkingAvatarUrl,
      onAvatarClick,
      t
    };
  },[isThinking, thinkingAction, activeAvatarName, thinkingAvatarUrl, onAvatarClick, t]);

  const virtuosoComponents = useMemo(() => {
    return { Footer: ChatFooter };
  }, Array(0));

  const itemContent = (index: number, message: ChatMessage) => {
    const { onAvatarClick } = virtuosoContext; // Estrazione dal contesto
    const isEditing = editingMessageId === message.id;
    const isAudio = message.mediaType === 'audio';
    
    // Check se è una trascrizione storica (testo che inizia con tag)
    const isHistoricalTranscription = message.content?.startsWith("[Trascrizione Vocale]:");

    // --- [NUOVO v11.4] ESTRAZIONE ASSET CLICCABILI ---
    let displayContent = message.content || "";
    const createdFiles: string[] = [];
    
    // Regex per trovare [FILE_CREATED: path]
    const fileRegex = /\[FILE_CREATED:\s*(.*?)\]/g;
    let match;
    while ((match = fileRegex.exec(displayContent)) !== null) {
        createdFiles.push(match[1]);
    }
    // Rimuovi i tag FILE_CREATED dal testo visualizzato
    displayContent = displayContent.replace(fileRegex, "").trim();

    // --- [NUOVO v12.0] SILENZIATORE INTENT (VISUAL CLEANUP) ---
        // Rimuove tag tecnici come[INTENT: ...],[AZIONE: ...], [USA_STRUMENTO: ...]
        // per evitare che l'utente veda i metadati interni.
        displayContent = displayContent.replace(/\[(INTENT|AZIONE|USA_STRUMENTO|SISTEMA|RUOLO|DEBUG|SENSORY_DATA).*?\]/gi, "").trim();

        const isClickableAvatar = message.sender && message.sender !== "System" && message.sender !== "Dungeon Master";

        // --- [FIX CRITICO] SMART AVATAR RESOLUTION ---
        // Garantisce che i PNG abbiano la loro miniatura anche se il backend fallisce il match
        let finalAvatarUrl = message.avatar;
        
        if (message.role !== "user" && isClickableAvatar && (!finalAvatarUrl || finalAvatarUrl === aiAvatarUrl)) {
            const senderLower = message.sender!.toLowerCase();
            const senderUnderscore = senderLower.replace(/ /g, '_');
            
            let matchedPath = pngAvatarUrls[senderLower] || pngAvatarUrls[senderUnderscore];
            
            if (!matchedPath) {
                const matchedKey = Object.keys(pngAvatarUrls).find(k => 
                    k.includes(senderLower) || senderLower.includes(k) || k.startsWith(senderLower.split(' ')[0])
                );
                if (matchedKey) {
                    matchedPath = pngAvatarUrls[matchedKey];
                }
            }
            
            if (matchedPath) {
                finalAvatarUrl = matchedPath.startsWith('http') ? matchedPath : `${serverUrl}${matchedPath}`;
            }
        }

        return (
          <div
            className={cn(
              "group flex flex-col animate-in fade-in px-4 py-2",
              message.role === "user" ? "items-end" : "items-start"
            )}
          >
            <div className={cn(
                "flex gap-3 max-w-full",
                message.role === "user" ? "flex-row-reverse" : "flex-row"
            )}>
                <Avatar 
                  className={cn(
                    "w-8 h-8 flex-shrink-0 border border-border mt-1",
                    isClickableAvatar && "cursor-pointer hover:ring-2 hover:ring-primary/50 transition-all"
                  )}
                  onClick={() => {
                    if (onAvatarClick && isClickableAvatar) {
                      onAvatarClick(message.sender!);
                    }
                  }}
                >
                  {message.sender === "Dungeon Master" ? (
                      <AvatarImage src={dmIcon} alt="DM" className="object-cover" />
                  ) : (
                      <AvatarImage 
                        src={finalAvatarUrl} 
                        alt={message.sender || message.role} 
                        className="object-cover"
                      />
                  )}
                  <AvatarFallback>
                {message.role === "user" 
                  ? (userName ? userName.charAt(0).toUpperCase() : "U") 
                  : (message.sender ? message.sender.charAt(0).toUpperCase() : activeAvatarName.charAt(0).toUpperCase())}
              </AvatarFallback>
            </Avatar>

            <div
              className={cn(
                "relative rounded-2xl px-4 py-2.5 transition-all duration-200",
                isEditing ? "w-full min-w-[280px] sm:min-w-[400px]" : "max-w-[85%] sm:max-w-[75%]",
                message.role === "user"
                  ? (isAudio ? "bg-transparent p-0 border-none" : "chat-message-user rounded-br-none") 
                  : "chat-message-gemma rounded-bl-none"
              )}
              style={{ 
                transform: 'translateZ(0)', 
                backfaceVisibility: 'hidden'
              }}
            >
              {message.role !== "user" && message.sender && (
                <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold text-primary opacity-80">
                      {message.sender.replace(/_/g, ' ')}
                    </span>
                    {message.guildName && (
                        <div className="flex items-center gap-1 bg-primary/10 px-1.5 py-0.5 rounded text-[9px] text-primary border border-primary/20">
                            {message.guildSymbol && <img src={message.guildSymbol} className="w-3 h-3 rounded-full" alt="" />}
                            {message.guildName}
                        </div>
                    )}
                </div>
              )}

              {message.mediaUrl && (
                <div className="mb-2 mt-1">
                  {message.mediaType === 'audio' && (
                      <AudioMessageBubble src={`${serverUrl}${message.mediaUrl}`} isUser={message.role === 'user'} />
                  )}
                  
                  {message.mediaType === 'image' && (
                    <div className="rounded-lg overflow-hidden border border-white/20">
                      <SecureImage 
                        src={`${serverUrl}${message.mediaUrl}`} 
                        alt={t("chat_area.alt_user_upload")} 
                        className="max-w-full h-auto max-h-[300px] object-contain"
                      />
                    </div>
                  )}
                  {message.mediaType === 'video' && (
                    <div className="rounded-lg overflow-hidden border border-white/20">
                      <SecureVideo 
                        src={`${serverUrl}${message.mediaUrl}`} 
                        className="max-w-full h-auto max-h-[300px]"
                      />
                    </div>
                  )}
                  {message.mediaType === 'document' && (
                    <a 
                      href={`${serverUrl}${message.mediaUrl}`} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 p-3 rounded-lg bg-background/20 hover:bg-background/30 transition-colors border border-white/10"
                    >
                      <div className="p-2 bg-white/10 rounded-full">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{message.fileName || t("chat_area.document")}</p>
                        <p className="text-xs opacity-70">{t("chat_area.open_file")}</p>
                      </div>
                    </a>
                  )}
                </div>
              )}

              {isEditing ? (
                <div className="space-y-2 w-full">
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className="w-full bg-transparent text-sm p-1 rounded focus:outline-none focus:ring-1 focus:ring-white/50 resize-y"
                    rows={Math.max(3, editText.split('\n').length)}
                    autoFocus
                  />
                  <div className="flex gap-2 justify-end">
                    <Button size="sm" variant="ghost" onClick={handleCancelEdit}>{t("chat_area.btn_cancel")}</Button>
                    <Button size="sm" onClick={handleSaveEdit}>{t("chat_area.btn_save")}</Button>
                  </div>
                </div>
              ) : (
                <>
                  {/* FIX: Styling per trascrizioni storiche (quando l'audio non è più disponibile) */}
                  {isHistoricalTranscription ? (
                      <div className="flex items-start gap-2 opacity-80 italic text-sm bg-black/10 p-2 rounded-lg border border-white/5">
                          <Mic className="w-4 h-4 mt-0.5 shrink-0" />
                          <span>{message.content?.replace("[Trascrizione Vocale]:", t("chat_area.transcription_prefix") + ":").trim()}</span>
                      </div>
                  ) : (
                      displayContent && displayContent !== "[Voice Message]" && (
                        // --- [NUOVO] RENDERING GHOST TEXT PERSISTENTE ---
                        displayContent.startsWith("[GHOST] ") ? (
                            !revealedGhosts.has(message.id) ? (
                                <div className="flex flex-col gap-2 opacity-80 my-1">
                                    <div className="flex items-center gap-2 text-muted-foreground italic text-xs">
                                        <Ban className="w-3.5 h-3.5" />
                                        {t("chat_area.message_deleted_by", { name: message.sender.replace(/_/g, ' ') })}
                                    </div>
                                    <Button
                                        variant="outline" 
                                        size="sm" 
                                        className="h-6 text-[10px] w-fit border-primary/30 hover:bg-primary/10"
                                        onClick={() => setRevealedGhosts(prev => new Set(prev).add(message.id))}
                                    >
                                        {t("chat_area.restore_message")}
                                    </Button>
                                </div>
                            ) : (
                                <div className="border-2 border-dashed border-red-500/70 bg-red-500/10 p-3 rounded-lg relative mt-1 mb-1">
                                    <Eye className="w-4 h-4 text-red-400 absolute top-2 right-2 opacity-70" />
                                    <p className="text-sm italic text-red-200 pr-6 leading-relaxed">
                                        {renderFormattedText(displayContent.replace("[GHOST] ", ""), userName, t)}
                                    </p>
                                </div>
                            )
                        ) : (
                            <p className="text-sm leading-relaxed whitespace-pre-wrap">
                              {renderFormattedText(displayContent, userName, t)}
                            </p>
                        )
                      )
                  )}
                  
                  {/* --- [NUOVO v11.4] RENDERING FILE CARDS --- */}
                  {createdFiles.length > 0 && (
                      <div className="mt-3 space-y-2">
                          {createdFiles.map((filePath, idx) => {
                              const fileName = filePath.split(/[/\\]/).pop();
                              
                              // FIX v13.1: Routing intelligente dei file
                              // Se è un file generato dal Demiurgo (non zip di export), si trova in /documents/
                              // Se è un export di sistema, si trova in /download/ (che mappa su exports/)
                              const isExport = fileName?.startsWith('export_') && fileName?.endsWith('.zip');
                              const downloadUrl = isExport 
                                  ? `${serverUrl}/download/${fileName}`
                                  : `${serverUrl}/documents/${fileName}`;
                              
                              return (
                                  <a 
                                      key={idx}
                                      href={downloadUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="flex items-center gap-3 p-2 rounded-lg bg-black/20 border border-white/10 hover:bg-black/30 transition-colors group/file"
                                  >
                                      <div className="p-2 bg-purple-500/20 rounded-md text-purple-300">
                                          <FileCode className="w-5 h-5" />
                                      </div>
                                      <div className="flex-1 min-w-0">
                                          <p className="text-xs font-bold truncate text-purple-100">{fileName}</p>
                                          <p className="text-[10px] text-muted-foreground">{t("chat_area.generated_asset")}</p>
                                      </div>
                                      <ExternalLink className="w-4 h-4 text-muted-foreground group-hover/file:text-white transition-colors" />
                                  </a>
                              );
                          })}
                      </div>
                  )}

                  <span className={cn(
                      "text-xs mt-1 block text-right",
                      message.role === 'user' ? 'text-primary-foreground/60' : 'text-muted-foreground/60'
                    )}>
                    {message.timestamp.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </>
              )}

              {/* --- RESTAURAZIONE: ICONE ESTERNE (v9.6) --- */}
              {!isPortrait && (
                  <div className={cn(
                    "absolute top-0 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity",
                    message.role === 'user' ? "right-full mr-2" : "left-full ml-2"
                  )}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleEditClick(message)}><Edit className="w-4 h-4" /></Button>
                      </TooltipTrigger>
                      <TooltipContent><p>{t("chat_area.edit")}</p></TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => onReRun(message.id)}><RefreshCw className="w-4 h-4" /></Button>
                      </TooltipTrigger>
                      <TooltipContent><p>{t("chat_area.re_run")}</p></TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleCopy(message.content || "")}><Copy className="w-4 h-4" /></Button>
                      </TooltipTrigger>
                      <TooltipContent><p>{t("chat_area.copy")}</p></TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500/80 hover:text-red-500" onClick={() => onDelete(message.id)}><Trash2 className="w-4 h-4" /></Button>
                      </TooltipTrigger>
                      <TooltipContent><p>{t("chat_area.delete")}</p></TooltipContent>
                    </Tooltip>
                  </div>
              )}
            </div>
        </div>

        {isPortrait && !isEditing && (
            <div className={cn(
                "flex items-center gap-4 mt-1 px-3 py-1 rounded-full bg-black/40 backdrop-blur-md border border-white/10 shadow-sm transition-all",
                message.role === "user" ? "mr-12 justify-end" : "ml-12 justify-start"
            )}>
                <button onClick={() => handleEditClick(message)} className="text-muted-foreground hover:text-white transition-colors p-1"><Edit className="w-3.5 h-3.5" /></button>
                <button onClick={() => onReRun(message.id)} className="text-muted-foreground hover:text-white transition-colors p-1"><RefreshCw className="w-3.5 h-3.5" /></button>
                <button onClick={() => handleCopy(message.content || "")} className="text-muted-foreground hover:text-white transition-colors p-1"><Copy className="w-3.5 h-3.5" /></button>
                <button onClick={() => onDelete(message.id)} className="text-red-400 hover:text-red-500 transition-colors p-1"><Trash2 className="w-3.5 h-3.5" /></button>
            </div>
        )}
      </div>
    );
  };

  return (
    <div className="h-full w-full overflow-hidden flex flex-col relative">
      
      {/* --- [NUOVO] GHOST TEXT BANNER FLUTTUANTE --- */}
      {effectiveGhostStatus && effectiveGhostStatus !== 'hidden' && ghostText && !isGhostDismissed && (
          <div className="absolute top-4 left-0 right-0 z-50 flex justify-center px-4 pointer-events-none">
              <div className="bg-background/95 backdrop-blur-md border border-primary/50 shadow-lg shadow-primary/20 rounded-xl p-3 max-w-md w-full pointer-events-auto flex gap-3 items-start animate-in slide-in-from-top-5 fade-in duration-300">
                  <Ghost className={cn("w-5 h-5 text-primary shrink-0 mt-0.5", effectiveGhostStatus === 'typing' && "animate-pulse")} />
                  <div className="flex-1 min-w-0 flex flex-col">
                      <p className="text-[10px] font-bold text-primary/80 mb-0.5 uppercase tracking-wider shrink-0">
                          {effectiveGhostStatus === 'typing' ? t("chat_area.typing") : t("chat_area.deleting")}
                      </p>
                      {/* FIX MOBILE: Aggiunto touch-pan-y, overscroll-contain e pointer-events-auto per forzare lo scroll col dito */}
                      <div className="max-h-[25vh] overflow-y-auto custom-scrollbar pr-2 mt-1 touch-pan-y overscroll-contain pointer-events-auto">
                          <p className="text-xs italic text-foreground/90 leading-relaxed">
                              {ghostText ? renderFormattedText(ghostText, userName, t) : null}
                          </p>
                      </div>
                  </div>
                  <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 shrink-0 text-muted-foreground hover:text-foreground hover:bg-white/10 -mt-1 -mr-1"
                      onClick={() => setIsGhostDismissed(true)}
                  >
                      <X className="w-4 h-4" />
                  </Button>
              </div>
          </div>
      )}

      {/* --- [NUOVO v27.0] HUD COMBATTIMENTO (STICKY HEADER) --- */}
      {combatEntities.length > 0 && (
          <div className="w-full bg-background/80 backdrop-blur-md border-b border-red-500/30 p-2 shrink-0 z-10 shadow-md">
              <div className="flex items-center gap-2 mb-1 px-1">
                  <ShieldAlert className="w-3 h-3 text-red-500 animate-pulse" />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-red-400">{t("chat_area.combat_phase")}</span>
              </div>
              
              {/* Carosello Orizzontale per Mobile/Desktop */}
              <div className="flex gap-3 overflow-x-auto pb-1 custom-scrollbar">
                  {combatEntities.map((entity) => {
                      // --- [FIX CRASH] PREVENZIONE DIVISIONE PER ZERO ---
                      const safeMaxHp = entity.hp_massimi > 0 ? entity.hp_massimi : 1;
                      const hpPercent = Math.max(0, Math.min(100, (entity.hp_attuali / safeMaxHp) * 100));
                      const isCritical = hpPercent <= 25;
                      
                      // Risoluzione Avatar
                      let avatarSrc = entity.avatar_url;
                      if (!avatarSrc) {
                          const lowerName = entity.nome.toLowerCase();
                          const underscoreName = lowerName.replace(/ /g, '_');
                          const path = pngAvatarUrls[lowerName] || pngAvatarUrls[underscoreName];
                          if (path) avatarSrc = `${serverUrl}${path}`;
                      }

                      return (
                          <div key={entity.id} className={cn(
                              "flex items-center gap-2 p-1.5 rounded-lg border min-w-[140px] max-w-[180px] shrink-0 transition-all",
                              entity.is_enemy ? "bg-red-950/20 border-red-900/50" : "bg-blue-950/20 border-blue-900/50",
                              isCritical && "animate-pulse border-red-500"
                          )}>
                              <Avatar className="w-8 h-8 border border-border shrink-0">
                                  <SecureAvatarImage src={avatarSrc} alt={entity.nome} className="object-cover" />
                                  <AvatarFallback className={entity.is_enemy ? "bg-red-900/50 text-red-200" : "bg-blue-900/50 text-blue-200"}>
                                      {entity.nome.charAt(0).toUpperCase()}
                                  </AvatarFallback>
                              </Avatar>
                              
                              <div className="flex-1 min-w-0 flex flex-col justify-center">
                                  <span className="text-[10px] font-bold truncate leading-none mb-1">{entity.nome}</span>
                                  <div className="flex items-center gap-1">
                                      <Heart className={cn("w-2.5 h-2.5 shrink-0", isCritical ? "text-red-500" : "text-muted-foreground")} />
                                      <Progress 
                                          value={hpPercent} 
                                          className="h-1.5 flex-1 bg-black/50" 
                                          indicatorClassName={cn(
                                              isCritical ? "bg-red-500" : 
                                              entity.is_enemy ? "bg-orange-500" : "bg-green-500"
                                          )}
                                      />
                                      <span className="text-[8px] font-mono text-muted-foreground shrink-0 w-8 text-right">
                                          {entity.hp_attuali}/{entity.hp_massimi}
                                      </span>
                                  </div>
                              </div>
                          </div>
                      );
                  })}
              </div>
          </div>
      )}

      <Virtuoso
        ref={virtuosoRef}
        style={{ height: '100%', width: '100%' }}
        data={filteredMessages}
        itemContent={itemContent}
        followOutput="auto"
        alignToBottom
        components={virtuosoComponents}
        context={virtuosoContext}
        className="custom-scrollbar"
      />

      <style>{`
        .custom-scrollbar::-webkit-scrollbar { width: 10px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: hsl(340 82% 52% / 0.5); border-radius: 5px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: hsl(340 82% 52% / 0.7); }
        @keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-4px); } }
        @keyframes waveform { 0%, 100% { transform: scaleY(0.5); } 50% { transform: scaleY(1.5); } }
        .animate-waveform { animation: waveform 0.8s ease-in-out infinite; transform-origin: center; }
      `}</style>
    </div>
  );
};