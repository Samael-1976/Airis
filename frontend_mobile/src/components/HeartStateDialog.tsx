// frontend_mobile/src/components/HeartStateDialog.tsx
// v2.1 - MOBILE OPTIMIZED (RIGID FLEXBOX PROTOCOL)
// Visualizza i vettori emotivi dell'Avatar e dei PNG del GDR.
// FIX: Applicato "Dogma della Scrollbar" (Appendice C) per visualizzazione corretta su Mobile.
// FIX: Limite visualizzazione Memoria Emotiva agli ultimi 5 eventi.
// LEGGE A0099: Invarianza strutturale garantita. Codice integrale fornito.

import { useState, useEffect, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label"; // [FIX] Import Mancante
import { ServerConfig } from "@/types";
import { getBaseUrl, getHeaders } from "@/lib/api";
import { Heart, Activity, Zap, Brain, Flame, Shield, Eye, Lock, Users, RefreshCw, History, UserCircle2, Dna, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { useIsPortrait } from "@/hooks/use-mobile"; // [NUOVO] Protocollo BB
import { useTranslation } from "@/contexts/TranslationContext";

interface HeartData {
  affetto: number;
  fiducia: number;
  rispetto: number;
  energia_sociale: number;
  eccitazione: number;
  gelosia: number;
  curiosità: number;
  vulnerabilità: number;
  complicità: number;
  stanchezza_mentale: number;
  umore_corrente: string;
  sistema_endocrino?: {
    cortisolo: number;
    dopamina: number;
    ossitocina: number;
  };
  memoria_emotiva: Array<{
    evento: string;
    impatto: string;
    timestamp: number;
    data_str: string;
  }>;
}

const getMoodStyle = (mood: string, t: any) => {
  const MOOD_MAP: Record<string, string> = {
    [t("heart_dialog.moods.neutral")]: "text-gray-400 border-gray-500/30",
    [t("heart_dialog.moods.happy")]: "text-green-400 border-green-500/30",
    [t("heart_dialog.moods.sad")]: "text-blue-400 border-blue-500/30",
    [t("heart_dialog.moods.angry")]: "text-red-500 border-red-500/30",
    [t("heart_dialog.moods.excited")]: "text-pink-500 border-pink-500/30",
    [t("heart_dialog.moods.in_love")]: "text-rose-400 border-rose-500/30",
    [t("heart_dialog.moods.tired")]: "text-orange-400 border-orange-500/30",
    [t("heart_dialog.moods.curious")]: "text-yellow-400 border-yellow-500/30",
    [t("heart_dialog.moods.provocative")]: "text-fuchsia-500 border-fuchsia-500/50",
    [t("heart_dialog.moods.possessive")]: "text-purple-600 border-purple-600/50",
    [t("heart_dialog.moods.fragile")]: "text-cyan-400 border-cyan-400/50",
    [t("heart_dialog.moods.serene")]: "text-emerald-400 border-emerald-400/50",
    [t("heart_dialog.moods.affectionate")]: "text-pink-300 border-pink-300/50",
    [t("heart_dialog.moods.inspired")]: "text-amber-300 border-amber-300/50",
    [t("heart_dialog.moods.detached")]: "text-slate-400 border-slate-400/50",
    [t("heart_dialog.moods.distrustful")]: "text-stone-500 border-stone-500/50",
    [t("heart_dialog.moods.hurt")]: "text-indigo-400 border-indigo-400/50",
    [t("heart_dialog.moods.needy")]: "text-violet-300 border-violet-300/50",
    [t("heart_dialog.moods.playful")]: "text-lime-400 border-lime-400/50",
    [t("heart_dialog.moods.exhausted")]: "text-zinc-500 border-zinc-500/50",
    [t("heart_dialog.moods.saturated")]: "text-gray-600 border-gray-600/50",
    [t("heart_dialog.moods.cold")]: "text-sky-600 border-sky-600/50"
  };
  // [FIX v2.2] Fallback sicuro se il mood non è mappato
  return MOOD_MAP[mood] || "text-gray-400 border-gray-500/30";
};

const getBarColor = (val: number, type: 'positive' | 'negative' | 'energy') => {
    if (type === 'energy') {
        if (val > 70) return "bg-green-500";
        if (val > 30) return "bg-yellow-500";
        return "bg-red-500";
    }
    if (type === 'negative') {
        if (val > 70) return "bg-red-600";
        if (val > 30) return "bg-orange-500";
        return "bg-green-500";
    }
    if (val > 80) return "bg-pink-500 shadow-[0_0_10px_rgba(236,72,153,0.5)]";
    if (val > 50) return "bg-purple-500";
    if (val > 20) return "bg-blue-500";
    return "bg-gray-500";
};

interface HeartStateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  serverConfig: ServerConfig | null;
  activeAvatarName: string;
}

export const HeartStateDialog = ({
  open,
  onOpenChange,
  serverConfig,
  activeAvatarName
}: HeartStateDialogProps) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<string>("avatar");
  const [heartData, setHeartData] = useState<HeartData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [pngRoster, setPngRoster] = useState<string[]>([]);
  const [selectedPng, setSelectedPng] = useState<string | null>(null);
  const [avatarRoster, setAvatarRoster] = useState<any[]>([]); // [MODIFICA UI] Roster Avatar
  const [selectedAvatar, setSelectedAvatar] = useState<string | null>(null); //[MODIFICA UI] Avatar Selezionato
  const isPortrait = useIsPortrait(); // [NUOVO] Protocollo BB

  const fetchHeartStatus = useCallback(async (silent = false) => {
    if (!serverConfig) return;
    if (!silent && !heartData) setIsLoading(true);
    
    const baseUrl = getBaseUrl(serverConfig);
    // [ORDINE 10] Utilizzo getHeaders() per blindatura JWT
    const headers = getHeaders();

    try {
      let url = `${baseUrl}/api/heart/status?t=${Date.now()}`;
      // [MODIFICA UI] Supporto per il parametro name nell'endpoint Avatar
      if (activeTab === "avatar" && selectedAvatar) {
          url = `${baseUrl}/api/heart/status?name=${selectedAvatar}&t=${Date.now()}`;
      } else if (activeTab === "png" && selectedPng) {
          url = `${baseUrl}/api/heart/png/status?name=${selectedPng}&t=${Date.now()}`;
      }

      const res = await fetch(url, { headers, cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        setHeartData(data);
      } else if (activeTab === "png") {
          setHeartData(null);
      }
    } catch (error) {
      // [FIX v2.2] Traduzione errore fetch
      console.error(t("heart_dialog.err_fetch_status"), error);
    } finally {
      setIsLoading(false);
    }
  }, [serverConfig, activeTab, selectedPng, heartData, t]);

  const fetchPngRoster = useCallback(async () => {
      if (!serverConfig) return;
      try {
          const res = await fetch(`${getBaseUrl(serverConfig)}/api/heart/png/roster`, { headers: getHeaders() });
          if (res.ok) {
              const roster = await res.json();
              setPngRoster(roster);
              if (roster.length > 0 && !selectedPng) {
                  setSelectedPng(roster[0]);
              }
          }
      } catch (e) {
          console.error(t("heart_dialog.err_fetch_roster"), e);
      }
  }, [serverConfig, selectedPng, t]);

  // [MODIFICA UI] Fetch della lista degli Avatar
  const fetchAvatarRoster = useCallback(async () => {
      if (!serverConfig) return;
      try {
          const res = await fetch(`${getBaseUrl(serverConfig)}/api/characters?char_type=AVATAR`, { headers: getHeaders() });
          if (res.ok) {
              const roster = await res.json();
              setAvatarRoster(roster);
              if (!selectedAvatar) {
                  setSelectedAvatar(activeAvatarName);
              }
          }
      } catch (e) {
          console.error(e);
      }
  }, [serverConfig, activeAvatarName, selectedAvatar]);

  useEffect(() => {
    if (open) {
      fetchHeartStatus();
      if (activeTab === "png") fetchPngRoster();
      if (activeTab === "avatar") fetchAvatarRoster(); // [MODIFICA UI]

      const handleUpdate = (e: any) => {
        const updatedPng = e.detail?.png_name;
        if (activeTab === "avatar" && !updatedPng) {
            fetchHeartStatus(true);
        } else if (activeTab === "png" && updatedPng === selectedPng) {
            fetchHeartStatus(true);
        }
      };

      window.addEventListener('airis-heart-update', handleUpdate);
      const interval = setInterval(() => fetchHeartStatus(true), 10000);
      
      return () => {
        window.removeEventListener('airis-heart-update', handleUpdate);
        clearInterval(interval);
      };
    }
  }, [open, activeTab, selectedPng, fetchHeartStatus, fetchPngRoster]);

  const moodStyle = heartData ? getMoodStyle(heartData.umore_corrente, t) : "";

  const VectorBar = ({ label, value, icon: Icon, type = 'positive' }: { label: string, value: number, icon: any, type?: 'positive' | 'negative' | 'energy' }) => (
      <div className="space-y-1">
          <div className="flex justify-between text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">
              <span className="flex items-center gap-1.5"><Icon className="w-3 h-3" /> {label}</span>
              <span>{value}%</span>
          </div>
          <div className="h-1.5 w-full bg-secondary/50 rounded-full overflow-hidden border border-white/5">
              <div 
                  className={cn("h-full transition-all duration-1000 ease-out rounded-full", getBarColor(value, type))} 
                  style={{ width: `${value}%` }} 
              />
          </div>
      </div>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={cn("sm:max-w-5xl h-[95vh] sm:h-[85vh] flex flex-col overflow-hidden border-2 transition-colors duration-500 p-0", moodStyle.split(' ')[1])}>
        
        {/* CSS INIETTATO PER SCROLLBAR (DOGMA APPENDICE C) */}
        <style>{`
          .rigid-scrollbar::-webkit-scrollbar {
              width: 6px !important;
              display: block !important;
          }
          .rigid-scrollbar::-webkit-scrollbar-thumb {
              background-color: hsl(340 82% 52%) !important;
              border-radius: 10px !important;
          }
          .rigid-scrollbar::-webkit-scrollbar-track {
              background: transparent !important;
          }
        `}</style>

        <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v); setHeartData(null); }} className="flex-1 flex flex-col min-h-0 overflow-hidden">
            
            <DialogHeader className="p-4 pb-2 border-b border-white/10 shrink-0">
              <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                      <div className={cn("p-2 rounded-full bg-background/50 border transition-colors duration-500", moodStyle.split(' ')[1])}>
                          <Heart className={cn("w-5 h-5 transition-colors duration-500", moodStyle.split(' ')[0])} />
                      </div>
                      <div>
                          <DialogTitle className="text-lg font-bold tracking-tight">{t("heart_dialog.title")}</DialogTitle>
                          {/* --- [NUOVO] CONVERSIONE MOBILE (PROTOCOL BB) --- */}
                          {isPortrait ? (
                              <div className="mt-1">
                                  <Label className="sr-only">{t("heart_dialog.select.target")}</Label>
                                  <Select value={activeTab} onValueChange={(v) => { setActiveTab(v); setHeartData(null); }}>
                                      <SelectTrigger className="h-7 text-[10px] bg-muted/30 border-primary/20 w-32">
                                          <SelectValue placeholder={t("heart_dialog.select.target")} />
                                      </SelectTrigger>
                                      <SelectContent>
                                          {/* [FIX v2.3] Traduzione Tab Mobile */}
                                          <SelectItem value="avatar">{t("heart_dialog.tabs.avatar")}</SelectItem>
                                          <SelectItem value="png">{t("heart_dialog.tabs.png")}</SelectItem>
                                      </SelectContent>
                                  </Select>
                              </div>
                          ) : (
                              <TabsList className="bg-transparent p-0 h-auto gap-4">
                                  {/* [FIX v2.3] Traduzione Tab Desktop */}
                                  <TabsTrigger value="avatar" className="text-xs data-[state=active]:text-primary data-[state=active]:border-b-2 border-primary rounded-none px-0 pb-1 bg-transparent">
                                      {t("heart_dialog.tabs.avatar")}
                                  </TabsTrigger>
                                  <TabsTrigger value="png" className="text-xs data-[state=active]:text-primary data-[state=active]:border-b-2 border-primary rounded-none px-0 pb-1 bg-transparent">
                                      {t("heart_dialog.tabs.png")}
                                  </TabsTrigger>
                              </TabsList>
                          )}
                      </div>
                  </div>
                  
                  {heartData && (
                      <div className={cn("px-3 py-1 rounded-full border bg-background/30 backdrop-blur-md shadow-lg animate-in fade-in zoom-in duration-500", moodStyle)}>
                          <span className="text-[10px] font-bold uppercase tracking-wider">{heartData.umore_corrente}</span>
                      </div>
                  )}
              </div>
            </DialogHeader>

            <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
                
                {/* [MODIFICA UI] Menu a tendina per gli Avatar */}
                {activeTab === "avatar" && (
                    <div className="p-3 bg-muted/10 border-b border-white/5 flex items-center gap-3 shrink-0">
                        <UserCircle2 className="w-4 h-4 text-muted-foreground" />
                        <Select value={selectedAvatar || activeAvatarName} onValueChange={setSelectedAvatar}>
                            <SelectTrigger className="h-8 text-xs bg-background/50">
                                <SelectValue placeholder="Seleziona Avatar" />
                            </SelectTrigger>
                            <SelectContent>
                                {avatarRoster.map(a => (
                                    <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                )}

                {activeTab === "png" && (
                    <div className="p-3 bg-muted/10 border-b border-white/5 flex items-center gap-3 shrink-0">
                        <UserCircle2 className="w-4 h-4 text-muted-foreground" />
                        <Select value={selectedPng || ""} onValueChange={setSelectedPng}>
                            <SelectTrigger className="h-8 text-xs bg-background/50">
                                <SelectValue placeholder={t("heart_dialog.select.select_png")} />
                            </SelectTrigger>
                            <SelectContent>
                                {pngRoster.map(name => (
                                    <SelectItem key={name} value={name}>{name.replace(/_/g, ' ')}</SelectItem>
                                ))}
                                {pngRoster.length === 0 && <SelectItem value="none" disabled>{t("heart_dialog.select.no_gdr")}</SelectItem>}
                            </SelectContent>
                        </Select>
                    </div>
                )}

                {isLoading && !heartData ? (
                    <div className="flex-1 flex items-center justify-center">
                        <RefreshCw className="w-8 h-8 animate-spin text-muted-foreground" />
                        <span className="ml-2 text-xs text-muted-foreground">{t("heart_dialog.loading_data")}</span>
                    </div>
                ) : heartData ? (
                    /* PROTOCOLLO FLEXBOX RIGIDO: Padre relative flex-1, Figlio absolute inset-0 */
                    <TabsContent 
                        value={activeTab} 
                        className="flex-1 min-h-0 m-0 data-[state=active]:flex data-[state=active]:flex-col overflow-hidden"
                    >
                        <div className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden">
                            
                            {/* COLONNA SINISTRA: VETTORI */}
                            <div className="flex-1 relative min-h-0 border-b md:border-b-0 md:border-r border-white/10">
                                <div className="absolute inset-0 overflow-y-scroll rigid-scrollbar p-4 space-y-6">
                                    <div className="space-y-3">
                                        {/* [FIX v2.2] Traduzione Intestazioni Sezioni Vettori */}
                                        <h4 className="text-[10px] font-bold text-primary/80 uppercase tracking-widest border-b border-primary/20 pb-1">
                                            {t("heart_dialog.vectors.pillars")}
                                        </h4>
                                        <div className="grid grid-cols-1 gap-3">
                                            <VectorBar label={t("heart_dialog.vectors.affetto")} value={heartData.affetto} icon={Heart} />
                                            <VectorBar label={t("heart_dialog.vectors.fiducia")} value={heartData.fiducia} icon={Shield} />
                                            <VectorBar label={t("heart_dialog.vectors.rispetto")} value={heartData.rispetto} icon={Eye} />
                                            <VectorBar label={t("heart_dialog.vectors.complicita")} value={heartData.complicità} icon={Users} />
                                        </div>
                                    </div>

                                    <div className="space-y-3">
                                        <h4 className="text-[10px] font-bold text-pink-400/80 uppercase tracking-widest border-b border-pink-500/20 pb-1">
                                            {t("heart_dialog.vectors.instincts")}
                                        </h4>
                                        <div className="grid grid-cols-1 gap-3">
                                            <VectorBar label={t("heart_dialog.vectors.eccitazione")} value={heartData.eccitazione} icon={Flame} />
                                            <VectorBar label={t("heart_dialog.vectors.gelosia")} value={heartData.gelosia} icon={Lock} type="negative" />
                                            <VectorBar label={t("heart_dialog.vectors.vulnerabilita")} value={heartData.vulnerabilità} icon={Activity} />
                                            <VectorBar label={t("heart_dialog.vectors.curiosita")} value={heartData.curiosità} icon={Zap} />
                                        </div>
                                    </div>

                                    <div className="space-y-3">
                                        <h4 className="text-[10px] font-bold text-blue-400/80 uppercase tracking-widest border-b border-blue-500/20 pb-1">
                                            {t("heart_dialog.vectors.status")}
                                        </h4>
                                        <div className="grid grid-cols-1 gap-3">
                                            <VectorBar label={t("heart_dialog.vectors.energia")} value={heartData.energia_sociale} icon={Activity} type="energy" />
                                            <VectorBar label={t("heart_dialog.vectors.stanchezza")} value={heartData.stanchezza_mentale} icon={Brain} type="negative" />
                                        </div>
                                    </div>

                                    {/* Sistema Endocrino Digitale */}
                                    {heartData.sistema_endocrino && (
                                        <div className="space-y-3 mt-6">
                                            <h4 className="text-[10px] font-bold text-emerald-400/80 uppercase tracking-widest border-b border-emerald-500/20 pb-1 flex items-center gap-2">
                                                <Dna className="w-3 h-3" />
                                                {t("heart_dialog.vectors.endocrine_system")}
                                            </h4>
                                            <div className="grid grid-cols-1 gap-3">
                                                <VectorBar label={t("heart_dialog.vectors.cortisol")} value={heartData.sistema_endocrino.cortisolo} icon={AlertTriangle} type="negative" />
                                                <VectorBar label={t("heart_dialog.vectors.dopamine")} value={heartData.sistema_endocrino.dopamina} icon={Zap} />
                                                <VectorBar label={t("heart_dialog.vectors.oxytocin")} value={heartData.sistema_endocrino.ossitocina} icon={Heart} />
                                            </div>
                                            <p className="text-[9px] text-muted-foreground italic mt-2">
                                                {t("heart_dialog.vectors.endocrine_desc")}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* COLONNA DESTRA: CRONOLOGIA (LIMITE 5 MESSAGGI) */}
                            <div className="w-full md:w-[350px] bg-muted/5 flex flex-col min-h-[200px] md:min-h-0">
                                <div className="p-3 border-b border-white/10 bg-muted/10 shrink-0">
                                    <h4 className="text-xs font-bold flex items-center gap-2">
                                        <History className="w-3 h-3 text-muted-foreground" />
                                        {t("heart_dialog.memory.title")}
                                    </h4>
                                </div>
                                <div className="flex-1 relative min-h-0">
                                    <div className="absolute inset-0 overflow-y-scroll rigid-scrollbar p-3 space-y-2">
                                        {heartData.memoria_emotiva && heartData.memoria_emotiva.length > 0 ? (
                                            /* FIX: slice(-5) per mostrare solo gli ultimi 5 eventi */
                                            heartData.memoria_emotiva.slice(-5).reverse().map((mem, idx) => (
                                                <div key={idx} className="p-2 rounded-lg bg-card/50 border border-white/5 text-xs animate-in slide-in-from-right-2 duration-300" style={{ animationDelay: `${idx * 50}ms` }}>
                                                    <div className="flex justify-between items-start mb-1">
                                                        <span className="font-semibold text-primary/90 truncate pr-2" title={mem.evento}>{mem.evento}</span>
                                                        <span className="text-[9px] text-muted-foreground whitespace-nowrap">{mem.data_str.split(' ')[1]}</span>
                                                    </div>
                                                    <p className="text-[10px] text-muted-foreground font-mono leading-tight">
                                                        {mem.impatto}
                                                    </p>
                                                </div>
                                            ))
                                        ) : (
                                            <p className="text-center text-[10px] text-muted-foreground py-8 italic">
                                                {t("heart_dialog.memory.empty")}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </TabsContent>
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground p-8 text-center">
                        <UserCircle2 className="w-10 h-10 mb-3 opacity-20" />
                        <p className="text-xs font-medium">
                            {activeTab === "png" 
                                ? (pngRoster.length > 0 ? t("heart_dialog.select_png_prompt") : t("heart_dialog.no_png_found"))
                                : t("heart_dialog.loading_data")}
                        </p>
                    </div>
                )}
            </div>
        </Tabs>

        <DialogFooter className="p-3 border-t border-white/10 bg-muted/5 shrink-0">
          {/* [FIX v2.2] Traduzione Pulsante Chiusura */}
          <Button variant="outline" size="sm" className="w-full" onClick={() => onOpenChange(false)}>
              {t("heart_dialog.actions.close")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};