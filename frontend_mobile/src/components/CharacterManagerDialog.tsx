// frontend_mobile/src/components/CharacterManagerDialog.tsx
// v4.0 - UI CONSOLIDATION (SOULS & WORLDS)
// ADD: Tab "Souls" e "Worlds" per la gestione Export/Import.
// ADD: Logica di MultiSelectExport integrata direttamente nel dialogo.
// MANTENUTO: Gestione PG, PNG, Avatar, Styles.
// LEGGE A0099: Invarianza strutturale garantita. Codice integrale fornito.

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ServerConfig } from "@/types";
import { toast } from "@/components/ui/sonner";
import { Loader2, UserPlus, Edit, Trash2, Shirt, Snowflake, Sun, Leaf, Circle, UserCheck, UserMinus, Download, Upload, CheckSquare, Square, Ghost, Globe, Sparkles, Dices } from "lucide-react";
import { useTranslation } from "@/contexts/TranslationContext";
import { getBaseUrl, getHeaders } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useIsPortrait } from "@/hooks/use-mobile"; // [NUOVO] Per Protocollo BB
import { Switch } from "@/components/ui/switch"; // [NUOVO v27.0]

// Definiamo la struttura del personaggio che ci arriva dal server
interface Character {
  id: string;
  name: string;
  avatar_url: string | null;
  is_unified_avatar?: boolean; // [NUOVO v124.0] Identifica l'Anima nel roster PNG
}

interface StyleData {
  active_set: string;
  available_sets: string[];
  current_season: string;
  viewing_season: string;
}

interface CharacterManagerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  type: "PG" | "PNG" | "AVATAR";
  onTypeChange?: (type: "PG" | "PNG" | "AVATAR") => void;
  serverConfig: ServerConfig | null;
  onAdd: () => void;
  onEdit: (characterId: string) => void;
  onDelete: (characterId: string) => void;
  // Nuove props per Export/Import
  onExport: (type: 'pure' | 'world', avatars: string[], lore?: string) => Promise<void>;
  onImport: () => void;
}

