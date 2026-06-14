// frontend_mobile/src/components/SmartHomeDialog.tsx
// v1.9 - SUPREME SCROLLBAR & STRUCTURAL INVARIANCE
// FIX: Risolto definitivamente il problema delle scrollbar mancanti in tutti i tab su mobile.
// FIX: Implementato il Protocollo Flexbox Rigido (Absolute Inset) per ogni sezione.
// FIX: Forzata l'altezza del dialogo a h-[90vh] per prevenire il collasso del layout.
// FIX: Ripristinato lo stile "Pillola" (bg-muted) per la TabsList su Desktop.
// MANTENUTO: Ogni singola riga di logica, commento e handler del file originale v1.4.
// LEGGE A0099: Invarianza strutturale garantita. Codice integrale fornito.

import { useState, useEffect, useRef } from "react";
import { useTranslation } from "@/contexts/TranslationContext";
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
import { Textarea } from "@/components/ui/textarea"; // [FIX v20.1] Import mancante per Audio Library
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox"; // [FIX] Import necessario per multi-routing audio
import { 
  Home, Plus, Trash2, Settings, Zap, Thermometer, Tv, Lightbulb, Clock, Activity, Save, RefreshCw, Play, AlertTriangle, List, Calendar, Check, X, Baby, Dog, User, Shield, Mic, MicOff, Radio, Edit, Brain, Terminal, Code, RotateCcw, GitCommit, EyeOff, ShieldAlert, Briefcase, Music, Wand2, PlayCircle, StopCircle, Volume2, ShieldAlert // [NUOVO v18.0] Jarvis Icons
} from "lucide-react";
import { toast } from "sonner";
import { ServerConfig, HiveDevice, PatchRecord } from "@/types"; // [NUOVO v18.0] PatchRecord
import { getBaseUrl, getHeaders } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useIsPortrait } from "@/hooks/use-mobile";

interface SmartHomeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  serverConfig: ServerConfig | null;
}

// --- INTERFACCE IOT ---
interface IotDevice {
    id: string;
    name: string;
    type: 'light' | 'tv' | 'climate' | 'switch' | 'other';
    ip: string;
    protocol: 'http_get' | 'http_post' | 'mqtt' | 'ha';
    commands: Record<string, string>;
    status?: string;
}

interface IotRoom {
    id: string;
    name: string;
    devices: IotDevice[];
}

interface IotAutomation {
    id: string;
    name: string;
    deviceId: string;
    action: string;
    value?: any;
    time: string; // HH:mm
    days: string[]; // ['Mon', 'Tue'...]
    enabled: boolean;
}

interface IotLayout {
    rooms: IotRoom[];
    automations: IotAutomation[];
}

// --- INTERFACCE CARE OS ---
interface CareModuleConfig {
    enabled: boolean;
    sensitivity?: string;
    // [NUOVO v19.0] Elderly Helper Advanced
    inactivity_alert_minutes?: number;
    active_from?: string;
    active_until?: string;
    [key: string]: any;
}

interface CareRule {
    id: string;
    name: string;
    trigger: string;
    conditions: Record<string, any>;
    actions: Array<{ type: string; [key: string]: any }>;
    enabled: boolean;
}

interface CronJob {
    id: string;
    name: string;
    time: string;
    days: string[];
    action: string;
    payload: string;
    enabled: boolean;
}

// [NUOVO v1.3] Interfaccia Trigger Dinamico
interface CareTrigger {
    value: string;
    label: string;
}

interface EmergencyContact {
    email: string;
    phone: string;
}

interface CareConfig {
    modules: {
        baby_monitor: CareModuleConfig;
        elderly_helper: CareModuleConfig;
        pet_monitor: CareModuleConfig;
    };
    zones: any[];
    rules: CareRule[];
    cron_jobs: CronJob[];
    triggers?: CareTrigger[]; // [NUOVO v1.3] Lista dinamica trigger
    emergency_contacts?: EmergencyContact; // [NUOVO v19.0]
}

const DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

// [NUOVO v1.3] Default Triggers se non presenti nel JSON
const DEFAULT_TRIGGERS: CareTrigger[] = [
    { value: "audio_cry", label: "Baby Cry" },
    { value: "audio_bark", label: "Dog Bark" },
    { value: "visual_zone_entry", label: "Zone Entry" },
    { value: "fall_detected", label: "Fall Detected" }
];

