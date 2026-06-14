// frontend_mobile/src/types/index.ts

export interface IntentData {
  description: string;
  filepath: string;
  category: string;
  short_description: string;
  is_alternative: boolean;
  duration_seconds: number;
}

export interface ChatMessage {
  id: string;
  role?: "user" | "gemma"; // Mantenuto per compatibilità
  sender?: string;         // Aggiunto per compatibilità con Index.tsx
  content?: string;        // Mantenuto per compatibilità
  text?: string;           // Aggiunto per compatibilità con Index.tsx
  timestamp: Date;
  avatar?: string;
  // Campi per supporto media
  mediaUrl?: string;
  mediaType?: "image" | "video" | "document";
  fileName?: string;
  // --- [NUOVO] Araldica Gilda ---
  guildName?: string;
  guildSymbol?: string;
}

export interface WebSocketMessage {
  type: string; // "text_message", "action", "system_status", "prompt", "playback_complete", "user_media", "hive_focus_change", "demiurge_toast", "rpg_update", etc.
  intent?: string;
  audio_url?: string;
  video_url?: string;
  loop?: boolean;
  payload?: any;
  message?: string;
  text?: string;
  avatar_url?: string;
  avatar?: string;
  // Campi per user_media
  media_type?: "image" | "video" | "document";
  url?: string;
  filename?: string;
  // Campi per Hive Mind
  device_id?: string;
  // Campi per Demiurge Toast
  level?: string;
  // Campi per RPG Engine (v27.0)
      combat_entities?: CombatEntity[];
      // ---[NUOVO v28.0] Campi per Multiplayer Network ---
      target_player?: string;
      history?: any[];
      world_state?: any;
      // --- [NUOVO] Campi per Handshake e Araldica ---
      guild_name?: string;
      guild_symbol?: string;
      gender?: string;
}


// ---[NUOVO v20.0] INTERFACCIA PANOPTICON ---
export interface PanopticonConfig {
  enabled: boolean;
  sherlock_enabled: boolean;
  gamer_enabled: boolean;
  media_enabled: boolean;
  life_guardian_enabled: boolean;
  sherlock_blacklist: Array<string>;
}

// ---[NUOVO] INTERFACCIA MCP SERVER ---
export interface McpServerConfig {
  id: string;
  name: string;
  transport: 'stdio' | 'sse';
  command?: string;
  args?: string[];
  url?: string;
  enabled: boolean;
}

export interface ServerConfig {
  ip: string;
  port: string;
  protocol: "ws" | "wss";
  currentAvatar: string;
  panopticon?: PanopticonConfig; //[NUOVO v20.0]
  mcp_servers?: McpServerConfig[]; // [NUOVO]
}

export interface ThemeConfig {
  background: string;
  foreground: string;
  primary: string;
  "primary-foreground": string;
  secondary: string;
  "secondary-foreground": string;
  muted: string;
  "muted-foreground": string;
  accent: string;
  "accent-foreground": string;
  card: string;
  "card-foreground": string;
  border: string;
}

export interface UserProfile {
  name: string;
  age?: string;
  birthDate?: string; // NUOVO CAMPO: Data di nascita
  gender?: string;
  email?: string;
  mobileNumber?: string;
  avatar?: string;
  bio?: string;
  preferredLanguage?: string;
  preferredVoice?: string;
  // --- [NUOVO] Araldica Gilda Locale ---
  guildName?: string;
  guildSymbol?: string;
  // ---[NUOVO] Modalità Stealth ---
  isStealthMode?: boolean;
  // --- [NUOVO] Tema UI ---
  theme?: ThemeConfig;
}

// --- [NUOVO] Dati Quest Generata ---
export interface GeneratedQuestData {
  titolo: string;
  descrizione: string;
  livello_minimo: number;
  livello_massimo: number;
}

export interface VoiceInfo {
  id: string;
  name: string;
  gender: string;
}

export interface LanguageInfo {
  name: string;
  default_voice: string;
  kokoro_code: string;
  voices: VoiceInfo[];
}

export interface AvailableLanguages {
  [key: string]: LanguageInfo;
}

export type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

export interface ChatSession {
  id: string;
  name: string;
  creation_date: number; // Timestamp
  last_access_date: number; // Timestamp
  gdr_snapshot_path: string | null;
}

export interface ProactiveMemorySettings {
  reflection_time: string; // "HH:MM"
  reminder_check_interval_minutes: number;
}