export const CharacterManagerDialog = ({
  open,
  onOpenChange,
  type,
  onTypeChange,
  serverConfig,
  onAdd,
  onEdit,
  onDelete,
  onExport,
  onImport,
}: CharacterManagerDialogProps) => {
  const { t } = useTranslation();
  const [characters, setCharacters] = useState<Character[]>([]);
  const [activeRoster, setActiveRoster] = useState<string[]>([]); 
  const [selectedCharacterId, setSelectedCharacterId] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  
  const [activeTab, setActiveTab] = useState<string>(type);
  const [styleData, setStyleData] = useState<StyleData | null>(null);
  const [selectedStyle, setSelectedStyle] = useState<string>("");
  const [viewingSeason, setViewingSeason] = useState<string>(""); 
  const [isStyleLoading, setIsStyleLoading] = useState(false);
  const[isSavingStyle, setIsSavingStyle] = useState(false);
  const [isTogglingRoster, setIsTogglingRoster] = useState<string | null>(null); 
  
  // --- [NUOVO v27.0] STATO MODALITÀ CAMPAGNA ---
  const [isCampaignMode, setIsCampaignMode] = useState(false);
  const [isTogglingCampaign, setIsTogglingCampaign] = useState(false);

  const isPortrait = useIsPortrait(); // [NUOVO] Rilevamento orientamento

  useEffect(() => {
      if (open) {
          // Se il tab corrente non è uno di quelli speciali, resetta al tipo passato
          if (!["STYLES", "SOULS", "WORLDS"].includes(activeTab)) {
              setActiveTab(type);
          }
      }
  }, [open, type]);

  const fetchData = async () => {
    if (open && serverConfig) {
      // Se siamo in tab speciali, non facciamo fetch dei personaggi standard qui
      if (["STYLES", "SOULS", "WORLDS"].includes(activeTab)) {
          if (activeTab === "STYLES") {
              // Per Styles serve comunque la lista avatar
              const targetType = "AVATAR";
              setIsLoading(true);
              const serverUrl = getBaseUrl(serverConfig);
              const headers = getHeaders();
              try {
                const charsRes = await fetch(`${serverUrl}/api/characters?char_type=${targetType}`, { headers });
                if (!charsRes.ok) throw new Error(`Failed to fetch ${targetType} list`);
                const charsData: Character[] = await charsRes.json();
                setCharacters(charsData);
              } catch (error) {
                console.error(`Error fetching data:`, error);
              } finally {
                setIsLoading(false);
              }
          }
          return;
      }

      const targetType = activeTab;
      
      setIsLoading(true);
      const serverUrl = getBaseUrl(serverConfig);
      const headers = getHeaders();

      try {
        const charsRes = await fetch(`${serverUrl}/api/characters?char_type=${targetType}`, { headers });
        if (!charsRes.ok) throw new Error(`Failed to fetch ${targetType} list`);
        const charsData: Character[] = await charsRes.json();
        setCharacters(charsData);

        if (targetType !== "AVATAR") {
            const rosterRes = await fetch(`${serverUrl}/api/rpg/active-roster`, { headers });
            if (rosterRes.ok) {
                const rosterData: string[] = await rosterRes.json();
                setActiveRoster(rosterData);
            }
            
            // Fetch Campaign Mode
            const campaignRes = await fetch(`${serverUrl}/api/rpg/campaign-mode`, { headers });
            if (campaignRes.ok) {
                const campaignData = await campaignRes.json();
                setIsCampaignMode(campaignData.enabled);
            }
        } else {
            setActiveRoster([]);
        }

      } catch (error) {
        console.error(t("character_manager.err_fetching_data"), error);
        toast.error(t("character_manager.error_load_list"), {
          description: t("character_manager.error_server_unreachable"),
        });
      } finally {
        setIsLoading(false);
      }
    }
  };

  useEffect(() => {
    fetchData();
  }, [open, serverConfig, activeTab]);

  useEffect(() => {
      if (activeTab === "STYLES" && selectedCharacterId && serverConfig) {
          setIsStyleLoading(true);
          const serverUrl = getBaseUrl(serverConfig);
          const headers = getHeaders();

          let url = `${serverUrl}/api/avatars/${selectedCharacterId}/styles`;
          if (viewingSeason) {
              url += `?season=${viewingSeason}`;
          }

          fetch(url, { headers })
            .then(res => {
                if (!res.ok) throw new Error(t("character_manager.err_fetch_styles"));
                return res.json();
            })
            .then((data: StyleData) => {
                setStyleData(data);
                setSelectedStyle(data.active_set);
                if (!viewingSeason) {
                    setViewingSeason(data.viewing_season);
                }
            })
            .catch(err => {
                console.error(t("character_manager.err_fetching_data"), err);
                toast.error(t("character_manager.error_load_style"));
            })
            .finally(() => setIsStyleLoading(false));
      }
  }, [selectedCharacterId, activeTab, serverConfig, viewingSeason]);

  const handleSaveStyle = async () => {
      if (!selectedCharacterId || !selectedStyle || !serverConfig) return;
      
      setIsSavingStyle(true);
      const serverUrl = getBaseUrl(serverConfig);
      const headers = { 
          ...getHeaders(),
          "Content-Type": "application/json"
      };

      try {
          const res = await fetch(`${serverUrl}/api/avatars/${selectedCharacterId}/style`, {
              method: 'POST',
              headers: headers,
              body: JSON.stringify({ active_set: selectedStyle })
          });
          
          if (!res.ok) throw new Error(t("character_manager.err_save_style"));
          
          toast.success(t("character_manager.success_style_updated"), {
              description: t("character_manager.success_style_desc", { style: selectedStyle })
          });
      } catch (error: any) {
          toast.error(t("character_manager.error_save_style"), { description: error.message });
      } finally {
          setIsSavingStyle(false);
      }
  };

  // --- [NUOVO] EFFETTO DI ASCOLTO EVENTO ROSTER SYNC ---
  useEffect(() => {
    const handleRosterUpdate = () => {
      console.log("[CharacterManagerDialog] Ricevuto evento airis-roster-update, ricarico la lista...");
      fetchData();
    };

    window.addEventListener('airis-roster-update', handleRosterUpdate);
    return () => {
      window.removeEventListener('airis-roster-update', handleRosterUpdate);
    };
  }, [activeTab]);

  const handleToggleRoster = async (char: Character) => {
      if (!serverConfig) return;
      
      // [FIX] Normalizzazione per confronto robusto (ignora underscore e maiuscole)
      const isInScene = activeRoster.some((r: string) => r && char.name && r.replace(/_/g, ' ').toLowerCase() === char.name.replace(/_/g, ' ').toLowerCase());
      const action = isInScene ? 'remove' : 'add';
      
      setIsTogglingRoster(char.id);
      const serverUrl = getBaseUrl(serverConfig);
      const headers = { ...getHeaders(), "Content-Type": "application/json" };

      try {
          const res = await fetch(`${serverUrl}/api/rpg/roster/toggle`, {
              method: 'POST',
              headers: headers,
              body: JSON.stringify({ 
                  char_name: char.name, 
                  action: action 
              })
          });
          
          if (!res.ok) throw new Error(t("character_manager.err_toggle_failed"));
          
          const data = await res.json();
          toast.success(data.message);
          
          // Nota: La rimozione o l'aggiunta fisica avverrà asincronamente in RAM su chat.py,
          // che poi invierà un WebSocket broadcast per attivare il reload tramite 'airis-roster-update'.
          // Chiamiamo comunque fetchData() locale per un feedback immediato nell'interfaccia.
          fetchData();
      } catch (error: any) {
          toast.error(t("character_manager.error_roster_update"), { description: error.message });
      } finally {
          setIsTogglingRoster(null);
      }
  };

  // ---[NUOVO v27.0] TOGGLE CAMPAIGN MODE ---
  const handleToggleCampaignMode = async (enabled: boolean) => {
      if (!serverConfig) return;
      setIsTogglingCampaign(true);
      const serverUrl = getBaseUrl(serverConfig);
      const headers = { ...getHeaders(), "Content-Type": "application/json" };

      try {
          const res = await fetch(`${serverUrl}/api/rpg/campaign-mode`, {
              method: 'POST',
              headers: headers,
              body: JSON.stringify({ enabled })
          });
          
          if (!res.ok) throw new Error(t("character_manager.err_toggle_failed_msg"));
          
          setIsCampaignMode(enabled);
          if (enabled) {
              toast.success(t("character_manager.campaign_activated"), { description: t("character_manager.dm_listening") });
          } else {
              toast.info(t("character_manager.campaign_deactivated"), { description: t("character_manager.free_roleplay") });
          }
      } catch (error: any) {
          toast.error(t("character_manager.error"), { description: error.message });
      } finally {
          setIsTogglingCampaign(false);
      }
  };

  const getSeasonIcon = (season: string) => {
      switch (season.toLowerCase()) {
          case 'winter': return <Snowflake className="w-4 h-4 text-blue-400" />;
          case 'summer': return <Sun className="w-4 h-4 text-yellow-400" />;
          case 'autumn': return <Leaf className="w-4 h-4 text-orange-400" />;
          case 'spring': return <Leaf className="w-4 h-4 text-green-400" />;
          case 'default': return <Circle className="w-4 h-4 text-gray-400" />;
          default: return null;
      }
  };

  const handleTabChange = (val: string) => {
      setActiveTab(val);
      setSelectedCharacterId("");
      setViewingSeason("");
      
      if (!["STYLES", "SOULS", "WORLDS"].includes(val) && onTypeChange) {
          onTypeChange(val as "PG" | "PNG" | "AVATAR");
      }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>{t("character_manager.title")}</DialogTitle>
          <DialogDescription>
            {t("character_manager.description")}
          </DialogDescription>
        </DialogHeader>

        <style>{`
            .airis-scrollbar {
                overflow-y: auto !important;
                scrollbar-width: thin;
                scrollbar-color: hsl(340 82% 52%) hsl(220 15% 10%);
                -webkit-overflow-scrolling: touch;
            }
            .airis-scrollbar::-webkit-scrollbar {
                width: 8px !important;
                height: 8px !important;
                display: block !important;
            }
            .airis-scrollbar::-webkit-scrollbar-track {
                background: hsl(220 15% 10%) !important;
                border-radius: 10px;
            }
            .airis-scrollbar::-webkit-scrollbar-thumb {
                background-color: hsl(340 82% 52%) !important;
                border-radius: 10px;
                border: 2px solid hsl(220 15% 10%);
            }
            .airis-scrollbar::-webkit-scrollbar-thumb:hover {
                background-color: hsl(340 82% 60%) !important;
            }
        `}</style>

        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full flex-1 flex flex-col overflow-hidden">
            
            {/* --- [NUOVO v27.0] MASTER SWITCH MODALITÀ CAMPAGNA --- */}
            {activeTab !== "STYLES" && activeTab !== "SOULS" && activeTab !== "WORLDS" && (
                <div className="px-6 pt-4 pb-2 shrink-0">
                    <div className={cn(
                        "flex items-center justify-between p-3 rounded-lg border transition-all",
                        isCampaignMode ? "bg-primary/10 border-primary/30" : "bg-muted/20 border-border/50"
                    )}>
                        <div className="space-y-0.5">
                            <Label className="text-sm font-bold flex items-center gap-2">
                                <Dices className={cn("w-4 h-4", isCampaignMode ? "text-primary" : "text-muted-foreground")} />
                                {t("character_manager.campaign_mode")}
                            </Label>
                            <p className="text-[10px] text-muted-foreground">
                                {t("character_manager.campaign_mode_desc")}
                            </p>
                        </div>
                        <div className="flex items-center gap-2">
                            {isTogglingCampaign && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
                            <Switch 
                                checked={isCampaignMode} 
                                onCheckedChange={handleToggleCampaignMode} 
                                disabled={isTogglingCampaign}
                            />
                        </div>
                    </div>
                </div>
            )}

            {/* --- [NUOVO] CONVERSIONE MOBILE (PROTOCOL BB) --- */}
            <div className="px-6 py-2 shrink-0">
                {isPortrait ? (
                    <div className="space-y-1">
                        <Label className="text-[10px] uppercase text-muted-foreground font-bold tracking-widest">{t("character_manager.section_label")}</Label>
                        <Select value={activeTab} onValueChange={handleTabChange}>
                            <SelectTrigger className="w-full bg-muted/50 border-primary/20">
                                <SelectValue placeholder={t("character_manager.select_category")} />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="PG">{t("character_manager.pg")}</SelectItem>
                                <SelectItem value="PNG">{t("character_manager.png")}</SelectItem>
                                <SelectItem value="AVATAR">{t("character_manager.avatar")}</SelectItem>
                                <SelectItem value="STYLES">{t("character_manager.styles")}</SelectItem>
                                <SelectItem value="SOULS">{t("character_manager.souls")}</SelectItem>
                                <SelectItem value="WORLDS">{t("character_manager.worlds")}</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                ) : (
                    <TabsList className="grid w-full grid-cols-6">
                        <TabsTrigger value="PG">{t("character_manager.tabs.pg")}</TabsTrigger>
                        <TabsTrigger value="PNG">{t("character_manager.tabs.png")}</TabsTrigger>
                        <TabsTrigger value="AVATAR">{t("character_manager.tabs.avatars")}</TabsTrigger>
                        <TabsTrigger value="STYLES">{t("character_manager.tabs.styles")}</TabsTrigger>
                        <TabsTrigger value="SOULS">{t("character_manager.tabs.souls")}</TabsTrigger>
                        <TabsTrigger value="WORLDS">{t("character_manager.tabs.worlds")}</TabsTrigger>
                    </TabsList>
                )}
            </div>
            
            <TabsContent value="PG" className="flex-1 overflow-hidden mt-2 px-6">
                <CharacterCrud 
                    isLoading={isLoading} 
                    characters={characters} 
                    activeRoster={activeRoster}
                    onAdd={onAdd} 
                    onEdit={onEdit} 
                    onDelete={onDelete} 
                    onToggleRoster={handleToggleRoster}
                    isToggling={isTogglingRoster}
                    type="PG"
                />
            </TabsContent>

            <TabsContent value="PNG" className="flex-1 overflow-hidden mt-4">
                <CharacterCrud 
                    isLoading={isLoading} 
                    characters={characters} 
                    activeRoster={activeRoster}
                    onAdd={onAdd} 
                    onEdit={onEdit} 
                    onDelete={onDelete} 
                    onToggleRoster={handleToggleRoster}
                    isToggling={isTogglingRoster}
                    type="PNG"
                />
            </TabsContent>
            
            <TabsContent value="AVATAR" className="flex-1 overflow-hidden mt-4">
                <CharacterCrud 
                    isLoading={isLoading} 
                    characters={characters} 
                    activeRoster={[]} 
                    onAdd={onAdd} 
                    onEdit={onEdit} 
                    onDelete={onDelete} 
                    onToggleRoster={handleToggleRoster}
                    isToggling={isTogglingRoster}
                    type="AVATAR"
                />
            </TabsContent>

            <TabsContent value="STYLES" className="flex-1 overflow-hidden mt-4">
                <div className="space-y-4 p-1">
                    <div className="space-y-2">
                        <Label>{t("character_manager.select_avatar")}</Label>
                        {isLoading ? (
                            <div className="flex items-center justify-center h-10 border rounded-md">
                                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                            </div>
                        ) : (
                            <Select value={selectedCharacterId} onValueChange={setSelectedCharacterId}>
                                <SelectTrigger>
                                    <SelectValue placeholder={t("character_manager.select_avatar_placeholder")} />
                                </SelectTrigger>
                                <SelectContent>
                                    {characters.map((char) => (
                                        <SelectItem key={char.id} value={char.id}>{char.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        )}
                    </div>

                    {selectedCharacterId && (
                        <div className="p-4 border rounded-lg bg-muted/20 space-y-4 animate-in fade-in slide-in-from-top-2">
                            {isStyleLoading ? (
                                <div className="flex justify-center py-4"><Loader2 className="animate-spin" /></div>
                            ) : styleData ? (
                                <>
                                    <div className="space-y-2">
                                        <Label>{t("character_manager.season_context")}</Label>
                                        <Select value={viewingSeason} onValueChange={setViewingSeason}>
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {['default', 'Winter', 'Spring', 'Summer', 'Autumn'].map((season) => (
                                                    <SelectItem key={season} value={season}>
                                                        <div className="flex items-center gap-2">
                                                            {getSeasonIcon(season)}
                                                            {season === 'default' ? t("character_manager.season_default") : season}
                                                        </div>
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <p className="text-xs text-muted-foreground">
                                            {t("character_manager.season_desc")}
                                        </p>
                                    </div>
                                    
                                    <div className="space-y-2">
                                        <Label>{t("character_manager.active_style")}</Label>
                                        <Select value={selectedStyle} onValueChange={setSelectedStyle}>
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {styleData.available_sets.map(set => (
                                                    <SelectItem key={set} value={set}>{set}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <p className="text-xs text-muted-foreground">
                                            {t("character_manager.style_desc")}
                                        </p>
                                    </div>

                                    <Button 
                                        className="w-full" 
                                        onClick={handleSaveStyle} 
                                        disabled={isSavingStyle || selectedStyle === styleData.active_set}
                                    >
                                        {isSavingStyle ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Shirt className="mr-2 h-4 w-4" />}
                                        {t("character_manager.apply_style")}
                                    </Button>
                                </>
                            ) : (
                                <p className="text-sm text-red-400 text-center">{t("character_manager.error_load_style")}</p>
                            )}
                        </div>
                    )}
                </div>
            </TabsContent>

            {/* --- NUOVO TAB: SOULS (EXPORT PURE) --- */}
            <TabsContent value="SOULS" className="flex-1 overflow-hidden mt-4">
                <ExportTabContent 
                    exportType="pure" 
                    serverConfig={serverConfig} 
                    onExport={onExport} 
                    onImport={onImport} 
                />
            </TabsContent>

            {/* --- NUOVO TAB: WORLDS (EXPORT WORLD) --- */}
            <TabsContent value="WORLDS" className="flex-1 overflow-hidden mt-4">
                <ExportTabContent 
                    exportType="world" 
                    serverConfig={serverConfig} 
                    onExport={onExport} 
                    onImport={onImport} 
                />
            </TabsContent>
        </Tabs>
        
        <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>{t("character_manager.btn_close")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// --- SOTTO-COMPONENTE PER CRUD PERSONAGGI ---
const CharacterCrud = ({ 
    isLoading, 
    characters, 
    activeRoster, 
    onAdd, 
    onEdit, 
    onDelete, 
    onToggleRoster, 
    isToggling, 
    type 
}: any) => {
    const { t } = useTranslation();
    return (
    <div className="flex flex-col h-full gap-4">
        <div className="flex justify-between items-center shrink-0">
            <Label className="text-sm font-medium text-muted-foreground">
                {type === "AVATAR" ? t("character_manager.crud.avatars") : type === "PG" ? t("character_manager.crud.pgs") : t("character_manager.crud.npcs")} ({characters.length})
            </Label>
            <Button onClick={onAdd} size="sm" className="gap-2">
                <UserPlus className="h-4 w-4" /> {t("character_manager.crud.add_new")}
            </Button>
        </div>

        {isLoading ? (
            <div className="flex-1 flex items-center justify-center border rounded-md bg-muted/10">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
        ) : characters.length === 0 ? (
            <div className="flex-1 flex items-center justify-center border rounded-md bg-muted/10 text-muted-foreground text-sm">
                {t("character_manager.crud.no_characters")}
            </div>
        ) : (
            <div className="flex-1 border rounded-md bg-muted/10 p-2 airis-scrollbar overflow-y-auto max-h-[45vh] pr-3">
                <div className="space-y-2">
                    {characters.map((char: Character) => {
                        // [FIX] Normalizzazione per confronto robusto (ignora underscore e maiuscole)
                        const isInScene = activeRoster.some((r: string) => r && char.name && r.replace(/_/g, ' ').toLowerCase() === char.name.replace(/_/g, ' ').toLowerCase());
                        const isBusy = isToggling === char.id;
                        
                        return (
                            <div key={char.id} className={cn(
                                "flex items-center justify-between p-3 rounded-lg bg-card border transition-all group",
                                char.is_unified_avatar ? "border-primary/40 bg-primary/5" : "border-border/50 hover:border-primary/30"
                            )}>
                                <div className="flex items-center gap-3 overflow-hidden">
                                    {type !== "AVATAR" && (
                                        <div className={cn(
                                            "w-2 h-2 rounded-full shrink-0",
                                            isInScene ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" : "bg-muted-foreground/30"
                                        )} />
                                    )}
                                    
                                    {/* [NUOVO v124.0] Icona distintiva per l'Anima Unificata */}
                                    {char.is_unified_avatar && (
                                        <Sparkles className="w-3.5 h-3.5 text-primary shrink-0 animate-pulse" title={t("character_manager.unified_soul")} />
                                    )}
                                    
                                    <span className={cn("font-medium truncate", char.is_unified_avatar && "text-primary")}>
                                        {char.name}
                                    </span>
                                </div>

                                <div className="flex items-center gap-1">
                                    {type !== "AVATAR" && (
                                        <Button 
                                            variant="ghost" 
                                            size="icon" 
                                            className={cn("h-8 w-8", isInScene ? "text-green-500 hover:text-green-600" : "text-muted-foreground hover:text-primary")}
                                            onClick={() => onToggleRoster(char)}
                                            disabled={isBusy}
                                            title={isInScene ? t("character_manager.crud.remove_scene") : t("character_manager.crud.add_scene")}
                                        >
                                            {isBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : (isInScene ? <UserCheck className="w-4 h-4" /> : <UserMinus className="w-4 h-4" />)}
                                        </Button>
                                    )}

                                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-primary" onClick={() => onEdit(char.id)}>
                                        <Edit className="w-4 h-4" />
                                    </Button>
                                    
                                    {/* [AGGIORNATO v124.0] L'Anima Unificata non può essere eliminata dal roster PNG */}
                                    {!char.is_unified_avatar ? (
                                        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" onClick={() => onDelete(char.id)}>
                                            <Trash2 className="w-4 h-4" />
                                        </Button>
                                    ) : (
                                        <div className="w-8 h-8" /> // Spacer
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        )}
    </div>
)};

// --- NUOVO SOTTO-COMPONENTE PER EXPORT/IMPORT (INTEGRATO) ---
const ExportTabContent = ({ 
    exportType, 
    serverConfig, 
    onExport, 
    onImport 
}: { 
    exportType: 'pure' | 'world', 
    serverConfig: ServerConfig | null,
    onExport: (type: 'pure' | 'world', avatars: string[], lore?: string) => Promise<void>,
    onImport: () => void
}) => {
    const { t } = useTranslation();
    const[availableAvatars, setAvailableAvatars] = useState<string[]>([]);
    const [availableLores, setAvailableLores] = useState<string[]>([]);
    const [selectedAvatars, setSelectedAvatars] = useState<string[]>([]);
    const [selectedLore, setSelectedLore] = useState<string>("");
    const [isLoading, setIsLoading] = useState(false);
    const [isExporting, setIsExporting] = useState(false);

    useEffect(() => {
        if (serverConfig) {
            setIsLoading(true);
            const serverUrl = getBaseUrl(serverConfig);
            const headers = getHeaders();

            const fetchData = async () => {
                try {
                    const avatarsRes = await fetch(`${serverUrl}/api/exportable-items?item_type=avatar`, { headers });
                    if (!avatarsRes.ok) throw new Error(t("character_manager.err_fetch_avatars"));
                    const avatars = await avatarsRes.json();
                    setAvailableAvatars(avatars);
                    setSelectedAvatars([]); 

                    if (exportType === 'world') {
                        const loresRes = await fetch(`${serverUrl}/api/exportable-items?item_type=lore`, { headers });
                        if (!loresRes.ok) throw new Error(t("character_manager.err_fetch_worlds"));
                        const lores = await loresRes.json();
                setAvailableLores(lores);
                if (lores.length > 0) setSelectedLore(lores[0]);
            }
        } catch (error) {
            console.error(error);
            toast.error(t("character_manager.error_load_list"));
        } finally {
            setIsLoading(false);
        }
            };
            fetchData();
        }
    }, [serverConfig, exportType]);

    const handleToggleAvatar = (avatar: string) => {
        setSelectedAvatars(prev => 
            prev.includes(avatar) 
                ? prev.filter(a => a !== avatar)
                : [...prev, avatar]
        );
    };

    const handleSelectAll = () => {
        if (selectedAvatars.length === availableAvatars.length) {
            setSelectedAvatars([]); 
        } else {
            setSelectedAvatars([...availableAvatars]); 
        }
    };

    const handleExportClick = async () => {
        if (selectedAvatars.length === 0) {
            toast.warning(t("character_manager.warning_avatar"));
            return;
        }
        if (exportType === 'world' && !selectedLore) {
            toast.warning(t("character_manager.warning_world"));
            return;
        }

        setIsExporting(true);
        try {
            await onExport(exportType, selectedAvatars, selectedLore);
        } finally {
            setIsExporting(false);
        }
    };

    const isAllSelected = availableAvatars.length > 0 && selectedAvatars.length === availableAvatars.length;

    return (
        <div className="flex flex-col h-full gap-4 p-1">
            <div className="flex items-center justify-between">
                <div className="space-y-1">
                    <h3 className="text-sm font-bold flex items-center gap-2">
                        {exportType === 'pure' ? <Ghost className="w-4 h-4 text-primary" /> : <Globe className="w-4 h-4 text-primary" />}
                        {exportType === 'pure' ? t("character_manager.manage_pure_souls") : t("character_manager.manage_souls_world")}
                    </h3>
                    <p className="text-xs text-muted-foreground">{t("character_manager.export_desc")}</p>
                </div>
            </div>

            {isLoading ? (
                <div className="flex-1 flex items-center justify-center border rounded-md bg-muted/10">
                    <Loader2 className="w-8 h-8 animate-spin text-primary" />
                </div>
            ) : (
                <div className="flex-1 flex flex-col gap-4 overflow-hidden">
                    
                    {exportType === 'world' && (
                        <div className="space-y-2 p-3 border rounded-lg bg-muted/10">
                            <Label>{t("character_manager.select_world")}</Label>
                            <Select value={selectedLore} onValueChange={setSelectedLore}>
                                <SelectTrigger>
                                    <SelectValue placeholder={t("character_manager.select_world_placeholder")} />
                                </SelectTrigger>
                                <SelectContent>
                                    {availableLores.map(lore => (
                                        <SelectItem key={lore} value={lore}>{lore}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    )}

                    <div className="flex items-center justify-between px-1">
                        <Label>{t("character_manager.select_avatars_label", { selected: selectedAvatars.length, total: availableAvatars.length })}</Label>
                        <Button variant="ghost" size="sm" onClick={handleSelectAll} className="h-8 px-2 text-xs">
                            {isAllSelected ? (
                                <><Square className="w-3 h-3 mr-1" /> {t("character_manager.deselect_all")}</>
                            ) : (
                                <><CheckSquare className="w-3 h-3 mr-1" /> {t("character_manager.select_all")}</>
                            )}
                        </Button>
                    </div>

                    <div className="flex-1 border rounded-md bg-muted/10 overflow-hidden">
                        <ScrollArea className="h-full p-3 airis-scrollbar">
                            <div className="grid grid-cols-1 gap-2">
                                {availableAvatars.map(avatar => (
                                    <div key={avatar} className="flex items-center space-x-3 p-2 rounded hover:bg-muted/50 transition-colors border border-transparent hover:border-primary/20">
                                        <Checkbox 
                                            id={`avatar-${avatar}`} 
                                            checked={selectedAvatars.includes(avatar)}
                                            onCheckedChange={() => handleToggleAvatar(avatar)}
                                        />
                                        <label
                                            htmlFor={`avatar-${avatar}`}
                                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer flex-1"
                                        >
                                            {avatar}
                                        </label>
                                    </div>
                                ))}
                                {availableAvatars.length === 0 && (
                                    <p className="text-sm text-muted-foreground text-center py-8">{t("character_manager.no_avatars_found")}</p>
                                )}
                            </div>
                        </ScrollArea>
                    </div>

                    <div className="flex gap-2 pt-2 border-t border-border/50">
                        <Button variant="secondary" onClick={onImport} className="flex-1">
                            <Upload className="mr-2 h-4 w-4" /> {t("character_manager.btn_import")}
                        </Button>
                        <Button onClick={handleExportClick} disabled={isLoading || isExporting || selectedAvatars.length === 0} className="flex-1">
                            {isExporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                            {t("character_manager.btn_export")}
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
};