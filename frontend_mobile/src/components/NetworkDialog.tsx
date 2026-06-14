// frontend_mobile/src/components/NetworkDialog.tsx
// v2.0 - MMORPG ECOSYSTEM EXPANSION
// ADD: Dashboard Gilda (Roster, Ufficiali, Candidature).
// ADD: Bacheca LFG (Looking For Group).
// ADD: Level Gating (Min/Max) e Generazione Procedurale Quest.
// ADD: Stealth Mode (Stanze Private).
// LEGGE A0099: Invarianza strutturale garantita.
// LEGGE A0120: Scrollbar e Sicurezza applicate.

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch"; // FIX: Aggiunto import mancante per lo switch Invisibile
import { toast } from "sonner";
import { Loader2, Globe, Search, Server, Shield, Users, Swords, KeyRound, LogOut, Plus, UserPlus, Trash2, Upload, Wand2, MessageSquare, Check, X, Crown, Star, Clock, Ghost, AlertTriangle } from "lucide-react";
import { getBaseUrl, getHeaders } from "@/lib/api";
import { ServerConfig, NetworkMode } from "@/types";
import { useTranslation } from "@/contexts/TranslationContext";
import { cn } from "@/lib/utils";

interface NetworkDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  serverConfig: ServerConfig | null;
  networkMode: NetworkMode;
  onSetNetworkMode: (mode: NetworkMode, roomUrl?: string, lobbyPassword?: string) => void;
  playerName: string;
  userProfile?: any; // FIX BUG 01
  connectedGuests: string[];
  onKickPlayer: (playerName: string) => void;
  lowBandwidthMode: boolean;
  setLowBandwidthMode: (val: boolean) => void;
  onHostRoom: (title: string, desc: string, pwd: string, max: string, lang: string, womenOnly: boolean, minLvl: number, maxLvl: number, isPrivate: boolean) => void;
  onCloseRoom: () => void;
  onGuildCommand?: (cmd: string, payload?: any) => void;
  generatedQuest?: any | null;
  isStealthMode?: boolean;
  onToggleStealthMode?: () => void; // FIX SCREEN 4
  onClearLocalGuild?: () => void; // FIX BUG 01
}

