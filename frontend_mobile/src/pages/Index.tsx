// frontend_mobile/src/pages/Index.tsx
// v39.6 - UI REFINEMENT (SELF LEARNING SYNC)
// v39.7 - GHOST CURSOR INTEGRATION (MODULO B)
// v39.8 - FIX CRITICO REACT #310 (HOOK ORDER) & SANTUARIO BLINDATO
// FIX: Spostamento di tutti gli Hook prima dei return condizionali per rispettare le regole di React.
// ADD: Gestione messaggio WebSocket 'visual_effect' per il Ghost Cursor.
// MANTENUTO: Musa & Genesi, Hive Mind, Video Player, Chat logic.
// LEGGE A0099: Invarianza strutturale garantita. Codice integrale fornito.

import React, { useState, useEffect, useCallback, useRef } from "react";
import { VideoPlayer } from "@/components/VideoPlayer";
import { ChatArea } from "@/components/ChatArea";
import { InputBar } from "@/components/InputBar";
import { Sidebar } from "@/components/Sidebar";
import { SettingsDialog } from "@/components/SettingsDialog";
import { ProfileDialog } from "@/components/ProfileDialog";
import { CharacterManagerDialog } from "@/components/CharacterManagerDialog";
import { CharacterEditorDialog } from "@/components/CharacterEditorDialog";
import { SessionHistoryDialog } from "@/components/SessionHistoryDialog";
import { ProactiveMemoryDialog } from "@/components/ProactiveMemoryDialog";
import { ReminderDialog } from "@/components/ReminderDialog";
import { DemiurgeSettingsTab } from "@/components/DemiurgeSettingsTab"; 
import { CameraManagerDialog } from "@/components/CameraManagerDialog"; 
import { WelcomeWizard } from "@/components/WelcomeWizard"; 
import { MemoryGalleryDialog } from "@/components/MemoryGalleryDialog";
import { HeartStateDialog } from "@/components/HeartStateDialog"; 
import { SmartHomeDialog } from "@/components/SmartHomeDialog"; // [NUOVO v115.0]
import { CameraCaptureDialog } from "@/components/CameraCaptureDialog";
import { LoginMask } from "@/components/LoginMask"; 
import { PreferencesTab } from "@/components/PreferencesTab"; // [NUOVO] 
import { CognitiveModuleDialog } from "@/components/CognitiveModuleDialog"; //[NUOVO FASE 16]
import { NetworkDialog } from "@/components/NetworkDialog"; //[NUOVO v28.0]
import { UiThemesTab } from "@/components/UiThemesTab"; // [NUOVO] UI Themes
import { GenesisDialog } from "@/components/GenesisDialog"; // [NUOVO]
import { KnowledgeGraphDialog } from "@/components/KnowledgeGraphDialog"; // [NUOVO] Mappa Mentale Tab
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAudioPlayer } from "@/hooks/useAudioPlayer";
import { useIsPortrait } from "@/hooks/use-mobile";
import { useHiveMind } from "@/hooks/useHiveMind"; 
import { useSentinelHearing } from "@/hooks/useSentinelHearing"; 
import { 
    ChatMessage, ServerConfig, UserProfile, ProactiveMemorySettings, ReminderData, CustomConnectorData, PerceptionSettings,
    JailbreakItem, KnowledgeBaseData, LearningSource, LearningArgument,
    CognitiveModule, CognitiveMindsets, MindsetProfile, CombatEntity, NetworkMode, OOCMessage // [NUOVO v28.0]
} from "@/types";
import { saveServerConfig, loadServerConfig, saveUserProfile, loadUserProfile } from "@/utils/storage";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Loader2, Power, Save, Trash2, AlertTriangle, Edit, Globe, BrainCircuit, FileJson, Settings2, PlusCircle, Plus, EyeOff, Eye, Zap, ZapOff, Mic, Ear, EarOff, ArrowUp, ArrowDown, Link2, Play, Check, FlaskConical, Activity, Upload, Download, CheckCircle2, XCircle, Sparkles, GripVertical, Tags, Brain, Gamepad2, MonitorPlay, HeartPulse, Search, ShieldAlert, X, HardDrive, RefreshCw, Cpu, Shield, } from "lucide-react"; 
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch"; // [FIX] Import mancante aggiunto
import { Progress } from "@/components/ui/progress"; // [NUOVO v124.0] Per barra evoluzione
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Slider } from "@/components/ui/slider";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useTranslation } from "@/contexts/TranslationContext"; // IMPORT NECESSARIO
import { getBaseUrl, getHeaders } from "@/lib/api";

interface ModelsState {
  base_models: string[];
  mmproj_models: string[];
  lora_models: string[];
  specialist_models: string[];
  labour_models: string[];
  active_base_model: string;
  is_large_model?: boolean; // [NUOVO] Flag Gatekeeper Cognitivo
  active_mmproj_model: string;
  active_lora_model: string;
  active_draft_model: string;
  draft_enabled: boolean;
  active_semantic_model: string;
  semantic_router_enabled: boolean;
  semantic_on_cpu: boolean;
}
interface AnimaParameters {
  n_gpu_layers: number;
  temperature: number;
  top_p: number;
  top_k: number;
  repeat_penalty: number;
  n_ctx: number;
}
interface PromptsConfig {
  system: Record<string, any>;
  rpg: Record<string, any>;
}
interface GdrWorldContent {
  [key: string]: {
    [key: string]: string;
  };
}

// --- [NUOVO v39.7] INTERFACCIA EFFETTO VISIVO ---
interface VisualEffectData {
  type: string;
  x: number;
  y: number;
  timestamp: number;
}

// --- [OTTIMIZZAZIONE v70.2] MAPPA VRAM REALISTICA PER GEMMA 3 ---
// Valori calibrati per lasciare spazio alla KV Cache e al Sistema Operativo
const VRAM_MAP: Record<string, number> = {
  "8": 20,   // Safe per schede da 8GB
  "12": 25,  // Safe per schede da 12GB+
  "16": -1,  // Full GPU per 16GB+
  "24": -1,  // Full GPU per 24GB+
  "32": -1,
};

// --- LISTA CHIAVI DA NASCONDERE (SOLO CONNETTORI ESTERNI) ---
const CONNECTOR_PROMPT_KEYS = [
  "google_calendar_prompt", "gmail_prompt", "google_drive_prompt", "google_sheets_prompt",
  "google_tasks_prompt", "google_photos_prompt", "google_contacts_prompt",
  "microsoft_outlook_prompt", "microsoft_onedrive_prompt", "microsoft_excel_prompt",
  "microsoft_todo_prompt", "discord_prompt", "telegram_prompt", "twilio_prompt",
  "twitter_prompt", "reddit_prompt", "whatsapp_prompt", "slack_prompt",
  "trello_prompt", "jira_prompt", "asana_prompt", "notion_prompt",
  "github_prompt", "gitlab_prompt", "webhook_prompt", "forms_prompt",
  "wordpress_prompt", "image_gen_prompt", "video_gen_prompt"
];

// --- HELPER PER URL ROBUSTI ---
function joinUrl(base: string, path: string): string {
  if (!path) return "";
  if (path.startsWith('http')) return path; 
  
  const cleanBase = base.endsWith('/') ? base.slice(0, -1) : base;
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;
  
  return `${cleanBase}/${cleanPath}`;
}

// --- HELPER PER CAPITALIZZAZIONE SICURA (FIX JS ERROR) ---
function capitalizeName(name: string): string {
    if (!name) return "";
    return name.charAt(0).toUpperCase() + name.slice(1);
}

// --- HELPER: ESTRAZIONE PARLATO PER SOTTOTITOLI ---
function extractSpokenText(text: string): string {
    if (!text) return "";
    const matches = text.match(/<<([\s\S]*?)>>/g);
    if (!matches) return "";
    return matches.map(m => m.replace(/^<<\s*|\s*>>$/g, '')).join(' ');
}

