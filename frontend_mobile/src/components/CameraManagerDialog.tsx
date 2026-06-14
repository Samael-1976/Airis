// frontend_mobile/src/components/CameraManagerDialog.tsx
// v4.2 - HIVE IP EDITING & SYNTAX FIX
// FIX: Riparato errore di chiusura tag JSX (DialogContent) che causava il fallimento della build.
// FIX: Abilitata la modifica manuale dell'indirizzo IP nel modulo di editing.
// MANTENUTO: Intercom, IP Binding, Focus Control, Delete Device.
// LEGGE A0099: Invarianza strutturale garantita.

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
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ServerConfig, HiveDevice } from "@/types";
import { toast } from "sonner";
import { getBaseUrl, getHeaders } from "@/lib/api";
import { Loader2, Network, Smartphone, Tablet, Monitor, MapPin, Power, Eye, Lock, Unlock, Wifi, Mic, MicOff, Pencil, Trash2, Save, X } from "lucide-react";
import { useTranslation } from "@/contexts/TranslationContext";

interface CameraManagerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  serverConfig: ServerConfig | null;
}

// Estensione locale per supportare i nuovi campi prima dell'aggiornamento di types/index.ts
interface ExtendedHiveDevice extends HiveDevice {
    ip?: string;
}

export const CameraManagerDialog = ({
  open,
  onOpenChange,
  serverConfig,
}: CameraManagerDialogProps) => {
  const { t } = useTranslation();
  const [devices, setDevices] = useState<Record<string, ExtendedHiveDevice>>({});
  const [ipBindings, setIpBindings] = useState<Record<string, any>>({});
  const [activeFocusId, setActiveFocusId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  // Stato Locale del Dispositivo
  const [myDeviceId, setMyDeviceId] = useState<string>("");
  const [isRegistered, setIsRegistered] = useState(false);
  
  // Form Registrazione
  const [regName, setRegName] = useState("");
  const [regType, setRegType] = useState<"mobile" | "tablet" | "desktop">("tablet");
  const [isRegistering, setIsRegistering] = useState(false);

  // --- STATI INTERCOM ---
  const [recordingDeviceId, setRecordingDeviceId] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // --- STATI EDITING ---
  const [editingDeviceId, setEditingDeviceId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editIp, setEditIp] = useState("");

  // Inizializzazione ID Locale
  useEffect(() => {
      let id = localStorage.getItem("airis_device_id");
      if (!id) {
          id = crypto.randomUUID();
          localStorage.setItem("airis_device_id", id);
      }
      setMyDeviceId(id);
  }, []);

  const fetchHiveState = async () => {
    if (!serverConfig) return;
    setIsLoading(true);
    
    const baseUrl = getBaseUrl(serverConfig);
    const headers = getHeaders();

    try {
      const response = await fetch(`${baseUrl}/api/hive/devices`, { headers });
      if (!response.ok) throw new Error("Failed to fetch hive state");
      
      const data = await response.json();
      setDevices(data.devices || {});
      setIpBindings(data.ip_bindings || {});
      setActiveFocusId(data.active_focus_id);
      
      // Verifica se questo dispositivo è registrato
      if (data.devices && data.devices[myDeviceId]) {
          setIsRegistered(true);
      } else {
          setIsRegistered(false);
      }

    } catch (error: any) {
      console.error(t("camera_manager.err_fetch_hive_state"), error);
      toast.error(t("camera_manager.error.unreachable"), { description: error.message });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
        fetchHiveState();
        // Polling leggero per aggiornare lo stato mentre il dialog è aperto
        const interval = setInterval(fetchHiveState, 5000);
        return () => clearInterval(interval);
    }
  }, [open, serverConfig, myDeviceId]);

  const handleRegister = async () => {
      if (!regName.trim() || !serverConfig) return;
      setIsRegistering(true);
      
      const baseUrl = getBaseUrl(serverConfig);
      const headers = { ...getHeaders(), "Content-Type": "application/json" };

      try {
          const res = await fetch(`${baseUrl}/api/hive/register`, {
              method: 'POST',
              headers: headers,
              body: JSON.stringify({
                  device_id: myDeviceId,
                  device_name: regName,
                  device_type: regType
              })
          });
          
          if (!res.ok) throw new Error(t("camera_manager.error.registration_failed"));
          
          const data = await res.json();
          
          // Se il server ci ha assegnato un nuovo ID (Binding IP), aggiorniamo il locale
      if (data.device_id && data.device_id !== myDeviceId) {
          localStorage.setItem("airis_device_id", data.device_id);
          setMyDeviceId(data.device_id);
          toast.success(t("camera_manager.toast.identity_restored"), { description: t("camera_manager.toast.recognized_ip") });
      } else {
          toast.success(t("camera_manager.toast.device_assimilated"), { description: t("camera_manager.toast.welcome_hive") });
      }
          
          setIsRegistered(true);
          fetchHiveState();
      } catch (error: any) {
          toast.error(t("camera_manager.error.registration_failed"), { description: error.message });
      } finally {
          setIsRegistering(false);
      }
  };

  const handleForceFocus = async (targetDeviceId: string) => {
      if (!serverConfig) return;
      
      const baseUrl = getBaseUrl(serverConfig);
      const headers = { ...getHeaders(), "Content-Type": "application/json" };
      
      try {
          const res = await fetch(`${baseUrl}/api/hive/focus`, {
              method: 'POST',
              headers: headers,
              body: JSON.stringify({ device_id: targetDeviceId })
          });
          
          if (!res.ok) throw new Error(t("camera_manager.error.focus_failed"));
          
          toast.success(t("camera_manager.toast.focus_shifted"), { description: t("camera_manager.toast.avatar_moving") });
          fetchHiveState();
      } catch (error: any) {
          toast.error(t("camera_manager.error.focus_title"), { description: error.message });
      }
  };

  // --- GESTIONE BINDING IP ---
  const handleBindIp = async (ip: string, deviceId: string, name: string) => {
      if (!serverConfig) return;
      const baseUrl = getBaseUrl(serverConfig);
      const headers = { ...getHeaders(), "Content-Type": "application/json" };

      try {
          const res = await fetch(`${baseUrl}/api/hive/bind`, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({ ip, device_id: deviceId, name })
      });
      if (!res.ok) throw new Error(t("camera_manager.error.bind_failed"));
      toast.success(t("camera_manager.toast.ip_bound"), { description: t("camera_manager.toast.ip_bound_desc", { name, ip }) });
      fetchHiveState();
  } catch (error: any) {
      toast.error(t("camera_manager.error.binding_error"), { description: error.message });
  }
};

  const handleUnbindIp = async (ip: string) => {
      if (!serverConfig) return;
      const baseUrl = getBaseUrl(serverConfig);
      const headers = { ...getHeaders(), "Content-Type": "application/json" };

      try {
          const res = await fetch(`${baseUrl}/api/hive/unbind`, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({ ip })
      });
      if (!res.ok) throw new Error(t("camera_manager.error.unbind_failed"));
      toast.success(t("camera_manager.toast.ip_unbound"), { description: t("camera_manager.toast.ip_unbound_desc", { ip }) });
      fetchHiveState();
  } catch (error: any) {
      toast.error(t("camera_manager.error.unbinding_error"), { description: error.message });
  }
};

  // --- GESTIONE INTERCOM (PUSH-TO-TALK) ---
  const startIntercom = async (targetDeviceId: string) => {
      if (recordingDeviceId) return; // Già in registrazione
      
      try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const recorder = new MediaRecorder(stream);
          mediaRecorderRef.current = recorder;
          audioChunksRef.current = [];

          recorder.ondataavailable = (e) => {
              if (e.data.size > 0) audioChunksRef.current.push(e.data);
          };

          recorder.onstop = async () => {
              const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
              await sendIntercomAudio(targetDeviceId, audioBlob);
              stream.getTracks().forEach(track => track.stop());
          };

          recorder.start();
          setRecordingDeviceId(targetDeviceId);
      } catch (err) {
          console.error(t("camera_manager.err_intercom"), err);
          toast.error(t("camera_manager.error.mic_denied"));
      }
  };

  const stopIntercom = () => {
      if (mediaRecorderRef.current && recordingDeviceId) {
          mediaRecorderRef.current.stop();
          setRecordingDeviceId(null);
      }
  };

  const sendIntercomAudio = async (targetDeviceId: string, audioBlob: Blob) => {
      if (!serverConfig) return;
      
      const formData = new FormData();
      formData.append("device_id", targetDeviceId);
      formData.append("audio", audioBlob, "intercom.webm");

      try {
          const baseUrl = getBaseUrl(serverConfig);
          const res = await fetch(`${baseUrl}/api/hive/intercom`, {
              method: 'POST',
              body: formData,
              headers: { "ngrok-skip-browser-warning": "true" }
          });
          
          if (!res.ok) throw new Error(t("camera_manager.error.intercom_failed"));
          toast.success(t("camera_manager.toast.message_sent"), { description: t("camera_manager.toast.voice_transmitted") });
      } catch (error: any) {
          toast.error(t("camera_manager.error.intercom_failed"), { description: error.message });
      }
  };

  // --- GESTIONE EDITING (v4.2) ---
  const startEditing = (dev: ExtendedHiveDevice, id: string) => {
      setEditingDeviceId(id);
      setEditName(dev.name);
      setEditIp(dev.ip || "");
  };

  const cancelEditing = () => {
      setEditingDeviceId(null);
      setEditName("");
      setEditIp("");
  };

  const saveEditing = async () => {
      if (!serverConfig || !editingDeviceId) return;
      const baseUrl = getBaseUrl(serverConfig);
      const headers = { ...getHeaders(), "Content-Type": "application/json" };

      try {
          const res = await fetch(`${baseUrl}/api/hive/device/update`, {
              method: 'POST',
              headers: headers,
              body: JSON.stringify({ 
                  device_id: editingDeviceId,
                  name: editName,
                  ip: editIp // Invia l'IP modificato manualmente
              })
          });
          if (!res.ok) throw new Error(t("camera_manager.error.update_failed"));
          toast.success(t("camera_manager.toast.device_updated"));
          cancelEditing();
          fetchHiveState();
      } catch (error: any) {
          toast.error(t("camera_manager.error.update_error"), { description: error.message });
      }
  };

  const deleteDevice = async (deviceId: string) => {
      if (!serverConfig) return;
      const baseUrl = getBaseUrl(serverConfig);
      const headers = { ...getHeaders(), "Content-Type": "application/json" };

      if (!confirm(t("camera_manager.confirm_remove"))) return;

      try {
          const res = await fetch(`${baseUrl}/api/hive/device/remove`, {
              method: 'POST',
              headers: headers,
              body: JSON.stringify({ device_id: deviceId })
          });
          if (!res.ok) throw new Error(t("camera_manager.error.remove_failed"));
          toast.success(t("camera_manager.toast.device_removed"));
          
          // Se ho rimosso me stesso, resetto lo stato locale
          if (deviceId === myDeviceId) {
              setIsRegistered(false);
          }
          
          fetchHiveState();
      } catch (error: any) {
          toast.error(t("camera_manager.error.remove_error"), { description: error.message });
      }
  };

  const getDeviceIcon = (type: string) => {
      switch (type) {
          case 'mobile': return <Smartphone className="w-5 h-5" />;
          case 'tablet': return <Tablet className="w-5 h-5" />;
          case 'desktop': return <Monitor className="w-5 h-5" />;
          default: return <Network className="w-5 h-5" />;
      }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-primary">
              <Network className="w-6 h-6" />
              {t("camera_manager.title")}
          </DialogTitle>
          <DialogDescription>
            {t("camera_manager.description")}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-hidden flex flex-col gap-6 py-4">
            
            {/* SEZIONE REGISTRAZIONE (Se non registrato) */}
            {!isRegistered && !isLoading && (
                <Card className="border-primary/50 bg-primary/5 animate-in fade-in slide-in-from-top-2">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-bold uppercase tracking-wider flex items-center gap-2">
                            <Power className="w-4 h-4" /> {t("camera_manager.new_node")}
                        </CardTitle>
                        <CardDescription>
                            {t("camera_manager.new_node_desc")}
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col sm:flex-row gap-4 items-end">
                        <div className="grid w-full gap-2">
                            <Label>{t("camera_manager.device_name")}</Label>
                            <Input 
                                placeholder={t("camera_manager.placeholder_name")} 
                                value={regName} 
                                onChange={(e) => setRegName(e.target.value)} 
                            />
                        </div>
                        <div className="grid w-full sm:w-[180px] gap-2">
                            <Label>{t("camera_manager.type")}</Label>
                            <Select value={regType} onValueChange={(v: any) => setRegType(v)}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="tablet">{t("camera_manager.tablet")}</SelectItem>
                                    <SelectItem value="mobile">{t("camera_manager.mobile")}</SelectItem>
                                    <SelectItem value="desktop">{t("camera_manager.desktop")}</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <Button 
                            onClick={handleRegister} 
                            disabled={isRegistering || !regName.trim()}
                            className="w-full sm:w-auto"
                        >
                            {isRegistering ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Power className="w-4 h-4 mr-2" />}
                            {t("camera_manager.assimilate")}
                        </Button>
                    </CardContent>
                </Card>
            )}

            {/* LISTA DISPOSITIVI */}
            <div className="flex flex-col gap-2 flex-1 min-h-0">
                <div className="flex justify-between items-center px-1">
                    <Label className="text-xs text-muted-foreground uppercase tracking-wider">{t("camera_manager.connected_nodes")}</Label>
                    {isLoading && <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />}
                </div>
                
                <ScrollArea className="flex-1 border rounded-md bg-muted/10 p-4">
                    {Object.keys(devices).length === 0 ? (
                        <div className="text-center text-muted-foreground py-8">
                            {t("camera_manager.no_devices")}
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {Object.entries(devices).map(([id, dev]) => {
                                const isBound = dev.ip && ipBindings[dev.ip];
                                const isRecordingThis = recordingDeviceId === id;
                                const isEditing = editingDeviceId === id;
                                
                                return (
                                    <Card key={id} className={`relative overflow-hidden transition-all ${id === myDeviceId ? 'border-primary/40 bg-primary/5' : ''} ${dev.status === 'offline' ? 'opacity-60 grayscale' : ''}`}>
                                        {/* Indicatore Focus Attivo */}
                                        {activeFocusId === id && (
                                            <div className="absolute top-0 right-0 p-1 bg-primary text-primary-foreground rounded-bl-lg shadow-sm z-10">
                                                <Eye className="w-4 h-4" />
                                            </div>
                                        )}
                                        
                                        <CardHeader className="p-3 pb-1">
                                            <div className="flex justify-between items-start">
                                                <div className="flex items-center gap-2">
                                                    <div className={`p-2 rounded-full ${dev.status === 'online' ? 'bg-green-500/10 text-green-500' : 'bg-gray-500/10 text-gray-500'}`}>
                                                        {getDeviceIcon(dev.type)}
                                                    </div>
                                                    
                                                    {isEditing ? (
                                                        <div className="flex flex-col gap-1">
                                                            <Input 
                                                                value={editName} 
                                                                onChange={(e) => setEditName(e.target.value)} 
                                                                className="h-6 text-xs w-32"
                                                                placeholder={t("camera_manager.edit_name")}
                                                            />
                                                        </div>
                                                    ) : (
                                                        <div>
                                                            <CardTitle className="text-sm font-bold flex items-center gap-2">
                                                                {dev.name}
                                                                {isBound && <Lock className="w-3 h-3 text-yellow-500" title={t("camera_manager.ip_bound")} />}
                                                            </CardTitle>
                                                            <CardDescription className="text-[10px] font-mono truncate max-w-[150px]">
                                                                {id === myDeviceId ? t("camera_manager.this_device") : id.slice(0, 8)}
                                                            </CardDescription>
                                                        </div>
                                                    )}
                                                </div>
                                                
                                                <div className="flex items-center gap-1">
                                                    {isEditing ? (
                                                        <>
                                                            <Button variant="ghost" size="icon" className="h-6 w-6 text-green-500" onClick={saveEditing}><Save className="w-3 h-3" /></Button>
                                                            <Button variant="ghost" size="icon" className="h-6 w-6 text-red-500" onClick={cancelEditing}><X className="w-3 h-3" /></Button>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <Badge variant={dev.status === 'online' ? 'default' : 'secondary'} className="text-[10px] uppercase mr-1">
                                                                {dev.status}
                                                            </Badge>
                                                            <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-primary" onClick={() => startEditing(dev, id)}>
                                                                <Pencil className="w-3 h-3" />
                                                            </Button>
                                                            <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-destructive" onClick={() => deleteDevice(id)}>
                                                                <Trash2 className="w-3 h-3" />
                                                            </Button>
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                        </CardHeader>
                                        
                                        <CardContent className="p-3 pt-2 flex flex-col gap-2">
                                            {/* IP Info & Binding Controls */}
                                            <div className="flex items-center justify-between bg-muted/30 px-2 py-1 rounded text-xs">
                                                <div className="flex items-center gap-1 text-muted-foreground">
                                                    <Wifi className="w-3 h-3" />
                                                    {isEditing ? (
                                                        <Input 
                                                            value={editIp} 
                                                            onChange={(e) => setEditIp(e.target.value)} 
                                                            className="h-6 text-xs w-32 font-mono p-1 border border-primary/30 bg-background rounded"
                                                            placeholder={t("camera_manager.ip_address")}
                                                        />
                                                    ) : (
                                                        <span className="font-mono">{dev.ip || t("camera_manager.unknown_ip")}</span>
                                                    )}
                                                </div>
                                                
                                                {!isEditing && dev.ip && (
                                                    isBound ? (
                                                        <Button 
                                                            variant="ghost" 
                                                            size="icon" 
                                                            className="h-5 w-5 text-yellow-500 hover:text-destructive"
                                                            onClick={() => handleUnbindIp(dev.ip!)}
                                                            title={t("camera_manager.unbind_ip")}
                                                        >
                                                            <Unlock className="w-3 h-3" />
                                                        </Button>
                                                    ) : (
                                                        <Button 
                                                            variant="ghost" 
                                                            size="icon" 
                                                            className="h-5 w-5 text-muted-foreground hover:text-primary"
                                                            onClick={() => handleBindIp(dev.ip!, id, dev.name)}
                                                            title={t("camera_manager.ip_bound_desc_short")}
                                                        >
                                                            <Lock className="w-3 h-3" />
                                                        </Button>
                                                    )
                                                )}
                                            </div>

                                            {/* Action Controls (Focus & Intercom) */}
                                            {dev.status === 'online' && id !== myDeviceId && !isEditing && (
                                                <div className="flex gap-2 mt-1">
                                                    {activeFocusId !== id && (
                                                        <Button 
                                                            size="sm" 
                                                            variant="secondary" 
                                                            className="h-8 text-xs flex-1"
                                                            onClick={() => handleForceFocus(id)}
                                                        >
                                                            <MapPin className="w-3 h-3 mr-1" /> {t("camera_manager.summon")}
                                                        </Button>
                                                    )}
                                                    
                                                    {/* INTERCOM BUTTON (PUSH-TO-TALK) */}
                                                    <Button
                                                        size="sm"
                                                        variant={isRecordingThis ? "destructive" : "outline"}
                                                        className={`h-8 text-xs flex-1 ${isRecordingThis ? "animate-pulse" : ""}`}
                                                        onMouseDown={() => startIntercom(id)}
                                                        onMouseUp={stopIntercom}
                                                        onMouseLeave={stopIntercom}
                                                        onTouchStart={(e) => { e.preventDefault(); startIntercom(id); }}
                                                        onTouchEnd={(e) => { e.preventDefault(); stopIntercom(); }}
                                                    >
                                                        {isRecordingThis ? <Mic className="w-3 h-3 mr-1" /> : <MicOff className="w-3 h-3 mr-1" />}
                                                        {isRecordingThis ? t("camera_manager.speaking") : t("camera_manager.speak")}
                                                    </Button>
                                                </div>
                                            )}
                                            
                                            {activeFocusId === id && (
                                                <div className="h-7 flex items-center justify-center w-full text-xs text-primary font-medium bg-primary/10 rounded-md mt-1">
                                                    {t("camera_manager.active_presence")}
                                                </div>
                                            )}
                                        </CardContent>
                                    </Card>
                                );
                            })}
                        </div>
                    )}
                </ScrollArea>
            </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>{t("camera_manager.close")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};