export const NetworkDialog = ({
  open,
  onOpenChange,
  serverConfig,
  networkMode,
  onSetNetworkMode,
  playerName,
  userProfile,
  connectedGuests,
  onKickPlayer,
  lowBandwidthMode,
  setLowBandwidthMode,
  onHostRoom,
  onCloseRoom,
  onGuildCommand,
  generatedQuest,
  isStealthMode = false,
  onToggleStealthMode,
  onClearLocalGuild
}: NetworkDialogProps) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState("search");
  const [isLoading, setIsLoading] = useState(false);
  
  // FIX SCREEN 3: Lingue dinamiche
  const [availableLanguages, setAvailableLanguages] = useState<any>({});
  useEffect(() => {
      if (open && serverConfig) {
          fetch(`${getBaseUrl(serverConfig)}/api/tts/languages`, { headers: getHeaders() })
          .then(res => res.json())
          .then(data => setAvailableLanguages(data))
          .catch(console.error);
      }
  }, [open, serverConfig]);
  
  // Stati Ricerca & LFG
  const [rooms, setRooms] = useState<any[]>(Array(0));
  const [joinPassword, setJoinPassword] = useState("");
  const [selectedRoom, setSelectedRoom] = useState<any | null>(null);
  const [lfgPosts, setLfgPosts] = useState<any[]>(Array(0));
  const [newLfgClass, setNewLfgClass] = useState("");
  const [newLfgLevel, setNewLfgLevel] = useState("1");
  const [newLfgNote, setNewLfgNote] = useState("");

  // Stati Host
  const [hostTitle, setHostTitle] = useState("");
  const [hostDesc, setHostDesc] = useState("");
  const [hostPassword, setHostPassword] = useState("");
  const [hostMaxPlayers, setHostMaxPlayers] = useState("10");
  const [womenOnly, setWomenOnly] = useState(false);
  const [hostLang, setHostLang] = useState("all");
  const [hostMinLevel, setHostMinLevel] = useState("1"); // [NUOVO]
  const [hostMaxLevel, setHostMaxLevel] = useState("20"); // [NUOVO]
  const [isPrivateRoom, setIsPrivateRoom] = useState(false); // [NUOVO]

  // Stati Gilda
  const [guildSymbol, setGuildSymbol] = useState("");
  const [guilds, setGuilds] = useState<any[]>(Array(0));
  const [newGuildName, setNewGuildName] = useState("");
  const [guildAlignment, setGuildAlignment] = useState("Casual"); 
  const [isCustomAlignment, setIsCustomAlignment] = useState(false); // FIX SCREEN 2
  const [guildObjective, setGuildObjective] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [applyLetter, setApplyLetter] = useState(""); // [NUOVO]
  const [applyLevel, setApplyLevel] = useState("1"); // [NUOVO]
  const [applyClass, setApplyClass] = useState("Avventuriero"); // [NUOVO]
  const [selectedGuildToApply, setSelectedGuildToApply] = useState<any | null>(null);

  // Dialogs Gilda
  const [isEditGuildOpen, setIsEditGuildOpen] = useState(false);
  const [isDeleteGuildOpen, setIsDeleteGuildOpen] = useState(false);
  const [isLeaveGuildOpen, setIsLeaveGuildOpen] = useState(false);
  const [editGuildName, setEditGuildName] = useState("");
  const [editGuildSymbol, setEditGuildSymbol] = useState("");
  const [editGuildAlignment, setEditGuildAlignment] = useState("");
  const [isEditCustomAlignment, setIsEditCustomAlignment] = useState(false); // FIX: Stato per input custom in modifica
  const [editGuildObjective, setEditGuildObjective] = useState("");
  const [newLeaderUid, setNewLeaderUid] = useState("");

  // --- AUTO-FILL QUEST GENERATA ---
  useEffect(() => {
      if (generatedQuest) {
          setHostTitle(generatedQuest.titolo || "");
          setHostDesc(generatedQuest.descrizione || "");
          setHostMinLevel(String(generatedQuest.livello_minimo || 1));
          setHostMaxLevel(String(generatedQuest.livello_massimo || 20));
      }
  }, [generatedQuest]);

  const fetchGuilds = async () => {
    try {
      // FIX: URL aggiornato al Tracker Proprietario
      const res = await fetch(`https://www.omnia-diffusion.com/airis_tracker/api.php?path=gilde.json`);
      if (res.ok) {
        const data = await res.json() || {};
        const guildsArray = Object.keys(data).map(key => ({ id: key, ...data[key] }));
        // Ordina per numero di membri (Top 100)
        guildsArray.sort((a, b) => (Object.keys(b.membri || {}).length) - (Object.keys(a.membri || {}).length));
        setGuilds(guildsArray);
      }
    } catch (e) {
      console.error(t("network_dialog.err_fetch_guilds"), e);
    }
  };

  const fetchLfgBoard = async () => {
      try {
          const res = await fetch(`https://www.omnia-diffusion.com/airis_tracker/api.php?path=lfg_board.json`);
          if (res.ok) {
              const data = await res.json() || {};
              const now = Math.floor(Date.now() / 1000);
              // Filtra post più vecchi di 30 minuti (1800 secondi)
              const lfgArray = Object.keys(data)
                  .map(key => ({ id: key, ...data[key] }))
                  .filter(post => (now - post.timestamp) <= 1800);
              
              // Ordina dal più recente
              lfgArray.sort((a, b) => b.timestamp - a.timestamp);
              setLfgPosts(lfgArray);
          }
      } catch (e) {
          console.error(t("network_dialog.err_fetch_lfg"), e);
      }
  };

  useEffect(() => {
    if (open) {
        if (activeTab === "guild") fetchGuilds();
        if (activeTab === "lfg") fetchLfgBoard();
    }
  }, [open, activeTab]);

  // --- HANDLERS GILDA ---
  const handleCreateGuild = () => {
    try {
        if (!newGuildName.trim()) return;
        if (onGuildCommand) {
            onGuildCommand("GUILD_CREATE", { 
                name: newGuildName, 
                symbol: guildSymbol,
                tags: guildAlignment,
                obiettivo: guildObjective
            });
        }
        toast.success(t("network_dialog.toast_guild_found_sent"));
        setNewGuildName("");
        setGuildSymbol(""); 
        setGuildObjective("");
        setTimeout(fetchGuilds, 2000);
    } catch (e: any) {
        toast.error(t("network_dialog.err_connection", { error: e.message }));
    }
  };

  const handleEditGuild = () => {
      if (!editGuildName.trim()) return;
      if (onGuildCommand && myGuild) {
          onGuildCommand("GUILD_EDIT", { 
              guild_id: myGuild.id, 
              name: editGuildName, 
              symbol: editGuildSymbol,
              tags: editGuildAlignment,
              obiettivo: editGuildObjective
          });
      }
      setIsEditGuildOpen(false);
      setTimeout(fetchGuilds, 2000);
  };

  const handleDeleteGuild = () => {
      if (onGuildCommand && myGuild) {
          onGuildCommand("GUILD_DELETE", { guild_id: myGuild.id });
      }
      setIsDeleteGuildOpen(false);
      setTimeout(fetchGuilds, 2000);
  };

  const handleLeaveGuild = () => {
      if (onGuildCommand && myGuild) {
          onGuildCommand("GUILD_LEAVE", { guild_id: myGuild.id, my_uid: myUid, new_leader_uid: newLeaderUid });
      }
      setIsLeaveGuildOpen(false);
      setTimeout(fetchGuilds, 2000);
  };

  const handleKickGuild = (guildId: string, targetUid: string, targetName: string) => {
    if (onGuildCommand) onGuildCommand("GUILD_KICK", { guild_id: guildId, target_uid: targetUid });
    toast.success(t("network_dialog.toast_kick_requested", { name: targetName }));
    setTimeout(fetchGuilds, 2000);
  };

  const handlePromote = (guildId: string, targetUid: string, targetName: string) => {
      if (onGuildCommand) onGuildCommand("GUILD_PROMOTE", { guild_id: guildId, target_uid: targetUid, target_nome: targetName });
      toast.success(t("network_dialog.toast_promoted", { name: targetName }));
      setTimeout(fetchGuilds, 2000);
  };

  const handleDemote = (guildId: string, targetUid: string, targetName: string) => {
      if (onGuildCommand) onGuildCommand("GUILD_DEMOTE", { guild_id: guildId, target_uid: targetUid });
      toast.info(t("network_dialog.toast_demoted", { name: targetName }));
      setTimeout(fetchGuilds, 2000);
  };

  const handleApplyGuild = () => {
      if (!selectedGuildToApply) return;
      
      // Genera un UID deterministico basato sul nome per gestire gli ospiti senza account
      // In un sistema reale, questo verrebbe dal backend
      const myUid = "usr_" + btoa(playerName).substring(0, 8);
      
      if (onGuildCommand) {
          onGuildCommand("GUILD_APPLY", {
              guild_id: selectedGuildToApply.id,
              my_uid: myUid,
              my_name: playerName,
              lettera: applyLetter,
              livello: parseInt(applyLevel) || 1,
              classe: applyClass
          });
      }
      toast.success(t("network_dialog.toast_apply_success"));
      setSelectedGuildToApply(null);
      setApplyLetter("");
  };

  const handleAcceptRequest = (guildId: string, targetUid: string, targetName: string) => {
      if (onGuildCommand) onGuildCommand("GUILD_ACCEPT", { guild_id: guildId, target_uid: targetUid, target_nome: targetName });
      toast.success(t("network_dialog.toast_apply_accepted", { name: targetName }));
      setTimeout(fetchGuilds, 2000);
  };

  const handleRejectRequest = (guildId: string, targetUid: string) => {
      if (onGuildCommand) onGuildCommand("GUILD_REJECT", { guild_id: guildId, target_uid: targetUid });
      toast.info(t("network_dialog.toast_apply_rejected"));
      setTimeout(fetchGuilds, 2000);
  };

  // --- HANDLERS LFG ---
  const handlePublishLfg = () => {
      if (!newLfgClass.trim()) return;
      const lfgId = `lfg_${Date.now()}`;
      if (onGuildCommand) {
          onGuildCommand("LFG_PUBLISH", {
              lfg_id: lfgId,
              nome_pg: playerName,
              classe: newLfgClass,
              livello: parseInt(newLfgLevel) || 1,
              nota: newLfgNote
          });
      }
      toast.success(t("network_dialog.toast_lfg_published"));
      setNewLfgClass("");
      setNewLfgNote("");
      setTimeout(fetchLfgBoard, 2000);
  };

  const handleRemoveLfg = (lfgId: string) => {
      if (onGuildCommand) onGuildCommand("LFG_REMOVE", { lfg_id: lfgId });
      toast.info(t("network_dialog.toast_lfg_removed"));
      setTimeout(fetchLfgBoard, 2000);
  };

  // --- IDENTIFICAZIONE GILDA E RUOLI ---
  const myGuild = guilds.find(g => g.membri && Object.values(g.membri).some((m: any) => String(m).trim().toLowerCase() === playerName.trim().toLowerCase()));
  
  let isLeader = false;
  let isOfficer = false;
  let myUid = "";
  let otherMembers: {uid: string, name: string}[] =[];

  if (myGuild && myGuild.membri) {
      const entry = Object.entries(myGuild.membri).find(([uid, name]) => String(name).trim().toLowerCase() === playerName.trim().toLowerCase());
      if (entry) {
          myUid = entry[0];
          isLeader = myGuild.capo_gilda === myUid;
          isOfficer = myGuild.sottocapi && myGuild.sottocapi[myUid] !== undefined;
      }
      otherMembers = Object.entries(myGuild.membri)
          .filter(([uid, name]) => uid !== myUid)
          .map(([uid, name]) => ({ uid, name: String(name) }));
  }

  const fetchRooms = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`https://www.omnia-diffusion.com/airis_tracker/api.php?path=stanze_attive.json`);
      if (res.ok) {
        const data = await res.json() || {};
        const now = Math.floor(Date.now() / 1000);
        
        const roomsArray = Object.keys(data)
          .map(key => ({ id: key, ...data[key] }))
          .filter(room => (now - room.ultimo_ping) <= 180) // Filtro 3 minuti
          .filter(room => !room.is_private || room.host_nome === playerName); // Filtro Stealth Mode
          
        setRooms(roomsArray);
      }
    } catch (e) {
      console.error(t("network_dialog.err_fetch_rooms"), e);
      toast.error(t("network_dialog.err_global_board"));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (open && activeTab === "search") {
      fetchRooms();
    }
  }, [open, activeTab]);

  const handleHostStart = async () => {
    if (!hostTitle.trim() || !hostDesc.trim()) {
      toast.warning(t("network_dialog.warn_host_mandatory"));
      return;
    }
    
    onHostRoom(
        hostTitle, 
        hostDesc, 
        hostPassword, 
        hostMaxPlayers, 
        hostLang === "all" ? "" : hostLang, 
        womenOnly,
        parseInt(hostMinLevel) || 1,
        parseInt(hostMaxLevel) || 20,
        isPrivateRoom
    );
    onSetNetworkMode('HOST');
    onOpenChange(false);
  };

  const handleGenerateQuest = () => {
      if (onGuildCommand) {
          onGuildCommand("GENERATE_QUEST");
          toast.info(t("network_dialog.toast_generating_quest"));
      }
  };

  const handleJoinRoom = () => {
    if (!selectedRoom) return;
    if (!joinPassword.trim() && selectedRoom.url_ngrok.includes("wss")) {
      // Se è una stanza protetta, chiedi la password (logica base)
      // toast.warning("Inserisci la password della locanda.");
      // return;
    }
    onSetNetworkMode('CLIENT', selectedRoom.url_ngrok, joinPassword, selectedRoom.id);
    onOpenChange(false);
  };

  const handleDisconnect = () => {
    if (networkMode === 'HOST') {
        onCloseRoom();
    }
    onSetNetworkMode('OFF');
    toast.info(t("network_dialog.toast_disconnected"));
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl h-[85vh] flex flex-col p-0 gap-0 bg-background">
        <DialogHeader className="p-6 pb-4 border-b border-white/10 shrink-0">
          <DialogTitle className="flex items-center gap-2 text-primary">
            <Globe className="w-5 h-5" />
            {t("network_dialog.title")}
          </DialogTitle>
          <DialogDescription>
            {t("network_dialog.description")}
          </DialogDescription>
        </DialogHeader>

        {/* FIX SCREEN 4: Spostato switch Invisibile qui in alto */}
        <div className="px-6 py-3 bg-muted/10 border-b border-white/5 flex items-center justify-between shrink-0">
            <Label className="flex items-center gap-2 cursor-pointer text-sm font-medium">
                <Ghost className={cn("w-4 h-4", isStealthMode ? "text-purple-400" : "text-muted-foreground")} />
                {t("network_dialog.stealth_mode")}
            </Label>
            <div className="flex items-center gap-2">
                <span className="text-[10px] text-muted-foreground hidden sm:inline-block">{t("network_dialog.stealth_desc")}</span>
                <Switch checked={isStealthMode} onCheckedChange={onToggleStealthMode} />
            </div>
        </div>

        {/* CSS INIETTATO PER SCROLLBAR (DOGMA APPENDICE C) */}

        <style>{`
          .tavern-scrollbar::-webkit-scrollbar {
              width: 8px !important;
              display: block !important;
          }
          .tavern-scrollbar::-webkit-scrollbar-thumb {
              background-color: hsl(340 82% 52%) !important;
              border-radius: 10px !important;
          }
          .tavern-scrollbar::-webkit-scrollbar-track {
              background: transparent !important;
          }
        `}</style>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0 overflow-hidden">
         <div className="px-6 pt-2 shrink-0">
            <TabsList className="grid w-full grid-cols-3 sm:grid-cols-6 h-auto gap-1">
              <TabsTrigger value="search" className="text-[10px] sm:text-sm px-1"><Search className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2 hidden sm:block"/> {t("network_dialog.tabs.search")}</TabsTrigger>
              <TabsTrigger value="lfg" className="text-[10px] sm:text-sm px-1"><Users className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2 hidden sm:block"/> {t("network_dialog.tabs.lfg")}</TabsTrigger>
              <TabsTrigger value="host" className="text-[10px] sm:text-sm px-1"><Server className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2 hidden sm:block"/> {t("network_dialog.tabs.host")}</TabsTrigger>
              <TabsTrigger value="guild" className="text-[10px] sm:text-sm px-1"><Shield className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2 hidden sm:block"/> {t("network_dialog.tabs.guild")}</TabsTrigger>
              <TabsTrigger value="top100" className="text-[10px] sm:text-sm px-1"><Crown className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2 hidden sm:block"/> {t("network_dialog.tabs.top100")}</TabsTrigger>
              <TabsTrigger value="new_guilds" className="text-[10px] sm:text-sm px-1"><Star className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2 hidden sm:block"/> {t("network_dialog.tabs.new_guilds")}</TabsTrigger>
            </TabsList>
          </div>

          {/* TAB RICERCA */}
          <TabsContent value="search" className="flex-1 min-h-0 m-0 data-[state=active]:flex flex-col overflow-hidden">
            <div className="flex-1 relative min-h-0 p-4">
              <div className="absolute inset-0 overflow-y-scroll tavern-scrollbar px-4 space-y-4">
                <div className="flex justify-between items-center">
                  <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{t("network_dialog.search.active_rooms")}</Label>
                  <Button variant="ghost" size="sm" onClick={fetchRooms} disabled={isLoading}>
                    {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  </Button>
                </div>

                {rooms.length === 0 && !isLoading ? (
                  <div className="text-center py-10 text-muted-foreground border border-dashed rounded-xl bg-muted/5">
                    <Globe className="w-10 h-10 mx-auto mb-3 opacity-20" />
                    <p className="text-sm">{t("network_dialog.search.no_rooms")}</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-3">
                    {rooms.map(room => (
                      <div 
                        key={room.id} 
                        className={cn(
                          "p-4 rounded-xl border transition-all cursor-pointer",
                          selectedRoom?.id === room.id ? "bg-primary/10 border-primary/50" : "bg-card hover:border-primary/30"
                        )}
                        onClick={() => setSelectedRoom(room)}
                      >
                        <div className="flex justify-between items-start mb-2">
                          <h4 className="font-bold text-lg text-primary">{room.titolo_avventura}</h4>
                          <span className="text-xs bg-muted px-2 py-1 rounded-full flex items-center gap-1">
                            <Users className="w-3 h-3" /> {room.giocatori_attuali}/{room.max_giocatori}
                          </span>
                        </div>
                        <p className="text-sm text-foreground/80 mb-3">{room.descrizione_avventura}</p>
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <div className="flex items-center gap-2">
                              <Server className="w-3 h-3" /> {t("network_dialog.search.host", { name: room.host_nome })}
                          </div>
                          <div className="flex items-center gap-2">
                              <span className="bg-background/50 px-2 py-0.5 rounded border border-white/5">{t("network_dialog.search.level_range", { min: room.livello_minimo || 1, max: room.livello_massimo || 20 })}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Pannello Join */}
            {selectedRoom && (
              <div className="p-4 border-t bg-muted/10 shrink-0 animate-in slide-in-from-bottom-2 space-y-4">
                <div className="flex items-center justify-between bg-background/50 p-2 rounded-lg border border-white/5">
                    <div className="space-y-0.5">
                        <Label className="text-xs font-bold text-primary">{t("network_dialog.search.low_bandwidth")}</Label>
                        <p className="text-[10px] text-muted-foreground">{t("network_dialog.search.low_bandwidth_desc")}</p>
                    </div>
                    <input 
                        type="checkbox" 
                        checked={lowBandwidthMode} 
                        onChange={(e) => setLowBandwidthMode(e.target.checked)}
                        className="w-4 h-4 accent-primary"
                    />
                </div>
                
                <div className="flex gap-3 items-end">
                  <div className="flex-1 space-y-2">
                    <Label className="text-xs uppercase">{t("network_dialog.search.password_label")}</Label>
                    <div className="relative">
                      <KeyRound className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                      <Input 
                        type="password" 
                        placeholder={t("network_dialog.search.password_placeholder")} 
                        className="pl-9"
                        value={joinPassword}
                        onChange={(e) => setJoinPassword(e.target.value)}
                      />
                    </div>
                  </div>
                  <Button 
                    className="bg-primary hover:bg-primary/90" 
                    onClick={handleJoinRoom}
                    disabled={networkMode !== 'OFF'}
                  >
                    <Swords className="w-4 h-4 mr-2" /> {t("network_dialog.search.btn_join")}
                  </Button>
                </div>
              </div>
            )}
          </TabsContent>

          {/* TAB LFG (LOOKING FOR GROUP) */}
          <TabsContent value="lfg" className="flex-1 min-h-0 m-0 data-[state=active]:flex flex-col overflow-hidden">
            <div className="flex-1 relative min-h-0 p-4">
              <div className="absolute inset-0 overflow-y-scroll tavern-scrollbar px-4 space-y-6">
                  
                  <div className="space-y-3 bg-background/50 p-4 rounded-xl border border-white/5">
                      <Label className="text-xs font-bold uppercase tracking-wider text-primary">{t("network_dialog.lfg.title")}</Label>
                      <p className="text-[10px] text-muted-foreground">{t("network_dialog.lfg.desc")}</p>
                      <div className="grid grid-cols-2 gap-2">
                          <Input placeholder={t("network_dialog.lfg.placeholder_class")} value={newLfgClass} onChange={e => setNewLfgClass(e.target.value)} className="h-8 text-xs" />
                          <Input type="number" placeholder={t("network_dialog.lfg.placeholder_level")} value={newLfgLevel} onChange={e => setNewLfgLevel(e.target.value)} className="h-8 text-xs" />
                      </div>
                      <div className="flex gap-2">
                          <Input placeholder={t("network_dialog.lfg.placeholder_note")} value={newLfgNote} onChange={e => setNewLfgNote(e.target.value)} className="h-8 text-xs flex-1" />
                          <Button size="sm" className="h-8" onClick={handlePublishLfg} disabled={!newLfgClass.trim()}>{t("network_dialog.lfg.btn_publish")}</Button>
                      </div>
                  </div>

                  <div className="space-y-3">
                      <div className="flex justify-between items-center">
                          <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{t("network_dialog.lfg.active_adventurers")}</Label>
                          <Button variant="ghost" size="sm" onClick={fetchLfgBoard} className="h-6 w-6 p-0"><Search className="w-3 h-3" /></Button>
                      </div>
                      
                      {lfgPosts.length === 0 ? (
                          <p className="text-xs text-muted-foreground italic text-center py-4">{t("network_dialog.lfg.no_adventurers")}</p>
                      ) : (
                          <div className="grid gap-2">
                              {lfgPosts.map(post => (
                                  <div key={post.id} className="p-3 rounded-lg border bg-card flex justify-between items-center">
                                      <div>
                                          <h4 className="font-bold text-sm text-primary">{post.nome_pg} <span className="text-xs text-muted-foreground font-normal">({post.classe} Lv.{post.livello})</span></h4>
                                          <p className="text-xs text-foreground/80 mt-1">{post.nota}</p>
                                      </div>
                                      {post.nome_pg === playerName && (
                                          <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive" onClick={() => handleRemoveLfg(post.id)}>
                                              <Trash2 className="w-3 h-3" />
                                          </Button>
                                      )}
                                  </div>
                              ))}
                          </div>
                      )}
                  </div>

              </div>
            </div>
          </TabsContent>

          {/* TAB OSPITA */}
          <TabsContent value="host" className="flex-1 min-h-0 m-0 data-[state=active]:flex flex-col overflow-hidden">
            <div className="flex-1 relative min-h-0 p-4">
              <div className="absolute inset-0 overflow-y-scroll tavern-scrollbar px-4 space-y-6">
                
                {networkMode === 'HOST' ? (
                  <div className="flex flex-col items-center justify-center h-full text-center space-y-4 py-4">
                    <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center border border-green-500/50 animate-pulse">
                      <Server className="w-8 h-8 text-green-500" />
                    </div>
                    <div>
                      <h3 className="text-xl font-bold text-green-500">{t("network_dialog.host.room_open")}</h3>
                      <p className="text-sm text-muted-foreground mt-2">{t("network_dialog.host.room_open_desc")}</p>
                    </div>
                    
                    <div className="w-full max-w-sm mt-6 bg-background/50 border border-white/10 rounded-xl p-4 text-left">
                        <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3 block">{t("network_dialog.host.connected_guests", { count: connectedGuests.length })}</Label>
                        <div className="space-y-2">
                            {connectedGuests.length === 0 ? (
                                <p className="text-xs text-center text-muted-foreground italic">{t("network_dialog.host.no_guests")}</p>
                            ) : (
                                connectedGuests.map((guest, idx) => (
                                    <div key={idx} className="flex items-center justify-between bg-muted/30 p-2 rounded-lg border border-white/5">
                                        <span className="text-sm font-medium">{guest}</span>
                                        <Button 
                                            variant="destructive" 
                                            size="sm" 
                                            className="h-7 text-[10px] px-2"
                                            onClick={() => onKickPlayer(guest)}
                                        >
                                            {t("network_dialog.host.btn_kick")}
                                        </Button>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    <Button variant="destructive" onClick={handleDisconnect} className="mt-4 w-full max-sm">
                      <LogOut className="w-4 h-4 mr-2" /> {t("network_dialog.host.btn_close_room")}
                    </Button>
                  </div>
                ) : (
                  <>
                    {/* FIX SCREEN 3: Bottone centrato e distanziato dai tab */}
                    <div className="flex justify-center mb-2 mt-4">
                        <Button variant="outline" size="sm" onClick={handleGenerateQuest} className="bg-purple-600/20 text-purple-400 border-purple-500/30 hover:bg-purple-600/40 w-full max-w-xs">
                            <Wand2 className="w-4 h-4 mr-2" /> {t("network_dialog.host.btn_generate_quest")}
                        </Button>
                    </div>

                    <div className="space-y-2">
                      <Label>{t("network_dialog.host.label_title")}</Label>
                      <Input 
                        placeholder={t("network_dialog.host.placeholder_title")} 
                        value={hostTitle}
                        onChange={(e) => setHostTitle(e.target.value)}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label>{t("network_dialog.host.label_desc")}</Label>
                      <Textarea 
                        placeholder={t("network_dialog.host.placeholder_desc")} 
                        className="min-h-[100px] resize-none"
                        value={hostDesc}
                        onChange={(e) => setHostDesc(e.target.value)}
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>{t("network_dialog.host.label_password")}</Label>
                        <Input 
                          type="password" 
                          placeholder={t("network_dialog.host.placeholder_password")} 
                          value={hostPassword}
                          onChange={(e) => setHostPassword(e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>{t("network_dialog.host.label_max_players")}</Label>
                        <Input 
                          type="number" 
                          min="2" max="10" 
                          value={hostMaxPlayers}
                          onChange={(e) => setHostMaxPlayers(e.target.value)}
                        />
                      </div>
                    </div>

                    {/* ---[NUOVO] LEVEL GATING --- */}
                    <div className="grid grid-cols-2 gap-4 mt-2">
                        <div className="space-y-2">
                            <Label>{t("network_dialog.host.label_min_level")}</Label>
                            <Input type="number" min="1" value={hostMinLevel} onChange={e => setHostMinLevel(e.target.value)} />
                        </div>
                        <div className="space-y-2">
                            <Label>{t("network_dialog.host.label_max_level")}</Label>
                            <Input type="number" min="1" value={hostMaxLevel} onChange={e => setHostMaxLevel(e.target.value)} />
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mt-4">
                        <div className="space-y-2">
                            <Label>{t("network_dialog.language")} ({t("reminder_dialog.notes_placeholder").split(' ')[1]})</Label>
                            <Select value={hostLang} onValueChange={setHostLang}>
                                <SelectTrigger><SelectValue placeholder={t("network_dialog.all_languages")} /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">{t("network_dialog.all_languages")}</SelectItem>
                                    {/* FIX SCREEN 3: Lingue dinamiche da Kokoro/VibeVoice */}
                                    {Object.entries(availableLanguages).map(([code, details]: [string, any]) => (
                                        <SelectItem key={code} value={code}>{details.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="flex flex-col gap-2 pt-6">
                            <div className="flex items-center space-x-2">
                                <Checkbox id="womenOnly" checked={womenOnly} onCheckedChange={(c) => setWomenOnly(!!c)} />
                                <Label htmlFor="womenOnly" className="text-sm font-bold text-pink-500">{t("network_dialog.women_only")}</Label>
                            </div>
                            <div className="flex items-center space-x-2">
                                <Checkbox id="privateRoom" checked={isPrivateRoom} onCheckedChange={(c) => setIsPrivateRoom(!!c)} />
                                <Label htmlFor="privateRoom" className="text-sm font-bold text-muted-foreground">{t("network_dialog.host.private_room")}</Label>
                            </div>
                        </div>
                    </div>

                    <div className="pt-4">
                      <Button 
                        className="w-full bg-primary hover:bg-primary/90 h-12 text-lg" 
                        onClick={handleHostStart}
                        disabled={isLoading || networkMode !== 'OFF'}
                      >
                        {isLoading ? <Loader2 className="w-5 h-5 animate-spin mr-2" /> : <Server className="w-5 h-5 mr-2" />}
                        {t("network_dialog.host.btn_open_room")}
                      </Button>
                      <p className="text-[10px] text-center text-muted-foreground mt-3">
                        {t("network_dialog.host.host_note")}
                      </p>
                    </div>
                  </>
                )}
              </div>
            </div>
          </TabsContent>

          {/* TAB GILDA */}
          <TabsContent value="guild" className="flex-1 min-h-0 m-0 data-[state=active]:flex flex-col overflow-hidden">
            <div className="flex-1 relative min-h-0 p-4">
              <div className="absolute inset-0 overflow-y-scroll tavern-scrollbar px-4 space-y-6">
                
                {!myGuild ? (
                  <div className="space-y-6 mt-4"> {/* FIX SCREEN 4: Aggiunto mt-4 per spaziatura */}
                    <div className="text-center py-6 text-muted-foreground border border-dashed rounded-xl bg-muted/5">
                      <Shield className="w-10 h-10 mx-auto mb-3 opacity-40 text-primary" />
                      <h3 className="text-lg font-bold text-foreground">{t("network_dialog.guild.no_guild_title")}</h3>
                      <p className="text-sm mt-2">{t("network_dialog.guild.no_guild_desc")}</p>
                      
                      {/* FIX BUG 01: Auto-Guarigione Desync Profilo */}
                      {userProfile?.guildName && (
                          <div className="mt-4 p-3 bg-red-950/30 border border-red-900/50 rounded-lg inline-block text-left">
                              <p className="text-xs text-red-400 mb-2"><AlertTriangle className="w-3 h-3 inline mr-1"/> {t("network_dialog.guild.anomaly_detected", { name: userProfile.guildName })}</p>
                              <Button variant="outline" size="sm" className="h-7 text-xs w-full" onClick={onClearLocalGuild}>
                                  {t("network_dialog.guild.btn_sync_profile")}
                              </Button>
                          </div>
                      )}
                    </div>
                    
                    <div className="space-y-3 bg-background/50 p-4 rounded-xl border border-white/5">
                      <Label className="text-xs font-bold uppercase tracking-wider text-primary">{t("network_dialog.guild.found_guild_title")}</Label>
                      <div className="grid grid-cols-2 gap-2">
                          <Input placeholder={t("network_dialog.guild.placeholder_name")} value={newGuildName} onChange={(e) => setNewGuildName(e.target.value)} className="h-8 text-xs" />
                          
                          {/* FIX SCREEN 2: Allineamento Custom e rimozione PvP */}
                          {isCustomAlignment ? (
                              <div className="flex gap-1">
                                  <Input value={guildAlignment} onChange={e => setGuildAlignment(e.target.value)} placeholder={t("network_dialog.guild.placeholder_custom_alignment")} className="h-8 text-xs flex-1" autoFocus />
                                  <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={() => { setIsCustomAlignment(false); setGuildAlignment("Casual"); }}><X className="w-4 h-4"/></Button>
                              </div>
                          ) : (
                              <Select value={guildAlignment} onValueChange={v => { if(v === 'custom') setIsCustomAlignment(true); else setGuildAlignment(v); }}>
                                  <SelectTrigger className="h-8 text-xs"><SelectValue placeholder={t("network_dialog.guild.placeholder_alignment")} /></SelectTrigger>
                                  <SelectContent>
                                      <SelectItem value="Casual">{t("network_dialog.guild.alignment_options.casual")}</SelectItem>
                                      <SelectItem value="Hardcore RP">{t("network_dialog.guild.alignment_options.hardcore")}</SelectItem>
                                      <SelectItem value="Esploratori">{t("network_dialog.guild.alignment_options.explorers")}</SelectItem>
                                      <SelectItem value="Mercenari">{t("network_dialog.guild.alignment_options.mercenaries")}</SelectItem>
                                      <SelectItem value="custom" className="font-bold text-primary">{t("network_dialog.guild.alignment_options.custom")}</SelectItem>
                                  </SelectContent>
                              </Select>
                          )}
                      </div>
                      <Input placeholder={t("network_dialog.guild.placeholder_objective")} value={guildObjective} onChange={(e) => setGuildObjective(e.target.value)} maxLength={100} className="h-8 text-xs" />
                      
                      <div className="flex gap-2 mt-2">
                        <Button variant="outline" size="sm" className="flex-1 h-8 text-xs" onClick={() => {
                            const input = document.createElement('input');
                            input.type = 'file';
                            input.accept = 'image/*';
                            input.onchange = (e: any) => {
                                const file = e.target.files[0];
                                const reader = new FileReader();
                                reader.onload = (ev: any) => {
                                    const img = new Image();
                                    img.onload = () => {
                                        const canvas = document.createElement('canvas');
                                        canvas.width = 512; canvas.height = 512;
                                        canvas.getContext('2d')?.drawImage(img, 0, 0, 512, 512);
                                        setGuildSymbol(canvas.toDataURL('image/webp', 0.6));
                                    };
                                    img.src = ev.target.result;
                                };
                                reader.readAsDataURL(file);
                            };
                            input.click();
                        }}>
                            <Upload className="w-3 h-3 mr-2" /> {t("network_dialog.guild.btn_symbol")}
                        </Button>
                        <Button onClick={handleCreateGuild} disabled={!newGuildName.trim()} className="flex-1 h-8 text-xs">
                          <Plus className="w-3 h-3 mr-2" /> {t("network_dialog.guild.btn_found")}
                        </Button>
                      </div>
                      {guildSymbol && <img src={guildSymbol} className="w-12 h-12 rounded-full border border-primary mx-auto mt-2" alt={t("network_dialog.guild.btn_symbol")} />}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-6 mt-4">
                    {/* HEADER GILDA */}
                    <div className="p-4 rounded-xl border border-primary/30 bg-primary/5 text-center relative overflow-hidden">
                      <Shield className="absolute -right-4 -bottom-4 w-24 h-24 text-primary/10" />
                      {myGuild.simbolo_gilda && <img src={myGuild.simbolo_gilda} className="w-16 h-16 rounded-full mx-auto mb-2 border-2 border-primary relative z-10" alt="" />}
                      <h3 className="text-2xl font-bold text-primary relative z-10">{myGuild.nome_gilda}</h3>
                      <div className="flex justify-center gap-2 mt-2 relative z-10">
                          <span className="text-[10px] bg-primary/20 text-primary px-2 py-0.5 rounded-full uppercase tracking-wider">{myGuild.tags || t("network_dialog.guild.alignment_options.casual")}</span>
                          <span className="text-[10px] bg-muted text-muted-foreground px-2 py-0.5 rounded-full uppercase tracking-wider">{t("network_dialog.guild.members_count", { count: myGuild.membri ? Object.keys(myGuild.membri).length : 0 })}</span>
                      </div>
                      {myGuild.obiettivo && <p className="text-xs text-foreground/80 italic mt-3 relative z-10">"{myGuild.obiettivo}"</p>}
                    </div>

                    {/* SALA DEL TRONO (Solo Leader/Ufficiali) */}
                    {(isLeader || isOfficer) && (
                        <div className="space-y-3 bg-red-950/20 p-4 rounded-xl border border-red-900/50">
                            <Label className="text-xs font-bold uppercase tracking-wider text-red-400 flex items-center gap-2">
                                <Crown className="w-4 h-4" /> {t("network_dialog.guild.throne_room")}
                            </Label>
                            
                            {/* Richieste Pendenti */}
                            <div className="space-y-2 mt-2">
                                <Label className="text-[10px] text-muted-foreground">{t("network_dialog.guild.pending_applications")}</Label>
                                {!myGuild.richieste_pendenti || Object.keys(myGuild.richieste_pendenti).length === 0 ? (
                                    <p className="text-xs italic text-muted-foreground">{t("network_dialog.guild.no_applications")}</p>
                                ) : (
                                    Object.entries(myGuild.richieste_pendenti).map(([uid, req]: [string, any]) => (
                                        <div key={uid} className="p-2 bg-background/50 rounded border border-white/5 text-xs">
                                            <div className="flex justify-between items-center mb-1">
                                                <span className="font-bold text-primary">{req.nome} <span className="text-muted-foreground font-normal">({req.classe} Lv.{req.livello})</span></span>
                                                <div className="flex gap-1">
                                                    <Button size="icon" variant="ghost" className="h-6 w-6 text-green-500" onClick={() => handleAcceptRequest(myGuild.id, uid, req.nome)}><Check className="w-3 h-3" /></Button>
                                                    <Button size="icon" variant="ghost" className="h-6 w-6 text-destructive" onClick={() => handleRejectRequest(myGuild.id, uid)}><X className="w-3 h-3" /></Button>
                                                </div>
                                            </div>
                                            <p className="italic text-muted-foreground">"{req.lettera}"</p>
                                        </div>
                                    ))
                                )}
                            </div>

                            {/* Azioni Leader */}
                            {isLeader && (
                                <div className="flex flex-wrap gap-2 pt-3 border-t border-red-900/30">
                                    <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => {
                                        setEditGuildName(myGuild.nome_gilda);
                                        setEditGuildSymbol(myGuild.simbolo_gilda || "");
                                        
                                        // FIX: Determina se l'allineamento attuale è custom o standard
                                        const currentTag = myGuild.tags || "Casual";
                                        const standardTags = ["Casual", "Hardcore RP", "Esploratori", "Mercenari"];
                                        setEditGuildAlignment(currentTag);
                                        setIsEditCustomAlignment(!standardTags.includes(currentTag));
                                        
                                        setEditGuildObjective(myGuild.obiettivo || "");
                                        setIsEditGuildOpen(true);
                                    }}>{t("network_dialog.guild.btn_edit")}</Button>
                                    <Button variant="destructive" size="sm" className="h-7 text-xs" onClick={() => setIsDeleteGuildOpen(true)}>{t("network_dialog.guild.btn_dissolve")}</Button>
                                </div>
                            )}
                        </div>
                    )}

                    {/* ROSTER MEMBRI */}
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                          <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{t("network_dialog.guild.roster_title")}</Label>
                          <Button variant="destructive" size="sm" className="h-7 text-xs" onClick={() => {
                              if (isLeader && otherMembers.length === 0) {
                                  toast.warning(t("network_dialog.guild.err_leave_solo"));
                                  return;
                              }
                              setIsLeaveGuildOpen(true);
                          }}>{t("network_dialog.guild.btn_leave")}</Button>
                      </div>
                      
                      <div className="grid gap-2">
                        {myGuild.membri && Object.entries(myGuild.membri).map(([uid, name]) => {
                            const isThisLeader = myGuild.capo_gilda === uid;
                            const isThisOfficer = myGuild.sottocapi && myGuild.sottocapi[uid] !== undefined;
                            
                            return (
                              <div key={uid} className="flex items-center justify-between p-2 rounded-lg border bg-card">
                                <div className="flex items-center gap-3">
                                    <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" title={t("network_dialog.guild.online_status")} />
                                    <span className="text-sm font-medium flex items-center gap-2">
                                      {String(name)}
                                      {isThisLeader && <Crown className="w-3 h-3 text-yellow-500" title={t("network_dialog.guild.leader_tag")} />}
                                      {isThisOfficer && <Star className="w-3 h-3 text-blue-400" title={t("network_dialog.guild.officer_tag")} />}
                                    </span>
                                </div>
                                
                                {(isLeader || isOfficer) && !isThisLeader && (
                                          <div className="flex gap-1">
                                              {isLeader && (
                                                  isThisOfficer ? (
                                                      <Button variant="ghost" size="sm" className="h-6 text-[10px] px-2 text-muted-foreground" onClick={() => handleDemote(myGuild.id, uid, String(name))}>{t("network_dialog.guild.btn_demote")}</Button>
                                                  ) : (
                                                      <Button variant="ghost" size="sm" className="h-6 text-[10px] px-2 text-blue-400" onClick={() => handlePromote(myGuild.id, uid, String(name))}>{t("network_dialog.guild.btn_promote")}</Button>
                                                  )
                                              )}
                                              <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive hover:bg-destructive/20" onClick={() => handleKickGuild(myGuild.id, uid, String(name))}>
                                                <Trash2 className="w-3 h-3" />
                                              </Button>
                                          </div>
                                        )}
                                      </div>
                                    );
                                })}
                              </div>
                    </div>
                  </div>
                )}

                </div>
            </div>
          </TabsContent>

          {/* TAB TOP 100 GILDE */}
          <TabsContent value="top100" className="flex-1 min-h-0 m-0 data-[state=active]:flex flex-col overflow-hidden">
            <div className="flex-1 relative min-h-0 p-4">
              <div className="absolute inset-0 overflow-y-scroll tavern-scrollbar px-4 space-y-4">
                <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{t("network_dialog.guild.top_100_title")}</Label>
                {guilds.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">{t("network_dialog.guild.no_guilds_realm")}</p>
                ) : (
                  guilds.map(g => {
                    const isMyOwnGuild = myGuild && myGuild.id === g.id;
                    return (
                    <div key={g.id} className={cn("p-3 rounded-lg border flex flex-col gap-2", isMyOwnGuild ? "bg-primary/10 border-primary/30" : "bg-card")}>
                      <div className="flex justify-between items-start">
                          <div className="flex items-center gap-3">
                              {g.simbolo_gilda ? <img src={g.simbolo_gilda} className="w-8 h-8 rounded-full" alt="" /> : <Shield className="w-8 h-8 text-muted-foreground" />}
                              <div>
                                <h4 className="font-bold text-primary text-sm">{g.nome_gilda}</h4>
                                <div className="flex gap-2 text-[10px] text-muted-foreground">
                                    <span className="bg-muted px-1 rounded">{g.tags || t("network_dialog.guild.alignment_options.casual")}</span>
                                    <span>{t("network_dialog.guild.members_count", { count: g.membri ? Object.keys(g.membri).length : 0 })}</span>
                                </div>
                              </div>
                          </div>
                          {!isMyOwnGuild && (
                              <Button 
                                  size="sm" 
                                  variant="secondary" 
                                  className="h-7 text-xs" 
                                  onClick={() => {
                                      if (myGuild) {
                                          toast.warning(t("network_dialog.guild.toast_leave_warning"));
                                          return;
                                      }
                                      setSelectedGuildToApply(g);
                                  }}
                              >
                                  {t("network_dialog.guild.btn_request_access")}
                              </Button>
                          )}
                      </div>
                      {g.obiettivo && <p className="text-xs text-foreground/80 italic">"{g.obiettivo}"</p>}
                    </div>
                  )})
                )}
              </div>
            </div>
          </TabsContent>

          {/* TAB NUOVE GILDE 7D */}
          <TabsContent value="new_guilds" className="flex-1 min-h-0 m-0 data-[state=active]:flex flex-col overflow-hidden">
            <div className="flex-1 relative min-h-0 p-4">
              <div className="absolute inset-0 overflow-y-scroll tavern-scrollbar px-4 space-y-4">
                <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{t("network_dialog.guild.new_guilds_title")}</Label>
                {guilds.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">{t("network_dialog.guild.no_guilds_realm")}</p>
                ) : ([...guilds]
                    .sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0))
                    .filter(g => {
                        const now = Math.floor(Date.now() / 1000);
                        return g.timestamp ? (now - g.timestamp) <= 604800 : true;
                    })
                    .map(g => {
                    const isMyOwnGuild = myGuild && myGuild.id === g.id;
                    return (
                    <div key={g.id} className={cn("p-3 rounded-lg border flex flex-col gap-2", isMyOwnGuild ? "bg-primary/10 border-primary/30" : "bg-card")}>
                      <div className="flex justify-between items-start">
                          <div className="flex items-center gap-3">
                              {g.simbolo_gilda ? <img src={g.simbolo_gilda} className="w-8 h-8 rounded-full" alt="" /> : <Shield className="w-8 h-8 text-muted-foreground" />}
                              <div>
                                <h4 className="font-bold text-primary text-sm">{g.nome_gilda}</h4>
                                <div className="flex gap-2 text-[10px] text-muted-foreground">
                                    <span className="bg-muted px-1 rounded">{g.tags || t("network_dialog.guild.alignment_options.casual")}</span>
                                    <span>{t("network_dialog.guild.members_count", { count: g.membri ? Object.keys(g.membri).length : 0 })}</span>
                                </div>
                              </div>
                          </div>
                          {!isMyOwnGuild && (
                              <Button 
                                  size="sm" 
                                  variant="secondary" 
                                  className="h-7 text-xs" 
                                  onClick={() => {
                                      if (myGuild) {
                                          toast.warning(t("network_dialog.guild.toast_leave_warning"));
                                          return;
                                      }
                                      setSelectedGuildToApply(g);
                                  }}
                              >
                                  {t("network_dialog.guild.btn_request_access")}
                              </Button>
                          )}
                      </div>
                      {g.obiettivo && <p className="text-xs text-foreground/80 italic">"{g.obiettivo}"</p>}
                    </div>
                  )})
                )}
              </div>
            </div>
          </TabsContent>

        </Tabs>

        <DialogFooter className="p-4 border-t bg-muted/5 shrink-0">
          {networkMode === 'CLIENT' && (
            <Button variant="destructive" onClick={handleDisconnect} className="mr-auto">
              <LogOut className="w-4 h-4 mr-2" /> {t("network_dialog.footer.btn_disconnect")}
            </Button>
          )}
          <Button variant="outline" onClick={() => onOpenChange(false)}>{t("network_dialog.footer.btn_close")}</Button>
        </DialogFooter>
      </DialogContent>

      {/* DIALOGS GILDA */}
      <Dialog open={isEditGuildOpen} onOpenChange={setIsEditGuildOpen}>
          <DialogContent className="sm:max-w-md z-[100]">
              <DialogHeader><DialogTitle>{t("network_dialog.dialogs.edit_guild.title")}</DialogTitle></DialogHeader>
              <div className="space-y-4 py-4">
                  <div className="space-y-2">
                      <Label>{t("network_dialog.dialogs.edit_guild.label_name")}</Label>
                      <Input value={editGuildName} onChange={e => setEditGuildName(e.target.value)} />
                  </div>
                  <div className="space-y-2">
                      <Label>{t("network_dialog.dialogs.edit_guild.label_alignment")}</Label>
                      {/* FIX: Supporto per input custom nel dialogo di modifica e rimozione PvP */}
                      {isEditCustomAlignment ? (
                          <div className="flex gap-1">
                              <Input value={editGuildAlignment} onChange={e => setEditGuildAlignment(e.target.value)} placeholder={t("network_dialog.guild.placeholder_custom_alignment")} className="h-9 flex-1" autoFocus />
                              <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0" onClick={() => { setIsEditCustomAlignment(false); setEditGuildAlignment("Casual"); }}><X className="w-4 h-4"/></Button>
                          </div>
                      ) : (
                          <Select value={editGuildAlignment} onValueChange={v => { if(v === 'custom') setIsEditCustomAlignment(true); else setEditGuildAlignment(v); }}>
                              <SelectTrigger><SelectValue /></SelectTrigger>
                              <SelectContent className="z-[110]">
                                  <SelectItem value="Casual">{t("network_dialog.guild.alignment_options.casual")}</SelectItem>
                                  <SelectItem value="Hardcore RP">{t("network_dialog.guild.alignment_options.hardcore")}</SelectItem>
                                  <SelectItem value="Esploratori">{t("network_dialog.guild.alignment_options.explorers")}</SelectItem>
                                  <SelectItem value="Mercenari">{t("network_dialog.guild.alignment_options.mercenaries")}</SelectItem>
                                  <SelectItem value="custom" className="font-bold text-primary">{t("network_dialog.guild.alignment_options.custom")}</SelectItem>
                              </SelectContent>
                          </Select>
                      )}
                  </div>
                  <div className="space-y-2">
                      <Label>{t("network_dialog.dialogs.edit_guild.label_objective")}</Label>
                      <Input value={editGuildObjective} onChange={e => setEditGuildObjective(e.target.value)} maxLength={100} />
                  </div>
                  <div className="space-y-2">
                      <Label>{t("network_dialog.dialogs.edit_guild.label_symbol")}</Label>
                      <div className="flex gap-2 items-center">
                          <Button variant="outline" size="sm" onClick={() => {
                              const input = document.createElement('input');
                              input.type = 'file';
                              input.accept = 'image/*';
                              input.onchange = (e: any) => {
                                  const file = e.target.files[0];
                                  const reader = new FileReader();
                                  reader.onload = (ev: any) => {
                                      const img = new Image();
                                      img.onload = () => {
                                          const canvas = document.createElement('canvas');
                                          canvas.width = 512; canvas.height = 512;
                                          canvas.getContext('2d')?.drawImage(img, 0, 0, 512, 512);
                                          setEditGuildSymbol(canvas.toDataURL('image/webp', 0.6));
                                      };
                                      img.src = ev.target.result;
                                  };
                                  reader.readAsDataURL(file);
                              };
                              input.click();
                          }}>
                              <Upload className="w-4 h-4 mr-2" /> {t("network_dialog.dialogs.edit_guild.btn_change_symbol")}
                          </Button>
                          {editGuildSymbol && <img src={editGuildSymbol} className="w-10 h-10 rounded-full border border-primary" alt="Preview" />}
                      </div>
                  </div>
              </div>
              <DialogFooter>
                  <Button variant="outline" onClick={() => setIsEditGuildOpen(false)}>{t("network_dialog.dialogs.edit_guild.btn_cancel")}</Button>
                  <Button onClick={handleEditGuild}>{t("network_dialog.dialogs.edit_guild.btn_save")}</Button>
              </DialogFooter>
          </DialogContent>
      </Dialog>

      <AlertDialog open={isDeleteGuildOpen} onOpenChange={setIsDeleteGuildOpen}>
          <AlertDialogContent className="z-[100]">
              <AlertDialogHeader>
                  <AlertDialogTitle>{t("network_dialog.dialogs.dissolve_guild.title")}</AlertDialogTitle>
                  <AlertDialogDescription>
                      {t("network_dialog.dialogs.dissolve_guild.desc")}
                  </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                  <AlertDialogCancel>{t("network_dialog.dialogs.dissolve_guild.btn_cancel")}</AlertDialogCancel>
                  <AlertDialogAction onClick={handleDeleteGuild} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">{t("network_dialog.dialogs.dissolve_guild.btn_confirm")}</AlertDialogAction>
              </AlertDialogFooter>
          </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={isLeaveGuildOpen} onOpenChange={setIsLeaveGuildOpen}>
          <AlertDialogContent className="z-[100]">
              <AlertDialogHeader>
                  <AlertDialogTitle>{t("network_dialog.dialogs.leave_guild.title")}</AlertDialogTitle>
                  <AlertDialogDescription>
                      {t("network_dialog.dialogs.leave_guild.desc")}
                      {isLeader && otherMembers.length > 0 && (
                          <div className="mt-4 space-y-2 text-left">
                              <Label className="text-foreground font-bold">{t("network_dialog.dialogs.leave_guild.leader_warning")}</Label>
                              <Select value={newLeaderUid} onValueChange={setNewLeaderUid}>
                                  <SelectTrigger><SelectValue placeholder={t("network_dialog.dialogs.leave_guild.placeholder_new_leader")} /></SelectTrigger>
                                  <SelectContent className="z-[110]">
                                      {otherMembers.map(m => (
                                          <SelectItem key={m.uid} value={m.uid}>{m.name}</SelectItem>
                                      ))}
                                  </SelectContent>
                              </Select>
                          </div>
                      )}
                  </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                  <AlertDialogCancel>{t("network_dialog.dialogs.leave_guild.btn_cancel")}</AlertDialogCancel>
                  <AlertDialogAction onClick={handleLeaveGuild} disabled={isLeader && !newLeaderUid} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">{t("network_dialog.dialogs.leave_guild.btn_confirm")}</AlertDialogAction>
              </AlertDialogFooter>
          </AlertDialogContent>
      </AlertDialog>

      {/* DIALOG CANDIDATURA */}
      <Dialog open={!!selectedGuildToApply} onOpenChange={(open) => !open && setSelectedGuildToApply(null)}>
          <DialogContent className="sm:max-w-md z-[100]">
              <DialogHeader>
                  <DialogTitle>{t("network_dialog.dialogs.apply_guild.title", { name: selectedGuildToApply?.nome_gilda })}</DialogTitle>
                  <DialogDescription>{t("network_dialog.dialogs.apply_guild.desc")}</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                  <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                          <Label>{t("network_dialog.dialogs.apply_guild.label_class")}</Label>
                          <Input value={applyClass} onChange={e => setApplyClass(e.target.value)} placeholder={t("network_dialog.dialogs.apply_guild.placeholder_class")} />
                      </div>
                      <div className="space-y-2">
                          <Label>{t("network_dialog.dialogs.apply_guild.label_level")}</Label>
                          <Input type="number" value={applyLevel} onChange={e => setApplyLevel(e.target.value)} min="1" />
                      </div>
                  </div>
                  <div className="space-y-2">
                      <Label>{t("network_dialog.dialogs.apply_guild.label_letter")}</Label>
                      <Textarea 
                          value={applyLetter} 
                          onChange={e => setApplyLetter(e.target.value)} 
                          placeholder={t("network_dialog.dialogs.apply_guild.placeholder_letter")}
                          className="h-24 resize-none"
                      />
                  </div>
              </div>
              <DialogFooter>
                  <Button variant="outline" onClick={() => setSelectedGuildToApply(null)}>{t("network_dialog.dialogs.apply_guild.btn_cancel")}</Button>
                  <Button onClick={handleApplyGuild} disabled={!applyClass.trim() || !applyLetter.trim()}>{t("network_dialog.dialogs.apply_guild.btn_send")}</Button>
              </DialogFooter>
          </DialogContent>
      </Dialog>

    </Dialog>
  );
};