export interface EventReminder {
  id: string;
  event_name: string;
  content: string; // notes
  event_timestamp: number;
  trigger_timestamp: number; // Unix timestamp
  status: 'pending' | 'triggered' | 'dismissed';
  recurrence_rule: 'none' | 'daily' | 'weekly' | 'monthly' | 'yearly';
}

export interface ReminderData {
  eventName: string;
  eventDate: Date;
  notes: string;
  reminderDate: Date;
  recurrenceRule: 'none' | 'daily' | 'weekly' | 'monthly' | 'yearly';
}

export interface CustomConnectorData {
    name: string;
    scriptFile: File | null;
    scriptCode: string;
    fields: Record<string, string>;
    prompt: string;
    dependencies: string;
    def_structure: string;
}

// ---[NUOVO v27.0] INTERFACCE SCHEDA RPG E COMBATTIMENTO ---
export interface RpgStat {
  valore: number;
  modificatore: number;
}

export interface RpgWeapon {
  nome: string;
  bonus_attacco: number;
  danno: string;
  tipo: string;
}

export interface RpgArmor {
  nome: string;
  tipo: string;
  ca_bonus: string;
  svantaggio_furtivita: boolean;
}

export interface RpgSheet {
  dati_base: {
    razza: string;
    classe: string;
    livello: number;
    punti_esperienza: number;
    allineamento: string;
  };
  statistiche_core: {
    forza: RpgStat;
    destrezza: RpgStat;
    costituzione: RpgStat;
    intelligenza: RpgStat;
    saggezza: RpgStat;
    carisma: RpgStat;
  };
  combattimento: {
    hp_massimi: number;
    hp_attuali: number;
    classe_armatura: number;
    iniziativa: number;
    velocita: number;
  };
  equipaggiamento: {
    armi: RpgWeapon[];
    armature: RpgArmor[];
    inventario: string[];
    monete: { oro: number; argento: number; rame: number; };
  };
  magia_e_privilegi: {
    tratti_razziali: string[];
    privilegi_classe: string[];
    incantesimi: string[];
  };
}

export interface CombatEntity {
  id: string;
  nome: string;
  hp_attuali: number;
  hp_massimi: number;
  is_enemy: boolean;
  avatar_url?: string;
  // --- [NUOVO] Araldica Gilda ---
  guild_name?: string;
  guild_symbol?: string;
}

// --- NUOVE INTERFACCE PER STILISTA E ORARI ---

export interface TimeSchedule {
  morning: string;
  afternoon: string;
  night: string;
  bed_time: string;
}

export interface AvatarStyleInfo {
  active_set: string;
  available_sets: string[];
  current_season: string;
}

// --- NUOVE INTERFACCE PER BOYKEEP (FASE 16) ---
export interface BoykeepCamera {
    id: string;
    name: string;
    room_name?: string; // Mappatura stanza opzionale
}

export interface BoykeepConfig {
    enabled: boolean;
    monitoring_interval: number; // Secondi tra i check
    cameras: BoykeepCamera[];
}

// --- NUOVE INTERFACCE PER HIVE MIND (FASE 21) ---
export interface HiveDevice {
  id: string;
  name: string; // Es. "Cucina", "Salotto", "iPhone Sam"
  type: 'tablet' | 'mobile' | 'desktop';
  status: 'online' | 'offline';
  last_seen: number;
}

export interface HiveState {
  devices: Record<string, HiveDevice>;
  active_focus_id: string | null; // ID del dispositivo dove l'Avatar è attualmente "incarnato"
}

// --- NUOVA INTERFACCIA PER PERCEZIONE (v69.0) ---
export interface PerceptionSettings {
  silence_threshold: number;
  hotword_detection: {
    enabled_by_default: boolean;
    hotword: string;
    listen_timeout: number;
    phrase_time_limit: number;
  };
}

// --- NUOVA INTERFACCIA PER DEMIURGO (v69.1) ---
export interface DemiurgeConfig {
  enabled: boolean;
  provider: string;
  model: string;
  api_key: string;
  api_base: string;
  auto_run: boolean;
  safe_mode: boolean;
  labour_model_on_cpu: boolean; // [NUOVO v52.0]
}

// --- [NUOVO] INTERFACCE PER PROTOCOLLO MUSA & GENESI ---