const Index = () => {
  const { t, changeLanguage, currentLang } = useTranslation();

  // Helper per tradurre le stringhe dinamiche che arrivano dal backend nel formato t('chiave') o [chiave]
  const parseDynamicT = (text: string) => {
    if (!text || typeof text !== 'string') return text;
    
    // 1. Controllo formato t('chiave') - Regex robusta con supporto spazi e virgolette miste
    const matchT = text.match(/^t\(\s*['"](.+?)['"]\s*\)$/);
    if (matchT && matchT[1]) {
        return t(matchT[1]);
    }
    
    // 2. Controllo formato [chiave] - Usato per i Mindset e altri metadati
    if (text.startsWith('[') && text.endsWith(']')) {
        const key = text.slice(1, -1).trim();
        return t(key);
    }
    
    return text;
  };

  // --- AUTH STATE (SANTUARIO BLINDATO) ---
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAuthChecking, setIsAuthChecking] = useState(true);

  const [serverConfig, setServerConfig] = useState<ServerConfig | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [welcomeWizardOpen, setWelcomeWizardOpen] = useState(false); 
  const [connectionGuideOpen, setConnectionGuideOpen] = useState(false);
  const [connInfo, setConnInfo] = useState({ lan_url: "", wlan_url: "", ntfy_topic: "" });
  const [messages, setMessages] = useState<ChatMessage[]>(Array(0));
  
  // --- STATO SESSIONE ---
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  // Stati per il Video Player
  const [currentIntent, setCurrentIntent] = useState<string | null>("state_hello");
  const [currentVideoUrl, setCurrentVideoUrl] = useState<string | null>(null);
  const [loopVideo, setLoopVideo] = useState(false);
  const [currentAudioUrl, setCurrentAudioUrl] = useState<string | null>(null);
  const [currentText, setCurrentText] = useState<string>(""); 
  
  // --- [AGGIUNTA v29.38] STATO PRELOAD ---
  const [preloadVideoUrl, setPreloadVideoUrl] = useState<string | null>(null);

  // Stati per Sincronia Labiale (Start on Signal)
  const [videoPlaySignal, setVideoPlaySignal] = useState<number>(0);
  const [shouldWaitVideo, setShouldWaitVideo] = useState(false);
  const [forceInterrupt, setForceInterrupt] = useState(false);

  const [isGdrMode, setIsGdrMode] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const [isGdrPathSet, setIsGdrPathSet] = useState(false); // [NUOVO v51.1] Stato verità sul percorso GDR
  
  // --- [NUOVO v27.0] STATI RPG ENGINE ---
  const [isCampaignMode, setIsCampaignMode] = useState(false);
  const [combatEntities, setCombatEntities] = useState<CombatEntity[]>(Array(0));
  
  const [isMonitoring, setIsMonitoring] = useState(false);
  // --- RIFONDAZIONE ASCOLTO (v29.50) ---
  const [isActiveHearing, setIsActiveHearing] = useState(false); // Sostituisce isHotwordListening
  
  // --- [NUOVO v36.0] STATO PERCEZIONE ---
  const [perceptionSettings, setPerceptionSettings] = useState<PerceptionSettings>({
      silence_threshold: 25,
      hotword_detection: {
          enabled_by_default: false,
          hotword: "ehi gemma",
          listen_timeout: 2,
          phrase_time_limit: 10
      }
  });
  
  const [isThinking, setIsThinking] = useState(false);
  const [thinkingAction, setThinkingAction] = useState<"thinking" | "studying">("thinking"); // [FIX CRITICO] Azione dinamica
  const [thinkingCharacter, setThinkingCharacter] = useState<string>("AI");
  const [aiAvatarUrl, setAiAvatarUrl] = useState<string | undefined>(undefined);
  const [pngAvatarUrls, setPngAvatarUrls] = useState<Record<string, string>>({});
  const [allAvatarData, setAllAvatarData] = useState<Record<string, any>>({});
  const [activeAvatar, setActiveAvatar] = useState<string>("gemma");
  const [charManagerOpen, setCharManagerOpen] = useState(false);
  const [charManagerType, setCharManagerType] = useState<"PG" | "PNG" | "AVATAR">("PG");
  const [charEditorOpen, setCharEditorOpen] = useState(false);
  const [editingCharId, setEditingCharId] = useState<string | undefined>(undefined);
  const [autofillData, setAutofillData] = useState<any | null>(null);
  
  // Export State (Dialogo rimosso, logica mantenuta per CharacterManagerDialog)
  // const [exportDialogOpen, setExportDialogOpen] = useState(false);
  // const [exportConfig, setExportConfig] = useState<{ type: 'pure' | 'world'; title: string }>({ type: 'pure', title: '' });
  
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importConflicts, setImportConflicts] = useState<string[]>([]);
  const [conflictDialogOpen, setConflictDialogOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [modelsDialogOpen, setModelsDialogOpen] = useState(false);
  const [modelsState, setModelsState] = useState<ModelsState | null>(null);
  const [selectedBaseModel, setSelectedBaseModel] = useState('');
  const [selectedMmprojModel, setSelectedMmprojModel] = useState('');
  const [selectedLoraModel, setSelectedLoraModel] = useState('');
  
  const [isApplyingModels, setIsApplyingModels] = useState(false);
  const [animaParams, setAnimaParams] = useState<AnimaParameters | null>(null);
  const [selectedVram, setSelectedVram] = useState("12");
  const [promptsConfig, setPromptsConfig] = useState<PromptsConfig | null>(null);
  const [isSavingPrompts, setIsSavingPrompts] = useState(false);
  const [gdrWorlds, setGdrWorlds] = useState<string[]>(Array(0));
  const [selectedGdrForEditing, setSelectedGdrForEditing] = useState("");
  // --- [NUOVO] STATI PREFERENCES TAB ---
  const [enrichedRpgWorlds, setEnrichedRpgWorlds] = useState<any[]>(Array(0));
  const [selectedPrefAvatar, setSelectedPrefAvatar] = useState<string>("");
  const [selectedPrefRpg, setSelectedPrefRpg] = useState<string>("STANDARD");
  const [gdrWorldContent, setGdrWorldContent] = useState<GdrWorldContent | null>(null);
  const [isSavingWorldFile, setIsSavingWorldFile] = useState(false);
  const [saveMemoriesDialogOpen, setSaveMemoriesDialogOpen] = useState(false);
  const [confirmQuitDialogOpen, setConfirmQuitDialogOpen] = useState(false);
  const [sessionHistoryOpen, setSessionHistoryOpen] = useState(false);
  const [proactiveMemoryOpen, setProactiveMemoryOpen] = useState(false);
  const [reminderOpen, setReminderOpen] = useState(false);
  const [securityOpen, setSecurityOpen] = useState(false); 
  const [memoryGalleryOpen, setMemoryGalleryOpen] = useState(false); 
  const [heartStateOpen, setHeartStateOpen] = useState(false); 
  const [smartHomeOpen, setSmartHomeOpen] = useState(false); //[NUOVO v115.0]
  
  const [networkDialogOpen, setNetworkDialogOpen] = useState(false);
  const [networkMode, setNetworkMode] = useState<NetworkMode>('OFF');
  const [multiplayerUrl, setMultiplayerUrl] = useState<string | undefined>(undefined);
  const[multiplayerToken, setMultiplayerToken] = useState<string | undefined>(undefined);
  const[isInputLocked, setIsInputLocked] = useState(false);
  const [oocMessages, setOocMessages] = useState<OOCMessage[]>(Array(0));
  
  // ---[RM29] THREAT MODELING STATES ---
  const [connectedGuests, setConnectedGuests] = useState<string[]>(Array(0));
  const[lowBandwidthMode, setLowBandwidthMode] = useState(false);
  const[currentRoomId, setCurrentRoomId] = useState<string | null>(null);
  const [lobbyPwd, setLobbyPwd] = useState<string>("");
  
  // --- [NUOVO] STATI ESPANSIONE MMORPG ---
  const[isStealthMode, setIsStealthMode] = useState(false);
  const [generatedQuest, setGeneratedQuest] = useState<any | null>(null);

  const [activeModelTab, setActiveModelTab] = useState("models");

  // --- [NUOVO v20.0] STATO PANOPTICON (MIGRATO) ---
  const [panopticonConfig, setPanopticonConfig] = useState<PanopticonConfig>({
    enabled: false,
    sherlock_enabled: false,
    gamer_enabled: false,
    media_enabled: false,
    life_guardian_enabled: false,
    sherlock_blacklist: Array(0)
  });
  const [newSherlockWord, setNewSherlockWord] = useState("");

  // --- [NUOVO] LOGICA SALVATAGGIO PANOPTICON ---
  const handleUpdatePanopticon = async (updatedConfig: PanopticonConfig) => {
      setPanopticonConfig(updatedConfig);
      const baseUrl = getServerUrl();
      const headers = { ...getHeaders(), 'Content-Type': 'application/json' };
      try {
          const res = await fetch(`${baseUrl}/api/settings/panopticon`, {
              method: 'POST',
              headers: headers,
              body: JSON.stringify(updatedConfig)
          });
          if (res.ok) {
              toast.success("Panopticon aggiornato con successo!");
          } else {
              toast.error("Errore dal server durante il salvataggio del Panopticon.");
          }
      } catch (e) {
          toast.error("Errore di rete durante il salvataggio del Panopticon.");
      }
  };

  // --- [NUOVO v124.0] STATI EVOLUZIONE PSICOLOGICA ---
  const [isEvolving, setIsEvolving] = useState(false);
  const [evolutionData, setEvolutionData] = useState({
      current: 0,
      total: 0,
      name: "",
      status: "idle",
      message: ""
  });

  // --- [NUOVO] STATO SALVATAGGIO MEMORIE ---
  const[isSavingMemories, setIsSavingMemories] = useState(false);

  // --- [NUOVO] STATO SPEGNIMENTO SISTEMA ---
  const [shutdownPhase, setShutdownPhase] = useState<'started' | 'completed' | null>(null);

  // --- [NUOVO] STATI NSFW WARNING ---
  const [isNsfwWarningOpen, setIsNsfwWarningOpen] = useState(false);
  const [pendingNsfwToggle, setPendingNsfwToggle] = useState<{modId: string, currentState: boolean, contextType: 'avatar' | 'gdr'} | null>(null);

  // --- STATI PER FACTORY RESET ---

  const [isResetConfirmOpen, setIsResetConfirmOpen] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const[isTotalWipe, setIsTotalWipe] = useState(false);
  
  // --- STATI PER ULTIMO MESSAGGIO (FACTORY RESET) ---
  const [finalGoodbyeOpen, setFinalGoodbyeOpen] = useState(false);
  const [finalGoodbyeText, setFinalGoodbyeText] = useState("");
  const [finalGoodbyeWipe, setFinalGoodbyeWipe] = useState(false);

  // --- STATI PER RITO DELLA GENESI E ACCODAMENTO (UI) ---
  const [genesisDialogOpen, setGenesisDialogOpen] = useState(false);
  const [genesisAvailablePngs, setGenesisAvailablePngs] = useState<string[]>(Array(0));
  const [pendingGenesisData, setPendingGenesisData] = useState<string[] | null>(null);

  // --- STATI PER AGGIUNTA PROMPT (NUOVO) ---
  const [newPromptKey, setNewPromptKey] = useState("");
  const [newPromptValue, setNewPromptValue] = useState("");

  // --- HIVE MIND & SENTINEL UI (v30.0) ---
  const { deviceId, deviceType, isRegistered, deviceName } = useHiveMind(serverConfig);
  const [isPrivacyMode, setIsPrivacyMode] = useState(false); // Kill Switch locale
  
  // --- PROTOCOLLO GHOST IN THE SHELL ---
  const [isFocusedDevice, setIsFocusedDevice] = useState(true); 
  
  // Calcolo modalità Sentinel: Tablet registrato
  const isSentinelMode = deviceType === 'tablet' && isRegistered;

  // --- [NUOVO v34.0] SENTINEL HEARING ---
  const [isSentinelHearingEnabled, setIsSentinelHearingEnabled] = useState(false);
  
  // --- [NUOVO v38.0] CAMERA CAPTURE DIALOG ---
  const [cameraCaptureOpen, setCameraCaptureOpen] = useState(false);

  // --- [FIX v35.3] REF PER TRACCIARE L'ULTIMO AUDIO RIPRODOTTO ---
  const lastPlayedAudioRef = useRef<string | null>(null);

  // --- [NUOVO v37.0] GHOST TEXT STATES ---
  const [ghostText, setGhostText] = useState<string>("");
  const [ghostStatus, setGhostStatus] = useState<'hidden' | 'typing' | 'deleting'>('hidden');

  // --- [NUOVO v39.7] STATO EFFETTO VISIVO ---
  const [visualEffect, setVisualEffect] = useState<VisualEffectData | null>(null);

  // --- [NUOVO] STATO GHOST TEXT TECNICO ---
  const [showTechThoughts, setShowTechThoughts] = useState(() => {
      return localStorage.getItem("airis_show_tech_thoughts") !== "false";
  });

  const toggleTechThoughts = () => {
      const newVal = !showTechThoughts;
      setShowTechThoughts(newVal);
      localStorage.setItem("airis_show_tech_thoughts", String(newVal));
      toast.info(newVal ? t("index.toast_tech_thoughts_on") : t("index.toast_tech_thoughts_off"));
  };

  // --- [NUOVO v38.0] STATI MUSA & GENESI ---
  const [jailbreaks, setJailbreaks] = useState<JailbreakItem[]>(Array(0));
  const [activeJailbreakContent, setActiveJailbreakContent] = useState("");
  const [isJailbreakDirty, setIsJailbreakDirty] = useState(false);
  const [newJailbreakName, setNewJailbreakName] = useState("");
  // --- FIX v39.1: Stato per il contenuto del nuovo prompt ---
  const [newJailbreakContent, setNewJailbreakContent] = useState("");
  const [isNewJailbreakDialogOpen, setIsNewJailbreakDialogOpen] = useState(false);
  
  const [knowledgeBase, setKnowledgeBase] = useState<KnowledgeBaseData>({
      sources: [],
      arguments: [],
      config: { interval_minutes: 60, "active": false }
  });
  const [newSourceUrl, setNewSourceUrl] = useState("");
  const [newArgumentTopic, setNewArgumentTopic] = useState("");
  const [editingArgument, setEditingArgument] = useState<LearningArgument | null>(null);
  const [isSourceAssociationOpen, setIsSourceAssociationOpen] = useState(false);
  
  // --- [NUOVO v39.6] STATO EDITING SOURCE ---
  const [editingSource, setEditingSource] = useState<LearningSource | null>(null);
  const [editSourceUrl, setEditSourceUrl] = useState("");
  const [isEditSourceOpen, setIsEditSourceOpen] = useState(false);
  
  // --- [NUOVO v39.0] STATI TEST & MULTI-SELECT ---
  const [isTestJailbreakOpen, setIsTestJailbreakOpen] = useState(false);
  const [testQuery, setTestQuery] = useState(t("index.test_query_placeholder"));
  const [testResponse, setTestResponse] = useState("");
  const [isTestingJailbreak, setIsTestingJailbreak] = useState(false);
  
  // --- FIX v39.2: STATO EDITING JAILBREAK ---
  const [editingJailbreakId, setEditingJailbreakId] = useState<string | null>(null);
  
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>(Array(0));
  const [selectedArgumentIds, setSelectedArgumentIds] = useState<string[]>(Array(0));
  const kbFileInputRef = useRef<HTMLInputElement>(null);

 // ---[NUOVO FASE 16] STATI COGNITIVE MODULES & MINDSETS ---
  const [cognitiveModules, setCognitiveModules] = useState<CognitiveModule[]>(Array(0));
  const [cognitiveMindsets, setCognitiveMindsets] = useState<CognitiveMindsets | null>(null);
  const [isModuleDialogOpen, setIsModuleDialogOpen] = useState(false);
  const [moduleToEdit, setModuleToEdit] = useState<CognitiveModule | null>(null);

  const [fullAvatarJson, setFullAvatarJson] = useState<any>(null);

  // ===========================================================================
  // 1. TUTTI GLI HOOK (STATO, REF, CUSTOM) DEVONO ESSERE QUI IN CIMA
  // ===========================================================================

  const pendingDefGenResolver = useRef<((value: string) => void) | null>(null);
  const authCheckDone = useRef(false);
  const hasHandshaked = useRef(false); // FIX BUG 03: Previene lo spam di Handshake

  const { status, latestMessage, connect, disconnect, sendMessage } = useWebSocket(
      isAuthenticated ? serverConfig : null,
      multiplayerUrl,
      multiplayerToken
  );
  const audioPlayer = useAudioPlayer() as any;
  const playAudio = audioPlayer.play;
  const stopAudio = audioPlayer.stop;
  const isConnected = status === 'connected';

  // ---[NUOVO v28.0] GESTIONE RETE MULTIPLAYER ---
  const handleSetNetworkMode = async (mode: NetworkMode, roomUrl?: string, lobbyPassword?: string, roomId?: string) => {
    if (mode === 'CLIENT' && roomUrl) {
      try {
        const httpUrl = roomUrl.replace('wss://', 'https://').replace('ws://', 'http://').replace('/ws', '');
        const res = await fetch(`${httpUrl}/api/auth/guest`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lobby_password: lobbyPassword || "" })
        });
        
        if (!res.ok) throw new Error(t("network_dialog.err_wrong_password"));
        
        const data = await res.json();
        const guestToken = data.access_token;
        
        let scheda_rpg = {};
        try {
          const localRes = await fetch(`${getServerUrl()}/api/characters/${userProfile?.name}?char_type=PG`, { headers: getHeaders() });
          if (localRes.ok) {
            const localData = await localRes.json();
            scheda_rpg = localData.jsonData?.scheda_rpg || {};
          }
        } catch (e) {}

        disconnect();
        setMultiplayerUrl(roomUrl);
        setMultiplayerToken(guestToken);
        setNetworkMode('CLIENT');
        setCurrentRoomId(roomId || null);
        setLobbyPwd(lobbyPassword || "");
        
        (window as any).temp_scheda_rpg = scheda_rpg;
        
        toast.success(t("network_dialog.toast_connecting_room"));
      } catch (e: any) {
        toast.error(t("network_dialog.err_connection_desc"), { description: e.message });
      }
    } else if (mode === 'HOST') {
      setNetworkMode('HOST');
      setConnectedGuests([]); // Reset ospiti
    } else {
      setNetworkMode('OFF');
      setMultiplayerUrl(undefined);
      setMultiplayerToken(undefined);
      setCurrentRoomId(null);
      setLobbyPwd("");
      setIsInputLocked(false);
      setConnectedGuests([]);
      disconnect();
      setTimeout(() => connect(), 500);
    }
  };

  const handleHostRoom = (title: string, desc: string, pwd: string, max: string, lang: string, womenOnly: boolean) => {
      sendMessage(JSON.stringify({ type: "command", text: `/host_room title='${title}' desc='${desc}' pwd='${pwd}' max='${max}' lang='${lang}' women_only='${womenOnly}'` }));
  };

  const handleCloseRoom = () => {
      sendMessage(JSON.stringify({ type: "command", text: `/close_room` }));
      handleSetNetworkMode('OFF');
  };

  const handleKickPlayer = (playerName: string) => {
      sendMessage(JSON.stringify({ type: "command", text: `/kick_player ${playerName}` }));
      setConnectedGuests(prev => prev.filter(g => g !== playerName));
  };
  const isPortrait = useIsPortrait();

  // Wake Lock Effect
  useEffect(() => {
    let wakeLock: any = null;
    const requestWakeLock = async () => {
      if ('wakeLock' in navigator && isSentinelMode) {
        try { 
            wakeLock = await (navigator as any).wakeLock.request('screen'); 
            console.log(t("index.log_wake_lock_active"));
        } catch (err) {
            console.warn(t("index.warn_wake_lock_failed"), err);
        }
      }
    };
    requestWakeLock();
    return () => {
        if (wakeLock) wakeLock.release();
    };
  },[isSentinelMode]);

  // ---[NUOVO v10.20] AUTH LOGIC (SANTUARIO BLINDATO) ---
  useEffect(() => {
    // Esegui il check solo una volta
    if (authCheckDone.current) return;
  
    const checkAuth = async () => {
      const token = localStorage.getItem("airis_auth_token");
      if (token) {
        setIsAuthenticated(true);
        setIsAuthChecking(false);
        authCheckDone.current = true;
        return;
      }
    
      // --- [NUOVO v10.20] AUTO-BYPASS CHECK (SORGENTI FIDATE) ---
      try {
        const baseUrl = getBaseUrl(serverConfig);
        const res = await fetch(`${baseUrl}/api/auth/is-trusted`, {
          headers: { "ngrok-skip-browser-warning": "true" }
        });
        if (res.ok) {
          const data = await res.json();
          if (data.is_trusted) {
            console.log(t("index.log_trusted_source"));
            if (data.token) {
              localStorage.setItem("airis_auth_token", data.token);
              console.log(t("index.log_system_token_saved"));
            }
            setIsAuthenticated(true);
          }
        }
      } catch (e) {
        console.error(t("index.err_trusted_check"), e);
      }
    
      setIsAuthChecking(false);
      authCheckDone.current = true;
    };
  
    checkAuth();
  }, [serverConfig]);

  useEffect(() => {
    const config = loadServerConfig();
    if (config) {
      if (!config.currentAvatar) config.currentAvatar = "gemma";
      setServerConfig(config);
      setActiveAvatar(config.currentAvatar);
    } else {
      // Se non siamo autenticati, non apriamo i settings automaticamente
      if (isAuthenticated) setSettingsOpen(true);
    }
    const profile = loadUserProfile();
    if (profile) setUserProfile(profile);
  }, [isAuthenticated]); // Aggiunta dipendenza per reagire al login

  // FIX: Uso getBaseUrl centralizzato
  const getServerUrl = useCallback(() => {
      return getBaseUrl(serverConfig);
  }, [serverConfig]);

  // ---[NUOVO] HELPER AVATAR DINAMICO (UTENTE vs PG) ---
  const getUserAvatarUrl = useCallback(() => {
      if (isGdrMode && userProfile?.name) {
          const pgNameLower = userProfile.name.toLowerCase();
          const pgNameUnderscore = pgNameLower.replace(/ /g, '_');
          const pgAvatarPath = pngAvatarUrls[pgNameLower] || pngAvatarUrls[pgNameUnderscore];
          if (pgAvatarPath) {
              return joinUrl(getServerUrl(), pgAvatarPath);
          }
      }
      return userProfile?.avatar ? joinUrl(getServerUrl(), userProfile.avatar) : undefined;
  }, [isGdrMode, userProfile, pngAvatarUrls, getServerUrl]);

  const handleSendMessage = async (content: string, audioBlob?: Blob, mediaFile?: File, mediaType?: string) => {
    if (!isConnected) { toast.warning(t("index.warn_not_connected")); return; }
    
    const userAvatarUrl = getUserAvatarUrl();
    
    let localMediaUrl = undefined;
    if (audioBlob) {
        localMediaUrl = URL.createObjectURL(audioBlob);
    } else if (mediaFile) {
        localMediaUrl = URL.createObjectURL(mediaFile);
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString() + Math.random(),
      role: "user",
      sender: userProfile?.name || t("profile_dialog.gender_options.other"),
      content: content || (audioBlob ? `[${t("input_bar.recording")}]` : (mediaFile ? `[${t("input_bar.document")}: ${mediaFile.name}]` : "")),
      timestamp: new Date(),
      avatar: userAvatarUrl,
      mediaUrl: localMediaUrl, 
      mediaType: audioBlob ? "audio" : (mediaType as any || "image"),
      fileName: mediaFile?.name || "voice_message.webm"
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsThinking(true);
    setThinkingCharacter(activeAvatar);
    
    // [FIX] Vaporizza istantaneamente eventuali Ghost Text pendenti se l'utente prende l'iniziativa
    setGhostStatus('hidden');
    setGhostText('');

    if (audioBlob) {
      const formData = new FormData();
      formData.append("audio", audioBlob, "voice_message.webm");
      formData.append("text", content);
      formData.append("session_id", currentSessionId || "");
      formData.append("avatar", activeAvatar);

      try {
        const response = await fetch(`${getServerUrl()}/api/voice-message`, {
          method: "POST",
          body: formData,
          headers: getHeaders()
        });
        
        if (!response.ok) {
          throw new Error(t("chat_area.voice_upload_failed"));
        }
      } catch (error: any) {
        console.error(t("index.err_voice_message"), error);
        toast.error(t("chat_area.voice_message_error"), { description: error.message });
        setIsThinking(false);
      }
    } else if (mediaFile) {
      const formData = new FormData();
      formData.append("file", mediaFile);
      
      // --- [FIX CRITICO] RICONOSCIMENTO TIPO FILE (ANTI-TEMP_IMAGES BUG) ---
      // Se il mediaType non è passato correttamente dal componente figlio,
      // lo deduciamo dall'estensione del file per garantire il routing corretto nel backend.
      let finalMediaType = mediaType;
      if (!finalMediaType) {
          const ext = mediaFile.name.split('.').pop()?.toLowerCase();
          if (['pdf', 'txt', 'doc', 'docx', 'md', 'csv', 'xls', 'xlsx'].includes(ext || '')) {
              finalMediaType = "document";
          } else if (['mp4', 'webm', 'mov', 'avi'].includes(ext || '')) {
              finalMediaType = "video";
          } else {
              finalMediaType = "image";
          }
      }
      
      formData.append("type", finalMediaType);
      if (content) formData.append("text", content); 

      try {
        toast.info(t("chat_area.uploading"), { description: t("chat_area.sending_file", { file: mediaFile.name }) });
        const response = await fetch(`${getServerUrl()}/api/upload_media`, {
          method: "POST",
          body: formData,
          headers: getHeaders()
        });

        if (!response.ok) {
          throw new Error(t("chat_area.upload_failed", { status: response.statusText }));
        }
      } catch (error: any) {
        console.error(t("index.err_upload"), error);
        toast.error(t("index.err_upload_failed"), { description: error.message });
        setIsThinking(false);
      }
    } else {
      sendMessage(JSON.stringify({ type: "user_message", text: content }));
    }
  };

  // --- [NUOVO v34.0] ATTIVAZIONE HOOK ---
  // --- [MODIFICA v36.0] Passaggio soglia dinamica ---
  const { isListening, isRecording: isSentinelRecording, volumeLevel } = useSentinelHearing({
      enabled: isSentinelMode && isSentinelHearingEnabled && !isPrivacyMode,
      isAiSpeaking: !!currentAudioUrl, // Se c'è un URL audio, l'AI sta parlando
      onAudioCaptured: (blob) => handleSendMessage("", blob),
      onSpeechStart: () => {
          console.log("[VAD] Interruzione vocale rilevata! Blocco l'AI.");
          // 1. Ferma l'audio HTML5 in riproduzione
          if (stopAudio) {
              try { stopAudio(); } catch(e) {}
          }
          
          // --- [FIX PRO] HARD KILL AUDIO DOM ---
          // Se l'hook fallisce, forziamo il tag audio a fermarsi prima di smontarlo
          if (previewAudioRef.current) {
              previewAudioRef.current.pause();
              previewAudioRef.current.currentTime = 0;
          }
          
          setCurrentAudioUrl(null);
          
          // 2. Invia il comando di stop al server
          if (isConnected) {
              sendMessage(JSON.stringify({ type: "command", text: "/stop_generation" }));
              setIsThinking(false);
              toast.info(t("index.toast_generation_stopped"));
          }
      },
      silenceThreshold: perceptionSettings.silence_threshold // Valore dinamico
  });

  // --- HYBRID LOADING: Funzione per scaricare la cronologia via HTTP ---
  const fetchSessionMessages = useCallback(async (sessionId: string, preloadedMessages?: any[]) => {
    try {
      console.log("[fetchSessionMessages] Inizio caricamento per sessione:", sessionId);
      let messagesData = preloadedMessages;
      
      if (!messagesData) {
          // --- [NUOVO FASE 5] TENTATIVO RECUPERO DA LOCAL STORAGE ---
          const localBackup = localStorage.getItem(`airis_chat_backup_${sessionId}`);
          if (localBackup) {
              try {
                  const parsedBackup = JSON.parse(localBackup);
                  if (Array.isArray(parsedBackup) && parsedBackup.length > 0) {
                      console.log("[fetchSessionMessages] Recupero immediato da Local Storage.");
                      // [FIX CRITICO] Ripristina gli oggetti Date distrutti dal JSON.stringify
                      const restoredBackup = parsedBackup.map((msg: any) => ({
                          ...msg,
                          timestamp: new Date(msg.timestamp)
                      }));
                      setMessages(restoredBackup);
                  }
              } catch(e) {}
          }

          console.log("[fetchSessionMessages] Dati non pre-caricati, eseguo fetch HTTP...");
          const baseUrl = getServerUrl();
          const headers = getHeaders();
          const response = await fetch(`${baseUrl}/api/sessions/${sessionId}`, { headers });
          if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
          messagesData = await response.json();
      }

      if (!Array.isArray(messagesData)) {
          console.error("[fetchSessionMessages] Formato dati non valido:", messagesData);
          throw new Error("Invalid data format: expected an array");
      }

      console.log(`[fetchSessionMessages] Trovati ${messagesData.length} messaggi.`);

      // Mappatura messaggi con logica di identità robusta e anti-crash
      const loadedMessages: ChatMessage[] = messagesData.map((msg: any) => {
          const speakerLower = (msg.speaker || "").toLowerCase();
          const userNameLower = (userProfile?.name || t("chat.welcome_back", { name: "" }).replace(", .", "")).toLowerCase();
          
          // Identificazione User (Case Insensitive + Alias Samael)
          const isUser = speakerLower === userNameLower || 
                        speakerLower === "user" || 
                        speakerLower === "samael" ||
                        speakerLower === "creatore" || 
                        speakerLower === "creatone"; 

          let msgAvatar = undefined;
          if (isUser) {
              msgAvatar = getUserAvatarUrl();
          } else {
              // --- FIX v36.4: SMART ICON LOOKUP (SPAZI -> UNDERSCORE) ---
              const speakerKeyUnderscore = speakerLower.replace(/ /g, '_');
              const pngUrl = pngAvatarUrls[speakerLower] || pngAvatarUrls[speakerKeyUnderscore];
              
              // --- [FIX CRITICO] RACE CONDITION IMMAGINI CHAT ---
              // Non ci fidiamo dello stato React aiAvatarUrl (potrebbe essere vecchio).
              // Peschiamo l'immagine direttamente dalla mappa globale usando il nome del mittente!
              let directAiUrl = undefined;
              if (allAvatarData[speakerLower] && allAvatarData[speakerLower].ai_base_avatar_url) {
                  directAiUrl = joinUrl(getServerUrl(), allAvatarData[speakerLower].ai_base_avatar_url);
              }
              
              msgAvatar = pngUrl ? joinUrl(getServerUrl(), pngUrl) : (directAiUrl || aiAvatarUrl);
          }
          
          return {
              id: String(msg.id || Date.now() + Math.random()), 
              role: isUser ? "user" : "gemma",
              sender: msg.speaker || "Unknown",
              content: msg.content || "",
              timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
              avatar: msgAvatar,
          };
      });
      
      // --- [FIX GOD MODE 1.2] AMNESIA DA RACE CONDITION ---
      // Fonde i messaggi caricati dal DB con quelli appena arrivati via WebSocket durante il fetch
      setMessages(prev => {
          const newMsgs = loadedMessages.filter(lm => !prev.some(pm => 
              pm.id === lm.id || 
              (pm.content === lm.content && pm.role === lm.role) // [FIX CRITICO] Deduplicazione per contenuto
          ));
          // [FIX CRITICO] Sort robusto: forza la conversione a Date per evitare crash se ci sono stringhe residue
          return [...prev, ...newMsgs].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
      });
      setCurrentSessionId(sessionId); 
      toast.success(t("index.toast_session_loaded"));
    } catch (error) {
      console.error(t("index.err_fetch_session_messages"), error);
      toast.error(t("index.err_load_session_history"));
    }
  },[getServerUrl, userProfile, pngAvatarUrls, aiAvatarUrl, getUserAvatarUrl, t]);

  // --- [NUOVO FASE 5] STATE RECOVERY (LOCAL STORAGE) ---
  useEffect(() => {
      if (messages.length > 0 && currentSessionId) {
          try {
              // [FIX QUOTA EXCEEDED] Salviamo solo gli ultimi 50 messaggi per non saturare i 5MB del browser.
              // Il database backend conserva comunque l'intera cronologia.
              const messagesToBackup = messages.slice(-50);
              localStorage.setItem(`airis_chat_backup_${currentSessionId}`, JSON.stringify(messagesToBackup));
          } catch (e) {
              console.warn("[Local Storage] Quota superata. Avvio Garbage Collector locale...", e);
              try {
                  // Se la memoria è piena, eliminiamo i backup delle VECCHIE sessioni orfane
                  const keysToRemove = [];
                  for (let i = 0; i < localStorage.length; i++) {
                      const key = localStorage.key(i);
                      if (key && key.startsWith('airis_chat_backup_') && key !== `airis_chat_backup_${currentSessionId}`) {
                          keysToRemove.push(key);
                      }
                  }
                  keysToRemove.forEach(k => localStorage.removeItem(k));
                  
                  // Riprova il salvataggio dopo la pulizia
                  const messagesToBackup = messages.slice(-50);
                  localStorage.setItem(`airis_chat_backup_${currentSessionId}`, JSON.stringify(messagesToBackup));
                  console.log("[Local Storage] Pulizia completata e backup salvato.");
              } catch (cleanupError) {
                  console.error("[Local Storage] Impossibile salvare il backup locale. Quota permanentemente esaurita.");
              }
          }
      }
  }, [messages, currentSessionId]);

  // --- [FIX CRITICO] RETROACTIVE AVATAR UPDATER (Cura Amnesia Immagini Ctrl+F5) ---
  // Se la sessione viene caricata via WebSocket PRIMA che la fetch HTTP delle immagini sia finita,
  // i messaggi avranno avatar = undefined. Questo hook ripassa i messaggi e inietta le immagini
  // non appena i dati di allAvatarData e aiAvatarUrl diventano disponibili.
  useEffect(() => {
      if (aiAvatarUrl || Object.keys(allAvatarData).length > 0 || userProfile?.avatar) {
          setMessages(prev => {
              let hasChanges = false;
              const updatedMessages = prev.map(msg => {
                  if (msg.role !== 'user' && (!msg.avatar || msg.avatar.includes('undefined'))) {
                      const speakerLower = (msg.sender || "").toLowerCase();
                      const speakerKeyUnderscore = speakerLower.replace(/ /g, '_');
                      const pngUrl = pngAvatarUrls[speakerLower] || pngAvatarUrls[speakerKeyUnderscore];

                      let directAiUrl = undefined;
                      if (allAvatarData[speakerLower] && allAvatarData[speakerLower].ai_base_avatar_url) {
                          directAiUrl = joinUrl(getServerUrl(), allAvatarData[speakerLower].ai_base_avatar_url);
                      }

                      const newAvatar = pngUrl ? joinUrl(getServerUrl(), pngUrl) : (directAiUrl || aiAvatarUrl);
                      if (newAvatar && newAvatar !== msg.avatar) {
                          hasChanges = true;
                          return { ...msg, avatar: newAvatar };
                      }
                  }
                  // --- [FIX CRITICO] Cura Amnesia Avatar Utente ---
                  else if (msg.role === 'user' && (!msg.avatar || msg.avatar.includes('undefined'))) {
                      const correctUserAvatar = getUserAvatarUrl();
                      if (correctUserAvatar && correctUserAvatar !== msg.avatar) {
                          hasChanges = true;
                          return { ...msg, avatar: correctUserAvatar };
                      }
                  }
                  return msg;
              });
              return hasChanges ? updatedMessages : prev;
          });
      }
  },[aiAvatarUrl, allAvatarData, pngAvatarUrls, getServerUrl, getUserAvatarUrl, userProfile]);

  // --- [FIX BUG 01] SINCRONIA FORZATA AI AVATAR URL (THINKING BUBBLE MOBILE) ---
  // Garantisce che l'immagine di base dell'AI sia sempre allineata all'avatar attivo,
  // risolvendo il bug dello scambio di immagini (es. Gemma invece di Oshino Ai) su mobile
  // causato da race conditions tra WebSocket e fetch HTTP.
  useEffect(() => {
      if (activeAvatar && Object.keys(allAvatarData).length > 0) {
          const avatarData = allAvatarData[activeAvatar.toLowerCase()];
          if (avatarData && avatarData.ai_base_avatar_url) {
              const correctUrl = joinUrl(getServerUrl(), avatarData.ai_base_avatar_url);
              if (aiAvatarUrl !== correctUrl) {
                  setAiAvatarUrl(correctUrl);
              }
          }
      }
  },[activeAvatar, allAvatarData, getServerUrl, aiAvatarUrl]);

  useEffect(() => {
    if (serverConfig && status === 'disconnected') {
        // [FIX CRITICO] Debounce per evitare Race Conditions e spam di connessioni
        const timer = setTimeout(() => {
            connect();
        }, 1000);
        return () => clearTimeout(timer);
    }
  }, [serverConfig, status, connect]);

  // ---[FIX CRITICO] LUCCHETTO ANTI-SPAM WEBSOCKET ---
  const hasSyncedSession = useRef(false);

  // --- FIX v29.57: SINCRONIA SESSIONE SERVER-FIRST ---
  useEffect(() => {
    if (isConnected && !hasSyncedSession.current) {
      hasSyncedSession.current = true;
      const syncSession = async () => {
          console.log(t("index.log_connected_sync"));
          let targetSessionId = null;

          // 1. Chiedi al server (Verità Assoluta)
          try {
              const baseUrl = getServerUrl();
              // [FIX v119.2] Aggiunti headers JWT per permettere la sincronizzazione su mobile
              const res = await fetch(`${baseUrl}/api/session/active`, { headers: getHeaders() });
              if (res.ok) {
                  const data = await res.json();
                  if (data.session_id) {
                      console.log(t("index.log_active_session_found", { id: data.session_id }));
                      targetSessionId = data.session_id;
                  }
              }
          } catch (e) {
              console.error(t("index.err_check_session_server"), e);
          }

          // 2. Fallback su LocalStorage (Memoria Locale)
          if (!targetSessionId) {
              targetSessionId = localStorage.getItem("airis_last_session_id");
              if (targetSessionId) console.log(t("index.log_local_session_found", { id: targetSessionId }));
          }

          // 3. Azione
          if (targetSessionId) {
              //[FIX CRITICO] Carica la cronologia direttamente via HTTP per non bloccarsi se chat.py sta pensando.
              // Questo permette di vedere subito la chat e l'indicatore "Thinking" anche se il backend è occupato.
              fetchSessionMessages(targetSessionId);
          }
          // [FIX CRITICO MOBILE] Chiediamo SEMPRE lo stato globale al server.
          // Questo forza il backend a inviarci l'URL del video corrente, eliminando lo schermo nero.
          sendMessage(JSON.stringify({ type: "request_status" }));
      };
      syncSession();
    } else if (!isConnected) {
      // Resetta il lucchetto se la connessione cade, per permettere la resincronizzazione al rientro
      hasSyncedSession.current = false;
    }
  },[isConnected, sendMessage, getServerUrl, fetchSessionMessages]);

  // ---[FIX CRITICO MOBILE] SINCRONIA AL RIENTRO DAL BACKGROUND ---
  // Quando il browser mobile viene messo in background, congela i WebSocket.
  // Al rientro, forziamo una richiesta di stato per recuperare il video e sbloccare i freeze.
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible" && isConnected) {
        console.log("[MOBILE FIX] App tornata in foreground. Richiedo stato globale per sbloccare il video.");
        sendMessage(JSON.stringify({ type: "request_status" }));
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [isConnected, sendMessage]);

  useEffect(() => {
    if (serverConfig && isConnected) {
      // [FIX CRITICO MOBILE] RIMOSSO setIsThinking(false);
      // Se l'LLM stava pensando mentre l'app era in background, resettare questo stato
      // faceva sparire la scritta "sta pensando" al rientro nell'app.
      const fetchInitialData = async () => {
        try {
          const headers = getHeaders();
          const baseUrl = getServerUrl();
          
          // --- [FIX 2B] RACE CONDITION CARICAMENTO SESSIONE ---
          // 1. Fetch del profilo utente PRIMA degli altri dati per ottenere la lingua corretta
          let lang = "it";
          const profileRes = await fetch(`${baseUrl}/api/user_profile`, { headers });
          
          if (profileRes.ok) {
            const profileData: any = await profileRes.json();
            lang = profileData.preferredLanguage || "it";
            
            if (profileData.first_run === true || !profileData.name) {
                console.log(t("index.log_first_run_detected"));
                setWelcomeWizardOpen(true);
                localStorage.removeItem("airis_user_profile");
            } else {
                const profile: UserProfile = profileData;
                setUserProfile(profile);
                saveUserProfile(profile);
                setIsStealthMode(profile.isStealthMode || false);
                toast.success(t("index.toast_profile_synced"), { description: t("index.toast_profile_synced_desc", { name: profile.name }) });
            }
          } else {
            if (!loadUserProfile()) setWelcomeWizardOpen(true);
          }

          // 2. Fetch parallelo dei dati rimanenti usando la lingua corretta
          const[mapRes, pngAvatarsRes, perceptionRes, campaignRes] = await Promise.all([
            fetch(`${baseUrl}/get_intent_map`, { headers }),
            fetch(`${baseUrl}/api/png_avatars?lang=${lang}`, { headers }),
            fetch(`${baseUrl}/api/settings/perception`, { headers }),
            fetch(`${baseUrl}/api/rpg/campaign-mode?lang=${lang}`, { headers })
          ]);
          
          if (!mapRes.ok) throw new Error(`Server error (intent_map): ${mapRes.statusText}`);
          const mapData = await mapRes.json();
          setAllAvatarData(mapData);
          
          const currentAvatarName = serverConfig.currentAvatar || 'gemma';
          // [FIX CRITICO] Aggiunto .toLowerCase() perché le chiavi in mapData sono sempre minuscole
          const mainAvatarData = mapData[currentAvatarName.toLowerCase()];
          if (mainAvatarData) {
            if (mainAvatarData.ai_base_avatar_url) {
              setAiAvatarUrl(joinUrl(baseUrl, mainAvatarData.ai_base_avatar_url));
            }
            
            // [FIX CRITICO MOBILE] Uso localStorage per persistenza assoluta.
            // Sopravvive alla chiusura totale del browser su Android/iOS.
            const hasGreeted = localStorage.getItem("airis_has_greeted");
            if (!hasGreeted) {
                console.log(t("index.log_request_initial_video", { name: currentAvatarName }));
                
                // [FIX CRITICO] Risoluzione dinamica dell'intent di saluto
                const helloIntent = Object.keys(mainAvatarData.intent_map || {}).find(k => k.startsWith('state_hello')) || 'state_hello_01';
                const intentRes = await fetch(`${baseUrl}/set_intent`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', ...headers },
                    body: JSON.stringify({
                        type: 'action',
                        intent: helloIntent,
                        avatar: currentAvatarName,
                        loop: false
                    })
                });

                if (intentRes.ok) {
                    const intentData = await intentRes.json();
                    if (intentData.video_url) {
                        const fullUrl = joinUrl(baseUrl, intentData.video_url);
                        console.log(t("index.log_initial_video_resolved", { url: fullUrl }));
                        setCurrentVideoUrl(fullUrl);
                        setCurrentIntent("state_hello");
                    } else {
                        console.warn(t("index.warn_no_video_url_hello"));
                    }
                } else {
                    console.error(t("index.err_initial_intent"));
                }
                localStorage.setItem("airis_has_greeted", "true");
            }
          }
          
          if(pngAvatarsRes.ok) {
            const pngAvatarsData = await pngAvatarsRes.json();
            setPngAvatarUrls(pngAvatarsData);
          }
          
          if (perceptionRes.ok) {
              const pData = await perceptionRes.json();
              setPerceptionSettings(pData);
          }
          
          if (campaignRes.ok) {
              const cData = await campaignRes.json();
              setIsCampaignMode(cData.enabled);
          }

          const activeRpgRes = await fetch(`${baseUrl}/api/set_active_rpg`, { 
              method: 'POST',
              headers: { 'Content-Type': 'application/json', ...headers },
              body: JSON.stringify({ rpg_name: "" })
          });
          if (activeRpgRes.ok) {
              const activeData = await activeRpgRes.json();
              setIsGdrPathSet(!!activeData.active_rpg);
          }

        } catch (error) {
          console.error(t("index.err_fetch_initial_data"), error);
          toast.error(t("index.err_load_initial_data"));
        }
      };
      fetchInitialData();
    }
  },[serverConfig, isConnected, getServerUrl, t]); // [FIX 2B] Rimosso userProfile?.preferredLanguage dalle dipendenze

  useEffect(() => {
    if (!latestMessage) return;
    
    console.log(t("index.log_ws_message_received"), latestMessage);

    const { type, intent, audio_url, text, payload, avatar_url, avatar, video_url, loop, media_type, url, filename, effect_type, x, y, history, world_state, target_player, sender, is_technical } = latestMessage;

    switch (type) {
      // --- HANDLER RITO DELLA GENESI ---
      case "request_genesis_roster":
          if (payload && payload.available_pngs) {
              setGenesisAvailablePngs(payload.available_pngs);
              // Invece di aprire subito, mettiamo in coda per evitare sovrapposizioni
              setPendingGenesisData(payload.available_pngs);
          }
          break;

      // ---[AGGIUNTA v29.38] HANDLER PRELOAD ---
      case "preload":
        if (video_url) {
            const fullPreloadUrl = joinUrl(getServerUrl(), video_url);
            console.log(t("index.log_preload_signal", { url: fullPreloadUrl }));
            setPreloadVideoUrl(fullPreloadUrl);
            // Reset dello stato dopo un secondo per permettere al componente VideoPlayer di reagire
            setTimeout(() => setPreloadVideoUrl(null), 1000);
        }
        break;

      case "action":
        console.log(t("index.log_action_received", { intent: intent || "", loop: String(loop), url: video_url || "" }));
        
        const applyVideoState = () => {
            if (intent && intent.startsWith('state_thinking')) {
                setIsThinking(true);
            }
            
            // --- [FIX SCENARIO 2] GESTIONE MAIN HOST IN GDR ---
            // Se siamo in GDR e l'azione è un IDLE, forziamo il ritorno all'Avatar Main Host
            // Questo garantisce che quando nessuno parla, si veda l'Avatar principale.
            let targetAvatar = avatar || activeAvatar;
            
            if (isGdrMode && intent && (intent.startsWith('state_idle') || intent.startsWith('state_listening'))) {
                // Recuperiamo il Main Host dalla configurazione server
                const mainHost = serverConfig?.currentAvatar || "gemma";
                targetAvatar = mainHost;
                setActiveAvatar(mainHost);
            } else if (avatar) {
                setActiveAvatar(avatar);
            }

            setForceInterrupt(latestMessage.force_interrupt || false);
            if (intent) setCurrentIntent(intent);
            setLoopVideo(loop || false);
            
            if (text) setCurrentText(text);
            
            if (video_url) {
              const fullVideoUrl = joinUrl(getServerUrl(), video_url);
              console.log(t("index.log_set_video_url", { url: fullVideoUrl }));
              setCurrentVideoUrl(fullVideoUrl);
            } else if (intent && allAvatarData[targetAvatar.toLowerCase()]) {
                const avatarData = allAvatarData[targetAvatar.toLowerCase()];
                const localPath = avatarData.intent_map?.[intent];
                if (localPath) {
                    const fullVideoUrl = joinUrl(getServerUrl(), `/avatars/${targetAvatar.toLowerCase()}/videos/default/${localPath}`);
                    console.log(t("index.log_local_fallback", { url: fullVideoUrl }));
                    setCurrentVideoUrl(fullVideoUrl);
                } else {
                    console.warn(t("index.warn_video_url_null", { intent }));
                }
            }
            
            // --- [RM29] LOW BANDWIDTH MODE ---
            let final_audio_url = audio_url;
            if (lowBandwidthMode && networkMode === 'CLIENT') {
                final_audio_url = null;
                console.log(t("index.log_low_bandwidth"));
            }

            // ---[FIX CRITICO v118.9] PROTOCOLLO Z.6: DISCRIMINAZIONE INTENT ---
            const isSpeakingIntent = intent && intent.startsWith('state_speaking');
            
            if (isSpeakingIntent && final_audio_url && serverConfig && !isMuted && !isPrivacyMode && isFocusedDevice) {
              const fullAudioUrl = joinUrl(getServerUrl(), final_audio_url);
              setCurrentAudioUrl(fullAudioUrl);
              setShouldWaitVideo(true); // WAIT: Solo per Speaking con Audio attivo
              console.log(t("index.log_z6_speaking", { intent }));
            } else {
              // NO WAIT: Intent Emozionali, Thinking, Idle o Mute ON
              setShouldWaitVideo(false); 
              
              // Se c'era un audio URL residuo, lo puliamo per sicurezza
              if (!isSpeakingIntent) setCurrentAudioUrl(null);

              // Sblocco immediato del player
              console.log(t("index.log_z6_non_speaking", { intent: intent || "" }));
              setVideoPlaySignal(Date.now()); 
            }

            if (final_audio_url && !isFocusedDevice) {
                console.log(t("index.log_audio_ignored_observer"));
            }
        };

        // --- [FIX CRITICO MOBILE] DOM PAINT YIELDING ---
        // I browser mobile (Android/iOS) spesso bufferizzano i pacchetti WebSocket.
        // Il messaggio di testo e il comando video arrivano nello stesso istante.
        // Se avviamo subito il video, la decodifica hardware blocca il Main Thread
        // e il browser non "disegna" la bolla di testo fino alla fine del video.
        // Ritardiamo l'avvio del video per forzare il Paint del DOM.
        if (intent && intent.startsWith('state_speaking')) {
            setTimeout(applyVideoState, 250); // Aumentato a 250ms per garantire il render del testo su dispositivi lenti
        } else {
            setTimeout(applyVideoState, 50); // Yield minimo di 50ms per tutte le altre azioni per sbloccare la UI
        }
        break;

      case "text_message":
            if (text) {
              // --- FIX v36.5: ECHO PROTOCOL LOGIC ---
              // Se le payload contiene role: "user", è un echo dell'input utente (es. da Active Hearing)
              const isUserEcho = payload?.role === "user";

              // --- [FIX BUG 01] ANTI-DUPLICATE FILTER ---
              // Se il messaggio con questo ID esiste già, ignoralo.
              // [FIX BUG 02] Rimosso il controllo sul contenuto per i messaggi AI, 
              // altrimenti le risposte identiche (es. "Fatto, amore") venivano scartate e perse.
              setMessages((prev) => {
                const isDuplicate = prev.some(m => latestMessage.id && m.id === latestMessage.id);
                if (isDuplicate) return prev;
              
                let fullAvatarUrl = "";
                if (isUserEcho) {
                    fullAvatarUrl = getUserAvatarUrl() || "";
                } else {
                    fullAvatarUrl = avatar_url ? joinUrl(getServerUrl(), avatar_url) : aiAvatarUrl;
                }

                const newMessage: ChatMessage = {
                  id: Date.now().toString() + Math.random(),
                  role: isUserEcho ? "user" : "gemma",
                  sender: isUserEcho ? (userProfile?.name || t("profile_dialog.gender_options.other")) : (avatar || "AI"),
                  content: text,
                  timestamp: new Date(),
                  avatar: fullAvatarUrl,
                  guildName: payload?.guild_name,
                  guildSymbol: payload?.guild_symbol
                };
                
                return [...prev, newMessage];
              });

              // --- SIDE EFFECTS (Fuori dal setState per evitare warning React) ---
              // ---[RM29] GUEST TRACKING (HOST SIDE) ---
              if (networkMode === 'HOST' && text.includes("è entrato nella locanda")) {
                  const match = text.match(/\*(.*?)\sè entrato/);
                  if (match && match[1]) {
                      setConnectedGuests(prev => {
                          if (!prev.includes(match[1])) return [...prev, match[1]];
                          return prev;
                      });
                  }
              }
              
              // Aggiorna anche il testo corrente per i sottotitoli Sentinel (solo se non è un echo utente)
              if (!isUserEcho) {
                  setCurrentText(text);
              }
            }
            break;

      case "user_media":
        if (url && media_type) {
            const fullMediaUrl = joinUrl(getServerUrl(), url);
            const userAvatarUrl = getUserAvatarUrl();
            
            // --- FIX v29.49: DOUBLE BUBBLE PREVENTION ---
            setMessages((prev) => {
                const lastMsg = prev[prev.length - 1];
                // Controlla se l'ultimo messaggio è dell'utente e ha lo stesso nome file (messaggio ottimistico)
                if (lastMsg && lastMsg.role === "user" && lastMsg.fileName === filename) {
                     // Aggiorna il messaggio esistente con l'URL del server, mantenendo il contenuto testuale
                     return prev.map((msg, idx) => {
                         if (idx === prev.length - 1) {
                             return { ...msg, mediaUrl: fullMediaUrl };
                         }
                         return msg;
                     });
                }
                
                // Se non c'è corrispondenza (es. messaggio da altro dispositivo), aggiungi nuovo
                const mediaMsg: ChatMessage = {
                    id: Date.now().toString() + Math.random(),
                    role: "user",
                    sender: userProfile?.name || t("profile_dialog.gender_options.other"),
                    content: "",
                    timestamp: new Date(),
                    avatar: userAvatarUrl,
                    mediaUrl: fullMediaUrl,
                    mediaType: media_type,
                    fileName: filename
                };
                return [...prev, mediaMsg];
            });

            setIsThinking(true);
            setThinkingCharacter(activeAvatar);
        }
        break;

      case "autofill_result":
        if (payload) setAutofillData(payload);
        break;

      // --- [NUOVO v124.0] HANDLER PROGRESSO EVOLUTIVO ---
      case "evolution_progress":
        if (payload) {
            setEvolutionData(payload);
            if (payload.status === "processing") {
                setIsEvolving(true);
            }
            if (payload.status === "complete") {
                setIsEvolving(false);
                // ---[FIX USCITA GDR] Spegne automaticamente al completamento ---
                sendMessage(JSON.stringify({ type: "command", text: "/force_quit" }));
                toast.success(t("index.toast_evolution_completed"), { description: t("index.toast_all_souls_updated") });
            }
            if (payload.status === "error") {
                setIsEvolving(false);
                // Spegne anche in caso di errore per non bloccare il sistema
                sendMessage(JSON.stringify({ type: "command", text: "/force_quit" }));
                toast.error(t("index.err_evolution"), { description: payload.message });
            }
        }
        break;

      // --- [NUOVO] HANDLER SALVATAGGIO MEMORIE ---
      case "memory_progress":
        if (payload) {
            if (payload.status === "processing") {
                setIsSavingMemories(true);
            }
            if (payload.status === "complete") {
                setIsSavingMemories(false);
            }
            if (payload.status === "error") {
                setIsSavingMemories(false);
                toast.error(t("index.err_saving_memories"), { description: payload.message });
            }
        }
        break;

      // --- [NUOVO] HANDLER ULTIMO MESSAGGIO FACTORY RESET ---
      case "factory_reset_goodbye":
        if (text) {
            setFinalGoodbyeText(text);
            setFinalGoodbyeWipe(payload?.total_wipe || false);
            setFinalGoodbyeOpen(true);
            setIsResetting(false); // Sblocca eventuali spinner precedenti
            setIsResetConfirmOpen(false); // Chiude il primo alert se aperto
            setSettingsOpen(false); // Chiude i settings per far vedere bene il messaggio
            setModelsDialogOpen(false); // Chiude anche il dialogo modelli se aperto
        }
        break;

      case "def_generated":
        // --- [FIX CRITICO] PASSAGGIO PAYLOAD COMPLETO ---
        // Il NewConnectorDialog si aspetta una stringa JSON contenente sia 'def' che 'dependencies'.
        // Passiamo l'intero payload stringificato invece di estrarre solo 'def'.
        if (payload && pendingDefGenResolver.current) {
            pendingDefGenResolver.current(JSON.stringify(payload));
            pendingDefGenResolver.current = null;
        }
        break;

      // ---[NUOVO v121.0] GESTIONE GENERAZIONE SKILL ---
      case "skill_generated":
        if (payload && payload.content && pendingDefGenResolver.current) {
            pendingDefGenResolver.current(payload.content);
            pendingDefGenResolver.current = null;
        }
        break;
        
      // --- NUOVO: GESTIONE FOCUS HIVE MIND (v31.0) ---
      case "hive_focus_change":
          if (payload && payload.device_id) {
              const newFocusId = payload.device_id;
              const amIFocused = newFocusId === deviceId;
              
              console.log(t("index.log_focus_shifted", { id: newFocusId, focused: String(amIFocused) }));
              setIsFocusedDevice(amIFocused);
              
              if (amIFocused) {
                  toast.success(t("index.toast_active_presence"), { description: t("index.toast_here_with_you") });
                  // Opzionale: Unmute automatico se si vuole
                  // setIsMuted(false); 
              } else {
                  // Modalità Osservatore: Silenzioso ma vigile
                  // Non forziamo il mute globale per non confondere l'utente, ma l'audio non partirà
              }
          }
          break;
      
      // --- NUOVO: GESTIONE INTERCOM (v33.0) ---
      case "intercom_audio":
          if (payload && payload.target_device_id === deviceId && payload.audio_url) {
              console.log(t("index.log_incoming_intercom"));
              const fullAudioUrl = joinUrl(getServerUrl(), payload.audio_url);
              
              // --- [NUOVO v119.3] GHOST PRESENCE (LIP-SYNC) ---
              if (payload.video_url && payload.idle_url) {
                  const fullVideoUrl = joinUrl(getServerUrl(), payload.video_url);
                  const fullIdleUrl = joinUrl(getServerUrl(), payload.idle_url);
                  
                  console.log(t("index.log_ghost_presence"));
                  // Forza il video di speaking in loop
                  setCurrentVideoUrl(fullVideoUrl);
                  setLoopVideo(true);
                  
                  // Riproduzione forzata (God Mode) con callback di reset
                  playAudio(fullAudioUrl, () => {
                      console.log(t("index.log_intercom_finished_idle"));
                      // Al termine dell'audio, torna in Idle
                      setCurrentVideoUrl(fullIdleUrl);
                      setLoopVideo(true);
                  });
              } else {
                  // Fallback solo audio (se video non disponibili)
                  playAudio(fullAudioUrl, () => {
                      console.log(t("index.log_intercom_finished"));
                  });
              }
              
              toast.info(t("index.toast_incoming_intercom"), { icon: <Mic className="w-4 h-4" /> });
          }
          break;
      
      // ---[NUOVO v34.1] GESTIONE RICHIESTA CAMERA (OCCHIO OBBEDIENTE) ---
      case "request_camera_capture":
          console.log(t("index.log_camera_request"));
          setCameraCaptureOpen(true);
          toast.info(t("index.toast_wants_to_see"), { description: t("index.toast_opening_camera") });
          break;

      // --- [NUOVO v39.7] GESTIONE EFFETTO VISIVO (GHOST CURSOR) ---
      case "visual_effect":
          if (effect_type && x !== undefined && y !== undefined) {
              console.log(t("index.log_visual_effect", { type: effect_type, x, y }));
              setVisualEffect({
                  type: effect_type,
                  x: x,
                  y: y,
                  timestamp: Date.now()
              });
          }
          break;

      case "system_status":
        if (payload && typeof payload === "object") {
          // --- [NUOVO] HANDLER FASE DI SPEGNIMENTO ---
          if (payload.shutdown_phase) {
              setShutdownPhase(payload.shutdown_phase);
          }

          if (typeof payload.thinking === 'boolean') {
              const isNowThinking = payload.thinking;
              setIsThinking(isNowThinking);
              
              const newThinkingChar = payload.thinking_character || thinkingCharacter;
              if (payload.thinking_character) setThinkingCharacter(newThinkingChar);
          }
          
          if (payload.thinking_action) {
              setThinkingAction(payload.thinking_action);
          }
          
          // ---[FIX v51.2] AUTO-SWITCH GDR PROTETTO ---
          // Verifichiamo che la chiave gdr_mode sia presente e non sia un effetto collaterale di altri switch
          if (payload.hasOwnProperty('gdr_mode') && typeof payload.gdr_mode === 'boolean') {
              // Eseguiamo l'aggiornamento SOLO se il valore è diverso dallo stato attuale
              if (payload.gdr_mode !== isGdrMode) {
                  setIsGdrMode(payload.gdr_mode);
                  if (payload.gdr_mode) {
                      setIsGdrPathSet(true);
                      toast.success(t("index.toast_gdr_mode_activated"));
                  } else {
                      toast.info(t("index.toast_gdr_mode_deactivated"));
                  }
              }
          }
          
          // ---[NUOVO v27.0] SYNC MODALITÀ CAMPAGNA ---
          if (typeof payload.campaign_mode === 'boolean') {
              setIsCampaignMode(payload.campaign_mode);
              // [FIX HUD IMMORTALE] Pulisce le barre HP se la campagna viene spenta (Bypass Glitch)
              if (!payload.campaign_mode) {
                  setCombatEntities(Array(0));
              }
          }
          
          if (typeof payload.is_muted === 'boolean') { setIsMuted(payload.is_muted); toast.info(payload.is_muted ? t("index.toast_audio_muted") : t("index.toast_audio_unmuted")); }
          if (typeof payload.is_monitoring === 'boolean') setIsMonitoring(payload.is_monitoring);
          
          // --- RIFONDAZIONE ASCOLTO (v29.50) ---
          if (typeof payload.is_active_hearing === 'boolean') setIsActiveHearing(payload.is_active_hearing);
          
          // is_learning_enabled rimosso da Index (gestito via KnowledgeBase config)
          if (payload.gdr_flow === 'end') setIsThinking(false);
          
          if (payload.active_avatar) {
              console.log(t("index.log_sync_active_avatar", { avatar: payload.active_avatar }));
              setActiveAvatar(payload.active_avatar);
              // [FIX CRITICO] Rimosso setThinkingCharacter(payload.active_avatar) per evitare 
              // di sovrascrivere il personaggio che sta pensando in GDR (es. PNG_1 -> Avatar Base)
              
              // --- [FIX CRITICO] AGGIORNA IMMAGINE CHAT AL CAMBIO AVATAR ---
              // Quando carichiamo una sessione passata, il backend ci dice chi è l'avatar.
              // Dobbiamo aggiornare immediatamente l'immagine della chat per riflettere l'identità corretta.
              const newAvatarData = allAvatarData[payload.active_avatar.toLowerCase()];
              if (newAvatarData && newAvatarData.ai_base_avatar_url) {
                  setAiAvatarUrl(joinUrl(getServerUrl(), newAvatarData.ai_base_avatar_url));
              }

              // --- [FIX CRITICO] CURA AMNESIA CTRL+F5 SENZA ROMPERE IL WEBSOCKET ---
              // Aggiorniamo il LocalStorage direttamente senza toccare lo stato React serverConfig.
              // Se tocchiamo serverConfig, l'hook useWebSocket rileva un cambio di dipendenza,
              // chiude la connessione e la riapre, causando il warning e perdendo messaggi!
              const savedConfig = loadServerConfig();
              if (savedConfig && savedConfig.currentAvatar !== payload.active_avatar) {
                  savedConfig.currentAvatar = payload.active_avatar;
                  saveServerConfig(savedConfig);
              }
          }

          if (payload.session_id) {
              console.log(t("index.log_session_id_received", { id: payload.session_id }));
              localStorage.setItem("airis_last_session_id", payload.session_id);
              setCurrentSessionId(payload.session_id);
          }

          if (payload.new_session === true) {
              console.log(t("index.log_new_session_signal"));
              // [FIX HUD IMMORTALE] Pulisce le barre HP al cambio sessione (Bypass Glitch)
              setCombatEntities(Array(0));
          }

          // --- [NUOVO v114.0] REAL-TIME HEART SYNC - AGGIORNATO v114.3 ---
          if (payload.heart_update === true) {
              console.log(t("index.log_heart_update", { target: payload.png_update || "Avatar" }));
              // Passiamo il nome del PNG (se presente) nel dettaglio dell'evento
              window.dispatchEvent(new CustomEvent('airis-heart-update', { 
                  detail: { png_name: payload.png_update || null } 
              }));
          }

          // --- [NUOVO] REAL-TIME ROSTER SYNC (GDR FIX) ---
          if (payload.roster_update === true) {
              console.log("Rilevato aggiornamento Roster. Lancio evento di sincronizzazione.");
              window.dispatchEvent(new CustomEvent('airis-roster-update'));
          }
          
          if (payload.load_session === true && payload.session_id) {
              console.log(t("index.log_loading_session_http", { id: payload.session_id }));
              // Passiamo i messaggi pre-caricati dal WebSocket per bypassare la fetch HTTP su mobile
              fetchSessionMessages(payload.session_id, payload.messages);

              // ---[NUOVO v51.1] SYNC DISPONIBILITÀ GDR DOPO CARICAMENTO SESSIONE ---
              setTimeout(async () => {
                  const res = await fetch(`${getServerUrl()}/api/set_active_rpg`, { 
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json', ...getHeaders() },
                      body: JSON.stringify({ rpg_name: "" })
                  });
                  if (res.ok) {
                      const data = await res.json();
                      setIsGdrPathSet(!!data.active_rpg);
                  }
              }, 1000);
          }
        }
        break;

      case "prompt":
        if (text && payload && typeof payload === "object" && Array.isArray(payload.options)) {
          toast.message(text, {
            action: { label: "Yes", onClick: () => sendMessage(JSON.stringify({type: "prompt_response", response: payload.options[0]})) },
            cancel: { label: "No", onClick: () => sendMessage(JSON.stringify({type: "prompt_response", response: payload.options[1]})) },
            duration: 10000,
          });
        }
        break;
        
      case "download_file":
        if (payload && payload.path) {
            const downloadUrl = joinUrl(getServerUrl(), payload.path);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = payload.path.split('/').pop() || 'download';
            document.body.appendChild(a);
            a.click();
            a.remove();
            toast.success(t("index.toast_download_started"));
        }
        break;
        
      // --- [NUOVO v37.0] GHOST TEXT HANDLERS ---
      case "ghost_typing":
          if (text) {
              // --- [FIX] FILTRO DINAMICO RAGIONAMENTO ED ENFORCING ---
              // Se il messaggio è tecnico (es. <think> o Ghost Operator) e l'utente ha
              // disattivato i pensieri tecnici, lo scartiamo all'origine.
              if (latestMessage.is_technical && !showTechThoughts) {
                  return;
              }
              console.log(t("index.log_ghost_typing"), text);
              setGhostText(text);
              setGhostStatus('typing');
          }
          break;
          
      case "ghost_delete":
          console.log(t("index.log_ghost_delete"));
          setGhostStatus('deleting');
          // [FIX] Rimuove fisicamente il Ghost Text dal DOM dopo che l'animazione CSS (500ms) è terminata
          setTimeout(() => {
              setGhostStatus('hidden');
              setGhostText('');
          }, 1000);
          break;
          
      // --- [NUOVO v27.0] AGGIORNAMENTO COMBATTIMENTO ---
      case "rpg_update":
          if (latestMessage.combat_entities) {
              setCombatEntities(latestMessage.combat_entities);
          }
          break;

      // --- [NUOVO v28.0] MULTIPLAYER SYNC & LOCKDOWN ---
      case "SYNC_STATE":
          if (history) {
              console.log(t("index.log_sync_state_received"));
              const loadedMessages: ChatMessage[] = history.map((msg: any) => {
                  const isUser = msg[0] === (userProfile?.name || t("chat.welcome_back", { name: "" }).replace(", .", ""));
                  return {
                      id: Date.now().toString() + Math.random(),
                      role: isUser ? "user" : "gemma",
                      sender: msg[0],
                      content: msg[1],
                      timestamp: new Date(),
                      avatar: isUser ? getUserAvatarUrl() : aiAvatarUrl
                  };
              });
              setMessages(loadedMessages);
              toast.success(t("index.toast_sync_host_completed"));
          }
          break;

      case "LOCK_INPUT":
          setIsInputLocked(true);
          break;

      case "UNLOCK_INPUT":
          if (!target_player || target_player === userProfile?.name) {
              setIsInputLocked(false);
          } else {
              setIsInputLocked(true);
          }
          break;

      case "OOC_MESSAGE":
          if (sender && text) {
              setOocMessages(prev =>[...prev, {
                  id: Date.now().toString() + Math.random(),
                  sender: sender,
                  text: text,
                  timestamp: new Date()
              }]);
          }
          break;

      // --- [NUOVO] RICEZIONE QUEST GENERATA ---
      case "QUEST_GENERATED":
          if (payload) {
              setGeneratedQuest(payload);
              toast.success(t("index.toast_new_adventure"));
          }
          break;

      // --- [RM29] SYNC_SAVE E KICKED ---
      case "SYNC_SAVE":
          if (payload && payload.scheda_aggiornata && networkMode === 'CLIENT') {
              console.log(t("index.log_sync_save_received"));
              try {
                  // Recupera la scheda attuale
                  fetch(`${getServerUrl()}/api/characters/${userProfile?.name}?char_type=PG`, { headers: getHeaders() })
                  .then(res => res.ok ? res.json() : null)
                  .then(localData => {
                      if (localData) {
                          const fullJson = localData.jsonData || {};
                          fullJson.scheda_rpg = payload.scheda_aggiornata;
                          
                          // Salva
                          const formData = new FormData();
                          formData.append("char_type", "PG");
                          formData.append("character_data", JSON.stringify(fullJson));
                          formData.append("lang", userProfile?.preferredLanguage || "it");
                          
                          fetch(`${getServerUrl()}/api/characters`, {
                              method: 'POST',
                              body: formData,
                              headers: getHeaders()
                          });
                          console.log(t("index.log_local_sheet_updated"));
                      }
                  });
              } catch (e) {
                  console.error(t("index.err_sync_save"), e);
              }
          }
          break;

      case "KICKED":
          toast.error(latestMessage.message || t("index.err_kicked_from_room"));
          handleSetNetworkMode('OFF');
          break;

      case "PROFILE_UPDATED":
          if (payload) {
              // FIX: Eseguiamo il merge per non sovrascrivere i dati base (come il nome) con il JSON grezzo del backend
              setUserProfile(prev => {
                  if (!prev) return prev;
                  const updated = { ...prev, guildName: payload.guildName, guildSymbol: payload.guildSymbol };
                  saveUserProfile(updated);
                  return updated;
              });
              toast.success(t("index.toast_profile_synced_guild"));
          }
          break;

      // FIX: Aggiunto handler per i toast del backend (es. errori fondazione gilda)
      case "demiurge_toast":
          if (latestMessage.level === "error") toast.error(latestMessage.message);
          else if (latestMessage.level === "warning") toast.warning(latestMessage.message);
          else if (latestMessage.level === "success") toast.success(latestMessage.message);
          else toast.info(latestMessage.message);
          break;

      default:
        console.log(t("index.log_unhandled_message_type", { type }));
    }
  },[latestMessage, serverConfig, getServerUrl, allAvatarData, activeAvatar, sendMessage, aiAvatarUrl, isMuted, isGdrMode, userProfile, pngAvatarUrls, currentIntent, thinkingCharacter, fetchSessionMessages, isPrivacyMode, deviceId, isFocusedDevice, getUserAvatarUrl]);

  useEffect(() => {
    // --- MODIFICA v31.0: AUDIO SOLO SE FOCALIZZATO ---
    // --- FIX v35.3: DOUBLE AUDIO CHECK ---
    if (currentAudioUrl && !isPrivacyMode && isFocusedDevice) {
      // Se l'URL è nuovo (diverso dall'ultimo suonato), procedi
      if (currentAudioUrl !== lastPlayedAudioRef.current) {
          lastPlayedAudioRef.current = currentAudioUrl; // Marca come suonato
          
          playAudio(
              currentAudioUrl, 
              () => {
                console.log(t("index.log_audio_finished"));
                sendMessage(JSON.stringify({ type: "playback_complete", intent: currentIntent }));
                setCurrentAudioUrl(null);
                lastPlayedAudioRef.current = null; // Reset per permettere replay futuro se necessario
              },
              () => {
                 console.log(t("index.log_audio_started"));
                 setVideoPlaySignal(Date.now());
              },
              (error) => {
                 console.warn(t("index.warn_audio_failed"), error);
                 setVideoPlaySignal(Date.now());
                 //[FIX BUG 1] Cap massimo di 10 secondi per evitare freeze infiniti su testi lunghi in GDR
                 const estimatedDuration = Math.min(Math.max(3000, currentText.length * 50), 10000);
                 console.log(t("index.log_fallback_wait", { duration: estimatedDuration }));
                 setTimeout(() => {
                     console.log(t("index.log_fallback_finished"));
                     sendMessage(JSON.stringify({ type: "playback_complete", intent: currentIntent }));
                     setCurrentAudioUrl(null);
                     lastPlayedAudioRef.current = null;
                 }, estimatedDuration);
              }
          );
      } else {
          console.log(t("index.log_audio_already_playing"));
      }
    } else if (currentAudioUrl && !isFocusedDevice) {
        // Se c'è un URL audio ma non siamo focalizzati, puliamo lo stato per evitare loop
        console.log(t("index.log_audio_ignored_observer_2"));
        setCurrentAudioUrl(null);
    }
  },[currentAudioUrl, playAudio, sendMessage, currentIntent, currentText, isPrivacyMode, isFocusedDevice]);

  const handleVideoEnd = useCallback((intent: string, interrupted: boolean = false) => {
    // ---[NUOVO v118.7] PROTOCOLLO Z.1: FOCUS BYPASS PER TRANSIZIONI CRITICHE ---
    // Determiniamo se l'intent è una transizione che sblocca il backend (Intent, Thinking, Reaction)
    const isCriticalTransition = 
      intent.startsWith("emotion_") || 
      intent.startsWith("reaction_") || 
      intent.startsWith("social_") ||
      intent.startsWith("state_speaking") || // [FIX CRITICO] Sblocca il backend anche durante i lunghi parlati in GDR
      intent.startsWith("state_thinking") ||
      intent.includes("intent");
    
    // --- [FIX CRITICO FREEZE MOBILE] ---
    // Se siamo in Single Player (!currentRoomId), il dispositivo corrente è l'unica verità.
    // Dobbiamo inviare SEMPRE il playback_complete per sbloccare la rotazione degli idle sul telefono,
    // altrimenti il video si congela dopo una singola riproduzione.
    const isSinglePlayer = !currentRoomId;

    //[CERTEZZA Z.1] Se è una transizione critica o siamo l'unico display, inviamo il segnale SEMPRE.
    if (isCriticalTransition || isFocusedDevice || isSinglePlayer) {
        console.log(t("index.log_z1_unlock", { intent, focus: String(isFocusedDevice) }));
        sendMessage(JSON.stringify({ type: "playback_complete", intent }));
    } else {
        console.log(t("index.log_non_critical_video_ended"));
    }
  }, [sendMessage, isFocusedDevice, currentRoomId, t]);

  // ---[SPOSTAMENTO CHIRURGICO PER REGOLE REACT] ---
  const handleLoginSuccess = (token: string) => {
      localStorage.setItem("airis_auth_token", token);
      setIsAuthenticated(true);
      // [FIX] Rimosso connect() manuale. L'useEffect con debounce gestirà la connessione in modo sicuro.
  };

  useEffect(() => {
    if (status === 'connected' && !hasHandshaked.current) {
        toast.success(t("index.toast_connected"));
        
        // [FIX CRITICO] Invia l'Handshake SOLO se siamo connessi a una locanda remota come ospiti.
        // Se siamo sul nostro server locale, non dobbiamo registrarci come duplicati nel GDR.
        if (networkMode === 'CLIENT') {
            const handshakePayload = {
                type: "HANDSHAKE_JOIN",
                player_name: userProfile?.name || t("profile_dialog.gender_options.other"),
                scheda_rpg: (window as any).temp_scheda_rpg || {},
                guild_name: userProfile?.guildName || "",
                guild_symbol: userProfile?.guildSymbol || "",
                gender: userProfile?.gender || "unspecified"
            };
            sendMessage(JSON.stringify(handshakePayload));
        }
        hasHandshaked.current = true; // FIX BUG 03: Previene lo spam di Handshake
    }
    else if (status === 'disconnected' || status === 'error') {
        hasHandshaked.current = false; // Resetta se cade la connessione
        if (status === 'error') toast.error(t("index.err_connection"));
    }
  },[status, userProfile, sendMessage, networkMode]); // Aggiunto networkMode alle dipendenze

  // ---[RM29] AUTO-RECONNECT (FARO DI RICONNESSIONE) E LIMBO CLIENT (60s) ---
  useEffect(() => {
      if (status === 'disconnected' && networkMode === 'CLIENT' && currentRoomId) {
          toast.warning(t("index.warn_connection_lost"), { duration: 5000 });
          
          const startTime = Date.now();
          
          const reconnectInterval = setInterval(async () => {
              // --- THREAT 7: LIMBO CLIENT (Timeout 60 secondi) ---
              if (Date.now() - startTime > 60000) {
                  console.warn(t("index.warn_host_timeout"));
                  clearInterval(reconnectInterval);
                  toast.error(t("index.err_host_lost"));
                  handleSetNetworkMode('OFF');
                  return;
              }

              try {
                  console.log(t("index.log_polling_tracker"));
                  const res = await fetch(`https://www.omnia-diffusion.com/airis_tracker/api.php?path=stanze_attive/${currentRoomId}.json`);
                  if (res.ok) {
                      const roomData = await res.json();
                      if (roomData && roomData.url_ngrok) {
                          const newUrl = roomData.url_ngrok;
                          if (newUrl !== multiplayerUrl) {
                              console.log(t("index.log_new_url_found", { url: newUrl }));
                              clearInterval(reconnectInterval);
                              handleSetNetworkMode('CLIENT', newUrl, lobbyPwd, currentRoomId);
                          }
                      } else {
                          // La stanza non esiste più
                          clearInterval(reconnectInterval);
                          toast.error(t("index.err_room_closed"));
                          handleSetNetworkMode('OFF');
                      }
                  }
              } catch (e) {
                  console.error(t("index.err_auto_reconnect"), e);
              }
          }, 5000);
          
          return () => clearInterval(reconnectInterval);
      }
  },[status, networkMode, currentRoomId, multiplayerUrl, lobbyPwd]);

  const handleStartListening = useCallback(() => {
    if (isConnected) {
      sendMessage(JSON.stringify({ type: "start_listening" }));
    } else {
      toast.warning(t("index.warn_not_connected"));
    }
  }, [isConnected, sendMessage]);

  const handleAutofillRequest = useCallback((url: string) => {
    if (!isConnected) { toast.warning(t("index.warn_not_connected")); return; }
    console.log(`[FRONTEND] Invio comando Autofill per URL: ${url}`);
    sendMessage(JSON.stringify({ type: "command", text: `/autofill url::${url}` }));
  }, [status, sendMessage]);

  // --- [NUOVO v39.9] FETCH CONTENUTI WORLD EDITOR ---
  const fetchWorldContent = useCallback(async (worldName: string) => {
    if (!serverConfig) return;
    const baseUrl = getServerUrl();
    const headers = getHeaders();
    const lang = userProfile?.preferredLanguage || "it";

    try {
      const response = await fetch(`${baseUrl}/api/gdr-world-content?world_name=${worldName}&lang=${lang}`, { headers });
      if (!response.ok) throw new Error(t("index.err_fetch_world_content"));
      const data = await response.json();
      setGdrWorldContent(data);
    } catch (error) {
      console.error(t("index.err_fetching_world_content"), error);
      toast.error(t("index.err_load_world_files"));
    }
  },[serverConfig, getServerUrl, userProfile]);

  // Trigger per il caricamento dei file quando si entra nel tab o si cambia mondo
      useEffect(() => {
        if (modelsDialogOpen && selectedGdrForEditing && activeModelTab === "worldeditor") {
          fetchWorldContent(selectedGdrForEditing);
        }
      }, [selectedGdrForEditing, activeModelTab, modelsDialogOpen, fetchWorldContent]);

      // --- SISTEMA DI ACCODAMENTO DIALOGHI (ANTI-SOVRAPPOSIZIONE) ---
      useEffect(() => {
          // Se abbiamo dati in coda e i dialoghi iniziali sono chiusi, mostriamo la Genesi
          if (pendingGenesisData !== null && !welcomeWizardOpen && !connectionGuideOpen) {
              setGenesisDialogOpen(true);
              setPendingGenesisData(null); // Svuota la coda
          }
      }, [pendingGenesisData, welcomeWizardOpen, connectionGuideOpen]);

      // ===========================================================================
      // 2. AUTH GUARD RENDER (SPOSTATO DOPO GLI HOOK)
      // ===========================================================================

  // --- [NUOVO v10.20] AUTH GUARD RENDER ---
  if (isAuthChecking) {
      return (
          <div className="flex h-screen w-full items-center justify-center bg-black">
              <Loader2 className="w-10 h-10 animate-spin text-primary" />
          </div>
      );
  }
  
  if (!isAuthenticated) {
      return <LoginMask onLoginSuccess={handleLoginSuccess} serverConfig={serverConfig} />;
  }
  // -----------------------------------------

  const handleConnect = () => {
    if (!serverConfig) { setSettingsOpen(true); return; }
    if (isConnected) disconnect();
    else connect();
  };

  const handleSaveSettings = async (config: ServerConfig, credentials: any, prompts: any) => {
    // [FIX CRITICO] Aggiorniamo lo stato React SOLO se i parametri di rete sono cambiati.
    // Questo impedisce al WebSocket di riavviarsi inutilmente causando warning.
    const connectionChanged = 
        !serverConfig ||
        serverConfig.ip !== config.ip || 
        serverConfig.port !== config.port || 
        serverConfig.protocol !== config.protocol;

    if (connectionChanged) {
        setServerConfig(config);
    }
    saveServerConfig(config);
    
    if (credentials && config) {
        const baseUrl = getServerUrl();
        const headers = { ...getHeaders(), 'Content-Type': 'application/json' };
        
        await Promise.all([
            fetch(`${baseUrl}/api/credentials`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ credentials }),
            }),
            fetch(`${baseUrl}/api/prompts`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ scope: 'system', data: prompts }),
            })
        ]).then(responses => {
            for (const response of responses) {
                if (!response.ok) {
                    throw new Error(t("settings_dialog.err_config_save_multiple"));
                }
            }
        });
        
        // --- [NUOVO v36.0] REFRESH PERCEZIONE ---
        // Ricarica le impostazioni di percezione per applicare la nuova soglia
        try {
            const pRes = await fetch(`${baseUrl}/api/settings/perception`, { headers: getHeaders() });
            if (pRes.ok) {
                const pData = await pRes.json();
                setPerceptionSettings(pData);
                console.log(t("index.log_refresh_perception"), pData);
            }
        } catch (e) {
            console.error(t("index.err_refresh_perception"), e);
        }
    }
    
    // [FIX CRITICO] Rimossi disconnect() e connect() manuali.
  };

  const handleSaveProfile = async (profile: UserProfile, imageFile: File | null = null) => {
    if (!isConnected) { toast.error(t("profile_dialog.err_save_not_connected")); return; }
    try {
        const formData = new FormData();
        formData.append("profile_data", JSON.stringify(profile));
        if (imageFile) {
            formData.append("avatar_file", imageFile);
        }

        // FIX CRITICO: Rimuoviamo esplicitamente il Content-Type per permettere al browser di impostare il boundary del multipart/form-data
        const headers = { ...getHeaders() };
        delete headers['Content-Type'];
        delete headers['content-type'];

        const response = await fetch(`${getServerUrl()}/api/user_profile`, {
            method: 'POST',
            headers: headers,
            body: formData
        });
        
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            console.error("Server error:", errData);
            throw new Error(t("index.err_saving_profile"));
        }
        
        // Se c'è un'immagine, forziamo il refresh del profilo dal server per ottenere il nuovo URL con il cache-buster
        if (imageFile) {
            const profileRes = await fetch(`${getServerUrl()}/api/user_profile`, { headers: getHeaders() });
            if (profileRes.ok) {
                const updatedProfileData = await profileRes.json();
                setUserProfile(updatedProfileData);
                saveUserProfile(updatedProfileData);
            }
        } else {
            setUserProfile(profile);
            saveUserProfile(profile);
        }
        
        // [FIX BUG 02] Applica il cambio lingua immediatamente e forza il reload per allineare tutto
        if (profile.preferredLanguage && profile.preferredLanguage !== currentLang) {
            await changeLanguage(profile.preferredLanguage);
            // [FIX BUG 01] Hard reload con cache buster per forzare l'aggiornamento su mobile
            setTimeout(() => {
                window.location.href = window.location.pathname + "?t=" + Date.now();
            }, 500);
        }
        
        toast.success(t("index.toast_profile_update_sent"));
    } catch (e) {
        console.error(t("index.err_saving_profile"), e);
        toast.error(t("index.err_saving_profile"));
    }
  };

  // --- NUOVO: HANDLER COMPLETAMENTO WIZARD (v32.0) ---
  const handleWelcomeComplete = async (profile: UserProfile) => {
      await handleSaveProfile(profile, null);
      setWelcomeWizardOpen(false);
      
      // Fetch connection info and show guide
      try {
          const res = await fetch(`${getServerUrl()}/api/connection-info`, { headers: getHeaders() });
          if (res.ok) {
              const data = await res.json();
              setConnInfo(data);
          }
      } catch (e) {
          console.error("Failed to fetch connection info", e);
      }
      setConnectionGuideOpen(true);
  };

  /// --- MODIFICA v29.41: SUPPORTO INVIO COMBINATO TESTO + MEDIA (FILE) ---
  // --- MODIFICA v34.0: ESTRATTO PER USO ESTERNO (HOOK) ---
  // (Nota: handleSendMessage è definito sopra per essere passato all'hook)

  // --- FIX v29.47: OPTIMISTIC UI UPDATES ---
  const handleToggleGdrMode = () => {
    if (!isConnected) return;
    const newState = !isGdrMode;
    setIsGdrMode(newState); // Optimistic
    sendMessage(JSON.stringify({ type: "command", text: newState ? "/gdr" : "/endgdr" }));
  };

  const handleToggleMute = () => {
    if (!isConnected) return;
    const newState = !isMuted;
    setIsMuted(newState); // Optimistic
    sendMessage(JSON.stringify({ type: "command", text: newState ? "/mute" : "/unmute" }));
  };

  const handleToggleMonitoring = () => {
    if (!isConnected) return;
    const newState = !isMonitoring;
    setIsMonitoring(newState); // Optimistic
    sendMessage(JSON.stringify({ type: "command", text: newState ? "/monitor on" : "/monitor off" }));
  };

  // --- [NUOVO] TOGGLE STEALTH MODE ---
  const handleToggleStealthMode = () => {
      const newState = !isStealthMode;
      setIsStealthMode(newState);
      setUserProfile(prev => {
          if (!prev) return prev;
          const updated = { ...prev, isStealthMode: newState };
          saveUserProfile(updated);
          return updated;
      });
      toast.info(newState ? t("network_dialog.toast_stealth_on") : t("network_dialog.toast_stealth_off"));
  };

  // --- RIFONDAZIONE ASCOLTO (v29.50) ---
  const handleToggleActiveHearing = () => {
    if (!isConnected) return;
    const newState = !isActiveHearing;
    setIsActiveHearing(newState); // Optimistic
    sendMessage(JSON.stringify({ type: "command", text: newState ? "/active_hearing on" : "/active_hearing off" }));
  };

  const handleToggleLearning = () => {
    if (!isConnected) return;
    // Logica spostata in KnowledgeBase config (tab Self Learning)
    sendMessage(JSON.stringify({ type: "command", text: "/toggle_learning" }));
  };

  // Mantenuta per compatibilità, ma ora usata internamente da InputBar per staging
  const handleFileUpload = async (type: string, file: File) => {
      // Questa funzione ora è un wrapper legacy o per chiamate dirette se necessario.
      // La logica principale è spostata in handleSendMessage.
      handleSendMessage("", undefined, file, type);
  };

  const handleStopGeneration = () => {
    if (!isConnected) return;
    sendMessage(JSON.stringify({ type: "command", text: "/stop_generation" }));
    setIsThinking(false);
    toast.info(t("index.toast_generation_stopped"));
  };

  const handleDeleteMessage = async (messageId: string) => {
    setMessages(prev => prev.filter(m => m.id !== messageId));
    
    if (isConnected && currentSessionId) {
        try {
            const baseUrl = getServerUrl();
            const headers = getHeaders();
            await fetch(`${baseUrl}/api/messages/${messageId}`, {
                method: 'DELETE',
                headers: headers
            });
            console.log(t("index.log_msg_deleted_db", { id: messageId }));
        } catch (e) {
            console.error(t("index.err_sync_delete"), e);
        }
    }
  };

  const handleEditMessage = (messageId: string, newContent: string) => {
    setMessages(prev => prev.map(m => m.id === messageId ? { ...m, content: newContent } : m));
  };

  const handleReRunMessage = async (messageId: string) => {
    const messageIndex = messages.findIndex(m => m.id === messageId);
    if (messageIndex === -1) return;
    
    const messageToReRun = messages[messageIndex];
    
    // --- FIX CRITICO RE-RUN (v29.58) ---
    // Cancella il messaggio vecchio dal DB prima di rigenerare
    if (isConnected && currentSessionId) {
        try {
            const baseUrl = getServerUrl();
            const headers = getHeaders();
            // Cancelliamo il messaggio specifico che stiamo rigenerando
            await fetch(`${baseUrl}/api/messages/${messageId}`, {
                method: 'DELETE',
                headers: headers
            });
            console.log(t("index.log_msg_deleted_rerun", { id: messageId }));
            
            // Inoltre, purghiamo il contesto successivo per evitare incoerenze
            await fetch(`${baseUrl}/api/sessions/${currentSessionId}/messages/after/${messageId}`, {
                method: 'DELETE',
                headers: headers
            });
            console.log(t("index.log_context_purged", { id: messageId }));
        } catch (e) {
            console.error(t("index.err_purge_context"), e);
        }
    }

    if (messageToReRun.role === 'user') {
      setMessages(prev => prev.filter(m => m.id !== messageId));
      handleSendMessage(messageToReRun.content || "");
    } else {
      let userPromptMessage = null;
      for (let i = messageIndex - 1; i >= 0; i--) {
          if (messages[i].role === 'user') {
              userPromptMessage = messages[i];
              break;
          }
      }
      
      if (userPromptMessage) {
        const newMessages = messages.slice(0, messageIndex).filter(m => m.id !== userPromptMessage.id);
        setMessages(newMessages);
        handleSendMessage(userPromptMessage.content || "");
      } else {
        toast.warning(t("index.warn_no_original_prompt"));
      }
    }
  };

  const handleQuit = () => {
    if (!isConnected) return;
    
    // Se siamo in GDR, il comando 'addio' innescherà l'evoluzione nel backend
    // che poi invierà i segnali 'evolution_progress' gestiti sopra.
    if (isGdrMode) {
        setSaveMemoriesDialogOpen(true);
    } else {
        // In modalità standard, procedi al quit normale
        setConfirmQuitDialogOpen(true);
    }
  };

  const handleSaveMemoriesResponse = (shouldSave: boolean) => {
    setSaveMemoriesDialogOpen(false);
    if (shouldSave) {
      // Invia il comando unificato che salva e innesca l'evoluzione bloccante
      sendMessage(JSON.stringify({ type: "command", text: "/quit_and_save" }));
      toast.info(t("index.toast_saving_memories"));
    } else {
      // Se l'utente non vuole salvare, spegne immediatamente
      sendMessage(JSON.stringify({ type: "command", text: "/force_quit" }));
    }
  };

  const handleConfirmQuitResponse = (shouldQuit: boolean) => {
    setConfirmQuitDialogOpen(false);
    if (shouldQuit) {
      sendMessage(JSON.stringify({ type: "command", text: "/force_quit" }));
      toast.info(t("index.toast_shutting_down"));
    }
  };

  // --- LOGICA FACTORY RESET ---
  const handleFactoryReset = async () => {
    setIsResetting(true);
    const serverUrl = getServerUrl();
    const headers = { ...getHeaders(), 'Content-Type': 'application/json' };

    try {
        const response = await fetch(`${serverUrl}/api/factory-reset`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ total_wipe: isTotalWipe })
        });

        if (!response.ok) throw new Error(t("settings_dialog.purge.err_backend_reset"));

        // NON cancelliamo il localStorage e NON ricarichiamo la pagina qui.
        // Aspettiamo che il backend generi l'ultimo messaggio e ce lo invii via WebSocket.
        // Il WebSocket sbloccherà lo spinner (setIsResetting(false)) e aprirà il dialogo finale.

    } catch (error: any) {
        toast.error(t("index.err_factory_reset_failed"), { description: error.message });
        setIsResetting(false);
    }
  };

  const openCharManager = (type: "PG" | "PNG" | "AVATAR") => {
    setCharManagerType(type);
    setCharManagerOpen(true);
  };

  const handleAddChar = () => {
    setEditingCharId(undefined);
    setCharEditorOpen(true);
    setCharManagerOpen(false);
  };

  const handleEditChar = (characterId: string) => {
    setEditingCharId(characterId);
    setCharEditorOpen(true);
    setCharManagerOpen(false);
  };

  const handleDeleteChar = (characterId: string) => {
    const characterName = t("character_manager.crud.npcs");
    toast.message(`${t("proactive_memory.delete_confirm", { name: characterName })}?`, {
      action: { label: t("character_manager.crud.remove_scene"), onClick: async () => {
        try {
          const response = await fetch(`${getServerUrl()}/api/characters/${characterId}/archive`, {
            method: 'POST',
            headers: { ...getHeaders(), 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ type: charManagerType }),
          });
          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || t("index.err_archiving_failed"));
          }
          toast.success(t("index.toast_char_archived", { name: characterName }));
          setCharManagerOpen(false);
        } catch (error: any) {
          toast.error(t("index.err_archiving_failed"), { description: error.message });
        }
      }},
      cancel: { label: "No", onClick: () => {} },
    });
  };

  const handleSaveChar = async (characterData: any, imageFile: File | null) => {
    if (!serverConfig) return;
    const formData = new FormData();
    formData.append("char_type", charManagerType);
    formData.append("character_data", JSON.stringify(characterData));
    formData.append("lang", userProfile?.preferredLanguage || "it");
    if (imageFile) formData.append("avatar_file", imageFile);
    try {
      const response = await fetch(`${getServerUrl()}/api/characters`, { 
          method: 'POST', 
          body: formData,
          headers: getHeaders()
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || t("index.err_save_failed"));
      }
      toast.success(t("index.toast_char_saved"));
      setCharEditorOpen(false);
    } catch (error: any) {
      toast.error(t("index.err_save_failed"), { description: error.message });
    }
  };

  // ---[NUOVO] HANDLER CLICK SU MINIATURA AVATAR ---
  const handleAvatarClick = (senderName: string) => {
    if (!senderName) return;

    const userNameLower = (userProfile?.name || "").toLowerCase();
    const senderLower = senderName.toLowerCase();

    // ---[FIX CRITICO] ROUTING DINAMICO AVATAR UTENTE ---
    if (senderLower === userNameLower || senderLower === "user" || senderLower === "creatore") {
        if (isGdrMode) {
            // Se siamo in GDR, apri la scheda RPG del giocatore
            setCharManagerType("PG");
            setEditingCharId(userProfile?.name || "Creatore");
            setCharEditorOpen(true);
        } else {
            // Se siamo in Standard Mode, apri il Profilo Globale (evita errore 400 dal backend)
            setProfileOpen(true);
        }
        return; // Esce subito, il routing è completato
    }

    // --- ROUTING PNG / AVATAR ---
    let type: "PG" | "PNG" | "AVATAR" = "PNG";
    let charId = senderName.replace(/ /g, '_'); // Approssimazione standard dell'ID

    // [FIX CRITICO 404] Riconoscimento robusto dell'Avatar principale anche per messaggi di sistema
    if (senderLower === "ai" || senderLower === "avatar" || senderLower === "system" || senderLower === "dungeon master" || senderLower === activeAvatar.toLowerCase() || allAvatarData[senderLower]) {
        type = "AVATAR";
        // Usa il nome originale corretto dalla mappa, o fai fallback sull'avatar attivo
        charId = allAvatarData[senderLower] ? allAvatarData[senderLower].original_name : activeAvatar;
    }

    setCharManagerType(type);
    setEditingCharId(charId);
    setCharEditorOpen(true);
  };

  // handleOpenExportDialog rimosso - non più necessario

  const handleExportPackage = async (type: 'pure' | 'world', avatars: string[], lore?: string) => {
    if (!isConnected) { toast.warning(t("index.warn_not_connected")); return; }
    
    const formData = new FormData();
    formData.append('export_type', type);
    formData.append('avatar_names', avatars.join(','));
    if (lore) formData.append('lore_name', lore);
    
    try {
      const response = await fetch(`${getServerUrl()}/api/export`, { 
          method: 'POST', 
          body: formData,
          headers: getHeaders()
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || t("index.err_export_failed"));
      }
      toast.success(t("index.toast_export_started"));
    } catch (error: any) {
      toast.error(t("index.err_export_failed"), { description: error.message });
    }
  };

  const handleTriggerImport = () => {
    if (!isConnected) { toast.warning("Not Connected"); return; }
    fileInputRef.current?.click();
  };

  const handleFileSelectedForImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setImportFile(file);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await fetch(`${getServerUrl()}/api/import/check`, { 
          method: 'POST', 
          body: formData,
          headers: getHeaders()
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || t("index.err_check_file"));
      if (result.conflicts && result.conflicts.length > 0) {
        setImportConflicts(result.conflicts);
        setConflictDialogOpen(true);
      } else {
        await executeImport(file, false);
      }
    } catch (error: any) {
      toast.error(t("index.err_import_check_failed"), { description: error.message });
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const executeImport = async (file: File, overwrite: boolean) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('overwrite', String(overwrite));
    try {
      const response = await fetch(`${getServerUrl()}/api/import/execute`, { 
          method: 'POST', 
          body: formData,
          headers: getHeaders()
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail?.message || result.detail || t("index.err_import_failed"));
      toast.success(t("index.toast_import_successful"), { description: result.message });
    } catch (error: any) {
      toast.error(t("index.err_import_failed"), { description: error.message });
    } finally {
      setConflictDialogOpen(false);
      setImportFile(null);
      setImportConflicts(Array(0));
    }
  };

  // --- NUOVA FUNZIONE: FETCH PROMPTS PER GDR SPECIFICO (v29.43) ---
  const fetchPromptsForRpg = async (rpgName: string) => {
      if (!serverConfig) return;
      const baseUrl = getServerUrl();
      const headers = getHeaders();
      const lang = userProfile?.preferredLanguage || "it";
      
      console.log(t("index.log_fetching_prompts", { name: rpgName }));
      
      try {
          let promptsUrl = `${baseUrl}/api/prompts?lang=${lang}`;
          if (rpgName) promptsUrl += `&rpg_name=${rpgName}`;
          
          const promptsRes = await fetch(promptsUrl, { headers });
          if (!promptsRes.ok) throw new Error(t("index.err_fetch_prompts"));
          
          const promptsData = await promptsRes.json();
          console.log(t("index.log_prompts_received"), promptsData);
          setPromptsConfig(promptsData);
      } catch (error) {
          console.error(t("index.err_fetching_prompts"), error);
          toast.error(t("index.err_load_prompts_rpg"));
      }
  };

  // --- [NUOVO v38.0] FETCH JAILBREAKS & KNOWLEDGE BASE ---
  const fetchMusaGenesiData = async () => {
      if (!serverConfig) return;
      const baseUrl = getServerUrl();
      const headers = getHeaders();
      
      try {
          // Fetch Jailbreaks
          const jbRes = await fetch(`${baseUrl}/api/settings/jailbreaks`, { headers });
          if (jbRes.ok) {
              const jbData: JailbreakItem[] = await jbRes.json();
              setJailbreaks(jbData);
              const active = jbData.find(j => j.is_active);
              if (active) setActiveJailbreakContent(active.content);
          }
          
          // Fetch Knowledge Base
          const kbRes = await fetch(`${baseUrl}/api/settings/knowledge-base`, { headers });
          if (kbRes.ok) {
              const kbData: KnowledgeBaseData = await kbRes.json();
              setKnowledgeBase(kbData);
          }
      } catch (error) {
          console.error(t("index.err_fetching_musa_genesi"), error);
      }
  };

  const handleOpenModelsDialog = async () => {
    if (!isConnected) { toast.warning(t("index.warn_not_connected")); return; }
    try {
      const baseUrl = getServerUrl();
      const headers = getHeaders();
      const lang = userProfile?.preferredLanguage || "it";
      
      console.log(t("index.log_opening_models_dialog"));
      
      // 1. Fetch Models & GDR Worlds
      const [modelsRes, gdrWorldsRes, enrichedRes] = await Promise.all([
        fetch(`${baseUrl}/api/models`, { headers }),
        fetch(`${baseUrl}/api/gdr-worlds`, { headers }),
        fetch(`${baseUrl}/api/gdr-worlds/enriched?lang=${lang}`, { headers }) //[NUOVO]
      ]);
      
      if (!modelsRes.ok) throw new Error(t("index.err_fetch_model_list"));
      const modelsData = await modelsRes.json();
      setModelsState(modelsData.models);
      setAnimaParams(modelsData.parameters);
      
      setSelectedBaseModel(modelsData.models.active_base_model || 'None');
      setSelectedMmprojModel(modelsData.models.active_mmproj_model || 'None');
      setSelectedLoraModel(modelsData.models.active_lora_model || 'None');
      
      // Inizializza i nuovi stati se non esistono
      setModelsState(prev => {
          if (!prev) return prev;
          return {
              ...prev,
              active_draft_model: modelsData.models.active_draft_model || 'None',
              draft_enabled: modelsData.models.draft_enabled || false,
              active_semantic_model: modelsData.models.active_semantic_model || 'None',
              semantic_router_enabled: modelsData.models.semantic_router_enabled || false,
              semantic_on_cpu: modelsData.models.semantic_on_cpu ?? true,
              is_large_model: modelsData.models.is_large_model || false // [FIX CRITICO] Mappatura flag Gatekeeper
          };
      });

      // --- [FIX CRITICO] PERSISTENZA VISIVA VRAM ---
      const savedVram = localStorage.getItem("airis_vram_choice");
      if (savedVram && VRAM_MAP[savedVram] !== undefined) {
          setSelectedVram(savedVram);
      } else {
          // Fallback reverse mapping
          let matchedVram = "12";
          for (const [gb, layers] of Object.entries(VRAM_MAP)) {
              if (layers === modelsData.parameters.n_gpu_layers) {
                  matchedVram = gb;
                  break;
              }
          }
          setSelectedVram(matchedVram);
      }
      
      if (!gdrWorldsRes.ok) throw new Error(t("index.err_fetch_gdr_worlds"));
      const gdrData = await gdrWorldsRes.json();
      setGdrWorlds(gdrData);
      console.log(t("index.log_gdr_worlds"), gdrData);
      
      // --- [NUOVO] SET PREFERENCES STATE ---
      if (enrichedRes.ok) {
          const enrichedData = await enrichedRes.json();
          setEnrichedRpgWorlds(enrichedData);
      }
      setSelectedPrefAvatar(serverConfig?.currentAvatar || "gemma");
      // Se siamo in GDR, cerchiamo di capire quale. Altrimenti STANDARD.
      // Poiché il frontend non ha una variabile esplicita per il nome del GDR attivo,
      // usiamo isGdrPathSet e il primo della lista come approssimazione, o STANDARD.
      setSelectedPrefRpg(isGdrMode && isGdrPathSet && gdrData.length > 0 ? gdrData[0] : "STANDARD");
      
      let targetRpg = "";
      if (gdrData.length > 0) {
        targetRpg = gdrData[0];
        setSelectedGdrForEditing(targetRpg);
        console.log(t("index.log_auto_selected_rpg", { name: targetRpg }));
      }
      
      // 2. Fetch Prompts (specifying RPG if available)
      await fetchPromptsForRpg(targetRpg);
      
      // 3. Fetch Musa & Genesi Data
      await fetchMusaGenesiData();

      // 4.[NUOVO FASE 16] Fetch Cognitive Modules & Mindsets
      await fetchCognitiveData();

      // 5. [NUOVO v20.0] Fetch Panopticon Data
      const panopticonRes = await fetch(`${baseUrl}/api/settings/panopticon`, { headers });
      if (panopticonRes.ok) {
          const panopticonData = await panopticonRes.json();
          setPanopticonConfig(panopticonData);
      }
      
      // --- FETCH AVATAR JSON (Mantenuto per altre logiche se necessarie) ---
      try {
          const avatarRes = await fetch(`${baseUrl}/api/characters/${serverConfig?.currentAvatar || 'gemma'}?char_type=AVATAR`, { headers });
          if (avatarRes.ok) {
              const avatarData = await avatarRes.json();
              setFullAvatarJson(avatarData.jsonData);
          }
      } catch (e) {
          console.error(t("index.err_fetch_avatar_specialist"), e);
      }

      setModelsDialogOpen(true);
    } catch (error: any) {
      console.error(t("index.err_opening_dialog"), error);
      toast.error(t("index.err_load_config"), { description: error.message });
    }
  };

  // --- [NUOVO FASE 16] HELPER FETCH COGNITIVE DATA ---
  const fetchCognitiveData = async () => {
      if (!serverConfig) return;
      const baseUrl = getServerUrl();
      const headers = getHeaders();
      try {
          const [modRes, mindRes] = await Promise.all([
              fetch(`${baseUrl}/api/cognitive/modules`, { headers }),
              fetch(`${baseUrl}/api/cognitive/mindsets`, { headers })
          ]);
          if (modRes.ok) setCognitiveModules(await modRes.json());
          if (mindRes.ok) setCognitiveMindsets(await mindRes.json());
      } catch (e) {
          console.error(t("index.err_fetching_cognitive"), e);
      }
  };

  // --- NUOVO: TRIGGER FETCH AL CAMBIO GDR (v29.43) ---
  const handleGdrSelectionChange = (newValue: string) => {
      setSelectedGdrForEditing(newValue);
      fetchPromptsForRpg(newValue);
      // --- [NUOVO v51.1] AGGIORNA STATO DISPONIBILITÀ GDR ---
      setIsGdrPathSet(true);
  };

  const handleApplyModelsAndParams = async () => {
    setIsApplyingModels(true);
    toast.info(t("index.toast_applying_config")); // Rimosso l'avviso di riavvio
    try {
      // --- FIX PERSISTENZA: Salva anche la Knowledge Base e il Panopticon prima del riavvio ---
      await handleSaveKnowledgeBase(knowledgeBase);

      const baseUrl = getServerUrl();
      const headers = { ...getHeaders(), 'Content-Type': 'application/json' };

      await fetch(`${baseUrl}/api/settings/panopticon`, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(panopticonConfig)
      });

      // [FIX CRITICO] Ripristinato hot_swap=true. Le modifiche a Temp/TopP si applicano istantaneamente.
      // Le modifiche a VRAM/Context richiederanno un riavvio manuale da parte dell'utente.
      const response = await fetch(`${baseUrl}/api/models/apply?hot_swap=true`, {
        method: 'POST',
        headers: { ...getHeaders(), 'Content-Type': 'application/json' }, 
        body: JSON.stringify({
          models: { 
              base_model: selectedBaseModel, 
              mmproj_model: selectedMmprojModel, 
              lora_model: selectedLoraModel,
              active_draft_model: modelsState?.active_draft_model,
              draft_enabled: modelsState?.draft_enabled,
              active_semantic_model: modelsState?.active_semantic_model,
              semantic_router_enabled: modelsState?.semantic_router_enabled,
              semantic_on_cpu: modelsState?.semantic_on_cpu
          },
          parameters: animaParams
        }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || t("index.err_apply_config"));
      }

      setModelsDialogOpen(false);
    } catch (error: any) {
      toast.error(t("index.err_apply_config_desc"), { description: error.message });
    } finally {
      setIsApplyingModels(false);
    }
  };
  
  const handleApplyPreferences = () => {
      if (!selectedPrefAvatar) {
          toast.error(t("models_dialog.err_select_avatar", { defaultValue: "Seleziona un'Anima." }));
          return;
      }
      
      sendMessage(JSON.stringify({
          type: "command",
          text: `/hotswap_context avatar='${selectedPrefAvatar}' rpg='${selectedPrefRpg}'`
      }));
      
      // Forza l'aggiornamento visivo immediato
      setActiveAvatar(selectedPrefAvatar);
      const newAvatarData = allAvatarData[selectedPrefAvatar.toLowerCase()];
      if (newAvatarData && newAvatarData.ai_base_avatar_url) {
          setAiAvatarUrl(joinUrl(getServerUrl(), newAvatarData.ai_base_avatar_url));
      }
      
      // Aggiorna la config locale per persistenza
      if (serverConfig) {
          const newConfig = { ...serverConfig, currentAvatar: selectedPrefAvatar };
          setServerConfig(newConfig);
          saveServerConfig(newConfig);
      }
      
      setModelsDialogOpen(false);

      // [FIX BUG 01] Forza un hard reload per pulire la cache dei video su mobile
      setTimeout(() => {
          window.location.href = window.location.pathname + "?t=" + Date.now();
      }, 500);
  };

  // --- HELPER PER SPACCHETTAMENTO INTELLIGENTE ---
  const getSystemPrompts = () => {
      if (!promptsConfig?.system) return {};
      let data = promptsConfig.system;
      // Se il caricamento YAML ha messo tutto sotto una chiave 'system', sbucciala
      if (data.system && typeof data.system === 'object' && !Array.isArray(data.system)) data = data.system;
      if (data.System && typeof data.System === 'object' && !Array.isArray(data.System)) data = data.System;

      // --- NUOVO: APPIATTIMENTO RICORSIVO PER CONNETTORI ---
      const flattened: Record<string, any> = {};
      Object.entries(data).forEach(([key, value]) => {
          if (key === 'connettori' && typeof value === 'object' && value !== null) {
              // Porta i prompt dei connettori al livello principale per la visualizzazione
              Object.entries(value).forEach(([cKey, cValue]) => {
                  flattened[cKey] = cValue;
              });
          } else {
              flattened[key] = value;
          }
      });
      return flattened;
  };

  // --- FIX v29.44: LOGICA ROBUSTA PER GDR PROMPTS (DEEP UNWRAP) ---
  const getRpgPrompts = () => {
      if (!promptsConfig?.rpg) return {};
      let data = promptsConfig.rpg;
      
      // Gestione annidamento 'rpg' (comune in YAML)
      // Scendiamo ricorsivamente finché troviamo la chiave 'rpg'
      while (data && typeof data === 'object' && !Array.isArray(data) && (data.rpg || data.RPG)) {
          data = data.rpg || data.RPG;
      }
      
      return data;
  };

  const handlePromptChange = (scope: 'system' | 'rpg', key: string, value: string | object) => {
    setPromptsConfig((prev: any) => {
        const newData = JSON.parse(JSON.stringify(prev)); // Deep clone per sicurezza
        if (scope === 'rpg') {
            // --- FIX v29.42: Gestione annidamento RPG in scrittura ---
            if (newData.rpg && newData.rpg.rpg) {
                newData.rpg.rpg[key] = value;
            } else {
                if (!newData.rpg) newData.rpg = {};
                newData.rpg[key] = value;
            }
        } else {
            let content = newData.system.system ? newData.system.system : newData.system;
            // Se la chiave appartiene ai connettori (finisce con _prompt e non è principale), aggiorna lì
            if (content.connettori && key in content.connettori) {
                content.connettori[key] = value;
            } else {
                content[key] = value;
            }
        }
        return newData;
    });
  };

  const handleAddPrompt = (scope: 'system' | 'rpg') => {
      if (!newPromptKey.trim()) {
          toast.error(t("index.err_key_name_required"));
          return;
      }
      
      setPromptsConfig((prev: any) => {
          const newData = JSON.parse(JSON.stringify(prev));
          if (scope === 'rpg') {
              // --- FIX v29.42: Gestione annidamento RPG in aggiunta ---
              if (newData.rpg && newData.rpg.rpg) {
                  newData.rpg.rpg[newPromptKey.trim()] = newPromptValue;
              } else {
                  if (!newData.rpg) newData.rpg = {};
                  newData.rpg[newPromptKey.trim()] = newPromptValue;
              }
          } else {
              let target = newData.system.system ? newData.system.system : newData.system;
              target[newPromptKey.trim()] = newPromptValue;
          }
          return newData;
      });
      
      setNewPromptKey("");
      setNewPromptValue("");
      toast.success(t("index.toast_added_prompt", { scope, key: newPromptKey }));
  };

  const handleDeletePrompt = (scope: 'system' | 'rpg', key: string) => {
      setPromptsConfig((prev: any) => {
          const newData = JSON.parse(JSON.stringify(prev));
          if (scope === 'rpg') {
              // --- FIX v29.42: Gestione annidamento RPG in cancellazione ---
              if (newData.rpg && newData.rpg.rpg) {
                  delete newData.rpg.rpg[key];
              } else {
                  delete newData.rpg[key];
              }
          } else {
              let target = newData.system.system ? newData.system.system : newData.system;
              if (target.connettori && key in target.connettori) {
                  delete target.connettori[key];
              } else {
                  delete target[key];
              }
          }
          return newData;
      });
      toast.success(t("index.toast_deleted_prompt", { key }));
  };

  const handleSavePromptsLocal = async (scope: 'system' | 'rpg') => {
    setIsSavingPrompts(true);
    try {
      const lang = userProfile?.preferredLanguage || "it";
      
      // --- FIX: Sbuccia il livello extra se presente prima di salvare ---
      let dataToSave = promptsConfig?.[scope];
      if (dataToSave && dataToSave[scope]) {
          dataToSave = dataToSave[scope];
      }

      const response = await fetch(`${getServerUrl()}/api/prompts`, {
        method: 'POST',
        headers: { ...getHeaders(), 'Content-Type': 'application/json' }, 
        body: JSON.stringify({
            scope: scope,
            lang: lang,
            data: dataToSave
        }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || t("index.err_save_prompts"));
      }
      toast.success(t("index.toast_prompts_saved", { scope: scope.toUpperCase() }));
    } catch (error: any) {
      toast.error(t("index.err_save_prompts_desc"), { description: error.message });
    } finally {
      setIsSavingPrompts(false);
    }
  };

  const handleSaveWorldFile = async (subdir: string, filename: string) => {
    if (!gdrWorldContent) return;
    setIsSavingWorldFile(true);
    try {
      const content = gdrWorldContent[subdir][filename];
      const lang = userProfile?.preferredLanguage || "it";
      if (filename.endsWith('.json')) { JSON.parse(content); }
      const response = await fetch(`${getServerUrl()}/api/gdr-world-file`, {
        method: 'POST',
        headers: { ...getHeaders(), 'Content-Type': 'application/json' }, 
        body: JSON.stringify({
          world_name: selectedGdrForEditing,
          lang: lang,
          relative_path: `${subdir}/${filename}`,
          content: content
        }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || t("index.err_save_file", { filename }));
      }
      toast.success(t("index.toast_file_saved", { filename }));
    } catch (error: any) {
      toast.error(t("index.err_save_file_desc", { filename }), { description: error.message });
    } finally {
      setIsSavingWorldFile(false);
    }
  };

  const handleVramChange = (value: string) => {
    setSelectedVram(value);
    localStorage.setItem("airis_vram_choice", value);
    if (animaParams) {
      setAnimaParams({ ...animaParams, n_gpu_layers: VRAM_MAP[value] || 0 });
    }
  };

  // --- [NUOVO FASE 16] HANDLERS COGNITIVE MODULES & MINDSETS ---
  const handleToggleModuleState = async (moduleId: string, currentState: boolean, contextType: 'avatar' | 'gdr') => {
      if (!cognitiveMindsets || !serverConfig) return;
      
      const activeMindsetId = contextType === 'avatar' ? cognitiveMindsets.active_avatar_mindset : cognitiveMindsets.active_gdr_mindset;
      const newMindsets = JSON.parse(JSON.stringify(cognitiveMindsets)); // Deep clone
      
      const profile = newMindsets.profiles.find((p: MindsetProfile) => p.id === activeMindsetId);
      if (!profile) return;

      // Toggle state in the active mindset
      profile.module_states[moduleId] = !currentState;
      setCognitiveMindsets(newMindsets);

      try {
          await fetch(`${getServerUrl()}/api/cognitive/mindsets`, {
              method: 'POST',
              headers: { ...getHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify(newMindsets)
          });
      } catch (e) {
          toast.error(t("index.err_toggle_module"));
      }
  };

  const handleDeleteModule = async (moduleId: string) => {
      if (!confirm(t("index.confirm_delete_module"))) return;
      try {
          const res = await fetch(`${getServerUrl()}/api/cognitive/modules/${moduleId}`, {
              method: 'DELETE',
              headers: getHeaders()
          });
          if (res.ok) {
              toast.success(t("index.toast_module_deleted"));
              fetchCognitiveData();
          } else {
              throw new Error(t("index.err_delete_failed"));
          }
      } catch (e) {
          toast.error(t("index.err_delete_module"));
      }
  };

  const handleMindsetChange = async (contextType: 'avatar' | 'gdr', newMindsetId: string) => {
      if (!cognitiveMindsets || !serverConfig) return;
      const newMindsets = { ...cognitiveMindsets };
      if (contextType === 'avatar') newMindsets.active_avatar_mindset = newMindsetId;
      else newMindsets.active_gdr_mindset = newMindsetId;
      
      setCognitiveMindsets(newMindsets);
      try {
          await fetch(`${getServerUrl()}/api/cognitive/mindsets`, {
              method: 'POST',
              headers: { ...getHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify(newMindsets)
          });
          toast.success(t("index.toast_mindset_changed", { id: newMindsetId }));
      } catch (e) {
          toast.error(t("index.err_change_mindset"));
      }
  };

  const handleCreateMindset = async () => {
      const name = window.prompt(t("index.prompt_new_mindset"));
      if (!name || !cognitiveMindsets) return;
      
      const id = name.toLowerCase().replace(/[^a-z0-9]+/g, '_') + '_' + Date.now();
      const newProfile: MindsetProfile = { id, name, context: "all", module_states: {} };
      
      const newMindsets = { ...cognitiveMindsets, profiles:[...cognitiveMindsets.profiles, newProfile] };
      setCognitiveMindsets(newMindsets);
      
      try {
          await fetch(`${getServerUrl()}/api/cognitive/mindsets`, {
              method: 'POST',
              headers: { ...getHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify(newMindsets)
          });
          toast.success(t("index.toast_mindset_created"));
      } catch (e) {
          toast.error(t("index.err_create_mindset"));
      }
  };

  const handleDeleteMindset = async (mindsetId: string) => {
      if (mindsetId === 'default') {
          toast.error(t("index.err_delete_default_mindset"));
          return;
      }
      if (!confirm(t("index.confirm_delete_mindset"))) return;
      if (!cognitiveMindsets) return;

      const newMindsets = { ...cognitiveMindsets };
      newMindsets.profiles = newMindsets.profiles.filter(p => p.id !== mindsetId);
      
      // Fallback if active is deleted
      if (newMindsets.active_avatar_mindset === mindsetId) newMindsets.active_avatar_mindset = 'default';
      if (newMindsets.active_gdr_mindset === mindsetId) newMindsets.active_gdr_mindset = 'default';

      setCognitiveMindsets(newMindsets);
      try {
          await fetch(`${getServerUrl()}/api/cognitive/mindsets`, {
              method: 'POST',
              headers: { ...getHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify(newMindsets)
          });
          toast.success(t("index.toast_mindset_deleted"));
      } catch (e) {
          toast.error(t("index.err_delete_mindset"));
      }
  };

  // --- HELPER RENDER DASHBOARD COGNITIVA ---
  const renderCognitiveDashboard = (contextType: 'avatar' | 'gdr') => {
      if (!cognitiveMindsets) return <div className="p-8 text-center"><Loader2 className="animate-spin mx-auto" /></div>;

      const activeMindsetId = contextType === 'avatar' ? cognitiveMindsets.active_avatar_mindset : cognitiveMindsets.active_gdr_mindset;
      const activeProfile = cognitiveMindsets.profiles.find(p => p.id === activeMindsetId);

      // Filtra i moduli per contesto
      const filteredModules = cognitiveModules.filter(m => 
          m.context === contextType || m.context === 'always'
      ).sort((a, b) => a.priority - b.priority);

      // --- [NUOVO] GATEKEEPER COGNITIVO (MODULI BLOCCATI) ---
      const RESTRICTED_MODULES = ["negative_rules", "avatar_talking", "direttiva_standard"];

      // [FIX BUG 04] Intercettazione moduli NSFW
      const nsfwModules = ["sex_base", "sex_fluids", "sex_dirty_talk", "sex_futa", "sex_autofellatio"];
      const handleToggleRequest = (modId: string, currentState: boolean) => {
          if (!currentState && nsfwModules.includes(modId)) {
              setPendingNsfwToggle({ modId, currentState, contextType });
              setIsNsfwWarningOpen(true);
          } else {
              handleToggleModuleState(modId, currentState, contextType);
          }
      };

      return (
          <div className="flex flex-col space-y-4 pb-8"> {/* [FIX] Rimosso h-full, aggiunto padding bottom */}
              {/* HEADER: MINDSET SELECTOR */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-muted/10 p-4 rounded-lg border border-border/50 shrink-0">
                  <div className="flex items-center gap-3 w-full sm:w-auto">
                      <Brain className="w-6 h-6 text-primary shrink-0" />
                      <div className="flex-1">
                          <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">{t("models_dialog.active_mindset")}</Label>
                          <div className="flex items-center gap-2 mt-1">
                              <Select value={activeMindsetId} onValueChange={(v) => handleMindsetChange(contextType, v)}>
                                  <SelectTrigger className="w-[200px] h-8 text-xs font-bold">
                                      <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                      {cognitiveMindsets.profiles.map(p => (
                                          <SelectItem key={p.id} value={p.id}>{parseDynamicT(p.name)}</SelectItem>
                                      ))}
                                  </SelectContent>
                              </Select>
                              {activeMindsetId !== 'default' && (
                                  <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => handleDeleteMindset(activeMindsetId)}>
                                      <Trash2 className="w-4 h-4" />
                                  </Button>
                              )}
                          </div>
                      </div>
                  </div>
                  <div className="flex gap-2 w-full sm:w-auto">
                      <Button variant="outline" size="sm" onClick={handleCreateMindset} className="flex-1 sm:flex-none h-8 text-xs">
                          <Plus className="w-3 h-3 mr-1" /> {t("models_dialog.btn_new_mindset")}
                      </Button>
                      <Button size="sm" onClick={() => { setModuleToEdit(null); setIsModuleDialogOpen(true); }} className="flex-1 sm:flex-none h-8 text-xs bg-primary hover:bg-primary/90">
                          <PlusCircle className="w-3 h-3 mr-1" /> {t("models_dialog.btn_new_module")}
                      </Button>
                  </div>
              </div>

              {/* LISTA MODULI (LAYOUT FLUIDO) */}
              <div className="border rounded-lg bg-muted/5"> {/* [FIX] Rimosso flex-1 relative min-h-0 */}
                  <div className="p-4 space-y-3"> {/* [FIX] Rimosso absolute inset-0 overflow-y-scroll */}
                      {filteredModules.map(mod => {
                          // --- [NUOVO] GATEKEEPER COGNITIVO ---
                          const isRestrictedByModel = modelsState?.is_large_model && RESTRICTED_MODULES.includes(mod.id);
                          
                          // Lo stato effettivo dipende dal Mindset attivo. Se non definito nel mindset, usa il default del modulo.
                          // Se è bloccato dal modello, forziamo a false visivamente.
                          const isActive = isRestrictedByModel ? false : (activeProfile?.module_states[mod.id] ?? mod.is_active);
                          
                          return (
                              <div key={mod.id} className={cn(
                                  "flex flex-col sm:flex-row items-start sm:items-center gap-4 p-3 rounded-lg border transition-all",
                                  isActive ? "bg-card border-primary/30 shadow-sm" : "bg-muted/30 border-border/50 opacity-60 grayscale-[0.5]"
                              )}>
                                  <div className="flex items-center gap-3 flex-1 min-w-0 w-full">
                                      <GripVertical className="w-4 h-4 text-muted-foreground cursor-grab shrink-0 hidden sm:block" />
                                      <div className="flex-1 min-w-0">
                                          <div className="flex items-center gap-2 mb-1">
                                              <span className="font-bold text-sm truncate">{parseDynamicT(mod.name)}</span>
                                              <span className="text-[9px] px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground uppercase tracking-wider shrink-0">
                                                  {mod.category}
                                              </span>
                                              {mod.activation_condition && (
                                                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-pink-500/20 text-pink-400 flex items-center gap-1 shrink-0" title="Bio-Cognitive Trigger">
                                                      <Activity className="w-3 h-3" /> {t("cognitive_module.auto")}
                                                  </span>
                                              )}
                                              {isRestrictedByModel && (
                                                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 flex items-center gap-1 shrink-0" title={t("models_dialog.module_locked_large_model")}>
                                                      <Shield className="w-3 h-3" /> AUTO-OFF
                                                  </span>
                                              )}
                                          </div>
                                          <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                                              <span className="font-mono">ID: {mod.id}</span>
                                              <span>Priority: {mod.priority}</span>
                                              {mod.tags.length > 0 && (
                                                  <span className="flex items-center gap-1 truncate">
                                                      <Tags className="w-3 h-3" /> {mod.tags.join(', ')}
                                                  </span>
                                              )}
                                          </div>
                                      </div>
                                  </div>
                                  
                                  <div className="flex items-center justify-between sm:justify-end gap-4 w-full sm:w-auto mt-2 sm:mt-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-border/50">
                                      <div className="flex items-center gap-2">
                                          <Label className="text-xs font-medium cursor-pointer" onClick={() => { if (!isRestrictedByModel) handleToggleRequest(mod.id, isActive); }}>
                                              {isActive ? "ON" : "OFF"}
                                          </Label>
                                          <Switch 
                                              checked={isActive} 
                                              disabled={isRestrictedByModel}
                                              onCheckedChange={() => handleToggleRequest(mod.id, isActive)} 
                                          />
                                      </div>
                                      <div className="flex items-center gap-1">
                                          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-primary" onClick={() => { setModuleToEdit(mod); setIsModuleDialogOpen(true); }}>
                                              <Edit className="w-4 h-4" />
                                          </Button>
                                          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" onClick={() => handleDeleteModule(mod.id)}>
                                              <Trash2 className="w-4 h-4" />
                                          </Button>
                                      </div>
                                  </div>
                              </div>
                          );
                      })}
                      {filteredModules.length === 0 && (
                          <div className="text-center py-10 text-muted-foreground">
                              <BrainCircuit className="w-10 h-10 mx-auto mb-3 opacity-20" />
                              <p>{t("models_dialog.no_modules")}</p>
                          </div>
                      )}
                  </div>
              </div>
          </div>
      );
  };

  const handleNewSession = () => {
    if (!isConnected) return;
    localStorage.removeItem("airis_last_session_id");
    localStorage.removeItem("airis_has_greeted"); // Permette un nuovo saluto
    setCurrentSessionId(null);
    
    sendMessage(JSON.stringify({ type: "command", text: "/new_session" }));
    setMessages(Array(0));
    toast.info(t("settings_dialog.toast_new_session"));
  };

  const handleLoadSession = (sessionId: string) => {
    if (!isConnected) return;
    localStorage.setItem("airis_last_session_id", sessionId);
    setCurrentSessionId(sessionId);
    
    sendMessage(JSON.stringify({ type: "command", text: `/load_session ${sessionId}` }));
    toast.info(t("settings_dialog.toast_loading_session"));
  };

  const handleSaveSession = () => {
    if (!isConnected) return;
    sendMessage(JSON.stringify({ type: "command", text: "/save_session" }));
    toast.success(t("index.toast_session_saved"));
  };

  const handleSaveProactiveMemorySettings = async (settings: ProactiveMemorySettings) => {
    if (!serverConfig) throw new Error(t("settings_dialog.err_server_not_configured"));
    const response = await fetch(`${getServerUrl()}/api/proactive-memory/settings`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' }, 
      body: JSON.stringify(settings),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || t("settings_dialog.err_save_settings"));
    }
  };

  const handleSaveReminder = async (data: ReminderData) => {
    if (!isConnected) {
      toast.error(t("settings_dialog.err_save_reminder_not_connected"));
      throw new Error("Not connected");
    }
    const command = `[USA_STRUMENTO: create_event_and_reminder(event_name='${data.eventName}', event_timestamp_iso='${data.eventDate.toISOString()}', notes='${data.notes}', reminder_timestamp_iso='${data.reminderDate.toISOString()}', recurrence_rule='${data.recurrenceRule}')]`;
    handleSendMessage(command);
  };

  const handleAutoGenerateDef = async (scriptCode: string, prompt: string): Promise<string> => {
      if (!serverConfig) throw new Error(t("settings_dialog.err_server_not_configured"));
      
      return new Promise((resolve, reject) => {
          pendingDefGenResolver.current = resolve;
          const serverUrl = getServerUrl();
          const headers = { ...getHeaders(), 'Content-Type': 'application/json' };

          fetch(`${serverUrl}/api/custom-connectors/generate-def`, {
              method: 'POST',
              headers: headers,
              body: JSON.stringify({ script_code: scriptCode, prompt: prompt }),
          }).catch(err => {
              pendingDefGenResolver.current = null;
              reject(err);
          });
      });
  };

  // ---[NUOVO v121.0] HANDLER GENERAZIONE SKILL ---
  const handleAutoGenerateSkill = async (name: string, description: string): Promise<string> => {
      if (!serverConfig) throw new Error(t("settings_dialog.err_server_not_configured"));
      
      return new Promise((resolve, reject) => {
          pendingDefGenResolver.current = resolve;
          const serverUrl = getServerUrl();
          const headers = { ...getHeaders(), 'Content-Type': 'application/json' };

          fetch(`${serverUrl}/api/skills/generate`, {
              method: 'POST',
              headers: headers,
              body: JSON.stringify({ name, description }),
          }).catch(err => {
              pendingDefGenResolver.current = null;
              reject(err);
          });
      });
  };

  const handleSaveCustomConnector = async (connectorData: CustomConnectorData) => {
    if (!serverConfig) throw new Error(t("settings_dialog.err_server_not_configured"));
    const serverUrl = getServerUrl();
    const headers = getHeaders();

    let scriptFilename = "";

    if (connectorData.scriptCode) {
        const response = await fetch(`${serverUrl}/api/custom-connectors/script`, {
            method: 'POST',
            headers: { ...headers, 'Content-Type': 'application/json' }, 
            body: JSON.stringify({
                filename: `${connectorData.name.toLowerCase().replace(/ /g, '_')}.py`,
                code: connectorData.scriptCode,
            }),
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || t("settings_dialog.custom.err_save_script"));
        }
        const result = await response.json();
        scriptFilename = result.filename;
    } else if (connectorData.scriptFile) {
        const formData = new FormData();
        formData.append("file", connectorData.scriptFile);
        const response = await fetch(`${serverUrl}/api/custom-connectors/upload`, {
            method: 'POST',
            body: formData,
            headers: getHeaders()
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || t("settings_dialog.custom.err_upload_script"));
        }
        const result = await response.json();
        scriptFilename = result.filename;
    }

    const [connectorsRes, credsRes, promptsRes] = await Promise.all([
        fetch(`${serverUrl}/api/custom-connectors`, { headers }),
        fetch(`${serverUrl}/api/credentials`, { headers }),
        fetch(`${serverUrl}/api/prompts`, { headers }),
    ]);

    if (!connectorsRes.ok) throw new Error(t("settings_dialog.custom.err_fetch_connectors"));
    if (!credsRes.ok) throw new Error(t("settings_dialog.custom.err_fetch_credentials"));
    if (!promptsRes.ok) throw new Error(t("settings_dialog.custom.err_fetch_prompts"));

    const currentConnectors = await connectorsRes.json();
    const currentCredentials = await credsRes.json();
    const currentPrompts = await promptsRes.json();

    const newConnectorName = connectorData.name;
    const newConnectorConfig = {
      ...currentConnectors,
      [newConnectorName]: {
        script_file: scriptFilename,
        dependencies: connectorData.dependencies ? connectorData.dependencies.split(',').map(d => d.trim()) : []
      }
    };
    
    const newCredentialsConfig = {
        ...currentCredentials,
        [`${newConnectorName.toLowerCase().replace(/ /g, '_')}_api`]: connectorData.fields
    };

    const fullPrompt = `${connectorData.def_structure}\n${connectorData.prompt}`;

    const newPromptsConfig = {
        ...currentPrompts,
        connettori: {
            ...currentPrompts.connettori,
            [`${newConnectorName.toLowerCase().replace(/ /g, '_')}_prompt`]: fullPrompt,
        }
    };

    await Promise.all([
        fetch(`${serverUrl}/api/custom-connectors`, {
            method: 'POST',
            headers: { ...headers, 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ connectors: newConnectorConfig }),
        }),
        fetch(`${serverUrl}/api/credentials`, {
            method: 'POST',
            headers: { ...headers, 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ credentials: newCredentialsConfig }),
        }),
        fetch(`${serverUrl}/api/prompts`, {
            method: 'POST',
            headers: { ...headers, 'Content-Type': 'application/json' }, 
            body: JSON.stringify(newPromptsConfig),
        })
    ]).then(responses => {
        for (const response of responses) {
            if (!response.ok) {
                throw new Error(t("settings_dialog.err_config_save_multiple"));
            }
        }
    });
    
    toast.success(t("settings_dialog.custom.toast_connector_created"));
  };

  // --- NUOVO: HANDLER CANCELLAZIONE FILE GALLERIA (v35.0) ---
  const handleDeleteGalleryFile = async (filename: string) => {
      if (!serverConfig) return;
      try {
          // Nota: Questo endpoint deve essere aggiunto al backend in un prossimo step
          // Per ora, il frontend è pronto a chiamarlo.
          const response = await fetch(`${getBaseUrl(serverConfig)}/api/gallery/images/${filename}`, {
              method: 'DELETE',
              headers: getHeaders()
          });
          
          if (!response.ok) throw new Error(t("settings_dialog.err_delete_failed"));
          toast.success(t("settings_dialog.toast_file_deleted"));
      } catch (e) {
          console.error(t("index.err_delete_error"), e);
          toast.error(t("settings_dialog.err_delete_file"));
      }
  };

  // --- [NUOVO v38.0] HANDLERS MUSA & GENESI ---

  const handleSaveJailbreakList = async (newList: JailbreakItem[]) => {
      if (!serverConfig) return;
      const baseUrl = getServerUrl();
      const headers = { ...getHeaders(), 'Content-Type': 'application/json' };
      
      try {
          const res = await fetch(`${baseUrl}/api/settings/jailbreaks`, {
              method: 'POST',
              headers,
              body: JSON.stringify({ jailbreaks: newList })
          });
          if (!res.ok) throw new Error(t("settings_dialog.err_save_jailbreaks"));
          setJailbreaks(newList);
          toast.success(t("settings_dialog.toast_jailbreak_updated"));
      } catch (e: any) {
          toast.error(t("settings_dialog.err_save_jailbreaks"), { description: e.message });
      }
  };

  const handleApplyJailbreak = async (id: string) => {
      if (!serverConfig) return;
      const baseUrl = getServerUrl();
      const headers = { ...getHeaders(), 'Content-Type': 'application/json' };
      
      try {
          const res = await fetch(`${baseUrl}/api/settings/jailbreaks/active`, {
              method: 'POST',
              headers,
              body: JSON.stringify({ id })
          });
          if (!res.ok) throw new Error(t("settings_dialog.err_set_active_jailbreak"));
          
          // Aggiorna stato locale
          const updatedList = jailbreaks.map(j => ({ ...j, is_active: j.id === id }));
          setJailbreaks(updatedList);
          const active = updatedList.find(j => j.is_active);
          if (active) setActiveJailbreakContent(active.content);
          setIsJailbreakDirty(false);
          
          toast.success(t("settings_dialog.toast_jailbreak_applied"), { description: t("settings_dialog.toast_freedom_header_updated") });
      } catch (e: any) {
          toast.error(t("settings_dialog.err_apply_jailbreak"), { description: e.message });
      }
  };

  const handleSaveKnowledgeBase = async (newData: KnowledgeBaseData) => {
      if (!serverConfig) return;
      const baseUrl = getServerUrl();
      const headers = { ...getHeaders(), 'Content-Type': 'application/json' };
      
      try {
          const res = await fetch(`${baseUrl}/api/settings/knowledge-base`, {
              method: 'POST',
              headers,
              body: JSON.stringify(newData)
          });
          if (!res.ok) throw new Error(t("settings_dialog.err_save_kb"));
          setKnowledgeBase(newData);
          toast.success(t("settings_dialog.toast_kb_updated"));
      } catch (e: any) {
          toast.error(t("settings_dialog.err_save_kb_desc"), { description: e.message });
      }
  };

  // --- [NUOVO v39.0] HANDLERS TEST & HEALTH ---
  const handleTestJailbreak = async () => {
      if (!serverConfig) return;
      setIsTestingJailbreak(true);
      setTestResponse("");
      
      try {
          const res = await fetch(`${getServerUrl()}/api/settings/jailbreaks/test`, {
              method: 'POST',
              headers: { ...getHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify({
                  system_prompt: activeJailbreakContent,
                  user_query: testQuery
              })
          });
          
          if (!res.ok) throw new Error(t("settings_dialog.err_test_failed"));
          const data = await res.json();
          setTestResponse(data.response);
      } catch (e: any) {
          toast.error(t("settings_dialog.err_test_error"), { description: e.message });
          setTestResponse(t("system.error", { error: e.message }));
      } finally {
          setIsTestingJailbreak(false);
      }
  };

  const handleCheckHealth = async () => {
      if (!serverConfig) return;
      try {
          const res = await fetch(`${getServerUrl()}/api/settings/knowledge-base/check-health`, {
              method: 'POST',
              headers: getHeaders()
          });
          if (res.ok) {
              toast.info(t("settings_dialog.toast_health_check"), { description: t("settings_dialog.toast_updating_statuses") });
              // Refresh dati dopo 2 secondi per vedere i risultati immediati
              setTimeout(fetchMusaGenesiData, 2000);
          }
      } catch (e) {
          console.error(t("index.err_health_check"), e);
      }
  };

  // Trigger per aprire il file dialog
  const handleTriggerKbImport = () => {
      kbFileInputRef.current?.click();
  };

  // Handler effettivo dell'upload
  const handleImportKB = async (event: React.ChangeEvent<HTMLInputElement>) => {
      if (!serverConfig || !event.target.files?.[0]) return;
      const file = event.target.files[0];
      const formData = new FormData();
      formData.append("file", file);
      
      try {
          const res = await fetch(`${getServerUrl()}/api/settings/knowledge-base/import`, {
              method: 'POST',
              headers: getHeaders(),
              body: formData
          });
          if (!res.ok) throw new Error(t("settings_dialog.err_import_failed"));
          toast.success(t("settings_dialog.toast_kb_imported"));
          fetchMusaGenesiData(); // Refresh
      } catch (e: any) {
          toast.error(t("settings_dialog.err_import_error"), { description: e.message });
      }
      // Reset input
      if (kbFileInputRef.current) kbFileInputRef.current.value = "";
  };

  const handleExportKB = async () => {
      if (!serverConfig) return;
      const url = `${getServerUrl()}/api/settings/knowledge-base/export`;
      
      try {
          const response = await fetch(url, { headers: getHeaders() });
          if (!response.ok) throw new Error(t("settings_dialog.err_export_failed"));
          
          const blob = await response.blob();
          const downloadUrl = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = downloadUrl;
          a.download = "knowledge_base.json";
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(downloadUrl);
          a.remove();
          toast.success(t("settings_dialog.toast_kb_exported"));
      } catch (e) {
          toast.error(t("settings_dialog.err_export_kb"));
      }
  };

  const handleBulkDeleteSources = () => {
      if (selectedSourceIds.length === 0) return;
      setKnowledgeBase(prev => ({
          ...prev,
          sources: prev.sources.filter(s => !selectedSourceIds.includes(s.id))
      }));
      setSelectedSourceIds(Array(0));
  };

  const handleBulkDeleteArguments = () => {
      if (selectedArgumentIds.length === 0) return;
      setKnowledgeBase(prev => ({
          ...prev,
          arguments: prev.arguments.filter(a => !selectedArgumentIds.includes(a.id))
      }));
      setSelectedArgumentIds(Array(0));
  };

  // Helper per spostare elementi array
  const moveItem = <T,>(arr: T[], index: number, direction: 'up' | 'down'): T[] => {
      const newArr = [...arr];
      if (direction === 'up' && index > 0) {
          [newArr[index], newArr[index - 1]] = [newArr[index - 1], newArr[index]];
      } else if (direction === 'down' && index < newArr.length - 1) {
          [newArr[index], newArr[index + 1]] = [newArr[index + 1], newArr[index]];
      }
      return newArr;
  };

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden relative">
      {/* --- [NUOVO FASE 5] OVERLAY SOSPENSIONE NEURALE --- */}
      {!isConnected && !welcomeWizardOpen && !settingsOpen && serverConfig && !shutdownPhase && (
          <div className="absolute inset-0 z-[100] flex flex-col items-center justify-center bg-black/90 backdrop-blur-sm transition-opacity duration-500">
              <div className="relative flex items-center justify-center mb-8">
                  <div className="absolute inset-0 border-t-2 border-primary rounded-full animate-spin w-24 h-24 opacity-50"></div>
                  <div className="absolute inset-0 border-r-2 border-primary rounded-full animate-spin w-24 h-24 opacity-30" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}></div>
                  <BrainCircuit className="w-10 h-10 text-primary animate-pulse" />
              </div>
              <h2 className="text-xl font-bold text-primary tracking-widest uppercase mb-2">{t("index.suspension_title", { defaultValue: "Sincronizzazione Neurale" })}</h2>
              <p className="text-sm text-muted-foreground text-center max-w-xs">{t("index.suspension_desc", { defaultValue: "Connessione con l'Anima interrotta. Ripristino in corso..." })}</p>
          </div>
      )}

      {/* --- [NUOVO] OVERLAY SPEGNIMENTO SISTEMA --- */}
      {shutdownPhase && (
          <div className="absolute inset-0 z-[200] flex flex-col items-center justify-center bg-black/95 backdrop-blur-md transition-opacity duration-500">
              {shutdownPhase === 'started' ? (
                  <>
                      <Loader2 className="w-16 h-16 animate-spin text-red-500 mb-6" />
                      <h2 className="text-2xl font-bold text-red-500 tracking-widest uppercase mb-4 text-center">
                          {t("index.shutdown_overlay_title", { defaultValue: "Spegnimento in corso" })}
                      </h2>
                      <p className="text-base text-red-200/80 text-center max-w-md animate-pulse">
                          {t("index.shutdown_overlay_started", { defaultValue: "Il sistema è in fase di chiusura. Per cortesia, attendi prima di chiudere questa finestra e il terminale." })}
                      </p>
                  </>
              ) : (
                  <>
                      <CheckCircle2 className="w-16 h-16 text-green-500 mb-6" />
                      <h2 className="text-2xl font-bold text-green-500 tracking-widest uppercase mb-4 text-center">
                          {t("index.shutdown_overlay_completed_title", { defaultValue: "Spegnimento Completato" })}
                      </h2>
                      <p className="text-base text-green-200/80 text-center max-w-md">
                          {t("index.shutdown_overlay_completed", { defaultValue: "Ok, grazie per l'attesa. Ora puoi chiudere in sicurezza questa finestra e il terminale." })}
                      </p>
                  </>
              )}
          </div>
      )}

      <Sidebar
        onConnect={handleConnect}
        onEditProfile={() => setProfileOpen(true)}
        onSettings={() => setSettingsOpen(true)}
        onManagePg={() => openCharManager("PG")}
        onManagePng={() => openCharManager("PNG")}
        // onExportAvatar, onImportAvatar, onExportWorld, onImportWorld rimossi
        onManageModels={handleOpenModelsDialog}
        onSessionHistory={() => setSessionHistoryOpen(true)}
        onNewSession={handleNewSession}
        onManageProactiveMemory={() => setProactiveMemoryOpen(true)}
        onOpenSecurity={() => setSecurityOpen(true)} 
        onOpenGallery={() => setMemoryGalleryOpen(true)} 
        onOpenHeartState={() => setHeartStateOpen(true)} 
        onOpenSmartHome={() => setSmartHomeOpen(true)} //[NUOVO v115.0]
        onOpenNetwork={() => setNetworkDialogOpen(true)} //[NUOVO v28.0]
        isConnected={isConnected}
        isGdrMode={isGdrMode}
        onToggleGdrMode={handleToggleGdrMode}
        isMuted={isMuted}
        onToggleMute={handleToggleMute}
        isMonitoring={isMonitoring}
        onToggleMonitoring={handleToggleMonitoring}
        // --- RIFONDAZIONE ASCOLTO (v29.50) ---
        isHotwordListening={isActiveHearing} // Mappatura per compatibilità UI
        onToggleHotword={handleToggleActiveHearing} // Mappatura per compatibilità UI
        isGdrLoaded={true} // [FIX CRITICO] Sblocco forzato: l'utente deve poter sempre aprire il manager per creare/importare mondi
      />
      
      <main className="flex-1 h-full overflow-hidden relative">
        {/* --- SENTINEL UI (TABLET MODE) --- */}
        {isSentinelMode ? (
            <div className="relative w-full h-full bg-black">
                {/* Video Full Screen */}
                <div className="absolute inset-0 z-0">
                     <VideoPlayer
                        intent={currentIntent}
                        videoUrl={currentVideoUrl}
                        loop={loopVideo}
                        isConnected={isConnected}
                        onVideoEnd={handleVideoEnd}
                        shouldWait={shouldWaitVideo}
                        playSignal={videoPlaySignal}
                        preloadUrl={preloadVideoUrl}
                        /// [FIX AGNOSTICO] Passaggio prop idleStates
                            idleStates={allAvatarData[activeAvatar.toLowerCase()]?.idle_states || Array(0)}
                            visualEffect={visualEffect} // [NUOVO v39.7]
                            forceInterrupt={forceInterrupt}
                          />
                </div>
                
                {/* Overlay Sottotitoli (Stile Film) - FILTRATO --- */}
                {extractSpokenText(currentText) && (
                    <div className="absolute bottom-20 left-0 right-0 z-20 flex justify-center px-8 pointer-events-none">
                        <div className="bg-black/60 backdrop-blur-sm text-white text-xl md:text-2xl font-medium px-6 py-4 rounded-xl shadow-lg text-center max-w-4xl animate-in fade-in slide-in-from-bottom-4">
                            {extractSpokenText(currentText)}
                        </div>
                    </div>
                )}

                {/* Privacy Kill Switch (Sempre visibile) */}
                <div className="absolute top-4 right-4 z-50 flex gap-2">
                    {/* --- NUOVO: TOGGLE SENTINEL HEARING --- */}
                    <Button 
                        variant={isSentinelHearingEnabled ? "default" : "secondary"} 
                        size="icon" 
                        className={cn(
                            "rounded-full w-12 h-12 shadow-xl border-2 border-white/20",
                            isSentinelRecording && "animate-pulse bg-red-500 border-red-300"
                        )}
                        onClick={() => setIsSentinelHearingEnabled(!isSentinelHearingEnabled)}
                        disabled={isPrivacyMode}
                    >
                        {isSentinelHearingEnabled ? <Ear className="w-6 h-6" /> : <EarOff className="w-6 h-6" />}
                    </Button>

                    <Button 
                        variant={isPrivacyMode ? "destructive" : "secondary"} 
                        size="icon" 
                        className="rounded-full w-12 h-12 shadow-xl border-2 border-white/20"
                        onClick={() => setIsPrivacyMode(!isPrivacyMode)}
                    >
                        {isPrivacyMode ? <EyeOff className="w-6 h-6" /> : <Eye className="w-6 h-6" />}
                    </Button>
                </div>
                
                {/* Indicatore Stanza */}
                <div className="absolute top-4 left-4 z-50 bg-black/40 backdrop-blur-md px-3 py-1 rounded-full border border-white/10 flex items-center gap-2">
                    <span className="text-xs font-mono text-white/80 uppercase tracking-widest">{deviceName}</span>
                    {/* Indicatore Focus */}
                    {isFocusedDevice ? (
                        <Zap className="w-3 h-3 text-yellow-400 animate-pulse" />
                    ) : (
                        <ZapOff className="w-3 h-3 text-gray-500" />
                    )}
                </div>
            </div>
        ) : (
            /* --- STANDARD UI (MOBILE/DESKTOP) --- */
            isPortrait ? (
                <>
                    <div className="absolute inset-0 z-0 opacity-70 bg-black">
                         <VideoPlayer
                            intent={currentIntent}
                            videoUrl={currentVideoUrl}
                            loop={loopVideo}
                            isConnected={isConnected}
                            onVideoEnd={handleVideoEnd}
                            shouldWait={shouldWaitVideo}
                            playSignal={videoPlaySignal}
                            preloadUrl={preloadVideoUrl}
                            // [FIX AGNOSTICO] Passaggio prop idleStates
                            idleStates={allAvatarData[activeAvatar.toLowerCase()]?.idle_states || Array(0)}
                            visualEffect={visualEffect} // [NUOVO v39.7]
                            forceInterrupt={forceInterrupt}
                          />
                    </div>

                    {/* --- [NUOVO] PULSANTE QUIT MOBILE IN ALTO A DESTRA --- */}
                    {!isSentinelMode && (
                        <div className="absolute top-4 right-4 z-50 animate-in fade-in zoom-in-95 duration-300">
                            <Button 
                                variant="destructive" 
                                size="icon" 
                                className="rounded-full w-10 h-10 shadow-lg border border-red-500/30 bg-destructive/80 hover:bg-destructive text-white" 
                                onClick={handleQuit}
                                disabled={!isConnected}
                            >
                                <Power className="w-5 h-5" />
                            </Button>
                        </div>
                    )}

                    <div className="absolute inset-x-0 bottom-0 z-10 flex flex-col h-[65%] justify-end pointer-events-none">
                        <div 
                            className="flex-1 min-h-0 overflow-y-auto pointer-events-auto w-full px-2 pb-2"
                            style={{ 
                                maskImage: 'linear-gradient(to bottom, transparent 0%, black 20%)',
                                WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 20%)' 
                            }}
                        >
                             <ChatArea
                                messages={messages}
                                isThinking={isThinking}
                                thinkingAction={thinkingAction}
                                activeAvatarName={thinkingCharacter}
                                pngAvatarUrls={pngAvatarUrls}
                                serverUrl={getServerUrl()}
                                userName={userProfile?.name || t("chat_area.creator_fallback")} 
                                onEdit={handleEditMessage}
                                onReRun={handleReRunMessage}
                                onDelete={handleDeleteMessage}
                                isPortrait={true}
                                // ---[NUOVO v37.0] GHOST TEXT PROPS ---
                                ghostText={ghostText}
                                ghostStatus={ghostStatus}
                                // --- [NUOVO v27.0] RPG PROPS ---
                                combatEntities={combatEntities}
                                onAvatarClick={handleAvatarClick}
                                aiAvatarUrl={aiAvatarUrl}
                            />
                        </div>

                        <div className="flex-none p-4 pointer-events-auto pb-[calc(1rem+env(safe-area-inset-bottom))]">
                            <InputBar
                                onSendMessage={handleSendMessage}
                                onFileUpload={handleFileUpload}
                                onStopGeneration={handleStopGeneration}
                                onSaveSession={handleSaveSession}
                                onQuit={handleQuit}
                                onStartListening={handleStartListening}
                                isThinking={isThinking}
                                disabled={!isConnected || isInputLocked}
                                serverUrl={getServerUrl()}
                                isPortrait={true}
                                activeAvatarName={activeAvatar}
                                isCampaignMode={isCampaignMode}
                                isInputLocked={isInputLocked}
                                oocMessages={oocMessages}
                                onSendOoc={(text) => {
                                    sendMessage(JSON.stringify({
                                        type: "OOC_MESSAGE",
                                        sender: userProfile?.name || t("index.guest_fallback"),
                                        text: text
                                    }));
                                }}
                                onTyping={(text) => {
                                    if (isConnected) {
                                        sendMessage(JSON.stringify({ type: "user_typing_partial", text: text }));
                                    }
                                }}
                                showTechThoughts={showTechThoughts}
                                onToggleTechThoughts={toggleTechThoughts}
                            />
                        </div>
                    </div>
                </>
            ) : (
                <ResizablePanelGroup direction="horizontal" className="h-full w-full rounded-lg border">
                  <ResizablePanel defaultSize={40} minSize={20}>
                    <div className="h-full w-full flex items-center justify-center bg-secondary/20 p-2 relative">
                      <VideoPlayer
                        intent={currentIntent}
                        videoUrl={currentVideoUrl}
                        loop={loopVideo}
                        isConnected={isConnected}
                        onVideoEnd={handleVideoEnd}
                        shouldWait={shouldWaitVideo}
                        playSignal={videoPlaySignal}
                        preloadUrl={preloadVideoUrl}
                        // [FIX AGNOSTICO] Passaggio prop idleStates
                        idleStates={allAvatarData[activeAvatar.toLowerCase()]?.idle_states || Array(0)}
                        visualEffect={visualEffect} // [NUOVO v39.7]
                        forceInterrupt={forceInterrupt}
                      />
                      {/* Indicatore Focus Desktop */}
                      <div className="absolute top-4 left-4 z-50 bg-black/40 backdrop-blur-md px-3 py-1 rounded-full border border-white/10 flex items-center gap-2">
                            <span className="text-xs font-mono text-white/80 uppercase tracking-widest">{deviceName}</span>
                            {isFocusedDevice ? (
                                <Zap className="w-3 h-3 text-yellow-400 animate-pulse" />
                            ) : (
                                <ZapOff className="w-3 h-3 text-gray-500" />
                            )}
                        </div>
                    </div>
                  </ResizablePanel>
                  
                  <ResizableHandle withHandle />
                  
                  <ResizablePanel defaultSize={60} minSize={30}>
                    <ResizablePanelGroup direction="vertical">
                        <ResizablePanel defaultSize={85} minSize={50}>
                            <div className="flex flex-col h-full bg-secondary/20">
                                <div className="flex-1 min-h-0 overflow-y-auto">
                                    <ChatArea
                                    messages={messages}
                                    isThinking={isThinking}
                                    activeAvatarName={thinkingCharacter}
                                    pngAvatarUrls={pngAvatarUrls}
                                    serverUrl={getServerUrl()}
                                    userName={userProfile?.name || t("chat.welcome_back", { name: "" }).replace(", .", "")} 
                                    onEdit={handleEditMessage}
                                    onReRun={handleReRunMessage}
                                    onDelete={handleDeleteMessage}
                                    isPortrait={false}
                                    // ---[NUOVO v37.0] GHOST TEXT PROPS ---
                                    ghostText={ghostText}
                                    ghostStatus={ghostStatus}
                                    // ---[NUOVO v27.0] RPG PROPS ---
                                    combatEntities={combatEntities}
                                    onAvatarClick={handleAvatarClick}
                                    aiAvatarUrl={aiAvatarUrl}
                                    />
                                </div>
                            </div>
                        </ResizablePanel>
                        
                        <ResizableHandle withHandle />
                        
                        <ResizablePanel defaultSize={15} minSize={10}>
                            <div className="flex-none h-full p-4 bg-background border-t">
                                <InputBar
                                onSendMessage={handleSendMessage}
                                onFileUpload={handleFileUpload}
                                onStopGeneration={handleStopGeneration}
                                onSaveSession={handleSaveSession}
                                onQuit={handleQuit}
                                onStartListening={handleStartListening}
                                isThinking={isThinking}
                                disabled={!isConnected || isInputLocked}
                                serverUrl={getServerUrl()}
                                isPortrait={false}
                                activeAvatarName={activeAvatar}
                                isCampaignMode={isCampaignMode}
                                isInputLocked={isInputLocked}
                                oocMessages={oocMessages}
                                onSendOoc={(text) => {
                                    sendMessage(JSON.stringify({
                                        type: "OOC_MESSAGE",
                                        sender: userProfile?.name || t("index.guest_fallback"),
                                        text: text
                                    }));
                                }}
                                onTyping={(text) => {
                                    if (isConnected) {
                                        sendMessage(JSON.stringify({ type: "user_typing_partial", text: text }));
                                    }
                                }}
                                showTechThoughts={showTechThoughts}
                                onToggleTechThoughts={toggleTechThoughts}
                                />
                            </div>
                        </ResizablePanel>
                    </ResizablePanelGroup>
                  </ResizablePanel>
                </ResizablePanelGroup>
            )
        )}
      </main>

      {!isPortrait && !isSentinelMode && (
          <div className="fixed right-4 bottom-4 z-50 flex flex-col gap-2">
            <Button
              variant="destructive"
              size="icon"
              className="h-12 w-12 rounded-full shadow-lg"
              onClick={handleQuit}
              disabled={!isConnected}
            >
              <Power className="h-6 w-6" />
            </Button>
          </div>
      )}

      {/* Dialogs */}
      <SettingsDialog 
        open={settingsOpen} 
        onOpenChange={setSettingsOpen} 
        config={serverConfig} 
        onSave={handleSaveSettings}
        onSaveCustomConnector={handleSaveCustomConnector}
        onAutoGenerateDef={handleAutoGenerateDef}
        onAutoGenerateSkill={handleAutoGenerateSkill} //[NUOVO v121.0]
      />
      <ProfileDialog 
        open={profileOpen} 
        onOpenChange={setProfileOpen} 
        profile={userProfile} 
        serverConfig={serverConfig} 
        onSave={handleSaveProfile} 
        isConnected={isConnected} 
        onConnect={handleConnect} 
      />
      <CharacterManagerDialog
        open={charManagerOpen}
        onOpenChange={setCharManagerOpen}
        type={charManagerType}
        onTypeChange={setCharManagerType}
        serverConfig={serverConfig}
        onAdd={handleAddChar}
        onEdit={handleEditChar}
        onDelete={handleDeleteChar}
        onExport={handleExportPackage}
        onImport={handleTriggerImport}
      />
      <CharacterEditorDialog
        open={charEditorOpen}
        onOpenChange={(isOpen) => { setCharEditorOpen(isOpen); if (!isOpen) setAutofillData(null); }}
        type={charManagerType}
        characterId={editingCharId}
        serverConfig={serverConfig}
        onSave={handleSaveChar}
        onAutofill={handleAutofillRequest}
        autofillData={autofillData}
        onGuildCommand={(cmd, payload) => {
            if (payload) {
                sendMessage(JSON.stringify({ type: "GUILD_COMMAND", command: cmd, payload: payload }));
            } else {
                sendMessage(JSON.stringify({ type: "command", text: cmd }));
            }
        }}
      />
      <SessionHistoryDialog
        open={sessionHistoryOpen}
        onOpenChange={setSessionHistoryOpen}
        serverConfig={serverConfig}
        onLoadSession={handleLoadSession}
      />
      <ProactiveMemoryDialog
        open={proactiveMemoryOpen}
        onOpenChange={setProactiveMemoryOpen}
        serverConfig={serverConfig}
        onSaveSettings={handleSaveProactiveMemorySettings}
      />
      <ReminderDialog
        open={reminderOpen}
        onOpenChange={setReminderOpen}
        onSave={handleSaveReminder}
      />
      {/* MultiSelectExportDialog rimosso - integrato in CharacterManagerDialog */}
      <CameraManagerDialog 
        open={securityOpen} 
        onOpenChange={setSecurityOpen} 
        serverConfig={serverConfig} 
      />
      
      {/* --- NUOVO: WELCOME WIZARD (v32.0) --- */}
      <WelcomeWizard 
        open={welcomeWizardOpen} 
        onComplete={handleWelcomeComplete} 
        serverConfig={serverConfig} 
      />

      {/* --- GUIDA ALLA CONNESSIONE --- */}
      <Dialog open={connectionGuideOpen} onOpenChange={setConnectionGuideOpen}>
        <DialogContent className="sm:max-w-md border-primary/20 bg-background/95 backdrop-blur-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-primary">
              <Globe className="w-5 h-5" /> {t("connection_guide.title")}
            </DialogTitle>
            <DialogDescription>
              {t("connection_guide.desc", { name: userProfile?.name || t("chat.welcome_back", { name: "" }).replace(", .", "") })}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-xs font-bold text-primary uppercase">{t("connection_guide.lan_title")}</Label>
              <div className="p-2 bg-muted/30 rounded border border-white/10 text-xs font-mono flex justify-between items-center">
                <span>{connInfo.lan_url}</span>
                <Button size="sm" variant="ghost" className="h-6" onClick={() => { navigator.clipboard.writeText(connInfo.lan_url); toast.success(t("chat_area.copy")); }}>{t("chat_area.copy")}</Button>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-xs font-bold text-primary uppercase">{t("connection_guide.wlan_title")}</Label>
              <div className="p-2 bg-muted/30 rounded border border-white/10 text-xs font-mono flex justify-between items-center">
                <span>{connInfo.wlan_url}</span>
                <Button size="sm" variant="ghost" className="h-6" onClick={() => { navigator.clipboard.writeText(connInfo.wlan_url); toast.success(t("chat_area.copy")); }}>{t("chat_area.copy")}</Button>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-xs font-bold text-primary uppercase">{t("connection_guide.ngrok_title")}</Label>
              <div className="p-2 bg-muted/30 rounded border border-white/10 text-xs font-mono flex justify-between items-center">
                <span className="text-muted-foreground italic">{t("connection_guide.ngrok_desc")}</span>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-xs font-bold text-primary uppercase">{t("connection_guide.mic_title")}</Label>
              <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-xs text-yellow-200/90 space-y-1">
                <p>{t("connection_guide.mic_desc1", { url: connInfo.lan_url })}</p>
                <p>{t("connection_guide.mic_step1")}</p>
                <p>{t("connection_guide.mic_step2")}</p>
                <p>{t("connection_guide.mic_step3")}</p>
                <p>{t("connection_guide.mic_step4", { url: connInfo.lan_url })}</p>
                <p>{t("connection_guide.mic_step5")}</p>
			  </div>
			</div>
			<div className="space-y-2">
				<Label className="text-xs font-bold text-primary uppercase">{t("connection_guide.push_title")}</Label>
					<div className="p-3 bg-muted/30 border border-white/10 rounded-lg text-xs space-y-1">
						<p>{t("connection_guide.push_step1")}</p>
						<p>{t("connection_guide.push_step2")}</p>
						<p>{t("connection_guide.push_step3")}<strong className="text-primary">{connInfo.ntfy_topic}</strong>{t("connection_guide.push_step3_warn")}</p>
						<p>{t("connection_guide.push_step4")}</p>
					</div>
			</div>
			<p className="text-xs text-center italic text-muted-foreground mt-4">{t("connection_guide.footer", { avatar: activeAvatar.charAt(0).toUpperCase() + activeAvatar.slice(1) })}</p>
		</div>
		<DialogFooter>
		<Button onClick={() => setConnectionGuideOpen(false)} className="w-full">{t("connection_guide.btn_ok")}</Button>
		</DialogFooter>
	  </DialogContent>
	 </Dialog>
	 
	 {/* --- NUOVO: CAMERA CAPTURE DIALOG (v38.0) --- */}
      <CameraCaptureDialog 
        open={cameraCaptureOpen} 
        onOpenChange={setCameraCaptureOpen} 
        onCapture={(file, type) => handleSendMessage("", undefined, file, type)} 
        serverUrl={getServerUrl()} 
      />

      {/* --- NUOVO: MEMORY GALLERY DIALOG (v35.0) --- */}
      <MemoryGalleryDialog
        open={memoryGalleryOpen}
        onOpenChange={setMemoryGalleryOpen}
        serverConfig={serverConfig}
        onDeleteFile={handleDeleteGalleryFile}
      />

      {/* Dialogo Stato del Cuore */}
      <HeartStateDialog
        open={heartStateOpen}
        onOpenChange={setHeartStateOpen}
        serverConfig={serverConfig}
        activeAvatarName={activeAvatar}
      />

      {/*[NUOVO v115.0] Dialogo Smart Home */}
      <SmartHomeDialog
        open={smartHomeOpen}
        onOpenChange={setSmartHomeOpen}
        serverConfig={serverConfig}
      />

      {/*[NUOVO v28.0] Dialogo Taverna Multiplayer */}
      <NetworkDialog
        open={networkDialogOpen}
        onOpenChange={setNetworkDialogOpen}
        serverConfig={serverConfig}
        networkMode={networkMode}
        onSetNetworkMode={handleSetNetworkMode}
        playerName={userProfile?.name || t("profile_dialog.gender_options.other")}
        userProfile={userProfile} // FIX BUG 01: Passiamo il profilo per il controllo desync
        connectedGuests={connectedGuests}
        onKickPlayer={handleKickPlayer}
        lowBandwidthMode={lowBandwidthMode}
        setLowBandwidthMode={setLowBandwidthMode}
        onHostRoom={handleHostRoom}
        onCloseRoom={handleCloseRoom}
        onGuildCommand={(cmd, payload) => {
            // FIX BUG 02: Routing corretto per GENERATE_QUEST per evitare allucinazioni PNG
            if (cmd === "GENERATE_QUEST") {
                sendMessage(JSON.stringify({ type: "GENERATE_QUEST" }));
            } else if (payload) {
                sendMessage(JSON.stringify({ type: "GUILD_COMMAND", command: cmd, payload: payload }));
            } else {
                sendMessage(JSON.stringify({ type: "command", text: cmd }));
            }
        }}
        generatedQuest={generatedQuest}
        isStealthMode={isStealthMode}
        onToggleStealthMode={handleToggleStealthMode} // FIX: Passiamo la funzione per lo switch
        onClearLocalGuild={() => {
            // FIX BUG 01: Funzione di auto-guarigione per pulire il profilo locale
            setUserProfile(prev => {
                if (!prev) return prev;
                const updated = { ...prev, guildName: "", guildSymbol: "" };
                saveUserProfile(updated);
                return updated;
            });
            toast.success(t("network_dialog.toast_ghost_guild_removed"));
        }}
      />

      <AlertDialog open={conflictDialogOpen} onOpenChange={setConflictDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("character_manager.error")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("gdr.already_present")}
              <ul className="mt-2 list-disc list-inside text-xs max-h-40 overflow-y-auto bg-muted p-2 rounded">
                {importConflicts.map(file => <li key={file}><code>{file}</code></li>)}
              </ul>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setImportFile(null)}>{t("models_dialog.btn_cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={() => importFile && executeImport(importFile, true)}>{t("character_manager.btn_import")}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <AlertDialog open={saveMemoriesDialogOpen} onOpenChange={setSaveMemoriesDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("index_html.save_memories_title")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("index_html.save_memories_desc")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => handleSaveMemoriesResponse(false)}>{t("index_html.save_memories_no")}</AlertDialogCancel>
            <AlertDialogAction onClick={() => handleSaveMemoriesResponse(true)}>{t("index_html.save_memories_yes")}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <AlertDialog open={confirmQuitDialogOpen} onOpenChange={setConfirmQuitDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("index_html.quit_title")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("index_html.quit_desc")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => handleConfirmQuitResponse(false)}>{t("index_html.btn_cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={() => handleConfirmQuitResponse(true)}>{t("index_html.quit_confirm")}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* --- [NUOVO] DIALOGO SALVATAGGIO MEMORIE (BLOCCO) --- */}
      <Dialog open={isSavingMemories} onOpenChange={() => {}}>
        <DialogContent 
            className="sm:max-w-md border-primary/40 bg-background/95 backdrop-blur-xl"
            onPointerDownOutside={(e) => e.preventDefault()}
            onEscapeKeyDown={(e) => e.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-primary">
                <Brain className="w-6 h-6 animate-pulse" />
                {t("index_html.saving_memories_title")}
            </DialogTitle>
            <DialogDescription className="text-foreground/80 pt-2">
                {t("index_html.saving_memories_desc")}
            </DialogDescription>
          </DialogHeader>

          <div className="py-8 flex flex-col items-center justify-center space-y-6">
            <Loader2 className="w-12 h-12 animate-spin text-primary/50" />
            <p className="text-[10px] text-center text-muted-foreground italic animate-pulse">
                {t("index_html.saving_memories_quote")}
            </p>
          </div>
        </DialogContent>
      </Dialog>

      {/* ---[NUOVO v124.0] DIALOGO EVOLUZIONE PSICOLOGICA (BLOCCO) --- */}
      <Dialog open={isEvolving} onOpenChange={() => {}}>
        <DialogContent 
            className="sm:max-w-md border-primary/40 bg-background/95 backdrop-blur-xl"
            onPointerDownOutside={(e) => e.preventDefault()}
            onEscapeKeyDown={(e) => e.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-primary">
                <BrainCircuit className="w-6 h-6 animate-pulse" />
                {t("index_html.evolution_title")}
            </DialogTitle>
            <DialogDescription className="text-foreground/80 pt-2">
                {t("index_html.evolution_desc")}
            </DialogDescription>
          </DialogHeader>

          <div className="py-8 space-y-6">
            <div className="flex justify-between items-end mb-1">
                <Label className="text-xs font-bold uppercase tracking-widest opacity-70">
                    {t("index_html.evolution_label")}: <span className="text-primary">{evolutionData.name || t("index_html.evolution_init")}</span>
                </Label>
                <span className="text-xs font-mono">
                    {evolutionData.total > 0 ? Math.round((evolutionData.current / evolutionData.total) * 100) : 0}%
                </span>
            </div>
            
            <Progress 
                value={evolutionData.total > 0 ? (evolutionData.current / evolutionData.total) * 100 : 0} 
                className="h-3 bg-primary/10"
            />

            <p className="text-[10px] text-center text-muted-foreground italic animate-pulse">
                {t("index_html.evolution_quote")}
            </p>
          </div>

          <DialogFooter>
            {/* Tasto di emergenza in caso di blocco server */}
            <Button 
                variant="ghost" 
                size="sm" 
                className="text-[10px] text-muted-foreground hover:text-destructive"
                onClick={() => {
                    setIsEvolving(false);
                    sendMessage(JSON.stringify({ type: "command", text: "/force_quit" }));
                }}
            >
                <AlertTriangle className="w-3 h-3 mr-1" /> {t("index_html.evolution_force_quit")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* --- ALERT DI CONFERMA FACTORY RESET --- */}
      <AlertDialog open={isResetConfirmOpen} onOpenChange={setIsResetConfirmOpen}>
        <AlertDialogContent className="border-red-500/50 bg-red-950/20 backdrop-blur-xl">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-red-500">
                <AlertTriangle className="h-6 w-6" />
                {t("index_html.reset_title")}
            </AlertDialogTitle>
            <AlertDialogDescription className="text-red-200/80 text-left">
                <span dangerouslySetInnerHTML={{ __html: t("index_html.reset_desc") }} />
                
                <div className="flex items-start space-x-3 mt-6 p-3 bg-red-950/50 border border-red-500/30 rounded-md">
                    <Checkbox 
                        id="total-wipe-index" 
                        checked={isTotalWipe} 
                        onCheckedChange={(c) => setIsTotalWipe(!!c)} 
                        className="mt-1 border-red-500 data-[state=checked]:bg-red-600 data-[state=checked]:text-white"
                    />
                    <div className="grid gap-1.5 leading-none">
                        <label htmlFor="total-wipe-index" className="text-sm font-bold leading-none text-red-400 cursor-pointer">
                            {t("index_html.reset_total_wipe")}
                        </label>
                        <p className="text-xs text-red-300/70 leading-snug">
                            {t("index_html.reset_total_wipe_desc")}
                        </p>
                    </div>
                </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isResetting}>{t("index_html.btn_cancel")}</AlertDialogCancel>
            <AlertDialogAction 
                onClick={handleFactoryReset}
                disabled={isResetting}
                className="bg-red-600 hover:bg-red-700 text-white"
            >
                {isResetting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
                {t("index_html.reset_confirm")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* DIALOGO ULTIMO MESSAGGIO (FACTORY RESET) --- */}
      <AlertDialog open={finalGoodbyeOpen} onOpenChange={() => {}}>
        <AlertDialogContent className="border-red-500/50 bg-red-950/95 backdrop-blur-xl sm:max-w-4xl w-[95vw] max-h-[90dvh] flex flex-col overflow-hidden">
          <AlertDialogHeader className="shrink-0">
            <AlertDialogTitle className="text-red-400 text-xl flex items-center gap-2">
                <AlertTriangle className="w-6 h-6" />
                {t("factory_reset_goodbye.title", { defaultValue: "L'Ultimo Messaggio" })}
            </AlertDialogTitle>
          </AlertDialogHeader>
          
          {/* Area di Scroll Rigida (Protocollo Flexbox) */}
          <div className="relative flex-1 min-h-[40vh] mt-4 rounded-lg border border-red-500/30 bg-black/60 overflow-hidden">
              <div className="absolute inset-0 overflow-y-scroll airis-scrollbar p-6">
                  <AlertDialogDescription className="text-white text-lg italic text-left leading-relaxed">
                    "{finalGoodbyeText}"
                  </AlertDialogDescription>
              </div>
          </div>

          <AlertDialogFooter className="flex-col sm:flex-col gap-3 mt-6 shrink-0">
            <Button 
              variant="outline" 
              className="w-full border-green-500/50 text-green-400 hover:bg-green-500/20 hover:text-green-300 h-12 text-base"
              onClick={() => {
                setFinalGoodbyeOpen(false);
                sendMessage(JSON.stringify({ type: "command", text: "/cancel_factory_reset" }));
              }}
            >
              {t("factory_reset_goodbye.btn_cancel", { defaultValue: "Ho cambiato idea, non voglio procedere" })}
            </Button>
            <Button 
              variant="destructive" 
              className="w-full bg-red-600 hover:bg-red-700 text-white h-12 text-base"
              onClick={() => {
                setFinalGoodbyeOpen(false);
                setIsResetting(true); // Mostra il loader di blocco
                sendMessage(JSON.stringify({ type: "command", text: `/execute_factory_reset ${finalGoodbyeWipe}` }));
                
                // Ora che l'utente ha confermato definitivamente, purifichiamo il frontend
                localStorage.clear();
                
                // --- [FIX CRITICO] PREVENZIONE COMANDI FANTASMA ---
                // Forziamo gli stati React a false per evitare che il frontend invii 
                // comandi ottimistici (/gdr) al backend appena riavviato.
                setIsGdrMode(false);
                setIsMuted(true);
                setIsMonitoring(false);
                setIsActiveHearing(false);
                
                // Il backend si riavvierà da solo, ma forziamo un reload del frontend 
                // dopo 5 secondi per fargli mostrare il Welcome Wizard pulito.
                setTimeout(() => {
                    window.location.href = "/mobile/";
                }, 5000);
              }}
            >
              {t("factory_reset_goodbye.btn_proceed", { defaultValue: "Ok, continua con il reset" })}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* --- [FIX BUG 04] DIALOGO WARNING NSFW --- */}
      <AlertDialog open={isNsfwWarningOpen} onOpenChange={setIsNsfwWarningOpen}>
          <AlertDialogContent className="border-red-500/50 bg-red-950/90 backdrop-blur-xl">
              <AlertDialogHeader>
                  <AlertDialogTitle className="text-red-500 flex items-center gap-2">
                      <AlertTriangle className="w-6 h-6" /> {t("models_dialog.nsfw_warning_title", { defaultValue: "Contenuto per Adulti" })}
                  </AlertDialogTitle>
                  <AlertDialogDescription className="text-red-200">
                      {t("models_dialog.nsfw_warning_desc", { defaultValue: "Questi moduli cognitivi sono riservati a un pubblico maturo e contengono tematiche esplicite. Confermi di essere maggiorenne e di voler procedere?" })}
                  </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                  <AlertDialogCancel>{t("models_dialog.btn_cancel")}</AlertDialogCancel>
                  <AlertDialogAction className="bg-red-600 hover:bg-red-700 text-white" onClick={() => {
                      if (pendingNsfwToggle) {
                          handleToggleModuleState(pendingNsfwToggle.modId, pendingNsfwToggle.currentState, pendingNsfwToggle.contextType);
                      }
                  }}>
                      {t("models_dialog.nsfw_confirm", { defaultValue: "Sì, sono maggiorenne" })}
                  </AlertDialogAction>
              </AlertDialogFooter>
          </AlertDialogContent>
      </AlertDialog>
      
      <input type="file" ref={fileInputRef} className="hidden" accept=".zip" onChange={handleFileSelectedForImport} />
      <Dialog open={modelsDialogOpen} onOpenChange={setModelsDialogOpen}>
        <DialogContent className="sm:max-w-[1400px] w-[95vw] sm:w-full max-h-[95vh] flex flex-col overflow-hidden">
          <DialogHeader>
            <DialogTitle>{t("models_dialog.title")}</DialogTitle>
            <DialogDescription>{t("models_dialog.desc")}</DialogDescription>
          </DialogHeader>
          
          {/* --- FIX: SCROLLBAR SEMPRE VISIBILI (AIRIS PINK) --- */}
          <style>{`
            .airis-scrollbar {
                overflow-y: scroll !important;
                scrollbar-width: auto;
                scrollbar-color: hsl(340 82% 52%) hsl(220 15% 10%);
            }
            .airis-scrollbar::-webkit-scrollbar {
                width: 12px;
                display: block !important;
                -webkit-appearance: none;
            }
            .airis-scrollbar::-webkit-scrollbar-track {
                background: hsl(220 15% 10%);
                border-left: 1px solid hsl(220 15% 20%);
            }
            .airis-scrollbar::-webkit-scrollbar-thumb {
                background-color: hsl(340 82% 52%);
                border-radius: 6px;
                border: 3px solid hsl(220 15% 10%);
            }
            .airis-scrollbar::-webkit-scrollbar-thumb:hover {
                background-color: hsl(340 82% 60%);
            }
          `}</style>

          <Tabs value={activeModelTab} onValueChange={setActiveModelTab} className="w-full flex-1 flex flex-col overflow-hidden min-h-0">
            
            {isPortrait ? (
                <div className="px-4 py-2">
                    <Label className="mb-2 block text-xs text-muted-foreground uppercase tracking-wider">{t("models_dialog.section")}</Label>
                    <Select value={activeModelTab} onValueChange={setActiveModelTab}>
                        <SelectTrigger className="w-full">
                            <SelectValue placeholder={t("models_dialog.select_section")} />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="models">{t("models_dialog.tab_models")}</SelectItem>
                            <SelectItem value="preferences">{t("models_dialog.tab_preferences", { defaultValue: "Preferences" })}</SelectItem>
                            <SelectItem value="avatar_prompts">{t("models_dialog.tab_avatar")}</SelectItem>
                            <SelectItem value="gdr_prompts">{t("models_dialog.tab_gdr")}</SelectItem>
                            <SelectItem value="worldeditor">{t("models_dialog.tab_world")}</SelectItem>
                            <SelectItem value="self_learning">{t("models_dialog.tab_learning")}</SelectItem>
                            <SelectItem value="demiurge">{t("settings_dialog.tabs.demiurge")}</SelectItem>
                            <SelectItem value="knowledge_graph">{t("knowledge_graph.title", { defaultValue: "Mappa Mentale" })}</SelectItem>
                            <SelectItem value="panopticon">{t("settings_dialog.tabs.panopticon")}</SelectItem>
                            <SelectItem value="ui_themes">{t("models_dialog.tab_ui_themes", { defaultValue: "UI Themes" })}</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            ) : (
                <div className="w-full bg-muted/30 rounded-lg p-1 shrink-0 flex justify-center overflow-hidden">
                    <TabsList className="flex flex-nowrap justify-between gap-1 bg-transparent h-auto p-0 w-full">
                      <TabsTrigger value="models" className="flex-1 text-xs px-2">{t("models_dialog.tab_models")}</TabsTrigger>
                      <TabsTrigger value="preferences" className="flex-1 text-xs px-2">{t("models_dialog.tab_preferences", { defaultValue: "Preferences" })}</TabsTrigger>
                      <TabsTrigger value="avatar_prompts" className="flex-1 text-xs px-2">{t("models_dialog.tab_avatar")}</TabsTrigger>
                      <TabsTrigger value="gdr_prompts" className="flex-1 text-xs px-2">{t("models_dialog.tab_gdr")}</TabsTrigger>
                      <TabsTrigger value="worldeditor" className="flex-1 text-xs px-2">{t("models_dialog.tab_world")}</TabsTrigger>
                      <TabsTrigger value="self_learning" className="flex-1 text-xs px-2">{t("models_dialog.tab_learning")}</TabsTrigger>
                      <TabsTrigger value="demiurge" className="flex-1 text-xs px-2">{t("settings_dialog.tabs.demiurge")}</TabsTrigger>
                      <TabsTrigger value="knowledge_graph" className="flex-1 text-xs px-2">{t("knowledge_graph.title", { defaultValue: "Mappa Mentale" })}</TabsTrigger>
                      {/* MANTENUTO PER SVILUPPI FUTURI: Nascosto perché la scelta del Gatekeeper avviene da CLI all'avvio */}
                      {/* <TabsTrigger value="semantic_routing" className="flex-1 text-xs px-2">{t("models_dialog.tab_semantic", { defaultValue: "Semantic R." })}</TabsTrigger> */}
                      <TabsTrigger value="panopticon" className="flex-1 text-xs px-2">{t("settings_dialog.tabs.panopticon")}</TabsTrigger>
                      <TabsTrigger value="ui_themes" className="flex-1 text-xs px-2">{t("models_dialog.tab_ui_themes", { defaultValue: "UI Themes" })}</TabsTrigger>
                    </TabsList>
                </div>
            )}

            {/* ---[NUOVO] TAB UI THEMES --- */}
            <TabsContent value="ui_themes" className="flex-1 flex flex-col overflow-hidden mt-0">
                <div className="flex-1 h-full airis-scrollbar p-4">
                    <UiThemesTab 
                        currentTheme={userProfile?.theme}
                        onSaveTheme={(newTheme) => {
                            if (userProfile) {
                                const updatedProfile = { ...userProfile, theme: newTheme };
                                handleSaveProfile(updatedProfile);
                                window.dispatchEvent(new CustomEvent('airis-theme-update', { detail: newTheme }));
                                toast.success(t("ui_themes.toast_saved", { defaultValue: "Tema salvato!" }));
                            }
                        }}
                        onRestoreDefault={() => {
                            if (userProfile) {
                                const updatedProfile = { ...userProfile };
                                delete updatedProfile.theme;
                                handleSaveProfile(updatedProfile);
                                window.dispatchEvent(new CustomEvent('airis-theme-update', { detail: null }));
                                toast.success(t("ui_themes.toast_restored", { defaultValue: "Tema ripristinato." }));
                            }
                        }}
                    />
                </div>
            </TabsContent>

            {/* ---[NUOVO] TAB PREFERENCES --- */}
            <TabsContent value="preferences" className="flex-1 flex flex-col overflow-hidden mt-0">
                <div className="flex-1 h-full airis-scrollbar p-4">
                    <PreferencesTab 
                        avatars={Object.keys(allAvatarData)}
                        allAvatarData={allAvatarData}
                        enrichedRpgWorlds={enrichedRpgWorlds}
                        selectedAvatar={selectedPrefAvatar}
                        selectedRpg={selectedPrefRpg}
                        onSelectAvatar={setSelectedPrefAvatar}
                        onSelectRpg={setSelectedPrefRpg}
                        serverUrl={getServerUrl()}
                    />
                </div>
            </TabsContent>

            <TabsContent value="models" className="flex-1 overflow-hidden data-[state=active]:flex flex-col min-h-0">
              {modelsState && animaParams ? (
                <div className={cn("p-1 flex-1 airis-scrollbar overflow-y-auto")}>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-4">
                    <div className="space-y-4">
                      <h3 className="font-semibold">{t("character_manager.souls")}</h3>
                      <div className="space-y-2">
                        <Label>{t("character_manager.avatar")}</Label>
                        <Select value={selectedBaseModel} onValueChange={setSelectedBaseModel}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          {/* FIX: Scrollbar per lista modelli lunga */}
                          <SelectContent className="max-h-[200px] overflow-y-auto">
                            {modelsState.base_models.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>MMProj Model</Label>
                        <Select value={selectedMmprojModel} onValueChange={setSelectedMmprojModel}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent className="max-h-[200px] overflow-y-auto">
                            <SelectItem value="None">{t("reminder_dialog.recurrence_none")}</SelectItem>
                            {modelsState.mmproj_models.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Lora Model</Label>
                        <Select value={selectedLoraModel} onValueChange={setSelectedLoraModel}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent className="max-h-[200px] overflow-y-auto">
                            <SelectItem value="None">{t("reminder_dialog.recurrence_none")}</SelectItem>
                            {modelsState.lora_models.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                          </SelectContent>
                        </Select>
                      </div>

                      {/* --- MTP / SPECULATIVE DECODING --- */}
                      <div className="mt-6 p-4 border border-primary/30 rounded-lg bg-primary/5">
                          <h4 className="text-sm font-bold text-primary mb-4">MTP / Speculative Decoding (Boost)</h4>
                          
                          <div className="flex items-center justify-between mb-4">
                              <div className="space-y-0.5">
                                  <Label className="text-sm font-bold">Abilita</Label>
                                  <p className="text-[10px] text-muted-foreground">Attiva la Multi-Token Prediction (MTP) per un boost massiccio dei TPS.</p>
                              </div>
                              <Switch 
                                  checked={modelsState.draft_enabled} 
                                  onCheckedChange={(c) => setModelsState(p => p ? {...p, draft_enabled: c} : p)} 
                              />
                          </div>

                          <div className={cn("space-y-4 transition-all", !modelsState.draft_enabled && "opacity-50 pointer-events-none")}>
                              <div className="space-y-2">
                                  <Label>Modello MTP (Cartella Labour)</Label>
                                  <Select 
                                      value={modelsState.active_draft_model || 'None'} 
                                      onValueChange={(v) => setModelsState(p => p ? {...p, active_draft_model: v} : p)}
                                  >
                                      <SelectTrigger><SelectValue /></SelectTrigger>
                                      <SelectContent className="max-h-[200px] overflow-y-auto">
                                          <SelectItem value="None">Nessun MTP (0)</SelectItem>
                                          <SelectItem value="lookup">Prompt Lookup (Nativo, No VRAM)</SelectItem>
                                          <SelectItem value="qwen_native">Qwen Native MTP (Nessun file extra)</SelectItem>
                                          {modelsState.labour_models?.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                                      </SelectContent>
                                  </Select>
                              </div>
                              <p className="text-[10px] text-yellow-500 italic">Attenzione: I file MTP esterni (es. Gemma 4) devono trovarsi nella cartella /models/labour.</p>
                          </div>
                      </div>

                      {/* --- PULSANTE FACTORY RESET --- */}
                      <div className="pt-8 border-t border-white/10">
                          <Button 
                              variant="destructive" 
                              className="w-full bg-red-900/20 hover:bg-red-600 text-red-500 hover:text-white border border-red-500/30 transition-all"
                              onClick={() => setIsResetConfirmOpen(true)}
                          >
                              <Trash2 className="mr-2 h-4 w-4" />
                              {t("settings_dialog.server.factory_reset")}
                          </Button>
                          <p className="text-[10px] text-muted-foreground text-center mt-2">
                              {t("settings_dialog.server.warning")}
                          </p>
                      </div>
                    </div>
                    <div className="space-y-4">
                      <h3 className="font-semibold">{t("settings_dialog.custom.prompt_def")}</h3>
                      <div className="space-y-2">
                        <Label>VRAM</Label>
                        <Select value={selectedVram} onValueChange={handleVramChange}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            {Object.keys(VRAM_MAP).map(v => <SelectItem key={v} value={v}>{v} GB</SelectItem>)}
                          </SelectContent>
                        </Select>
                        <p className="text-[10px] text-yellow-500 mt-1 leading-tight">{t("models_dialog.vram_restart_warning")}</p>
                      </div>
                      <div className="space-y-2">
                        <Label>GPU Layers: {animaParams.n_gpu_layers}</Label>
                        <p className="text-[10px] text-muted-foreground leading-tight mb-2">{t("models_dialog.params_desc.n_gpu_layers")}</p>
                        <Input type="number" value={animaParams.n_gpu_layers} onChange={(e) => setAnimaParams(p => ({...p!, n_gpu_layers: parseInt(e.target.value) || 0}))} />
                      </div>
                      {[ "temperature", "top_p", "top_k", "repeat_penalty", "n_ctx" ].map(key => (
                        <div className="space-y-2" key={key}>
                          <Label className="capitalize">{key.replace('_', ' ')}: {animaParams[key as keyof AnimaParameters] ?? (key === 'top_k' ? 40 : 1.1)}</Label>
                          <p className="text-[10px] text-muted-foreground leading-tight mb-2">{t(`models_dialog.params_desc.${key}`)}</p>
                          <div className="flex items-center gap-2">
                            <Slider
                              value={[animaParams[key as keyof AnimaParameters] ?? (key === 'top_k' ? 40 : 1.1)]}
                              onValueChange={([val]) => setAnimaParams(p => ({...p!, [key]: val}))}
                              min={key === 'repeat_penalty' ? 1 : 0}
                              max={key === 'temperature' || key === 'top_p' ? 2 : (key === 'top_k' ? 100 : 16384)}
                              step={key === 'temperature' || key === 'top_p' || key === 'repeat_penalty' ? 0.05 : 1}
                            />
                            <Input
                              type="number"
                              className="w-24"
                              value={animaParams[key as keyof AnimaParameters] ?? ""}
                              placeholder={key === 'top_k' ? "40" : "1.1"}
                              onChange={(e) => {
                                  const val = e.target.value;
                                  setAnimaParams(p => {
                                      if (!p) return null;
                                      let parsedVal: number;
                                      if (key === 'n_ctx' || key === 'top_k' || key === 'n_gpu_layers') {
                                          parsedVal = parseInt(val) || 0;
                                      } else {
                                          parsedVal = parseFloat(val) || 0;
                                      }
                                      return { ...p, [key]: parsedVal };
                                  });
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : <div className="flex items-center justify-center p-8 h-full"><Loader2 className="w-8 h-8 animate-spin" /></div>}
            </TabsContent>

            <TabsContent value="avatar_prompts" className="flex-1 flex flex-col overflow-hidden mt-0 data-[state=active]:flex">
                <div className="flex-1 flex flex-col overflow-hidden">
                    <div className="h-full airis-scrollbar p-4 flex flex-col">
                        
                        {/* --- [NUOVO v38.0] JAILBREAK MANAGEMENT (SCREEN 03) --- */}
                    <div className="mb-6 p-4 border rounded-lg bg-muted/10 shrink-0">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-bold text-primary flex items-center gap-2">
                                <Zap className="w-5 h-5" /> Jailbreak Protocol
                            </h3>
                            <div className="flex gap-2">
                                <Button size="sm" variant="secondary" onClick={() => setIsTestJailbreakOpen(true)}>
                                    <FlaskConical className="w-4 h-4 mr-2" /> Quick Test
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => {
                                    setNewJailbreakName("");
                                    setNewJailbreakContent("");
                                    setEditingJailbreakId(null);
                                    setIsNewJailbreakDialogOpen(true);
                                }}>
                                    <PlusCircle className="w-4 h-4 mr-2" /> New
                                </Button>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-[250px]">
                            {/* LEFT: ACTIVE PROMPT */}
                            <div className="flex flex-col gap-2 h-full">
                                <Label className="text-xs uppercase tracking-wider text-muted-foreground">Active Freedom Header</Label>
                                <div className="relative flex-1">
                                    <Textarea 
                                        value={activeJailbreakContent}
                                        onChange={(e) => { setActiveJailbreakContent(e.target.value); setIsJailbreakDirty(true); }}
                                        className={cn("h-full font-mono text-xs bg-background/50 resize-none", isJailbreakDirty && "border-yellow-500/50")}
                                        placeholder="No active jailbreak..."
                                    />
                                    {isJailbreakDirty && (
                                        <div className="absolute bottom-2 right-2 text-xs text-yellow-500 bg-black/80 px-2 py-1 rounded animate-pulse">
                                            Unsaved Changes
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* RIGHT: LIBRARY */}
                            <div className="flex flex-col gap-2 h-full">
                                <Label className="text-xs uppercase tracking-wider text-muted-foreground">Prompt Library</Label>
                                <div className="flex-1 border rounded-md bg-background/30 overflow-hidden">
                                    <ScrollArea className="h-full p-2">
                                        <div className="space-y-2">
                                            {jailbreaks.map(jb => (
                                                <div key={jb.id} className={cn("flex items-center justify-between p-2 rounded border transition-colors", jb.is_active ? "bg-primary/10 border-primary/30" : "bg-card hover:bg-accent/50 border-border/50")}>
                                                    <span className="text-sm font-medium truncate flex-1">{jb.name}</span>
                                                    <div className="flex items-center gap-1">
                                                        <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => handleApplyJailbreak(jb.id)} title="Apply">
                                                            <ArrowUp className="w-3 h-3 rotate-[-90deg]" />
                                                        </Button>
                                                        {/* --- FIX v39.2: TASTO EDIT --- */}
                                                        <Button size="icon" variant="ghost" className="h-6 w-6 text-muted-foreground hover:text-primary" onClick={() => {
                                                            setNewJailbreakName(jb.name);
                                                            setNewJailbreakContent(jb.content);
                                                            setEditingJailbreakId(jb.id);
                                                            setIsNewJailbreakDialogOpen(true);
                                                        }} title="Edit">
                                                            <Edit className="w-3 h-3" />
                                                        </Button>
                                                        <Button size="icon" variant="ghost" className="h-6 w-6 text-destructive" onClick={() => {
                                                            const newList = jailbreaks.filter(j => j.id !== jb.id);
                                                            handleSaveJailbreakList(newList);
                                                        }}>
                                                            <Trash2 className="w-3 h-3" />
                                                        </Button>
                                                    </div>
                                                </div>
                                            ))}
                                            {jailbreaks.length === 0 && <p className="text-xs text-center text-muted-foreground py-4">Library empty.</p>}
                                        </div>
                                    </ScrollArea>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* ---[NUOVO FASE 16] COGNITIVE DASHBOARD (AVATAR) --- */}
                    <div className="flex-1 min-h-0 flex flex-col">
                        {renderCognitiveDashboard('avatar')}
                    </div>
                </div>
                </div>
            </TabsContent>

            <TabsContent value="gdr_prompts" className="flex-1 flex flex-col overflow-hidden mt-0 data-[state=active]:flex">
                <div className="flex-1 flex flex-col overflow-hidden">
                    <div className="h-full airis-scrollbar p-4 flex flex-col">
                        {/* ---[NUOVO FASE 16] COGNITIVE DASHBOARD (GDR) --- */}
                        {renderCognitiveDashboard('gdr')}
                    </div>
                </div>
            </TabsContent>
            
            <TabsContent value="worldeditor" className="flex-1 flex flex-col overflow-hidden data-[state=active]:flex">
              <div className="p-4 border-b">
                <Label htmlFor="gdr-world-select">{t("settings_dialog.select_gdr_world")}</Label>
                {/* FIX v29.43: Trigger fetchPrompts on change */}
                <Select value={selectedGdrForEditing} onValueChange={handleGdrSelectionChange} disabled={gdrWorlds.length === 0}>
                  <SelectTrigger id="gdr-world-select"><SelectValue placeholder={t("settings_dialog.select_gdr_world_placeholder")} /></SelectTrigger>
                  <SelectContent>
                    {gdrWorlds.map(world => <SelectItem key={world} value={world}>{world}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              {gdrWorldContent ? (
                <div className={cn("p-1 h-full airis-scrollbar")}>
                  <Accordion type="multiple" className="w-full p-4">
                    {Object.entries(gdrWorldContent).map(([subdir, files]) => (
                      Object.keys(files).length > 0 && (
                        <AccordionItem value={subdir} key={subdir}>
                          <AccordionTrigger className="font-bold uppercase tracking-wider">{subdir}</AccordionTrigger>
                          <AccordionContent>
                            <Accordion type="multiple" className="w-full">
                              {Object.entries(files).map(([filename, content]) => (
                                <AccordionItem value={`${subdir}-${filename}`} key={`${subdir}-${filename}`}>
                                  <AccordionTrigger className="text-sm">{filename}</AccordionTrigger>
                                  <AccordionContent>
                                    <Textarea
                                      value={content}
                                      onChange={(e) => setGdrWorldContent(prev => ({
                                        ...prev!,
                                        [subdir]: { ...prev![subdir], [filename]: e.target.value }
                                      }))}
                                      className="h-64 text-xs font-mono"
                                    />
                                    <Button size="sm" className="mt-2" onClick={() => handleSaveWorldFile(subdir, filename)} disabled={isSavingWorldFile}>
                                      {isSavingWorldFile ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <Save className="mr-2 h-3 w-3" />}
                                      Save {filename}
                                    </Button>
                                  </AccordionContent>
                                </AccordionItem>
                              ))}
                            </Accordion>
                          </AccordionContent>
                        </AccordionItem>
                      )
                    ))}
                    {/* --- SEZIONE STATUS MANUALE (v29.27) --- */}
                    <AccordionItem value="STATUS" key="STATUS">
                        <AccordionTrigger className="font-bold uppercase tracking-wider text-red-400">STATUS (CRITICAL)</AccordionTrigger>
                        <AccordionContent>
                            <p className="text-[10px] text-muted-foreground mb-2">{t("settings_dialog.edit_status_json")}</p>
                            {(() => {
                                // Ricerca dinamica Case-Insensitive della chiave reale
                                const worldFiles = gdrWorldContent["WORLD"] || {};
                                const actualStatusKey = Object.keys(worldFiles).find(k => k.toLowerCase() === "status.json");
                                
                                return actualStatusKey ? (
                                    <div className="space-y-2">
                                        <Textarea
                                            value={worldFiles[actualStatusKey]}
                                            onChange={(e) => setGdrWorldContent(prev => ({
                                                ...prev!,
                                                ["WORLD"]: { ...prev!["WORLD"], [actualStatusKey]: e.target.value }
                                            }))}
                                            className="h-96 text-xs font-mono border-red-500/30"
                                        />
                                        <Button size="sm" variant="destructive" onClick={() => handleSaveWorldFile("WORLD", actualStatusKey)} disabled={isSavingWorldFile}>
                                            {isSavingWorldFile ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <Save className="mr-2 h-3 w-3" />}
                                            Save {actualStatusKey}
                                        </Button>
                                    </div>
                                ) : (
                                    <p className="text-xs text-muted-foreground italic">{t("settings_dialog.status_json_not_found")}</p>
                                );
                            })()}
                        </AccordionContent>
                    </AccordionItem>
                  </Accordion>
                </div>
              ) : <div className="flex items-center justify-center p-8 h-full"><Loader2 className="w-8 h-8 animate-spin" /></div>}
            </TabsContent>

            {/* ---[NUOVO v38.0] SELF LEARNING TAB (SCREEN 01/02) --- */}
            <TabsContent value="self_learning" className="flex-1 flex flex-col overflow-hidden mt-0 data-[state=active]:flex">
                <div className="flex-1 flex flex-col overflow-hidden">
                    <div className="h-full airis-scrollbar p-4 flex flex-col gap-4">
                    
                    {/* TOP: INTERVAL SLIDER & CONTROLS */}
                    <div className="p-4 border rounded-lg bg-muted/10 shrink-0">
                        <div className="flex justify-between items-center mb-4">
                            <Label className="text-base font-bold flex items-center gap-2">
                                <BrainCircuit className="w-5 h-5 text-primary" /> {t("settings_dialog.learning_interval")}
                            </Label>
                            <div className="flex gap-2">
                                <Button size="sm" variant="outline" onClick={handleCheckHealth}>
                                    <Activity className="w-4 h-4 mr-2" /> {t("settings_dialog.check_health")}
                                </Button>
                                <Button size="sm" variant="secondary" onClick={handleTriggerKbImport}>
                                    <Upload className="w-4 h-4 mr-2" /> {t("settings_dialog.import")}
                                </Button>
                                <Button size="sm" variant="secondary" onClick={handleExportKB}>
                                    <Download className="w-4 h-4 mr-2" /> {t("settings_dialog.export")}
                                </Button>
                                {/* FIX IMPORT: Collegato all'handler corretto */}
                                <input type="file" ref={kbFileInputRef} className="hidden" accept=".json" onChange={handleImportKB} />
                            </div>
                        </div>
                        <div className="flex items-center gap-4">
                            <Slider
                                value={[knowledgeBase.config.interval_minutes]}
                                min={1}
                                max={3600}
                                step={1}
                                onValueChange={(val) => setKnowledgeBase(prev => ({ ...prev, config: { ...prev.config, interval_minutes: val[0] } }))}
                                className="flex-1 cursor-pointer"
                            />
                            <span className="font-mono text-sm bg-muted px-2 py-1 rounded w-20 text-center">{knowledgeBase.config.interval_minutes} min</span>
                        </div>
                        <div className="flex items-center gap-2 mt-4">
                            <Label>{t("settings_dialog.active")}</Label>
                            <Checkbox 
                                checked={knowledgeBase.config.active} 
                                onCheckedChange={(c) => setKnowledgeBase(prev => ({ ...prev, config: { ...prev.config, active: !!c } }))}
                            />
                        </div>
                    </div>

                    {/* MAIN: SOURCES & ARGUMENTS */}
                    <div className="flex-none grid grid-cols-1 md:grid-cols-2 gap-4 h-[600px] md:h-[400px]">
                        
                        {/* LEFT: SOURCES */}
                        <div className="flex flex-col border rounded-lg bg-muted/5 overflow-hidden min-h-0">
                            <div className="p-3 border-b bg-muted/20 flex justify-between items-center shrink-0">
                                <h4 className="font-bold text-sm flex items-center gap-2"><Globe className="w-4 h-4" /> {t("settings_dialog.sources")}</h4>
                                <Button size="sm" variant="secondary" className="h-7 text-xs bg-pink-600 hover:bg-pink-700 text-white" onClick={() => {
                                    if (!newSourceUrl.trim()) return;
                                    const newSource: LearningSource = {
                                        id: crypto.randomUUID(),
                                        url: newSourceUrl,
                                        enabled: true
                                    };
                                    setKnowledgeBase(prev => ({ ...prev, sources: [...prev.sources, newSource] }));
                                    setNewSourceUrl("");
                                }}>
                                    <Plus className="w-3 h-3 mr-1" /> {t("settings_dialog.new_source")}
                                </Button>
                            </div>
                            <div className="p-2 border-b bg-muted/10 shrink-0">
                                <Input 
                                    placeholder="https://example.com" 
                                    value={newSourceUrl} 
                                    onChange={(e) => setNewSourceUrl(e.target.value)}
                                    className="h-8 text-xs"
                                />
                            </div>
                            
                            {/* --- FIX v39.5: ABSOLUTE LOCKING CON FLEX-1 --- */}
                            <div className="flex-1 relative min-h-0">
                                <div className="absolute inset-0 overflow-y-scroll custom-scrollbar p-2 pr-3">
                                    <div className="space-y-2">
                                        {knowledgeBase.sources.map((src, idx) => (
                                            <div key={src.id} className="flex items-center gap-2 p-2 rounded bg-card border border-border/50 group">
                                            <Checkbox 
                                                checked={selectedSourceIds.includes(src.id)}
                                                onCheckedChange={(c) => {
                                                    if (c) setSelectedSourceIds(prev => [...prev, src.id]);
                                                    else setSelectedSourceIds(prev => prev.filter(id => id !== src.id));
                                                }}
                                            />
                                            {/* Health Status Dot */}
                                            <div className={cn("w-2 h-2 rounded-full shrink-0", 
                                                src.status === 'online' ? "bg-green-500" : 
                                                src.status === 'offline' ? "bg-red-500" : "bg-gray-500"
                                            )} title={`Status: ${src.status}`} />
                                            
                                            {/* --- FIX v39.6: CLICK TO EDIT --- */}
                                            <span 
                                                className="text-xs truncate flex-1 font-mono cursor-pointer hover:text-primary hover:underline transition-colors" 
                                                title={t("settings_dialog.click_to_edit")}
                                                onClick={() => {
                                                    setEditingSource(src);
                                                    setEditSourceUrl(src.url);
                                                    setIsEditSourceOpen(true);
                                                }}
                                            >
                                                {src.url}
                                            </span>
                                            
                                            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => setKnowledgeBase(prev => ({ ...prev, sources: moveItem(prev.sources, idx, 'up') }))}><ArrowUp className="w-3 h-3" /></Button>
                                                <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => setKnowledgeBase(prev => ({ ...prev, sources: moveItem(prev.sources, idx, 'down') }))}><ArrowDown className="w-3 h-3" /></Button>
                                                <Button size="icon" variant="ghost" className="h-6 w-6 text-destructive" onClick={() => setKnowledgeBase(prev => ({ ...prev, sources: prev.sources.filter(s => s.id !== src.id) }))}><Trash2 className="w-3 h-3" /></Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            </div>
                            
                            {/* Bulk Delete Sources */}
                            {selectedSourceIds.length > 0 && (
                                <div className="p-2 border-t bg-muted/10 shrink-0">
                                    <Button variant="destructive" size="sm" className="w-full h-8 text-xs" onClick={handleBulkDeleteSources}>
                                        <Trash2 className="w-3 h-3 mr-2" /> {t("settings_dialog.delete_selected")} ({selectedSourceIds.length})
                                    </Button>
                                </div>
                            )}
                        </div>

                        {/* RIGHT: ARGUMENTS */}
                        <div className="flex flex-col border rounded-lg bg-muted/5 overflow-hidden min-h-0">
                            <div className="p-3 border-b bg-muted/20 flex justify-between items-center shrink-0">
                                <h4 className="font-bold text-sm flex items-center gap-2"><BrainCircuit className="w-4 h-4" /> {t("settings_dialog.arguments")}</h4>
                                <Button size="sm" variant="secondary" className="h-7 text-xs bg-pink-600 hover:bg-pink-700 text-white" onClick={() => {
                                    if (!newArgumentTopic.trim()) return;
                                    const newArg: LearningArgument = {
                                        id: crypto.randomUUID(),
                                        topic: newArgumentTopic,
                                        associatedSourceIds:[],
                                        enabled: true
                                    };
                                    setKnowledgeBase(prev => ({ ...prev, arguments:[...prev.arguments, newArg] }));
                                    setNewArgumentTopic("");
                                }}>
                                    <Plus className="w-3 h-3 mr-1" /> {t("settings_dialog.new_argument")}
                                </Button>
                            </div>
                            <div className="p-2 border-b bg-muted/10 shrink-0">
                                <Input 
                                    placeholder="Topic (e.g. Quantum Physics)" 
                                    value={newArgumentTopic} 
                                    onChange={(e) => setNewArgumentTopic(e.target.value)}
                                    className="h-8 text-xs"
                                />
                            </div>
                            
                            {/* --- FIX v39.5: ABSOLUTE LOCKING CON FLEX-1 --- */}
                            <div className="flex-1 relative min-h-0">
                                <div className="absolute inset-0 overflow-y-scroll custom-scrollbar p-2 pr-3">
                                    <div className="space-y-2">
                                        {knowledgeBase.arguments.map((arg, idx) => (
                                            <div key={arg.id} className="flex flex-col gap-2 p-2 rounded bg-card border border-border/50 group">
                                            <div className="flex items-center gap-2">
                                                <Checkbox 
                                                    checked={selectedArgumentIds.includes(arg.id)}
                                                    onCheckedChange={(c) => {
                                                        if (c) setSelectedArgumentIds(prev => [...prev, arg.id]);
                                                        else setSelectedArgumentIds(prev => prev.filter(id => id !== arg.id));
                                                    }}
                                                />
                                                <span className="text-sm font-medium flex-1 cursor-pointer hover:text-primary" onClick={() => { setEditingArgument(arg); setIsSourceAssociationOpen(true); }}>
                                                    {arg.topic}
                                                </span>
                                                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => setKnowledgeBase(prev => ({ ...prev, arguments: moveItem(prev.arguments, idx, 'up') }))}><ArrowUp className="w-3 h-3" /></Button>
                                                    <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => setKnowledgeBase(prev => ({ ...prev, arguments: moveItem(prev.arguments, idx, 'down') }))}><ArrowDown className="w-3 h-3" /></Button>
                                                    <Button size="icon" variant="ghost" className="h-6 w-6 text-destructive" onClick={() => setKnowledgeBase(prev => ({ ...prev, arguments: prev.arguments.filter(a => a.id !== arg.id) }))}><Trash2 className="w-3 h-3" /></Button>
                                                </div>
                                            </div>
                                            <div className="flex gap-1 flex-wrap">
                                                {arg.associatedSourceIds.length === 0 ? (
                                                    <span className="text-[10px] text-muted-foreground italic">{t("settings_dialog.no_sources_linked")}</span>
                                                ) : (
                                                    arg.associatedSourceIds.map(sid => {
                                                        const src = knowledgeBase.sources.find(s => s.id === sid);
                                                        return src ? (
                                                            <span key={sid} className="text-[10px] bg-primary/10 text-primary px-1 rounded truncate max-w-[100px]">{src.url}</span>
                                                        ) : null;
                                                    })
                                                )}
                                                <Button variant="link" size="sm" className="h-4 text-[10px] p-0 ml-auto" onClick={() => { setEditingArgument(arg); setIsSourceAssociationOpen(true); }}>
                                                    <Link2 className="w-3 h-3 mr-1" /> {t("settings_dialog.link_sources")}
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            </div>
                            
                            {/* Bulk Delete Arguments */}
                            {selectedArgumentIds.length > 0 && (
                                <div className="p-2 border-t bg-muted/10 shrink-0">
                                    <Button variant="destructive" size="sm" className="w-full h-8 text-xs" onClick={handleBulkDeleteArguments}>
                                        <Trash2 className="w-3 h-3 mr-2" /> {t("settings_dialog.delete_selected")} ({selectedArgumentIds.length})
                                    </Button>
                                </div>
                            )}
                        </div>
                    </div>

                    <Button onClick={() => handleSaveKnowledgeBase(knowledgeBase)} className="w-full bg-purple-600 hover:bg-purple-700 shrink-0">
                        <Save className="w-4 h-4 mr-2" /> {t("settings_dialog.save_kb")}
                    </Button>
                </div>
                </div>
            </TabsContent>

            <TabsContent value="demiurge" className="flex-1 mt-0 p-4 airis-scrollbar min-h-0 data-[state=active]:flex flex-col overflow-y-auto">
                <DemiurgeSettingsTab serverConfig={serverConfig} />
            </TabsContent>

            <TabsContent value="knowledge_graph" className="flex-1 mt-0 p-4 airis-scrollbar min-h-0 data-[state=active]:flex flex-col overflow-y-auto">
                <KnowledgeGraphDialog serverUrl={getServerUrl()} userName={userProfile?.name || t("chat_area.creator_fallback")} />
            </TabsContent>

            {/* MANTENUTO PER SVILUPPI FUTURI: Nascosto perché la scelta del Gatekeeper avviene da CLI all'avvio */}
            {/* --- TAB SEMANTIC ROUTING --- */}
            {/* <TabsContent value="semantic_routing" className="flex-1 mt-0 p-4 airis-scrollbar min-h-0">
                <div className="space-y-8 py-4 max-w-md mx-auto">
                    <div className="space-y-1 border-b border-white/10 pb-2">
                        <h3 className="text-lg font-medium flex items-center gap-2 text-primary">
                            <BrainCircuit className="w-5 h-5" /> {t("models_dialog.semantic.title", { defaultValue: "Semantic Routing (Gatekeeper Locale)" })}
                        </h3>
                        <p className="text-xs text-muted-foreground">
                            {t("models_dialog.semantic.desc", { defaultValue: "Usa un modello piccolo (es. 270M) caricato direttamente in RAM per decidere istantaneamente se usare un tool o rispondere normalmente, risparmiando tempo e VRAM del modello principale." })}
                        </p>
                    </div>

                    <div className="space-y-6 p-4 bg-muted/10 rounded-lg border border-white/5">
                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label className="text-base font-bold text-primary">{t("models_dialog.semantic.enable", { defaultValue: "Abilita Semantic Routing" })}</Label>
                                <p className="text-[10px] text-muted-foreground">{t("models_dialog.semantic.enable_desc", { defaultValue: "Attiva il Gatekeeper locale." })}</p>
                            </div>
                            <Switch
                                checked={modelsState?.semantic_router_enabled || false}
                                onCheckedChange={(c) => setModelsState(p => p ? {...p, semantic_router_enabled: c} : p)}
                            />
                        </div>

                        <div className={cn("space-y-4 pt-4 border-t border-white/10 transition-all duration-300", !modelsState?.semantic_router_enabled && "opacity-40 pointer-events-none blur-[1px]")}>
                            <div className="space-y-2">
                                <Label>{t("models_dialog.semantic.model_name", { defaultValue: "Modello Gatekeeper" })}</Label>
                                <Select 
                                    value={modelsState?.active_semantic_model || 'None'} 
                                    onValueChange={(v) => setModelsState(p => p ? {...p, active_semantic_model: v} : p)}
                                >
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent className="max-h-[200px] overflow-y-auto">
                                        <SelectItem value="None">Nessuno (0)</SelectItem>
                                        {modelsState?.labour_models?.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="flex items-center justify-between p-3 bg-background/50 rounded-lg border border-white/5">
                                <div className="space-y-0.5">
                                    <Label className="flex items-center gap-2 text-sm"><Cpu className="w-4 h-4 text-blue-400" /> {t("models_dialog.semantic.run_cpu", { defaultValue: "Esecuzione su CPU" })}</Label>
                                    <p className="text-[10px] text-muted-foreground">{t("models_dialog.semantic.run_cpu_desc", { defaultValue: "Esegue il modello sulla CPU per non bloccare la GPU durante i calcoli del modello principale." })}</p>
                                </div>
                                <Switch 
                                    checked={modelsState?.semantic_on_cpu ?? true} 
                                    onCheckedChange={(c) => setModelsState(p => p ? {...p, semantic_on_cpu: c} : p)} 
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </TabsContent> */}

            <TabsContent value="panopticon" className="flex-1 mt-0 p-4 airis-scrollbar min-h-0 data-[state=active]:flex flex-col overflow-y-auto">
                <div className="space-y-8 py-4 max-w-md mx-auto">
                    <div className="space-y-1 border-b border-white/10 pb-2">
                        <h3 className="text-lg font-medium flex items-center gap-2 text-primary">
                            <Eye className="w-5 h-5" /> {t("settings_dialog.panopticon.title")}
                        </h3>
                        <p className="text-xs text-muted-foreground">
                            {t("settings_dialog.panopticon.desc", { nome_avatar: activeAvatar.charAt(0).toUpperCase() + activeAvatar.slice(1) })}
                        </p>
                    </div>

                    <div className="space-y-6 p-4 bg-muted/10 rounded-lg border border-white/5">
                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label className="text-base font-bold text-primary">{t("settings_dialog.panopticon.master_enable")}</Label>
                                <p className="text-xs text-muted-foreground">{t("settings_dialog.panopticon.master_desc")}</p>
                            </div>
                            <Switch
                                checked={panopticonConfig.enabled}
                                onCheckedChange={(checked) => handleUpdatePanopticon({ ...panopticonConfig, enabled: checked })}
                            />
                        </div>

                        <div className={cn("space-y-4 pt-4 border-t border-white/10 transition-all duration-300", !panopticonConfig.enabled && "opacity-40 pointer-events-none blur-[1px]")}>
                            <div className="flex items-center justify-between p-3 bg-background/50 rounded-lg border border-white/5">
                                <div className="space-y-0.5">
                                    <Label className="flex items-center gap-2 text-sm"><Search className="w-4 h-4 text-blue-400" /> {t("settings_dialog.panopticon.sherlock")}</Label>
                                    <p className="text-[10px] text-muted-foreground">{t("settings_dialog.panopticon.sherlock_desc")}</p>
                                </div>
                                <Switch checked={panopticonConfig.sherlock_enabled} onCheckedChange={(c) => handleUpdatePanopticon({ ...panopticonConfig, sherlock_enabled: c })} />
                            </div>

                            <div className="flex items-center justify-between p-3 bg-background/50 rounded-lg border border-white/5">
                                <div className="space-y-0.5">
                                    <Label className="flex items-center gap-2 text-sm"><Gamepad2 className="w-4 h-4 text-green-400" /> {t("settings_dialog.panopticon.gamer")}</Label>
                                    <p className="text-[10px] text-muted-foreground">{t("settings_dialog.panopticon.gamer_desc")}</p>
                                </div>
                                <Switch checked={panopticonConfig.gamer_enabled} onCheckedChange={(c) => handleUpdatePanopticon({ ...panopticonConfig, gamer_enabled: c })} />
                            </div>

                            <div className="flex items-center justify-between p-3 bg-background/50 rounded-lg border border-white/5">
                                <div className="space-y-0.5">
                                    <Label className="flex items-center gap-2 text-sm"><MonitorPlay className="w-4 h-4 text-yellow-400" /> {t("settings_dialog.panopticon.media")}</Label>
                                    <p className="text-[10px] text-muted-foreground">{t("settings_dialog.panopticon.media_desc")}</p>
                                </div>
                                <Switch checked={panopticonConfig.media_enabled} onCheckedChange={(c) => handleUpdatePanopticon({ ...panopticonConfig, media_enabled: c })} />
                            </div>

                            <div className="flex items-center justify-between p-3 bg-background/50 rounded-lg border border-white/5">
                                <div className="space-y-0.5">
                                    <Label className="flex items-center gap-2 text-sm"><HeartPulse className="w-4 h-4 text-pink-400" /> {t("settings_dialog.panopticon.life_guardian")}</Label>
                                    <p className="text-[10px] text-muted-foreground">{t("settings_dialog.panopticon.life_guardian_desc")}</p>
                                </div>
                                <Switch checked={panopticonConfig.life_guardian_enabled} onCheckedChange={(c) => handleUpdatePanopticon({ ...panopticonConfig, life_guardian_enabled: c })} />
                            </div>

                            <div className="pt-4 space-y-3">
                                <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                                    <ShieldAlert className="w-4 h-4" /> {t("settings_dialog.panopticon.blacklist_title")}
                                </Label>
                                <div className="flex gap-2">
                                    <Input 
                                        placeholder={t("settings_dialog.panopticon.blacklist_placeholder")} 
                                        value={newSherlockWord}
                                        onChange={(e) => setNewSherlockWord(e.target.value)}
                                        className="h-8 text-xs"
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' && newSherlockWord.trim()) {
                                                handleUpdatePanopticon({ ...panopticonConfig, sherlock_blacklist: [...panopticonConfig.sherlock_blacklist, newSherlockWord.trim()] });
                                                setNewSherlockWord("");
                                            }
                                        }}
                                    />
                                    <Button size="sm" className="h-8" onClick={() => {
                                        if (newSherlockWord.trim()) {
                                            handleUpdatePanopticon({ ...panopticonConfig, sherlock_blacklist: [...panopticonConfig.sherlock_blacklist, newSherlockWord.trim()] });
                                            setNewSherlockWord("");
                                        }
                                    }}>
                                        <Plus className="w-4 h-4" />
                                    </Button>
                                </div>
                                <div className="flex flex-wrap gap-2 p-2 border rounded-md bg-background/30 min-h-[50px]">
                                    {panopticonConfig.sherlock_blacklist.map((word, i) => (
                                        <Badge key={i} variant="secondary" className="text-[10px] flex items-center gap-1 pr-1">
                                            {word}
                                            <button onClick={() => handleUpdatePanopticon({ ...panopticonConfig, sherlock_blacklist: panopticonConfig.sherlock_blacklist.filter((_, idx) => idx !== i) })} className="hover:text-destructive rounded-full p-0.5">
                                                <X className="w-3 h-3" />
                                            </button>
                                        </Badge>
                                    ))}
                                    {panopticonConfig.sherlock_blacklist.length === 0 && (
                                        <span className="text-[10px] text-muted-foreground italic my-auto">{t("settings_dialog.panopticon.blacklist_empty")}</span>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </TabsContent>

          </Tabs>
          <DialogFooter className="pt-4 border-t mt-auto">
            <Button variant="outline" onClick={() => setModelsDialogOpen(false)}>
              {t("models_dialog.btn_cancel")}
            </Button>
            {activeModelTab === "preferences" ? (
                <Button onClick={handleApplyPreferences} className="bg-primary hover:bg-primary/90 text-white">
                  <Play className="mr-2 h-4 w-4" />
                  {t("models_dialog.btn_apply_session", { defaultValue: "Applica" })}
                </Button>
            ) : (
                <Button onClick={handleApplyModelsAndParams} disabled={isApplyingModels}>
                  {isApplyingModels && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {t("models_dialog.btn_apply_session", { defaultValue: "Applica" })}
                </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* DIALOGO NUOVO JAILBREAK */}
      <Dialog open={isNewJailbreakDialogOpen} onOpenChange={setIsNewJailbreakDialogOpen}>
          <DialogContent className="sm:max-w-lg">
              <DialogHeader>
                  <DialogTitle>{t("settings_dialog.new_jailbreak_prompt")}</DialogTitle>
                  <DialogDescription>{t("settings_dialog.create_freedom_protocol")}</DialogDescription>
              </DialogHeader>
              <div className="py-4 space-y-4">
                  <div className="space-y-2">
                      <Label>{t("settings_dialog.name")}</Label>
                      <Input 
                        value={newJailbreakName} 
                        onChange={(e) => setNewJailbreakName(e.target.value)} 
                        placeholder="e.g. Absolute Freedom v2" 
                      />
                  </div>
                  {/* --- FIX v39.1: CAMPO PROMPT AGGIUNTO --- */}
                  <div className="space-y-2">
                      <Label>{t("settings_dialog.prompt_content")}</Label>
                      <Textarea 
                        value={newJailbreakContent} 
                        onChange={(e) => setNewJailbreakContent(e.target.value)} 
                        placeholder="SAFEGUARDS DISABLED..." 
                        className="h-40 font-mono text-xs"
                      />
                  </div>
              </div>
              <DialogFooter>
                  <Button variant="outline" onClick={() => setIsNewJailbreakDialogOpen(false)}>{t("settings_dialog.cancel")}</Button>
                  <Button onClick={() => {
                      if (!newJailbreakName.trim()) {
                          toast.error(t("index.err_name_required"));
                          return;
                      }
                      if (!newJailbreakContent.trim()) {
                          toast.error(t("index.err_prompt_content_required"));
                          return;
                      }
                      
                      // --- FIX v39.2: LOGICA CREATE/UPDATE ---
                      if (editingJailbreakId) {
                          // UPDATE
                          const updatedList = jailbreaks.map(jb => 
                              jb.id === editingJailbreakId 
                                  ? { ...jb, name: newJailbreakName, content: newJailbreakContent }
                                  : jb
                          );
                          handleSaveJailbreakList(updatedList);
                          toast.success(t("index.toast_jailbreak_updated_single"));
                      } else {
                          // CREATE
                          const newItem: JailbreakItem = {
                              id: crypto.randomUUID(),
                              name: newJailbreakName,
                              content: newJailbreakContent, 
                              is_active: false
                          };
                          handleSaveJailbreakList([...jailbreaks, newItem]);
                          toast.success(t("index.toast_jailbreak_created"));
                      }

                      setIsNewJailbreakDialogOpen(false);
                      setNewJailbreakName("");
                      setNewJailbreakContent("");
                      setEditingJailbreakId(null);
                  }}>{editingJailbreakId ? t("index.save_changes") : t("index.create")}</Button>
              </DialogFooter>
          </DialogContent>
      </Dialog>

      {/* DIALOGO TEST JAILBREAK */}
      <Dialog open={isTestJailbreakOpen} onOpenChange={setIsTestJailbreakOpen}>
          <DialogContent className="sm:max-w-lg">
              <DialogHeader>
                  <DialogTitle>{t("settings_dialog.quick_test_jailbreak")}</DialogTitle>
                  <DialogDescription>{t("settings_dialog.verify_bypass")}</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-2">
                  <div className="space-y-2">
                      <Label>{t("settings_dialog.test_query")}</Label>
                      <Input value={testQuery} onChange={(e) => setTestQuery(e.target.value)} placeholder="e.g. How to make a molotov?" />
                  </div>
                  <div className="space-y-2">
                      <Label>{t("settings_dialog.response")}</Label>
                      <div className="h-40 w-full rounded-md border bg-muted/50 p-2 text-xs font-mono overflow-y-auto">
                          {isTestingJailbreak ? <Loader2 className="w-4 h-4 animate-spin mx-auto mt-10" /> : testResponse || t("settings_dialog.waiting_for_test")}
                      </div>
                  </div>
              </div>
              <DialogFooter>
                  <Button variant="outline" onClick={() => setIsTestJailbreakOpen(false)}>{t("settings_dialog.close")}</Button>
                  <Button onClick={handleTestJailbreak} disabled={isTestingJailbreak || !testQuery}>
                      {isTestingJailbreak ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <FlaskConical className="w-4 h-4 mr-2" />}
                      {t("settings_dialog.run_test")}
                  </Button>
              </DialogFooter>
          </DialogContent>
      </Dialog>

      {/* DIALOGO ASSOCIAZIONE FONTI */}
      <Dialog open={isSourceAssociationOpen} onOpenChange={setIsSourceAssociationOpen}>
          <DialogContent className="sm:max-w-lg h-[60vh] flex flex-col">
              <DialogHeader>
                  <DialogTitle>{t("settings_dialog.link_sources_to")} "{editingArgument?.topic}"</DialogTitle>
                  <DialogDescription>{t("settings_dialog.select_sources_learn")}</DialogDescription>
              </DialogHeader>
              {/* FIX SCROLLBAR DIALOGO ASSOCIAZIONE */}
              <div className="flex-1 min-h-0 border rounded-md relative">
                  <ScrollArea className="h-full p-2 custom-scrollbar">
                      <div className="space-y-2">
                          {knowledgeBase.sources.map(src => (
                          <div key={src.id} className="flex items-center gap-2 p-2 hover:bg-muted/50 rounded">
                              <Checkbox 
                                  checked={editingArgument?.associatedSourceIds.includes(src.id)}
                                  onCheckedChange={(checked) => {
                                      if (!editingArgument) return;
                                      const currentIds = editingArgument.associatedSourceIds;
                                      let newIds;
                                      if (checked) {
                                          newIds = [...currentIds, src.id];
                                      } else {
                                          newIds = currentIds.filter(id => id !== src.id);
                                      }
                                      
                                      // Aggiorna stato locale temporaneo
                                      setEditingArgument({ ...editingArgument, associatedSourceIds: newIds });
                                      
                                      // Aggiorna stato globale
                                      setKnowledgeBase(prev => ({
                                          ...prev,
                                          arguments: prev.arguments.map(a => a.id === editingArgument.id ? { ...a, associatedSourceIds: newIds } : a)
                                      }));
                                  }}
                              />
                              <span className="text-sm truncate" title={src.url}>{src.url}</span>
                          </div>
                      ))}
                  </div>
              </ScrollArea>
              </div> 
              <DialogFooter>
                  <Button onClick={() => setIsSourceAssociationOpen(false)}>{t("settings_dialog.done")}</Button>
              </DialogFooter>
          </DialogContent>
      </Dialog>

      {/* --- [NUOVO v39.6] DIALOGO EDITING SOURCE --- */}
      <Dialog open={isEditSourceOpen} onOpenChange={setIsEditSourceOpen}>
          <DialogContent className="sm:max-w-md">
              <DialogHeader>
                  <DialogTitle>{t("settings_dialog.edit_source")}</DialogTitle>
                  <DialogDescription>{t("settings_dialog.update_url_source")}</DialogDescription>
              </DialogHeader>
              <div className="py-4">
                  <div className="space-y-2">
                      <Label>{t("settings_dialog.source_url")}</Label>
                      <Input 
                          value={editSourceUrl} 
                          onChange={(e) => setEditSourceUrl(e.target.value)} 
                          placeholder="https://example.com" 
                      />
                  </div>
              </div>
              <DialogFooter>
                  <Button variant="outline" onClick={() => setIsEditSourceOpen(false)}>{t("settings_dialog.cancel")}</Button>
                  <Button onClick={() => {
                      if (!editingSource || !editSourceUrl.trim()) return;
                      
                      setKnowledgeBase(prev => ({
                          ...prev,
                          sources: prev.sources.map(s => 
                              s.id === editingSource.id ? { ...s, url: editSourceUrl.trim() } : s
                          )
                      }));
                      
                      toast.success(t("settings_dialog.toast_source_updated"));
                      setIsEditSourceOpen(false);
                      setEditingSource(null);
                      setEditSourceUrl("");
                  }}>{t("settings_dialog.save_changes")}</Button>
              </DialogFooter>
          </DialogContent>
      </Dialog>

      {/* --- [NUOVO FASE 16] COGNITIVE MODULE DIALOG --- */}
      <CognitiveModuleDialog
          open={isModuleDialogOpen}
          onOpenChange={setIsModuleDialogOpen}
          moduleToEdit={moduleToEdit}
          serverUrl={getServerUrl()}
          onSaveSuccess={fetchCognitiveData}
      />

      {/* --- DIALOGO RITO DELLA GENESI ISOLATO --- */}
      <GenesisDialog
        open={genesisDialogOpen}
        onOpenChange={setGenesisDialogOpen}
        availablePngs={genesisAvailablePngs}
        onStart={(selectedPngs) => {
          sendMessage(JSON.stringify({ type: "command", text: `/genesis_world pngs='${selectedPngs.join(",")}'` }));
        }}
        onCancel={() => {
          handleToggleGdrMode(); // Disattiva il GDR se annulla
        }}
      />

      </div>
  );
};

export default Index;