export const SmartHomeDialog = ({
  open,
  onOpenChange,
  serverConfig,
}: SmartHomeDialogProps) => {
  const { t } = useTranslation();
  // [NUOVO v1.9] CSS INIETTATO PER SCROLLBAR (DOGMA APPENDICE C)
  const scrollbarStyles = `
    .airis-scrollbar::-webkit-scrollbar {
        width: 8px !important;
        display: block !important;
    }
    .airis-scrollbar::-webkit-scrollbar-thumb {
        background-color: hsl(340 82% 52%) !important;
        border-radius: 10px !important;
    }
    .airis-scrollbar::-webkit-scrollbar-track {
        background: transparent !important;
    }
  `;

  const [layout, setLayout] = useState<IotLayout>({ rooms: [], automations: [] });
  const [logs, setLogs] = useState<string[]>([]);
  
  // --- STATI CARE OS ---
  const [careConfig, setCareConfig] = useState<CareConfig>({
      modules: {
          baby_monitor: { enabled: false },
          elderly_helper: { enabled: false },
          pet_monitor: { enabled: false }
      },
      zones: [],
      rules: [],
      cron_jobs: [],
      triggers: DEFAULT_TRIGGERS // Init con default
  });

  // --- STATI WALKIE TALKIE ---
  const [isRecording, setIsRecording] = useState(false);
  const [targetDeviceId, setTargetDeviceId] = useState<string>("");
  const [hiveDevices, setHiveDevices] = useState<HiveDevice[]>([]);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("dashboard");

  // Stati per nuovi inserimenti
  const [newRoomName, setNewRoomName] = useState("");
  
  // --- [NUOVO v1.3] STATI TRIGGER MANAGER ---
  const [isTriggerManagerOpen, setIsTriggerManagerOpen] = useState(false);
  const [newTriggerLabel, setNewTriggerLabel] = useState("");
  const [newTriggerValue, setNewTriggerValue] = useState("");

  // --- [NUOVO v19.3] STATI ZONE MANAGER ---
  const [isZoneManagerOpen, setIsZoneManagerOpen] = useState(false);
  const [newZoneName, setNewZoneName] = useState("");
  const [newZoneId, setNewZoneId] = useState("");

  // --- [NUOVO v18.0] STATI JARVIS CORTEX ---
  const [blacklist, setBlacklist] = useState<string[]>([]);
  const [newBlacklistWord, setNewBlacklistWord] = useState("");
  const [shadowLog, setShadowLog] = useState<string[]>([]);
  const [patches, setPatches] = useState<PatchRecord[]>([]);
  const [isRollingBack, setIsRollingBack] = useState<string | null>(null);

  // --- [NUOVO v19.2] STATI OPERATIVI JARVIS ---
  const [prudenceValue, setPrudenceValue] = useState<number>(50);
  const [isWorkMode, setIsWorkMode] = useState<boolean>(false);
  const [editingTriggerValue, setEditingTriggerValue] = useState<string | null>(null);

  // --- [NUOVO v20.0] STATI CORTEX AUDIO ---
  const [audioLibrary, setAudioLibrary] = useState<CareAudioClip[]>([]);
  const [isRecordingAudio, setIsRecordingAudio] = useState(false);
  const [recordingBlob, setRecordingBlob] = useState<Blob | null>(null);
  const [ttsText, setTtsText] = useState("");
  const [newClipLabel, setNewClipLabel] = useState("");
  const [newClipCategory, setNewClipCategory] = useState<CareAudioClip['category']>("Custom");
  const [isGeneratingTts, setIsGeneratingTts] = useState(false);
  
  const isPortrait = useIsPortrait();
  const isDraggingPrudenceRef = useRef(false); // [FIX] Anti-bounce per lo slider

  const fetchJarvisData = async () => {
    if (!serverConfig) return;
    const baseUrl = getBaseUrl(serverConfig);
    const headers = getHeaders();
    try {
        const [blRes, slRes, pRes, hRes] = await Promise.all([
            fetch(`${baseUrl}/api/jarvis/blacklist`, { headers }),
            fetch(`${baseUrl}/api/jarvis/shadow-log`, { headers }),
            fetch(`${baseUrl}/api/jarvis/patches`, { headers }),
            fetch(`${baseUrl}/api/heart/status`, { headers }) // Recupera Prudenza e WorkMode
        ]);
        if (blRes.ok) setBlacklist((await blRes.json()).blacklist_windows || []);
        if (slRes.ok) setShadowLog(await slRes.json());
        if (pRes.ok) setPatches(await pRes.json());
        if (hRes.ok) {
            const heart = await hRes.json();
            // [FIX] Aggiorna la prudenza solo se l'utente non la sta modificando manualmente
            if (!isDraggingPrudenceRef.current) {
                setPrudenceValue(heart.prudenza ?? 50);
            }
            setIsWorkMode(heart.work_mode ?? false);
        }
    } catch (e) {
        console.error(t("smart_home.err_fetch_jarvis"), e);
    }
  };

  // --- [NUOVO v19.2] API HANDLERS ---
  const handlePrudenceChange = async (val: number) => {
      setPrudenceValue(val);
      const baseUrl = getBaseUrl(serverConfig);
      try {
          await fetch(`${baseUrl}/api/jarvis/prudenza`, {
              method: 'POST',
              headers: { ...getHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify({ value: val })
          });
      } catch (e) { toast.error(t("smart_home.err_set_prudence")); }
  };

  const handleWorkModeToggle = async (enabled: boolean) => {
      setIsWorkMode(enabled);
      const baseUrl = getBaseUrl(serverConfig);
      try {
          await fetch(`${baseUrl}/api/jarvis/work-mode`, {
              method: 'POST',
              headers: { ...getHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify({ enabled })
          });
          toast.success(enabled ? t("smart_home.jarvis.work_mode_active") : t("smart_home.jarvis.work_mode_disabled"));
      } catch (e) { toast.error(t("smart_home.jarvis.err_work_mode_failed")); }
  };

  const handleUpdateTrigger = async (oldVal: string, newVal: string, newLab: string) => {
      const baseUrl = getBaseUrl(serverConfig);
      try {
          const res = await fetch(`${baseUrl}/api/care/triggers/update`, {
              method: 'POST',
              headers: { ...getHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify({ old_value: oldVal, new_value: newVal, new_label: newLab })
          });
          if (res.ok) {
              toast.success(t("smart_home.toast_trigger_updated"));
              setEditingTriggerValue(null);
              fetchLayout();
          }
      } catch (e) { toast.error(t("smart_home.err_update_trigger")); }
  };

  const fetchLayout = async () => {
    if (!serverConfig) return;
    setIsLoading(true);
    const baseUrl = getBaseUrl(serverConfig);
    const headers = getHeaders();

    try {
      // 1. IoT Layout
      const res = await fetch(`${baseUrl}/api/iot/layout`, { headers });
      if (res.ok) {
        const data = await res.json();
        setLayout(data);
      }

      // 2. Care Config
      const resCare = await fetch(`${baseUrl}/api/care/config`, { headers });
      if (resCare.ok) {
          const data = await resCare.json();
          // Assicura che i trigger esistano, altrimenti usa default
          if (!data.triggers || data.triggers.length === 0) {
              data.triggers = DEFAULT_TRIGGERS;
          }
          // [NUOVO v19.0] Init Contatti Emergenza
          if (!data.emergency_contacts) {
              data.emergency_contacts = { email: "", phone: "" };
          }
          setCareConfig(data);
      }

      // 3. Hive Devices (per Walkie Talkie)
      const resHive = await fetch(`${baseUrl}/api/hive/devices`, { headers });
      if (resHive.ok) {
          const data = await resHive.json();
          const devs = Object.entries(data.devices || {}).map(([id, d]: any) => ({ id, ...d }));
          setHiveDevices(devs);
          if (devs.length > 0 && !targetDeviceId) setTargetDeviceId(devs[0].id);
      }

    } catch (error) {
      console.error(t("smart_home.err_fetch_data_log"), error);
      toast.error(t("smart_home.err_fetch_data"));
    } finally {
      setIsLoading(false);
    }
  };

  const fetchLogs = async () => {
      if (!serverConfig) return;
      const baseUrl = getBaseUrl(serverConfig);
      const headers = getHeaders();
      try {
          const res = await fetch(`${baseUrl}/api/iot/logs`, { headers });
          if (res.ok) {
              const data = await res.json();
              setLogs(data);
          }
      } catch (e) {
          console.error(t("smart_home.err_fetch_iot_logs_log"), e);
      }
  };

  useEffect(() => {
    if (open) {
      fetchLayout();
      fetchLogs();
      fetchJarvisData();
      fetchAudioLibrary(); // [NUOVO v20.0]
      const logInterval = setInterval(() => {
          fetchLogs();
          fetchJarvisData(); // Aggiorna anche i log ombra
      }, 10000);
      return () => clearInterval(logInterval);
    }
  }, [open, serverConfig]);

  // --- [NUOVO v18.0] HANDLERS JARVIS CORTEX ---
  const handleAddBlacklist = async () => {
      if (!newBlacklistWord.trim() || !serverConfig) return;
      const newBl = [...blacklist, newBlacklistWord.trim()];
      const baseUrl = getBaseUrl(serverConfig);
      try {
          await fetch(`${baseUrl}/api/jarvis/blacklist`, {
              method: 'POST',
              headers: { ...getHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify({ windows: newBl })
          });
          setBlacklist(newBl);
          setNewBlacklistWord("");
          toast.success(t("smart_home.toast_blacklist_added"));
      } catch (e) {
          toast.error(t("smart_home.err_update_blacklist"));
      }
  };

  const handleRemoveBlacklist = async (word: string) => {
      if (!serverConfig) return;
      const newBl = blacklist.filter(w => w !== word);
      const baseUrl = getBaseUrl(serverConfig);
      try {
          await fetch(`${baseUrl}/api/jarvis/blacklist`, {
              method: 'POST',
              headers: { ...getHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify({ windows: newBl })
          });
          setBlacklist(newBl);
          toast.success(t("smart_home.toast_blacklist_removed"));
      } catch (e) {
          toast.error(t("smart_home.err_update_blacklist"));
      }
  };

  const handleRollback = async (patchId: string) => {
      if (!serverConfig || !confirm(t("smart_home.jarvis.rollback_confirm"))) return;
      setIsRollingBack(patchId);
      const baseUrl = getBaseUrl(serverConfig);
      try {
          const res = await fetch(`${baseUrl}/api/jarvis/patches/rollback`, {
              method: 'POST',
              headers: { ...getHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify({ patch_id: patchId })
          });
          if (!res.ok) {
              const err = await res.json();
              throw new Error(err.detail || t("smart_home.jarvis.err_rollback_failed"));
          }
          toast.success(t("smart_home.toast_patch_rolled_back"));
          fetchJarvisData();
      } catch (e: any) {
          toast.error(t("smart_home.jarvis.err_rollback_failed"), { description: e.message });
      } finally {
          setIsRollingBack(null);
      }
  };

  // --- [NUOVO v19.3] ZONE MANAGER HANDLERS ---
  const handleAddZone = () => {
      if (!newZoneName.trim() || !newZoneId.trim()) {
          toast.error(t("smart_home.care.err_zone_required"));
          return;
      }
      const newZone = { 
          id: newZoneId.trim(), 
          name: newZoneName.trim(), 
          type: "safe", 
          coordinates: [0,0,0,0], 
          description: "Custom Zone" 
      };
      const updatedZones = [...careConfig.zones, newZone];
      handleSaveCareConfig({ ...careConfig, zones: updatedZones });
      setNewZoneName("");
      setNewZoneId("");
      toast.success(t("smart_home.care.toast_zone_added"));
  };

  const handleDeleteZone = (zoneId: string) => {
      const updatedZones = careConfig.zones.filter(z => z.id !== zoneId);
      handleSaveCareConfig({ ...careConfig, zones: updatedZones });
      toast.success(t("smart_home.toast_zone_removed"));
  };

  // ---[NUOVO v20.0] CORTEX AUDIO HANDLERS ---
  const fetchAudioLibrary = async () => {
      if (!serverConfig) return;
      const baseUrl = getBaseUrl(serverConfig);
      try {
          const res = await fetch(`${baseUrl}/api/care/audio`, { headers: getHeaders() });
          if (res.ok) setAudioLibrary(await res.json());
      } catch (e) { console.error(t("smart_home.err_fetch_audio_library"), e); }
  };

  const startRecording = async () => {
      try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const recorder = new MediaRecorder(stream);
          mediaRecorderRef.current = recorder;
          audioChunksRef.current =[];
          recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
          recorder.onstop = () => {
              const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
              setRecordingBlob(blob);
              stream.getTracks().forEach(t => t.stop());
          };
          recorder.start();
          setIsRecordingAudio(true);
      } catch (e) { toast.error(t("smart_home.err_mic_denied")); }
  };

  const stopRecording = () => {
      if (mediaRecorderRef.current && isRecordingAudio) {
          mediaRecorderRef.current.stop();
          setIsRecordingAudio(false);
      }
  };

  const uploadClip = async () => {
      if (!recordingBlob || !newClipLabel.trim() || !serverConfig) return;
      const formData = new FormData();
      formData.append("file", recordingBlob, "clip.webm");
      formData.append("label", newClipLabel);
      formData.append("category", newClipCategory);
      
      try {
          const baseUrl = getBaseUrl(serverConfig);
          const res = await fetch(`${baseUrl}/api/care/audio/upload`, {
              method: 'POST',
              headers: { "ngrok-skip-browser-warning": "true" }, // No getHeaders per FormData
              body: formData
          });
          if (res.ok) {
              toast.success(t("smart_home.toast_clip_saved"));
              setRecordingBlob(null);
              setNewClipLabel("");
              fetchAudioLibrary();
          }
      } catch (e) { toast.error(t("smart_home.err_upload_failed")); }
  };

  const generateTtsClip = async () => {
      if (!ttsText.trim() || !newClipLabel.trim() || !serverConfig) return;
      setIsGeneratingTts(true);
      const baseUrl = getBaseUrl(serverConfig);
      try {
          const res = await fetch(`${baseUrl}/api/care/audio/generate`, {
              method: 'POST',
              headers: { ...getHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify({ text: ttsText, label: newClipLabel, category: newClipCategory })
          });
          if (res.ok) {
              toast.success(t("smart_home.audio_library.toast_ai_generated"));
              setTtsText("");
              setNewClipLabel("");
              fetchAudioLibrary();
          }
      } catch (e) { toast.error(t("smart_home.audio_library.err_generation_failed")); }
      finally { setIsGeneratingTts(false); }
  };

  const deleteClip = async (id: string) => {
      if (!serverConfig || !confirm(t("smart_home.confirm_delete_clip"))) return;
      const baseUrl = getBaseUrl(serverConfig);
      try {
          const res = await fetch(`${baseUrl}/api/care/audio/${id}`, {
              method: 'DELETE',
              headers: getHeaders()
          });
          if (res.ok) {
              toast.success(t("smart_home.toast_clip_removed"));
              fetchAudioLibrary();
          }
      } catch (e) { toast.error(t("smart_home.err_delete_failed")); }
  };

  const playPreview = (path: string) => {
      const baseUrl = getBaseUrl(serverConfig);
      const audio = new Audio(`${baseUrl}/${path}`);
      audio.play().catch(e => toast.error(t("smart_home.err_playback_failed")));
  };

  const handleSaveLayout = async (updatedLayout: IotLayout) => {
      if (!serverConfig) return;
      setIsSaving(true);
      const baseUrl = getBaseUrl(serverConfig);
      const headers = { ...getHeaders(), "Content-Type": "application/json" };

      try {
          const res = await fetch(`${baseUrl}/api/iot/layout`, {
              method: 'POST',
              headers,
              body: JSON.stringify(updatedLayout)
          });
          if (res.ok) {
              setLayout(updatedLayout);
              toast.success(t("smart_home.toast_layout_updated"));
          }
      } catch (error) {
          toast.error(t("smart_home.err_save_layout"));
      } finally {
          setIsSaving(false);
      }
  };

  const handleExecuteCommand = async (deviceId: string, action: string, value?: any) => {
      if (!serverConfig) return;
      const baseUrl = getBaseUrl(serverConfig);
      const headers = { ...getHeaders(), "Content-Type": "application/json" };

      try {
          const res = await fetch(`${baseUrl}/api/iot/execute`, {
              method: 'POST',
              headers,
              body: JSON.stringify({ device_id: deviceId, action, value })
          });
          if (res.ok) {
              toast.success(t("smart_home.toast_command_transmitted"));
              setTimeout(fetchLogs, 2000);
          }
      } catch (error) {
          toast.error(t("smart_home.err_transmission_failed"));
      }
  };

  // --- GESTIONE STANZE ---
  const addRoom = () => {
      if (!newRoomName.trim()) return;
      const newRoom: IotRoom = {
          id: crypto.randomUUID(),
          name: newRoomName.trim(),
          devices: []
      };
      const newLayout = { ...layout, rooms: [...layout.rooms, newRoom] };
      handleSaveLayout(newLayout);
      setNewRoomName("");
  };

  const deleteRoom = (roomId: string) => {
      if (!confirm(t("smart_home.confirm_delete_room"))) return;
      const newLayout = { ...layout, rooms: layout.rooms.filter(r => r.id !== roomId) };
      handleSaveLayout(newLayout);
  };

  // --- GESTIONE DISPOSITIVI ---
  const addDevice = (roomId: string) => {
      const newDevice: IotDevice = {
          id: crypto.randomUUID(),
          name: "New Device",
          type: 'light',
          ip: "192.168.1.X",
          protocol: 'http_get',
          commands: { "on": "/api/on", "off": "/api/off" }
      };
      const newLayout = {
          ...layout,
          rooms: layout.rooms.map(r => r.id === roomId ? { ...r, devices: [...r.devices, newDevice] } : r)
      };
      handleSaveLayout(newLayout);
  };

  const updateDevice = (roomId: string, deviceId: string, updates: Partial<IotDevice>) => {
      const newLayout = {
          ...layout,
          rooms: layout.rooms.map(r => r.id === roomId ? {
              ...r,
              devices: r.devices.map(d => d.id === deviceId ? { ...d, ...updates } : d)
          } : r)
      };
      handleSaveLayout(newLayout);
  };

  const deleteDevice = (roomId: string, deviceId: string) => {
      const newLayout = {
          ...layout,
          rooms: layout.rooms.map(r => r.id === roomId ? {
              ...r,
              devices: r.devices.filter(d => d.id !== deviceId)
          } : r)
      };
      handleSaveLayout(newLayout);
  };

  // --- GESTIONE AUTOMATISMI ---
  const addAutomation = () => {
      const newAuto: IotAutomation = {
          id: crypto.randomUUID(),
          name: "New Automation",
          deviceId: "",
          action: "",
          time: "08:00",
          days: ["Mon", "Tue", "Wed", "Thu", "Fri"],
          enabled: true
      };
      const newLayout = { ...layout, automations: [...layout.automations, newAuto] };
      handleSaveLayout(newLayout);
  };

  const updateAutomation = (id: string, updates: Partial<IotAutomation>) => {
      const newLayout = {
          ...layout,
          automations: layout.automations.map(a => a.id === id ? { ...a, ...updates } : a)
      };
      handleSaveLayout(newLayout);
  };

  const deleteAutomation = (id: string) => {
      const newLayout = { ...layout, automations: layout.automations.filter(a => a.id !== id) };
      handleSaveLayout(newLayout);
  };

  const toggleDay = (autoId: string, day: string) => {
      const auto = layout.automations.find(a => a.id === autoId);
      if (!auto) return;
      const newDays = auto.days.includes(day) 
          ? auto.days.filter(d => d !== day) 
          : [...auto.days, day];
      updateAutomation(autoId, { days: newDays });
  };

  const getDeviceIcon = (type: string) => {
      switch (type) {
          case 'light': return <Lightbulb className="w-5 h-5" />;
          case 'tv': return <Tv className="w-5 h-5" />;
          case 'climate': return <Thermometer className="w-5 h-5" />;
          case 'switch': return <Zap className="w-5 h-5" />;
          default: return <Settings className="w-5 h-5" />;
      }
  };

  // Helper per trovare un dispositivo nel layout
  const findDeviceById = (id: string) => {
      for (const room of layout.rooms) {
          const dev = room.devices.find(d => d.id === id);
          if (dev) return dev;
      }
      return null;
  };

  // --- CARE OS LOGIC ---
  const handleSaveCareConfig = async (updatedConfig: CareConfig) => {
      if (!serverConfig) return;
      setIsSaving(true);
      const baseUrl = getBaseUrl(serverConfig);
      const headers = { ...getHeaders(), "Content-Type": "application/json" };

      try {
          const res = await fetch(`${baseUrl}/api/care/config`, {
              method: 'POST',
              headers,
              body: JSON.stringify(updatedConfig)
          });
          if (res.ok) {
              setCareConfig(updatedConfig);
              toast.success(t("smart_home.toast_care_updated"));
          }
      } catch (error) {
          toast.error(t("smart_home.err_save_care_config"));
      } finally {
          setIsSaving(false);
      }
  };

  const toggleModule = (moduleName: keyof CareConfig['modules']) => {
      const newConfig = { ...careConfig };
      newConfig.modules[moduleName].enabled = !newConfig.modules[moduleName].enabled;
      handleSaveCareConfig(newConfig);
  };

  const addRule = () => {
      const newRule: CareRule = {
          id: crypto.randomUUID(), name: "New Rule", trigger: "audio_cry",
          conditions: {}, actions: [{ type: "notification", message: "Alert!" }], enabled: true
      };
      handleSaveCareConfig({ ...careConfig, rules: [...careConfig.rules, newRule] });
  };

  const updateRule = (id: string, updates: Partial<CareRule>) => {
      handleSaveCareConfig({
          ...careConfig,
          rules: careConfig.rules.map(r => r.id === id ? { ...r, ...updates } : r)
      });
  };

  const deleteRule = (id: string) => {
      handleSaveCareConfig({ ...careConfig, rules: careConfig.rules.filter(r => r.id !== id) });
  };

  const addCronJob = () => {
      const newJob: CronJob = {
          id: crypto.randomUUID(), name: "New Routine", time: "08:00",
          days: ["Mon", "Tue", "Wed", "Thu", "Fri"], action: "tts_speak", payload: "Time for medicine.", enabled: true
      };
      handleSaveCareConfig({ ...careConfig, cron_jobs: [...careConfig.cron_jobs, newJob] });
  };

  const updateCronJob = (id: string, updates: Partial<CronJob>) => {
      handleSaveCareConfig({
          ...careConfig,
          cron_jobs: careConfig.cron_jobs.map(j => j.id === id ? { ...j, ...updates } : j)
      });
  };

  const deleteCronJob = (id: string) => {
      handleSaveCareConfig({ ...careConfig, cron_jobs: careConfig.cron_jobs.filter(j => j.id !== id) });
  };

  const toggleCronDay = (jobId: string, day: string) => {
      const job = careConfig.cron_jobs.find(j => j.id === jobId);
      if (!job) return;
      const newDays = job.days.includes(day) ? job.days.filter(d => d !== day) : [...job.days, day];
      updateCronJob(jobId, { days: newDays });
  };

  // --- [NUOVO v1.3] TRIGGER MANAGER LOGIC ---
  const handleAddTrigger = () => {
      if (!newTriggerLabel.trim() || !newTriggerValue.trim()) {
          toast.error(t("smart_home.err_label_value_required"));
          return;
      }
      
      const newTrigger = { label: newTriggerLabel.trim(), value: newTriggerValue.trim() };
      const updatedTriggers =[...(careConfig.triggers || []), newTrigger];
      
      handleSaveCareConfig({ ...careConfig, triggers: updatedTriggers });
      setNewTriggerLabel("");
      setNewTriggerValue("");
      toast.success(t("smart_home.toast_trigger_added"));
  };

  const handleDeleteTrigger = (value: string) => {
      const updatedTriggers = (careConfig.triggers ||[]).filter(t => t.value !== value);
      handleSaveCareConfig({ ...careConfig, triggers: updatedTriggers });
      toast.success(t("smart_home.toast_trigger_removed"));
  };

  // --- WALKIE TALKIE LOGIC ---
  const startIntercom = async () => {
      if (!targetDeviceId) { toast.error(t("smart_home.err_select_target_device")); return; }
      try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const recorder = new MediaRecorder(stream);
          mediaRecorderRef.current = recorder;
          audioChunksRef.current =[];
          recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
          recorder.onstop = async () => {
              const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
              await sendIntercomAudio(audioBlob);
              stream.getTracks().forEach(track => track.stop());
          };
          recorder.start();
          setIsRecording(true);
      } catch (err) { console.error(err); toast.error(t("smart_home.err_mic_denied")); }
  };

  const stopIntercom = () => {
      if (mediaRecorderRef.current && isRecording) {
          mediaRecorderRef.current.stop();
          setIsRecording(false);
      }
  };

  const sendIntercomAudio = async (audioBlob: Blob) => {
      if (!serverConfig) return;
      const formData = new FormData();
      formData.append("device_id", targetDeviceId);
      formData.append("audio", audioBlob, "intercom.webm");
      try {
          const baseUrl = getBaseUrl(serverConfig);
          await fetch(`${baseUrl}/api/hive/intercom`, {
              method: 'POST', body: formData, headers: { "ngrok-skip-browser-warning": "true" }
          });
          toast.success(t("smart_home.toast_voice_sent"));
      } catch (error) { toast.error(t("smart_home.err_intercom_failed")); }
  };

  return (
    <>
    <Dialog open={open} onOpenChange={onOpenChange}>
      {/* [FIX v1.9] Altezza fissa h-[90vh] per garantire lo scroll ed evitare il collasso */}
      {/* [FIX v19.3] Allargato a max-w-7xl per ospitare i tab su una riga */}
      <DialogContent className="sm:max-w-7xl h-[90vh] flex flex-col overflow-hidden p-0 gap-0 bg-background">
        <style>{scrollbarStyles}</style>
        <DialogHeader className="p-6 pb-2 bg-muted/10 border-b shrink-0">
          <DialogTitle className="flex items-center gap-2 text-blue-400">
              <Home className="w-6 h-6" />
              {t("smart_home.title")}
          </DialogTitle>
          <DialogDescription>
            {t("smart_home.description")}
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden min-h-0">
            
            <div className="px-6 py-2 shrink-0">
                {isPortrait ? (
                    <div className="space-y-1">
                        <Label className="text-[10px] uppercase text-muted-foreground font-bold tracking-widest">Section</Label>
                        <Select value={activeTab} onValueChange={setActiveTab}>
                            <SelectTrigger className="w-full bg-muted/50 border-primary/20">
                                <SelectValue placeholder="Select section" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="dashboard">{t("smart_home.tabs.dashboard")}</SelectItem>
								<SelectItem value="map">{t("smart_home.tabs.rooms")}</SelectItem>
								<SelectItem value="care_monitor">{t("smart_home.tabs.care_monitor")}</SelectItem>
								<SelectItem value="care_rules">{t("smart_home.tabs.rules")}</SelectItem>
								<SelectItem value="care_cron">{t("smart_home.tabs.cron")}</SelectItem>
								<SelectItem value="walkie_talkie">{t("smart_home.tabs.walkie_talkie")}</SelectItem>
								<SelectItem value="audio_library">{t("smart_home.tabs.audio_library")}</SelectItem>
								<SelectItem value="logs">{t("smart_home.tabs.logs")}</SelectItem>
								{/* --- [NUOVO v18.0] JARVIS TABS --- */}
								<SelectItem value="mindset">{t("smart_home.tabs.mindset")}</SelectItem>
								<SelectItem value="shadow">{t("smart_home.tabs.shadow")}</SelectItem>
								<SelectItem value="architect">{t("smart_home.tabs.architect")}</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                ) : (
                    /* [FIX v1.9] TabsList con stile "Pillola" ripristinato (bg-muted/60 p-1) */
                    /* [FIX v19.3] flex-nowrap e overflow-x-auto per garantire singola riga */
                    <TabsList className="w-full flex flex-nowrap justify-start h-auto p-1 bg-muted/60 rounded-lg gap-1 overflow-x-auto no-scrollbar">
                        <TabsTrigger value="dashboard" className="whitespace-nowrap">{t("smart_home.tabs.dashboard")}</TabsTrigger>
                        <TabsTrigger value="map" className="whitespace-nowrap">{t("smart_home.tabs.rooms")}</TabsTrigger>
                        <TabsTrigger value="care_monitor" className="text-pink-400 whitespace-nowrap">{t("smart_home.tabs.care_monitor")}</TabsTrigger>
                        <TabsTrigger value="care_rules" className="text-pink-400 whitespace-nowrap">{t("smart_home.tabs.rules")}</TabsTrigger>
                        <TabsTrigger value="care_cron" className="text-pink-400 whitespace-nowrap">{t("smart_home.tabs.cron")}</TabsTrigger>
                        <TabsTrigger value="walkie_talkie" className="text-yellow-400 whitespace-nowrap">{t("smart_home.tabs.walkie_talkie")}</TabsTrigger>
                        <TabsTrigger value="audio_library" className="text-blue-400 whitespace-nowrap">{t("smart_home.tabs.audio_library")}</TabsTrigger>
                        <TabsTrigger value="logs" className="whitespace-nowrap">{t("smart_home.tabs.logs")}</TabsTrigger>
                        {/* --- [NUOVO v18.0] JARVIS TABS --- */}
                        <TabsTrigger value="mindset" className="text-purple-400 whitespace-nowrap">{t("smart_home.tabs.mindset")}</TabsTrigger>
                        <TabsTrigger value="shadow" className="text-purple-400 whitespace-nowrap">{t("smart_home.tabs.shadow")}</TabsTrigger>
                        <TabsTrigger value="architect" className="text-purple-400 whitespace-nowrap">{t("smart_home.tabs.architect")}</TabsTrigger>
                    </TabsList>
                )}
            </div>

            {/* [FIX v1.9] PROTOCOLLO FLEXBOX RIGIDO APPLICATO A TUTTI I TABSCONTENT */}
            
            <TabsContent value="dashboard" className="flex-1 min-h-0 m-0 data-[state=active]:flex data-[state=active]:flex-col overflow-hidden">
                <div className="flex-1 relative min-h-0">
                    <div className="absolute inset-0 overflow-y-scroll airis-scrollbar p-6">
                        {layout.rooms.length === 0 ? (
                            <div className="text-center py-20 text-muted-foreground">{t("smart_home.iot.no_rooms")}</div>
                        ) : (
                            <div className="space-y-8 pb-6">
                                {layout.rooms.map(room => (
                                    <div key={room.id} className="space-y-4">
                                        <h3 className="text-lg font-bold border-b border-white/10 pb-1 flex items-center gap-2">
                                            <Home className="w-4 h-4 text-primary" /> {room.name}
                                        </h3>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                                            {room.devices.map(device => (
                                                <Card key={device.id} className="bg-card/50 border-white/5 hover:border-primary/20 transition-all">
                                                    <CardHeader className="p-4 pb-2">
                                                        <div className="flex justify-between items-start">
                                                            <div className="flex items-center gap-2">
                                                                <div className="p-2 rounded-lg bg-primary/10 text-primary">{getDeviceIcon(device.type)}</div>
                                                                <div>
                                                                    <CardTitle className="text-sm font-bold">{device.name}</CardTitle>
                                                                    <CardDescription className="text-[10px] font-mono">{device.ip}</CardDescription>
                                                                </div>
                                                            </div>
                                                            <Badge variant="outline" className="text-[9px] uppercase">{device.protocol}</Badge>
                                                        </div>
                                                    </CardHeader>
                                                    <CardContent className="p-4 pt-2 flex flex-wrap gap-2">
                                                        {Object.keys(device.commands).map(cmd => (
                                                            <Button key={cmd} size="sm" variant={cmd === 'on' ? 'default' : 'secondary'} className="h-8 text-xs px-3" onClick={() => handleExecuteCommand(device.id, cmd)}>{cmd.toUpperCase()}</Button>
                                                        ))}
                                                    </CardContent>
                                                </Card>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </TabsContent>

            <TabsContent value="map" className="flex-1 min-h-0 m-0 data-[state=active]:flex data-[state=active]:flex-col overflow-hidden">
                <div className="px-6 py-2 shrink-0 flex gap-2">
                    <Input placeholder={t("smart_home.iot.room_name")} value={newRoomName} onChange={(e) => setNewRoomName(e.target.value)} />
                    <Button onClick={addRoom} disabled={!newRoomName.trim()}><Plus className="w-4 h-4 mr-2" /> {t("smart_home.iot.add_room")}</Button>
                </div>
                <div className="flex-1 relative min-h-0">
                    <div className="absolute inset-0 overflow-y-scroll airis-scrollbar p-6">
                        <Accordion type="multiple" className="space-y-4">
                            {layout.rooms.map(room => (
                                <AccordionItem key={room.id} value={room.id} className="border rounded-lg bg-card px-4">
                                    <div className="flex items-center justify-between">
                                        <AccordionTrigger className="hover:no-underline py-4">
                                            <span className="font-bold text-primary">{room.name}</span>
                                            <span className="ml-4 text-xs text-muted-foreground">({room.devices.length} devices)</span>
                                        </AccordionTrigger>
                                        <Button variant="ghost" size="icon" className="text-destructive" onClick={() => deleteRoom(room.id)}><Trash2 className="w-4 h-4" /></Button>
                                    </div>
                                    <AccordionContent className="pb-4 space-y-4">
                                        {room.devices.map(device => (
                                            <div key={device.id} className="p-4 border rounded-lg bg-muted/20 space-y-4 relative group">
                                                <Button variant="ghost" size="icon" className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 text-destructive" onClick={() => deleteDevice(room.id, device.id)}><Trash2 className="w-4 h-4" /></Button>
                                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                                    <div className="space-y-1"><Label className="text-[10px] uppercase">{t("smart_home.iot.device_name")}</Label><Input value={device.name} onChange={(e) => updateDevice(room.id, device.id, { name: e.target.value })} /></div>
                                                    <div className="space-y-1"><Label className="text-[10px] uppercase">{t("smart_home.iot.device_type")}</Label><Select value={device.type} onValueChange={(v: any) => updateDevice(room.id, device.id, { type: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="light">Light</SelectItem><SelectItem value="tv">TV</SelectItem><SelectItem value="climate">Climate</SelectItem><SelectItem value="switch">Switch</SelectItem><SelectItem value="other">Other</SelectItem></SelectContent></Select></div>
                                                    <div className="space-y-1"><Label className="text-[10px] uppercase">{t("smart_home.iot.device_ip")}</Label><Input value={device.ip} onChange={(e) => updateDevice(room.id, device.id, { ip: e.target.value })} /></div>
                                                    <div className="space-y-1"><Label className="text-[10px] uppercase">{t("smart_home.iot.device_protocol")}</Label><Select value={device.protocol} onValueChange={(v: any) => updateDevice(room.id, device.id, { protocol: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="http_get">HTTP GET</SelectItem><SelectItem value="http_post">HTTP POST</SelectItem><SelectItem value="ha">Home Assistant</SelectItem><SelectItem value="mqtt">MQTT</SelectItem></SelectContent></Select></div>
                                                </div>
                                                <div className="space-y-2">
                                                    <Label className="text-[10px] uppercase">{t("smart_home.iot.commands")}</Label>
                                                    {Object.entries(device.commands).map(([action, path]) => (
                                                        <div key={action} className="flex gap-2">
                                                            <Input className="w-1/3 font-bold" value={action} readOnly />
                                                            <Input className="flex-1 font-mono text-xs" value={path} onChange={(e) => { const newCmds = { ...device.commands, [action]: e.target.value }; updateDevice(room.id, device.id, { commands: newCmds }); }} />
                                                            <Button variant="outline" size="sm" onClick={() => handleExecuteCommand(device.id, action)}>{t("smart_home.iot.test")}</Button>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                        <Button variant="outline" className="w-full border-dashed" onClick={() => addDevice(room.id)}><Plus className="w-4 h-4 mr-2" /> {t("smart_home.iot.add_device_btn")}</Button>
                                    </AccordionContent>
                                </AccordionItem>
                            ))}
                        </Accordion>
                    </div>
                </div>
            </TabsContent>

            <TabsContent value="care_monitor" className="flex-1 min-h-0 m-0 data-[state=active]:flex data-[state=active]:flex-col overflow-hidden">
                <div className="px-6 py-2 shrink-0 flex justify-end">
                    <Button variant="outline" size="sm" onClick={() => setIsZoneManagerOpen(true)}>
                        <List className="w-4 h-4 mr-2" /> {t("smart_home.care.manage_zones")}
                    </Button>
                </div>
                <div className="flex-1 relative min-h-0">
                    <div className="absolute inset-0 overflow-y-scroll airis-scrollbar p-6">
                        
                        {/* [NUOVO v19.0] GLOBAL EMERGENCY CONTACTS */}
                        <Card className="border-2 border-red-500/20 bg-red-500/5 mb-6">
                            <CardHeader className="pb-2">
                                <CardTitle className="flex items-center gap-2 text-red-400 text-base">
                                    <ShieldAlert className="w-5 h-5" /> {t("smart_home.care.emergency_contacts")}
                                </CardTitle>
                                <CardDescription className="text-xs">
                                    {t("smart_home.care.emergency_desc")}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-1">
                                    <Label className="text-[10px] uppercase text-muted-foreground">{t("smart_home.care.email")}</Label>
                                    <Input 
                                        placeholder="family@example.com" 
                                        className="h-8 text-xs bg-background/50"
                                        value={careConfig.emergency_contacts?.email || ""}
                                        onChange={(e) => {
                                            const newConfig = { ...careConfig };
                                            if (!newConfig.emergency_contacts) newConfig.emergency_contacts = { email: "", phone: "" };
                                            newConfig.emergency_contacts.email = e.target.value;
                                            setCareConfig(newConfig);
                                        }}
                                        onBlur={() => handleSaveCareConfig(careConfig)}
                                    />
                                </div>
                                <div className="space-y-1">
                                    <Label className="text-[10px] uppercase text-muted-foreground">{t("smart_home.care.phone")}</Label>
                                    <Input 
                                        placeholder="+39 333..." 
                                        className="h-8 text-xs bg-background/50"
                                        value={careConfig.emergency_contacts?.phone || ""}
                                        onChange={(e) => {
                                            const newConfig = { ...careConfig };
                                            if (!newConfig.emergency_contacts) newConfig.emergency_contacts = { email: "", phone: "" };
                                            newConfig.emergency_contacts.phone = e.target.value;
                                            setCareConfig(newConfig);
                                        }}
                                        onBlur={() => handleSaveCareConfig(careConfig)}
                                    />
                                </div>
                            </CardContent>
                        </Card>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {/* BABY MONITOR ADVANCED */}
                            <Card className={cn("border-2 transition-all", careConfig.modules.baby_monitor.enabled ? "border-pink-400 bg-pink-500/5" : "border-border")}>
                                <CardHeader className="pb-2">
                                    <div className="flex justify-between items-center">
                                        <CardTitle className="flex items-center gap-2"><Baby className="w-5 h-5" /> {t("smart_home.care.baby_monitor")}</CardTitle>
                                        <Switch checked={careConfig.modules.baby_monitor.enabled} onCheckedChange={() => toggleModule('baby_monitor')} />
                                    </div>
                                    <CardDescription>Cry & Posture Detection</CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    <div className="space-y-1">
                                            <Label className="text-[10px] uppercase text-muted-foreground">{t("smart_home.care.sensitivity")}</Label>
                                            <Select 
                                                value={careConfig.modules.baby_monitor.sensitivity || "high"}
                                                onValueChange={(v) => {
                                                    const newConfig = { ...careConfig };
                                                    newConfig.modules.baby_monitor.sensitivity = v;
                                                    setCareConfig(newConfig);
                                                    handleSaveCareConfig(newConfig);
                                                }}
                                            >
                                                <SelectTrigger className="h-8 text-xs bg-background/50"><SelectValue /></SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="low">{t("smart_home.care.low")}</SelectItem>
                                                    <SelectItem value="medium">{t("smart_home.care.medium")}</SelectItem>
                                                    <SelectItem value="high">{t("smart_home.care.high")}</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                    <div className="grid grid-cols-2 gap-2">
                                        <div className="space-y-1">
                                            <Label className="text-[10px] uppercase text-muted-foreground">{t("smart_home.care.active_from")}</Label>
                                            <Input type="time" className="h-8 text-xs bg-background/50" value={careConfig.modules.baby_monitor.active_from || "00:00"} onChange={(e) => { const newConfig = { ...careConfig }; newConfig.modules.baby_monitor.active_from = e.target.value; setCareConfig(newConfig); }} onBlur={() => handleSaveCareConfig(careConfig)} />
                                        </div>
                                        <div className="space-y-1">
                                            <Label className="text-[10px] uppercase text-muted-foreground">{t("smart_home.care.until")}</Label>
                                            <Input type="time" className="h-8 text-xs bg-background/50" value={careConfig.modules.baby_monitor.active_until || "23:59"} onChange={(e) => { const newConfig = { ...careConfig }; newConfig.modules.baby_monitor.active_until = e.target.value; setCareConfig(newConfig); }} onBlur={() => handleSaveCareConfig(careConfig)} />
                                        </div>
                                    </div>
                                    <div className="pt-2 border-t border-white/5 space-y-2">
                                        <Label className="text-[10px] font-bold uppercase text-blue-400">{t("smart_home.care.safe_zone")}</Label>
                                        <Select value={careConfig.modules.baby_monitor.safe_zone_id || "none"} onValueChange={(v) => { const newConfig = { ...careConfig }; newConfig.modules.baby_monitor.safe_zone_id = v === "none" ? null : v; handleSaveCareConfig(newConfig); }}>
                                            <SelectTrigger className="h-7 text-[10px] bg-background/30"><SelectValue placeholder={t("smart_home.care.select_safe_zone")} /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="none">{t("smart_home.care.no_exclusion")}</SelectItem>
                                                {careConfig.zones.map(z => (<SelectItem key={z.id} value={z.id}>{z.name}</SelectItem>))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </CardContent>
                            </Card>
                            
                            <Card className={cn("border-2 transition-all", careConfig.modules.elderly_helper.enabled ? "border-blue-400 bg-blue-500/5" : "border-border")}>
                                <CardHeader className="pb-2">
                                    <div className="flex justify-between items-center">
                                        <CardTitle className="flex items-center gap-2"><User className="w-5 h-5" /> {t("smart_home.care.elderly_helper")}</CardTitle>
                                        <Switch checked={careConfig.modules.elderly_helper.enabled} onCheckedChange={() => toggleModule('elderly_helper')} />
                                    </div>
                                    <CardDescription>Fall Detection & Inactivity</CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    <div className="space-y-1">
                                            <Label className="text-[10px] uppercase text-muted-foreground">{t("smart_home.care.inactivity_alert")}</Label>
                                            <Input 
                                                type="number" 
                                                className="h-8 text-xs bg-background/50" 
                                                value={careConfig.modules.elderly_helper.inactivity_alert_minutes || 120} 
                                                onChange={(e) => {
                                                    const val = parseInt(e.target.value) || 120;
                                                    const newConfig = { ...careConfig };
                                                    newConfig.modules.elderly_helper.inactivity_alert_minutes = val;
                                                    setCareConfig(newConfig);
                                                }}
                                                onBlur={() => handleSaveCareConfig(careConfig)}
                                            />
                                        </div>
                                    <div className="grid grid-cols-2 gap-2">
                                        <div className="space-y-1">
                                            <Label className="text-[10px] uppercase text-muted-foreground">{t("smart_home.care.active_from")}</Label>
                                            <Input 
                                                type="time" 
                                                className="h-8 text-xs bg-background/50" 
                                                value={careConfig.modules.elderly_helper.active_from || "08:00"} 
                                                onChange={(e) => {
                                                    const newConfig = { ...careConfig };
                                                    newConfig.modules.elderly_helper.active_from = e.target.value;
                                                    setCareConfig(newConfig);
                                                }}
                                                onBlur={() => handleSaveCareConfig(careConfig)}
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <Label className="text-[10px] uppercase text-muted-foreground">{t("smart_home.care.until")}</Label>
                                            <Input 
                                                type="time" 
                                                className="h-8 text-xs bg-background/50" 
                                                value={careConfig.modules.elderly_helper.active_until || "22:00"} 
                                                onChange={(e) => {
                                                    const newConfig = { ...careConfig };
                                                    newConfig.modules.elderly_helper.active_until = e.target.value;
                                                    setCareConfig(newConfig);
                                                }}
                                                onBlur={() => handleSaveCareConfig(careConfig)}
                                            />
                                        </div>
                                    </div>

                                    <div className="pt-2 border-t border-white/5 space-y-2">
                                        <Label className="text-[10px] font-bold uppercase text-blue-400">{t("smart_home.care.safe_zone")}</Label>
                                        <div className="grid grid-cols-1 gap-2">
                                            <Select 
                                                value={careConfig.modules.elderly_helper.safe_zone_id || "none"}
                                                onValueChange={(v) => {
                                                    const newConfig = { ...careConfig };
                                                    newConfig.modules.elderly_helper.safe_zone_id = v === "none" ? null : v;
                                                    handleSaveCareConfig(newConfig);
                                                }}
                                            >
                                                <SelectTrigger className="h-7 text-[10px] bg-background/30">
                                                    <SelectValue placeholder={t("smart_home.care.select_safe_zone")} />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="none">{t("smart_home.care.no_exclusion")}</SelectItem>
                                                    {careConfig.zones.map(z => (
                                                        <SelectItem key={z.id} value={z.id}>{z.name}</SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                            {careConfig.modules.elderly_helper.safe_zone_id && (
                                                <div className="flex items-center gap-2">
                                                    <Clock className="w-3 h-3 text-muted-foreground" />
                                                    <Input 
                                                        placeholder={t("smart_home.care.exclusion_time")} 
                                                        className="h-7 text-[10px] bg-background/30"
                                                        value={careConfig.modules.elderly_helper.safe_zone_time || ""}
                                                        onChange={(e) => {
                                                            const newConfig = { ...careConfig };
                                                            newConfig.modules.elderly_helper.safe_zone_time = e.target.value;
                                                            setCareConfig(newConfig);
                                                        }}
                                                        onBlur={() => handleSaveCareConfig(careConfig)}
                                                    />
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>

                            <Card className={cn("border-2 transition-all", careConfig.modules.pet_monitor.enabled ? "border-yellow-400 bg-yellow-500/5" : "border-border")}>
                                <CardHeader className="pb-2">
                                    <div className="flex justify-between items-center">
                                        <CardTitle className="flex items-center gap-2"><Dog className="w-5 h-5" /> {t("smart_home.care.pet_monitor")}</CardTitle>
                                        <Switch checked={careConfig.modules.pet_monitor.enabled} onCheckedChange={() => toggleModule('pet_monitor')} />
                                    </div>
                                    <CardDescription>Bark Alert & Forbidden Zones</CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    <div className="grid grid-cols-2 gap-2">
                                        <div className="space-y-1">
                                            <Label className="text-[10px] uppercase text-muted-foreground">{t("smart_home.care.active_from")}</Label>
                                            <Input type="time" className="h-8 text-xs bg-background/50" value={careConfig.modules.pet_monitor.active_from || "08:00"} onChange={(e) => { const newConfig = { ...careConfig }; newConfig.modules.pet_monitor.active_from = e.target.value; setCareConfig(newConfig); }} onBlur={() => handleSaveCareConfig(careConfig)} />
                                        </div>
                                        <div className="space-y-1">
                                            <Label className="text-[10px] uppercase text-muted-foreground">{t("smart_home.care.until")}</Label>
                                            <Input type="time" className="h-8 text-xs bg-background/50" value={careConfig.modules.pet_monitor.active_until || "20:00"} onChange={(e) => { const newConfig = { ...careConfig }; newConfig.modules.pet_monitor.active_until = e.target.value; setCareConfig(newConfig); }} onBlur={() => handleSaveCareConfig(careConfig)} />
                                        </div>
                                    </div>
                                    <div className="pt-2 border-t border-white/5 space-y-2">
                                        <Label className="text-[10px] font-bold uppercase text-blue-400">{t("smart_home.care.safe_zone")}</Label>
                                        <Select value={careConfig.modules.pet_monitor.safe_zone_id || "none"} onValueChange={(v) => { const newConfig = { ...careConfig }; newConfig.modules.pet_monitor.safe_zone_id = v === "none" ? null : v; handleSaveCareConfig(newConfig); }}>
                                            <SelectTrigger className="h-7 text-[10px] bg-background/30"><SelectValue placeholder={t("smart_home.care.select_safe_zone")} /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="none">{t("smart_home.care.no_exclusion")}</SelectItem>
                                                {careConfig.zones.map(z => (<SelectItem key={z.id} value={z.id}>{z.name}</SelectItem>))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </div>
            </TabsContent>

            <TabsContent value="care_rules" className="flex-1 min-h-0 m-0 data-[state=active]:flex data-[state=active]:flex-col overflow-hidden">
                <div className="px-6 py-2 shrink-0 flex justify-between items-center">
                    <Button variant="outline" size="sm" onClick={() => setIsTriggerManagerOpen(true)}><List className="w-4 h-4 mr-2" /> {t("smart_home.care.manage_triggers")}</Button>
                    <Button size="sm" onClick={addRule}><Plus className="w-4 h-4 mr-2" /> {t("smart_home.care.new_rule")}</Button>
                </div>
                <div className="flex-1 relative min-h-0">
                    <div className="absolute inset-0 overflow-y-scroll airis-scrollbar p-6">
                        <div className="space-y-4">
                            {careConfig.rules.map(rule => (
                                <Card key={rule.id} className="bg-card border-white/10 relative group">
                                    <Button variant="ghost" size="icon" className="absolute top-2 right-2 text-destructive" onClick={() => deleteRule(rule.id)}><Trash2 className="w-4 h-4" /></Button>
                                    <CardContent className="p-4 space-y-4">
                                        <div className="flex items-center justify-between mr-8">
                                            <Input className="font-bold text-primary border-none bg-transparent p-0 h-auto focus-visible:ring-0 w-1/2" value={rule.name?.startsWith('smart_home.') ? t(rule.name) : rule.name} onChange={(e) => updateRule(rule.id, { name: e.target.value })} />
                                            <Switch checked={rule.enabled} onCheckedChange={(v) => updateRule(rule.id, { enabled: v })} />
                                        </div>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                            <div className="space-y-1">
                                                <Label className="text-[10px] uppercase">{t("smart_home.care.trigger_event")}</Label>
                                                <Select value={rule.trigger} onValueChange={(v) => updateRule(rule.id, { trigger: v })}>
                                                    <SelectTrigger className="h-8 text-xs bg-background/50">
                                                        <SelectValue placeholder="Select Trigger..." />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {(careConfig.triggers || DEFAULT_TRIGGERS).map(t => (
                                                            <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </div>
                                            <div className="space-y-1"><Label className="text-[10px] uppercase">{t("smart_home.care.action_type")}</Label><Select value={rule.actions[0]?.type} onValueChange={(v) => { const newActions =[...rule.actions]; newActions[0] = { ...newActions[0], type: v }; updateRule(rule.id, { actions: newActions }); }}><SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="notification">Notification</SelectItem><SelectItem value="tts_speak">Speak (TTS)</SelectItem><SelectItem value="play_audio">Play Audio</SelectItem><SelectItem value="iot_light">IoT Light</SelectItem></SelectContent></Select></div>
                                        </div>

                                        {/* [NUOVO v20.0] ADVANCED AUDIO ACTION CONFIG */}
                                        {rule.actions[0]?.type === 'play_audio' && (
                                            <div className="pt-4 border-t border-white/5 space-y-4 animate-in slide-in-from-top-2">
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                    <div className="space-y-2">
                                                        <Label className="text-[10px] uppercase text-blue-400">Select Audio Clip</Label>
                                                        <Select 
                                                            value={rule.actions[0]?.clip_id || ""} 
                                                            onValueChange={(v) => {
                                                                const newActions = [...rule.actions];
                                                                newActions[0] = { ...newActions[0], clip_id: v };
                                                                updateRule(rule.id, { actions: newActions });
                                                            }}
                                                        >
                                                            <SelectTrigger className="h-8 text-xs bg-background/50"><SelectValue placeholder="Choose clip..." /></SelectTrigger>
                                                            <SelectContent>
                                                                {audioLibrary.map(c => <SelectItem key={c.id} value={c.id}>{c.label}</SelectItem>)}
                                                            </SelectContent>
                                                        </Select>
                                                    </div>
                                                    <div className="space-y-2">
                                                        <Label className="text-[10px] uppercase text-red-400">Escalation Clip (90s Silence)</Label>
                                                        <Select 
                                                            value={rule.actions[0]?.escalation_clip_id || ""} 
                                                            onValueChange={(v) => {
                                                                const newActions = [...rule.actions];
                                                                newActions[0] = { ...newActions[0], escalation_clip_id: v, escalation_delay_seconds: 90 };
                                                                updateRule(rule.id, { actions: newActions });
                                                            }}
                                                        >
                                                            <SelectTrigger className="h-8 text-xs bg-background/50"><SelectValue placeholder="Emergency clip..." /></SelectTrigger>
                                                            <SelectContent>
                                                                <SelectItem value="none">No Escalation</SelectItem>
                                                                {audioLibrary.map(c => <SelectItem key={c.id} value={c.id}>{c.label}</SelectItem>)}
                                                            </SelectContent>
                                                        </Select>
                                                    </div>
                                                </div>

                                                <div className="space-y-2">
                                                    <Label className="text-[10px] uppercase text-yellow-400">Broadcast to Devices (Multi-Routing)</Label>
                                                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 p-2 border rounded bg-black/20">
                                                        {hiveDevices.map(dev => (
                                                            <div key={dev.id} className="flex items-center space-x-2">
                                                                <Checkbox 
                                                                    id={`dev-${rule.id}-${dev.id}`}
                                                                    checked={(rule.actions[0]?.target_device_ids || []).includes(dev.id)}
                                                                    onCheckedChange={(checked) => {
                                                                        const current = rule.actions[0]?.target_device_ids || [];
                                                                        const next = checked ? [...current, dev.id] : current.filter(id => id !== dev.id);
                                                                        const newActions = [...rule.actions];
                                                                        newActions[0] = { ...newActions[0], target_device_ids: next };
                                                                        updateRule(rule.id, { actions: newActions });
                                                                    }}
                                                                />
                                                                <label htmlFor={`dev-${rule.id}-${dev.id}`} className="text-[10px] truncate cursor-pointer">{dev.name}</label>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </div>
                </div>
            </TabsContent>

            <TabsContent value="care_cron" className="flex-1 min-h-0 m-0 data-[state=active]:flex data-[state=active]:flex-col overflow-hidden">
                <div className="px-6 py-2 shrink-0 flex justify-end"><Button size="sm" onClick={addCronJob}><Plus className="w-4 h-4 mr-2" /> {t("smart_home.care.new_routine")}</Button></div>
                <div className="flex-1 relative min-h-0">
                    <div className="absolute inset-0 overflow-y-scroll airis-scrollbar p-6">
                        <div className="space-y-4">
                            {careConfig.cron_jobs.map(job => (
                                <Card key={job.id} className="bg-card border-white/10 relative group">
                                    <Button variant="ghost" size="icon" className="absolute top-2 right-2 text-destructive" onClick={() => deleteCronJob(job.id)}><Trash2 className="w-4 h-4" /></Button>
                                    <CardContent className="p-4 space-y-4">
                                        <div className="flex items-center justify-between mr-8"><Input className="font-bold text-primary border-none bg-transparent p-0 h-auto focus-visible:ring-0 w-1/2" value={job.name?.startsWith('smart_home.') ? t(job.name) : job.name} onChange={(e) => updateCronJob(job.id, { name: e.target.value })} /><Switch checked={job.enabled} onCheckedChange={(v) => updateCronJob(job.id, { enabled: v })} /></div>
                                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                            <div className="space-y-1"><Label className="text-[10px] uppercase">{t("smart_home.care.time")}</Label><Input type="time" className="h-8 text-xs" value={job.time} onChange={(e) => updateCronJob(job.id, { time: e.target.value })} /></div>
                                            <div className="space-y-1"><Label className="text-[10px] uppercase">{t("smart_home.care.action")}</Label><Select value={job.action} onValueChange={(v) => updateCronJob(job.id, { action: v })}><SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="tts_speak">Speak (TTS)</SelectItem><SelectItem value="notification">Notification</SelectItem><SelectItem value="iot_command">IoT Command</SelectItem></SelectContent></Select></div>
                                            <div className="space-y-1"><Label className="text-[10px] uppercase">{t("smart_home.care.payload")}</Label><Input className="h-8 text-xs" value={job.payload?.startsWith('smart_home.') ? t(job.payload) : job.payload} onChange={(e) => updateCronJob(job.id, { payload: e.target.value })} /></div>
                                        </div>
                                        <div className="flex flex-wrap gap-2">{DAYS_OF_WEEK.map(day => (<Button key={day} size="sm" variant={job.days.includes(day) ? "default" : "outline"} className="h-6 text-[10px] px-2" onClick={() => toggleCronDay(job.id, day)}>{day}</Button>))}</div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </div>
                </div>
            </TabsContent>

            <TabsContent value="walkie_talkie" className="flex-1 min-h-0 m-0 data-[state=active]:flex data-[state=active]:flex-col overflow-hidden">
                <div className="flex-1 relative min-h-0">
                    <div className="absolute inset-0 overflow-y-scroll airis-scrollbar p-6 flex flex-col items-center justify-center">
                        <div className="w-full max-w-md space-y-8 text-center">
                            <div className="space-y-2"><h3 className="text-2xl font-bold text-yellow-400 flex items-center justify-center gap-2"><Radio className="w-8 h-8" /> {t("smart_home.walkie_talkie.title")}</h3><p className="text-muted-foreground">{t("smart_home.walkie_talkie.desc")}</p></div>
                            <div className="space-y-4"><Label>{t("smart_home.walkie_talkie.target")}</Label><Select value={targetDeviceId} onValueChange={setTargetDeviceId}><SelectTrigger className="w-full"><SelectValue placeholder={t("smart_home.walkie_talkie.select_room")} /></SelectTrigger><SelectContent>{hiveDevices.map(dev => (<SelectItem key={dev.id} value={dev.id}>{dev.name} ({dev.status})</SelectItem>))}</SelectContent></Select></div>
                            <Button size="lg" variant={isRecording ? "destructive" : "default"} className={cn("w-48 h-48 rounded-full text-xl font-bold shadow-[0_0_40px_rgba(234,179,8,0.3)] transition-all", isRecording ? "animate-pulse scale-110 bg-red-600 hover:bg-red-700" : "bg-yellow-500 hover:bg-yellow-600 text-black")} onMouseDown={startIntercom} onMouseUp={stopIntercom} onMouseLeave={stopIntercom} onTouchStart={(e) => { e.preventDefault(); startIntercom(); }} onTouchEnd={(e) => { e.preventDefault(); stopIntercom(); }}>{isRecording ? <Mic className="w-16 h-16" /> : <MicOff className="w-16 h-16" />}</Button>
                            <p className="text-sm text-muted-foreground animate-pulse">{isRecording ? t("smart_home.walkie_talkie.broadcasting") : t("smart_home.walkie_talkie.hold_to_speak")}</p>
                        </div>
                    </div>
                </div>
            </TabsContent>

            <TabsContent value="audio_library" className="flex-1 min-h-0 m-0 data-[state=active]:flex data-[state=active]:flex-col overflow-hidden">
                <div className="flex-1 relative min-h-0">
                    <div className="absolute inset-0 overflow-y-scroll airis-scrollbar p-6 space-y-8">
                        <div className="space-y-2 border-b border-white/10 pb-4">
                            <h3 className="text-xl font-bold text-blue-400 flex items-center gap-2">
                                <Music className="w-6 h-6" /> {t("smart_home.audio_library.title")}
                            </h3>
                            <p className="text-sm text-muted-foreground">{t("smart_home.audio_library.desc")}</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* CREATION PANEL */}
                            <Card className="bg-card/50 border-blue-500/20">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-sm flex items-center gap-2"><Plus className="w-4 h-4" /> {t("smart_home.audio_library.create_clip")}</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="space-y-2">
                                        <Label className="text-[10px] uppercase">{t("smart_home.audio_library.label")}</Label>
                                        <Input placeholder={t("smart_home.eg_medicine_reminder")} value={newClipLabel} onChange={(e) => setNewClipLabel(e.target.value)} />
                                    </div>
                                    <div className="space-y-2">
                                        <Label className="text-[10px] uppercase">{t("smart_home.audio_library.category")}</Label>
                                        <Select value={newClipCategory} onValueChange={(v: any) => setNewClipCategory(v)}>
                                            <SelectTrigger><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="Elders">Elders</SelectItem>
                                                <SelectItem value="Baby">Baby</SelectItem>
                                                <SelectItem value="Pets">Pets</SelectItem>
                                                <SelectItem value="Emergency">Emergency</SelectItem>
                                                <SelectItem value="Custom">Custom</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <Tabs defaultValue="record" className="pt-2">
                                        <TabsList className="grid w-full grid-cols-2 h-8">
                                            <TabsTrigger value="record" className="text-[10px]">{t("smart_home.audio_library.record")}</TabsTrigger>
                                            <TabsTrigger value="tts" className="text-[10px]">{t("smart_home.audio_library.ai_voice")}</TabsTrigger>
                                        </TabsList>
                                        <TabsContent value="record" className="space-y-4 pt-4">
                                            <div className="flex flex-col items-center gap-4">
                                                <Button 
                                                    size="lg" 
                                                    variant={isRecordingAudio ? "destructive" : "outline"}
                                                    className={cn("w-20 h-20 rounded-full", isRecordingAudio && "animate-pulse")}
                                                    onClick={isRecordingAudio ? stopRecording : startRecording}
                                                >
                                                    {isRecordingAudio ? <StopCircle className="w-8 h-8" /> : <Mic className="w-8 h-8" />}
                                                </Button>
                                                {recordingBlob && (
                                                    <Button className="w-full bg-green-600 hover:bg-green-700" onClick={uploadClip} disabled={!newClipLabel}>
                                                        <Save className="w-4 h-4 mr-2" /> {t("smart_home.audio_library.save")}
                                                    </Button>
                                                )}
                                            </div>
                                        </TabsContent>
                                        <TabsContent value="tts" className="space-y-4 pt-4">
                                            <Textarea 
                                                placeholder={t("smart_home.what_ai_say")} 
                                                value={ttsText} 
                                                onChange={(e) => setTtsText(e.target.value)}
                                                className="text-xs min-h-[80px]"
                                            />
                                            <Button className="w-full bg-blue-600 hover:bg-blue-700" onClick={generateTtsClip} disabled={isGeneratingTts || !ttsText || !newClipLabel}>
                                                {isGeneratingTts ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Wand2 className="w-4 h-4 mr-2" />}
                                                {t("smart_home.audio_library.generate")}
                                            </Button>
                                        </TabsContent>
                                    </Tabs>
                                </CardContent>
                            </Card>

                            {/* LIBRARY LIST */}
                            <div className="flex flex-col gap-4">
                                <Label className="text-xs font-bold uppercase text-muted-foreground px-1">{t("smart_home.audio_library.library")} ({audioLibrary.length})</Label>
                                <ScrollArea className="flex-1 border rounded-lg bg-muted/10 p-2 min-h-[300px]">
                                    <div className="space-y-2">
                                        {audioLibrary.map(clip => (
                                            <div key={clip.id} className="p-3 rounded-lg bg-card border border-white/5 group flex items-center justify-between">
                                                <div className="flex flex-col overflow-hidden">
                                                    <span className="text-sm font-bold truncate">{clip.label}</span>
                                                    <div className="flex items-center gap-2">
                                                        <Badge variant="outline" className="text-[8px] uppercase px-1 h-4">{clip.category}</Badge>
                                                        <span className="text-[9px] text-muted-foreground">{clip.type === 'recorded' ? t("smart_home.audio_library.user") : t("smart_home.audio_library.ai")}</span>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-1">
                                                    <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-400" onClick={() => playPreview(clip.path)}>
                                                        <PlayCircle className="w-5 h-5" />
                                                    </Button>
                                                    <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive opacity-0 group-hover:opacity-100" onClick={() => deleteClip(clip.id)}>
                                                        <Trash2 className="w-4 h-4" />
                                                    </Button>
                                                </div>
                                            </div>
                                        ))}
                                        {audioLibrary.length === 0 && <p className="text-center text-xs text-muted-foreground py-10 italic">{t("smart_home.audio_library.empty")}</p>}
                                    </div>
                                </ScrollArea>
                            </div>
                        </div>
                    </div>
                </div>
            </TabsContent>

            <TabsContent value="logs" className="flex-1 min-h-0 m-0 data-[state=active]:flex data-[state=active]:flex-col overflow-hidden">
                <div className="px-6 py-2 shrink-0 flex justify-between items-center"><Label className="text-[10px] uppercase text-muted-foreground">Recent Activity</Label><Button variant="ghost" size="icon" className="h-6 w-6" onClick={fetchLogs}><RefreshCw className="h-3 w-3" /></Button></div>
                <div className="flex-1 relative min-h-0">
                    <div className="absolute inset-0 overflow-y-scroll airis-scrollbar p-6 bg-black/20 font-mono text-[10px] leading-relaxed">
                        <div className="space-y-1">
                            {logs.length === 0 ? (<div className="text-muted-foreground italic">{t("smart_home.no_logs_available")}</div>) : (logs.map((log, i) => (<div key={i} className={cn(log.includes("[ERROR]") ? "text-red-400" : log.includes("[SUCCESS]") ? "text-green-400" : log.includes("[ANIMA]") ? "text-blue-400" : "text-muted-foreground")}>{log}</div>)))}
                        </div>
                    </div>
                </div>
            </TabsContent>

            <TabsContent value="mindset" className="flex-1 min-h-0 m-0 data-[state=active]:flex data-[state=active]:flex-col overflow-hidden">
                <div className="flex-1 relative min-h-0">
                    <div className="absolute inset-0 overflow-y-scroll airis-scrollbar p-6 space-y-6">
                        <div className="space-y-2 border-b border-white/10 pb-4">
                            <h3 className="text-xl font-bold text-purple-400 flex items-center gap-2">
                                <Brain className="w-6 h-6" /> {t("smart_home.jarvis.mindset_title")}
                            </h3>
                            <p className="text-sm text-muted-foreground">
                                {t("smart_home.jarvis.mindset_desc")}
                            </p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <Card className="bg-card/50 border-purple-500/20">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-sm flex items-center gap-2">
                                        <Activity className="w-4 h-4 text-purple-400" /> {t("smart_home.jarvis.prudence")}
                                    </CardTitle>
                                    <CardDescription className="text-xs">
                                        {t("smart_home.jarvis.prudence_desc")}
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-6">
                                    <div className="space-y-4">
                                        <div className="flex justify-between items-center">
                                            <span className="text-[10px] font-bold uppercase text-muted-foreground">{t("smart_home.jarvis.current_level")}</span>
                                            <Badge variant="outline" className="font-mono text-primary">{prudenceValue}</Badge>
                                        </div>
                                        <Slider 
                                            value={[prudenceValue]} 
                                            max={100} 
                                            step={1} 
                                            onValueChange={([v]) => {
                                                isDraggingPrudenceRef.current = true;
                                                setPrudenceValue(v);
                                            }}
                                            onValueCommit={([v]) => {
                                                handlePrudenceChange(v);
                                                setTimeout(() => { isDraggingPrudenceRef.current = false; }, 2000);
                                            }}
                                            className="cursor-pointer"
                                        />
                                        <div className="flex justify-between text-[9px] uppercase font-bold text-muted-foreground/60">
                                            <span>{t("smart_home.jarvis.audacious")}</span>
                                            <span>{t("smart_home.jarvis.timid")}</span>
                                        </div>
                                    </div>
                                    
                                    <div className="pt-4 border-t border-white/5 flex items-center justify-between">
                                        <div className="space-y-0.5">
                                            <Label className="text-sm flex items-center gap-2">
                                                <Briefcase className="w-4 h-4 text-blue-400" /> {t("smart_home.jarvis.work_mode")}
                                            </Label>
                                            <p className="text-[10px] text-muted-foreground">{t("smart_home.jarvis.work_mode_desc")}</p>
                                        </div>
                                        <Switch checked={isWorkMode} onCheckedChange={handleWorkModeToggle} />
                                    </div>
                                </CardContent>
                            </Card>

                            <Card className="bg-card/50 border-blue-500/20">
                                <CardHeader>
                                    <CardTitle className="text-sm flex items-center gap-2">
                                        <Zap className="w-4 h-4 text-blue-400" /> {t("smart_home.jarvis.hardware_mood")}
                                    </CardTitle>
                                    <CardDescription className="text-xs">
                                        {t("smart_home.jarvis.hardware_desc")}
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="space-y-2">
                                        <div className="flex justify-between text-xs">
                                            <span>{t("smart_home.jarvis.mental_tension")}</span>
                                            <span className="text-muted-foreground">{t("smart_home.auto_mapped")}</span>
                                        </div>
                                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                                            <div className="h-full bg-blue-500 w-[45%]" />
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <div className="flex justify-between text-xs">
                                            <span>{t("smart_home.jarvis.vulnerability")}</span>
                                            <span className="text-muted-foreground">{t("smart_home.auto_mapped")}</span>
                                        </div>
                                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                                            <div className="h-full bg-pink-500 w-[60%]" />
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </div>
            </TabsContent>

            <TabsContent value="shadow" className="flex-1 min-h-0 m-0 data-[state=active]:flex data-[state=active]:flex-col overflow-hidden">
                <div className="flex-1 relative min-h-0">
                    <div className="absolute inset-0 overflow-y-scroll airis-scrollbar p-6 flex flex-col gap-6">
                        <div className="space-y-2 border-b border-white/10 pb-4 shrink-0">
                            <h3 className="text-xl font-bold text-purple-400 flex items-center gap-2">
                                <EyeOff className="w-6 h-6" /> {t("smart_home.jarvis.shadow_title")}
                            </h3>
                            <p className="text-sm text-muted-foreground">
                                {t("smart_home.jarvis.shadow_desc")}
                            </p>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
                            <div className="lg:col-span-2 flex flex-col border rounded-lg bg-black/80 overflow-hidden min-h-[300px]">
                                <div className="bg-muted/20 p-2 border-b border-white/10 flex justify-between items-center shrink-0">
                                    <span className="text-xs font-mono text-green-400 flex items-center gap-2">
                                        <Terminal className="w-4 h-4" /> event_hub.log
                                    </span>
                                    <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground" onClick={fetchJarvisData}>
                                        <RefreshCw className="w-3 h-3" />
                                    </Button>
                                </div>
                                <ScrollArea className="flex-1 p-4 font-mono text-[10px] text-green-500/80 leading-relaxed">
                                    {shadowLog.length === 0 ? (
                                        <span className="opacity-50">{t("smart_home.jarvis.waiting_input")}</span>
                                    ) : (
                                        shadowLog.map((log, i) => (
                                            <div key={i} className="mb-1 hover:bg-white/5 px-1 rounded">{log}</div>
                                        ))
                                    )}
                                </ScrollArea>
                            </div>

                            <div className="flex flex-col gap-4 min-h-[300px]">
                                <Card className="flex-1 flex flex-col bg-card/50 border-red-500/20">
                                    <CardHeader className="pb-2 shrink-0">
                                        <CardTitle className="text-sm flex items-center gap-2 text-red-400">
                                            <Shield className="w-4 h-4" /> {t("smart_home.jarvis.blacklist")}
                                        </CardTitle>
                                        <CardDescription className="text-xs">
                                            {t("smart_home.jarvis.blacklist_desc")}
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent className="flex-1 flex flex-col gap-4 min-h-0">
                                        <div className="flex gap-2 shrink-0">
                                            <Input 
                                                placeholder={t("smart_home.jarvis.add_filter")} 
                                                value={newBlacklistWord}
                                                onChange={(e) => setNewBlacklistWord(e.target.value)}
                                                className="h-8 text-xs"
                                                onKeyDown={(e) => e.key === 'Enter' && handleAddBlacklist()}
                                            />
                                            <Button size="sm" className="h-8" onClick={handleAddBlacklist}>
                                                <Plus className="w-4 h-4" />
                                            </Button>
                                        </div>
                                        <ScrollArea className="flex-1 border rounded-md bg-muted/10 p-2">
                                            <div className="space-y-1">
                                                {blacklist.map((word, i) => (
                                                    <div key={i} className="flex items-center justify-between p-1.5 bg-background rounded border border-white/5 group">
                                                        <span className="text-xs font-medium truncate">{word}</span>
                                                        <Button variant="ghost" size="icon" className="h-5 w-5 text-destructive opacity-0 group-hover:opacity-100" onClick={() => handleRemoveBlacklist(word)}>
                                                            <X className="w-3 h-3" />
                                                        </Button>
                                                    </div>
                                                ))}
                                                {blacklist.length === 0 && (
                                                    <p className="text-xs text-center text-muted-foreground py-4">{t("smart_home.jarvis.no_filters")}</p>
                                                )}
                                            </div>
                                        </ScrollArea>
                                    </CardContent>
                                </Card>
                            </div>
                        </div>
                    </div>
                </div>
            </TabsContent>

            <TabsContent value="architect" className="flex-1 min-h-0 m-0 data-[state=active]:flex data-[state=active]:flex-col overflow-hidden">
                <div className="flex-1 relative min-h-0">
                    <div className="absolute inset-0 overflow-y-scroll airis-scrollbar p-6 space-y-6">
                        <div className="space-y-2 border-b border-white/10 pb-4 flex justify-between items-end">
                            <div>
                                <h3 className="text-xl font-bold text-purple-400 flex items-center gap-2">
                                    <Code className="w-6 h-6" /> {t("smart_home.jarvis.architect_title")}
                                </h3>
                                <p className="text-sm text-muted-foreground">
                                    {t("smart_home.jarvis.architect_desc")}
                                </p>
                            </div>
                            <Button variant="outline" size="sm" onClick={fetchJarvisData}>
                                <RefreshCw className="w-4 h-4 mr-2" /> {t("smart_home.actions.update")}
                            </Button>
                        </div>

                        <div className="space-y-4">
                            {patches.length === 0 ? (
                                <div className="text-center py-20 text-muted-foreground border-2 border-dashed rounded-xl bg-muted/5">
                                    <GitCommit className="w-10 h-10 mx-auto mb-3 opacity-20" />
                                    <p>{t("smart_home.jarvis.no_patches")}</p>
                                </div>
                            ) : (
                                patches.map((patch) => (
                                    <Card key={patch.id} className={cn("border-white/10 transition-all", patch.status === 'rolled_back' ? "opacity-60 grayscale" : "border-l-4 border-l-purple-500")}>
                                        <CardHeader className="p-4 pb-2">
                                            <div className="flex justify-between items-start">
                                                <div>
                                                    <CardTitle className="text-sm font-mono text-primary">{patch.file}</CardTitle>
                                                    <CardDescription className="text-xs mt-1">
                                                        {new Date(patch.timestamp * 1000).toLocaleString()}
                                                    </CardDescription>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <Badge variant={patch.status === 'applied' ? 'default' : 'secondary'} className="uppercase text-[10px]">
                                                        {patch.status}
                                                    </Badge>
                                                    {patch.status === 'applied' && (
                                                        <Button 
                                                            variant="destructive" 
                                                            size="sm" 
                                                            className="h-7 text-xs"
                                                            onClick={() => handleRollback(patch.id)}
                                                            disabled={isRollingBack === patch.id}
                                                        >
                                                            {isRollingBack === patch.id ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <RotateCcw className="w-3 h-3 mr-1" />}
                                                            {t("smart_home.jarvis.rollback")}
                                                        </Button>
                                                    )}
                                                </div>
                                            </div>
                                        </CardHeader>
                                        <CardContent className="p-4 pt-2">
                                            <Accordion type="single" collapsible className="w-full">
                                                <AccordionItem value="diff" className="border-none">
                                                    <AccordionTrigger className="py-2 text-xs hover:no-underline text-muted-foreground hover:text-foreground">
                                                        {t("smart_home.jarvis.view_changes")}
                                                    </AccordionTrigger>
                                                    <AccordionContent>
                                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                                                            <div className="space-y-1">
                                                                <Label className="text-[10px] uppercase text-red-400">{t("smart_home.jarvis.old_code")}</Label>
                                                                <div className="bg-red-950/30 border border-red-900/50 rounded p-2 overflow-x-auto">
                                                                    <pre className="text-[10px] font-mono text-red-200/70">{patch.old_code}</pre>
                                                                </div>
                                                            </div>
                                                            <div className="space-y-1">
                                                                <Label className="text-[10px] uppercase text-green-400">{t("smart_home.jarvis.new_code")}</Label>
                                                                <div className="bg-green-950/30 border border-green-900/50 rounded p-2 overflow-x-auto">
                                                                    <pre className="text-[10px] font-mono text-green-200/70">{patch.new_code}</pre>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </AccordionContent>
                                                </AccordionItem>
                                            </Accordion>
                                        </CardContent>
                                    </Card>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </TabsContent>

        </Tabs>

        <DialogFooter className="p-4 border-t bg-background z-20 shrink-0">
          <Button variant="outline" onClick={() => onOpenChange(false)}>{t("smart_home.actions.close")}</Button>
          <Button onClick={() => handleSaveCareConfig(careConfig)} disabled={isSaving}>
            {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
            {t("smart_home.actions.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog open={isTriggerManagerOpen} onOpenChange={setIsTriggerManagerOpen}>
        <DialogContent className="sm:max-w-md">
            <DialogHeader><DialogTitle>{t("smart_home.care.manage_triggers")}</DialogTitle><DialogDescription>Add or remove custom event triggers for Care Rules.</DialogDescription></DialogHeader>
            <div className="space-y-4 py-4">
                <div className="flex gap-2 items-end">
                    <div className="grid gap-1 flex-1"><Label className="text-xs">{t("smart_home.label")}</Label><Input placeholder="e.g. Glass Break" value={newTriggerLabel} onChange={(e) => setNewTriggerLabel(e.target.value)} className="h-8 text-xs" /></div>
                    <div className="grid gap-1 flex-1"><Label className="text-xs">{t("smart_home.value")}</Label><Input placeholder="e.g. audio_glass" value={newTriggerValue} onChange={(e) => setNewTriggerValue(e.target.value)} className="h-8 text-xs font-mono" /></div>
                    <Button size="sm" onClick={handleAddTrigger} className="h-8"><Plus className="w-4 h-4" /></Button>
                </div>
                <ScrollArea className="h-[250px] border rounded-md p-2 airis-scrollbar">
                    <div className="space-y-2">
                        {(careConfig.triggers || DEFAULT_TRIGGERS).map((t) => (
                            <div key={t.value} className="flex flex-col p-2 bg-muted/20 rounded border border-white/5 group">
                                {editingTriggerValue === t.value ? (
                                    <div className="space-y-2 animate-in fade-in">
                                        <div className="grid grid-cols-2 gap-2">
                                            <Input className="h-7 text-[10px]" value={newTriggerLabel} onChange={(e) => setNewTriggerLabel(e.target.value)} placeholder="Label" />
                                            <Input className="h-7 text-[10px] font-mono" value={newTriggerValue} onChange={(e) => setNewTriggerValue(e.target.value)} placeholder="Value" />
                                        </div>
                                        <div className="flex justify-end gap-2">
                                            <Button size="sm" variant="ghost" className="h-6 text-[10px]" onClick={() => setEditingTriggerValue(null)}>{t("smart_home.cancel")}</Button>
                                            <Button size="sm" className="h-6 text-[10px]" onClick={() => handleUpdateTrigger(t.value, newTriggerValue, newTriggerLabel)}>{t("smart_home.update")}</Button>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="flex items-center justify-between">
                                        <div className="flex flex-col">
                                            <span className="text-sm font-medium">{t.label}</span>
                                            <span className="text-[10px] text-muted-foreground font-mono">{t.value}</span>
                                        </div>
                                        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <Button variant="ghost" size="icon" className="h-7 w-7 text-blue-400" onClick={() => {
                                                setEditingTriggerValue(t.value);
                                                setNewTriggerLabel(t.label);
                                                setNewTriggerValue(t.value);
                                            }}><Edit className="w-3.5 h-3.5" /></Button>
                                            <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={() => handleDeleteTrigger(t.value)}><Trash2 className="w-3.5 h-3.5" /></Button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </ScrollArea>
            </div>
            <DialogFooter><Button variant="outline" onClick={() => setIsTriggerManagerOpen(false)}>Close</Button></DialogFooter>
        </DialogContent>
    </Dialog>

    {/* ZONE MANAGER DIALOG */}
    <Dialog open={isZoneManagerOpen} onOpenChange={setIsZoneManagerOpen}>
        <DialogContent className="sm:max-w-md">
            <DialogHeader><DialogTitle>{t("smart_home.care.manage_zones")}</DialogTitle><DialogDescription>Define zones where alerts should be suppressed.</DialogDescription></DialogHeader>
            <div className="space-y-4 py-4">
                <div className="flex gap-2 items-end">
                    <div className="grid gap-1 flex-1"><Label className="text-xs">{t("smart_home.zone_name")}</Label><Input placeholder="e.g. Culla" value={newZoneName} onChange={(e) => setNewZoneName(e.target.value)} className="h-8 text-xs" /></div>
                    <div className="grid gap-1 flex-1"><Label className="text-xs">{t("smart_home.zone_id")}</Label><Input placeholder="e.g. zone_culla" value={newZoneId} onChange={(e) => setNewZoneId(e.target.value)} className="h-8 text-xs font-mono" /></div>
                    <Button size="sm" onClick={handleAddZone} className="h-8"><Plus className="w-4 h-4" /></Button>
                </div>
                <ScrollArea className="h-[200px] border rounded-md p-2">
                    <div className="space-y-2">
                        {careConfig.zones.map((z) => (
                            <div key={z.id} className="flex items-center justify-between p-2 bg-muted/20 rounded border border-white/5">
                                <div className="flex flex-col"><span className="text-sm font-medium">{z.name}</span><span className="text-[10px] text-muted-foreground font-mono">{z.id}</span></div>
                                <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive hover:bg-destructive/10" onClick={() => handleDeleteZone(z.id)}><Trash2 className="w-3 h-3" /></Button>
                            </div>
                        ))}
                        {careConfig.zones.length === 0 && <p className="text-center text-xs text-muted-foreground py-4">{t("smart_home.no_zones_defined")}</p>}
                    </div>
                </ScrollArea>
            </div>
            <DialogFooter><Button variant="outline" onClick={() => setIsZoneManagerOpen(false)}>{t("smart_home.close")}</Button></DialogFooter>
        </DialogContent>
    </Dialog>
    </>
  );
};

const Loader2 = ({ className }: { className?: string }) => <RefreshCw className={cn("animate-spin", className)} />;