export interface JailbreakPrompt {
  id: string;
  name: string;
  content: string;
  is_active: boolean; // Se è quello attualmente caricato in memoria
}

export interface LearningSource {
  id: string;
  url: string;
  enabled: boolean;
  last_checked?: number; // Timestamp ultimo check salute
  status?: 'online' | 'offline' | 'unknown';
}

export interface LearningArgument {
  id: string;
  topic: string;
  associatedSourceIds: string[]; // IDs delle LearningSource collegate
  enabled: boolean;
}

export interface SelfLearningConfig {
  interval_minutes: number;
  active: boolean;
}

export interface KnowledgeBaseData {
  sources: LearningSource[];
  arguments: LearningArgument[];
  config: SelfLearningConfig;
}

// --- [NUOVO FASE 16] INTERFACCE COGNITIVE MODULES & MINDSETS ---

export interface ActivationCondition {
  vector: string;
  operator: ">" | "<" | ">=" | "<=" | "==";
  threshold: number;
}

export interface CognitiveModule {
  id: string;
  name: string;
  category: "identity" | "behavior" | "restriction" | "system";
  context: "always" | "avatar" | "gdr";
  content: string;
  is_active: boolean;
  priority: number;
  tags: string[];
  activation_condition?: ActivationCondition;
}

export interface MindsetProfile {
  id: string;
  name: string;
  context: "avatar" | "gdr" | "all";
  module_states: Record<string, boolean>;
}

export interface CognitiveMindsets {
  active_avatar_mindset: string;
  active_gdr_mindset: string;
  profiles: MindsetProfile[];
}

// --- [NUOVO v18.0] INTERFACCE JARVIS CORTEX ---

export interface PatchRecord {
  id: string;
  timestamp: number;
  file: string;
  old_code: string;
  new_code: string;
  status: 'applied' | 'rolled_back';
}

export interface JarvisConfig {
  blacklist_windows: string[];
}

// --- [NUOVO v19.0] CARE OS TYPES ---

export interface CareTrigger {
  value: string;
  label: string;
}

export interface CareModuleConfig {
  enabled: boolean;
  sensitivity?: string;
  inactivity_alert_minutes?: number; // Per Elderly Helper
  active_from?: string; // HH:MM
  active_until?: string; // HH:MM
  [key: string]: any;
}

export interface CareRule {
  id: string;
  name: string;
  trigger: string;
  conditions: Record<string, any>;
  actions: Array<{ type: string; [key: string]: any }>;
  enabled: boolean;
}

export interface CareCronJob {
  id: string;
  name: string;
  time: string;
  days: string[];
  action: string;
  payload: string;
  enabled: boolean;
}

export interface EmergencyContact {
  email: string;
  phone: string;
}

export interface CareConfig {
  modules: {
    baby_monitor: CareModuleConfig;
    elderly_helper: CareModuleConfig;
    pet_monitor: CareModuleConfig;
  };
  zones: any[];
  rules: CareRule[];
  cron_jobs: CareCronJob[];
  triggers?: CareTrigger[];
  emergency_contacts?: EmergencyContact;
  audio_library?: CareAudioClip[]; // [NUOVO v20.0]
}

// --- [NUOVO v20.0] CORTEX AUDIO TYPES ---

export interface CareAudioClip {
  id: string;
  label: string;
  category: 'Elders' | 'Baby' | 'Pets' | 'Emergency' | 'Custom';
  path: string; // Percorso relativo per il server
  type: 'recorded' | 'generated'; // Registrato dall'utente o generato via TTS
  created_at: number;
}

// Estensione di CareRule per supportare la logica avanzata
export interface CareRule {
  id: string;
  name: string;
  trigger: string;
  conditions: Record<string, any>;
  actions: Array<{ 
    type: string; 
    clip_id?: string; // ID della clip da riprodurre
    target_device_ids?: string[]; // [NUOVO] Routing Multi-Dispositivo
    escalation_clip_id?: string; // Clip da usare se la prima fallisce
    escalation_delay_seconds?: number; // Default 90s[key: string]: any; 
      }>;
      enabled: boolean;
}

// ---[NUOVO v28.0] TIPI MULTIPLAYER NETWORK ---
export type NetworkMode = 'OFF' | 'HOST' | 'CLIENT';

export interface OOCMessage {
  id: string;
  sender: string;
  text: string;
  timestamp: Date;
}