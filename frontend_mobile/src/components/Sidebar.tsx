// frontend_mobile/src/components/Sidebar.tsx
// v2.2 - SMART HOME INTEGRATION
// ADD: Pulsante "Smart Home" (onOpenSmartHome) sotto Hive.
// MANTENUTO: Hive, Intercom, GDR Mode, Settings, Memory Gallery, Manage RPG, Avatar Status.
// LEGGE A0099: Invarianza strutturale garantita. Codice integrale fornito.

import { useState } from "react";
import { useTranslation } from "@/contexts/TranslationContext";
import {
  ChevronLeft,
  ChevronRight,
  Power,
  UserCircle,
  Upload,
  Download,
  User,
  Settings,
  Dices,
  Volume2,
  VolumeX,
  Users,
  BrainCircuit,
  Eye,
  Ear,
  History,
  PlusSquare,
  BrainCog,
  Sparkles,
  Globe,
  Ghost,
  Network,
  Images,
  Heart,
  Home // [NUOVO] Icona per Smart Home
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { toast } from "sonner"; //[NUOVO] Import per le notifiche

interface SidebarProps {
  onConnect: () => void;
  onEditProfile: () => void;
  onSettings: () => void;
  onManagePg: () => void;
  onManagePng: () => void;
  onManageModels: () => void;
  onSessionHistory: () => void;
  onNewSession: () => void;
  onManageProactiveMemory: () => void;
  onOpenSecurity: () => void;
  onOpenGallery: () => void;
  onOpenHeartState: () => void;
  onOpenSmartHome: () => void; // [NUOVO] Prop per aprire SmartHomeDialog
  onOpenNetwork: () => void; // [NUOVO] Prop per aprire la Taverna Multiplayer
  isConnected: boolean;
  isGdrMode: boolean;
  onToggleGdrMode: () => void;
  isMuted: boolean;
  onToggleMute: () => void;
  isMonitoring: boolean;
  onToggleMonitoring: () => void;
  isHotwordListening: boolean;
  onToggleHotword: () => void;
  isGdrLoaded: boolean;
}

export const Sidebar = ({
  onConnect,
  onEditProfile,
  onSettings,
  onManagePg,
  onManagePng,
  onManageModels,
  onSessionHistory,
  onNewSession,
  onManageProactiveMemory,
  onOpenSecurity,
  onOpenGallery,
  onOpenHeartState,
  onOpenSmartHome, // [NUOVO]
  onOpenNetwork, //[NUOVO]
  isConnected,
  isGdrMode,
  onToggleGdrMode,
  isMuted,
  onToggleMute,
  isMonitoring,
  onToggleMonitoring,
  isHotwordListening,
  onToggleHotword,
  isGdrLoaded,
}: SidebarProps) => {
  const { t } = useTranslation();
  const[open, setOpen] = useState(false);

  const handleItemClick = (onClick: () => void) => {
    onClick();
    setOpen(false);
  };

  // --- [NUOVO] WRAPPER PER NOTIFICHE TOAST IMMEDIATE ---
  const handleGdrToggle = (checked: boolean) => {
    onToggleGdrMode();
    if (checked) toast.success(t("sidebar.toast_gdr_on"));
    else toast.info(t("sidebar.toast_gdr_off"));
  };

  const handleMuteToggle = (checked: boolean) => {
    onToggleMute();
    if (checked) toast.info(t("sidebar.toast_mute_on"));
    else toast.success(t("sidebar.toast_mute_off"));
  };

  const handleMonitoringToggle = (checked: boolean) => {
    onToggleMonitoring();
    if (checked) toast.success(t("sidebar.toast_monitoring_on"));
    else toast.info(t("sidebar.toast_monitoring_off"));
  };

  const handleHearingToggle = (checked: boolean) => {
    onToggleHotword();
    if (checked) toast.success(t("sidebar.toast_hearing_on"));
    else toast.info(t("sidebar.toast_hearing_off"));
  };

  return (
    <>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="fixed top-20 left-4 z-50 text-foreground/80 hover:text-primary hover:bg-primary/10"
          >
            <ChevronRight className="w-6 h-6" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-80 bg-sidebar-bg border-r p-0">
          <div className="flex flex-col h-full">
            <div className="flex items-center justify-between p-4 border-b">
              <SheetTitle className="text-xl font-semibold">{t("sidebar.menu_title")}</SheetTitle>
              <SheetDescription className="sr-only">
                {t("sidebar.description")}
              </SheetDescription>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setOpen(false)}
                className="text-foreground/80 hover:text-primary"
              >
                <ChevronLeft className="w-5 h-5" />
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto py-2 custom-scrollbar">
              <div className="px-4 py-2">
                <p className="text-xs uppercase text-muted-foreground font-semibold tracking-wider">{t("sidebar.nav_connection")}</p>
                
                {/* NOTA: Il pulsante di connessione è temporaneamente nascosto. Verrà spostato in una nuova posizione nei prossimi aggiornamenti. NON ELIMINARE IL CODICE. */}
                <div className="hidden">
                    <button
                      onClick={() => handleItemClick(onConnect)}
                      className="sidebar-item w-full text-left"
                    >
                      <Power className={cn("w-5 h-5", isConnected ? "text-green-500" : "text-red-500")} />
                      <span className={cn(isConnected ? "text-green-500" : "text-red-500")}>
                        {isConnected ? t("sidebar.disconnect") : t("sidebar.connect")}
                      </span>
                    </button>
                </div>
                
                <button
                  onClick={() => handleItemClick(onOpenSecurity)}
                  className="sidebar-item w-full text-left mt-2"
                  disabled={!isConnected}
                >
                  <Network className="w-5 h-5 text-purple-400" />
                  <span>{t("sidebar.hive")}</span>
                </button>

                {/* [NUOVO] Pulsante Smart Home */}
                <button
                  onClick={() => handleItemClick(onOpenSmartHome)}
                  className="sidebar-item w-full text-left mt-2"
                  disabled={!isConnected}
                >
                  <Home className="w-5 h-5 text-blue-400" />
                  <span>{t("sidebar.care_os")}</span>
                </button>

                {/* [NUOVO] Pulsante Taverna Multiplayer */}
                <button
                  onClick={() => handleItemClick(onOpenNetwork)}
                  className="sidebar-item w-full text-left mt-2"
                  disabled={!isConnected}
                >
                  <Globe className="w-5 h-5 text-emerald-400" />
                  <span>{t("sidebar.tavern")}</span>
                </button>
              </div>
              
              <Separator className="my-2 bg-border/50" />

              <div className="px-4 py-2">
                <p className="text-xs uppercase text-muted-foreground font-semibold tracking-wider">{t("sidebar.nav_session")}</p>
                <button
                  onClick={() => handleItemClick(onSessionHistory)}
                  className="sidebar-item w-full text-left"
                  disabled={!isConnected}
                >
                  <History className="w-5 h-5" />
                  <span>{t("sidebar.history")}</span>
                </button>
                
                <button
                  onClick={() => handleItemClick(onOpenGallery)}
                  className="sidebar-item w-full text-left"
                  disabled={!isConnected}
                >
                  <Images className="w-5 h-5" />
                  <span>{t("sidebar.gallery")}</span>
                </button>

                <button
                  onClick={() => handleItemClick(onNewSession)}
                  className="sidebar-item w-full text-left"
                  disabled={!isConnected}
                >
                  <PlusSquare className="w-5 h-5" />
                  <span>{t("sidebar.new_session")}</span>
                </button>
              </div>

              <Separator className="my-2 bg-border/50" />

              <div className="px-4 py-2">
                <p className="text-xs uppercase text-muted-foreground font-semibold tracking-wider">{t("sidebar.nav_perception")}</p>
                 <div className="flex items-center justify-between px-6 py-4">
                    <Label 
                      htmlFor="gdr-mode-switch" 
                      className="flex items-center gap-4 cursor-pointer text-sm font-medium"
                    >
                      <Dices className="w-5 h-5" />
                      {t("sidebar.gdr_mode")}
                    </Label>
                    <Switch
                      id="gdr-mode-switch"
                      checked={isGdrMode}
                      onCheckedChange={handleGdrToggle}
                      disabled={!isConnected || !isGdrLoaded}
                    />
                  </div>
                 <div className="flex items-center justify-between px-6 py-4">
                    <Label 
                      htmlFor="mute-switch" 
                      className="flex items-center gap-4 cursor-pointer text-sm font-medium"
                    >
                      {isMuted ? <VolumeX className="w-5 h-5 text-red-500" /> : <Volume2 className="w-5 h-5 text-green-500" />}
                      {t("sidebar.mute_audio")}
                    </Label>
                    <Switch
                      id="mute-switch"
                      checked={isMuted}
                      onCheckedChange={handleMuteToggle} 
                      disabled={!isConnected}
                    />
                  </div>
                  <div className="flex items-center justify-between px-6 py-4">
                    <Label 
                      htmlFor="monitoring-switch" 
                      className="flex items-center gap-4 cursor-pointer text-sm font-medium"
                    >
                      <Eye className={cn("w-5 h-5", isMonitoring ? "text-blue-400" : "text-muted-foreground")} />
                      {t("sidebar.screen_monitoring")}
                    </Label>
                    <Switch
                      id="monitoring-switch"
                      checked={isMonitoring}
                      onCheckedChange={handleMonitoringToggle}
                      disabled={!isConnected}
                    />
                  </div>
                   <div className="flex items-center justify-between px-6 py-4">
                    <Label 
                      htmlFor="hotword-switch" 
                      className="flex items-center gap-4 cursor-pointer text-sm font-medium"
                    >
                      <Ear className={cn("w-5 h-5", isHotwordListening ? "text-blue-400" : "text-muted-foreground")} />
                      {t("sidebar.active_hearing")}
                    </Label>
                    <Switch
                      id="hotword-switch"
                      checked={isHotwordListening}
                      onCheckedChange={handleHearingToggle}
                      disabled={!isConnected}
                    />
                  </div>
              </div>

              <Separator className="my-2 bg-border/50" />

              <div className="px-4 py-2">
                <p className="text-xs uppercase text-muted-foreground font-semibold tracking-wider">{t("sidebar.nav_characters")}</p>
                
                <button
                  onClick={() => handleItemClick(onOpenHeartState)}
                  className="sidebar-item w-full text-left"
                  disabled={!isConnected}
                >
                  <Heart className="w-5 h-5 text-pink-500" />
                  <span>{t("sidebar.souls_status")}</span>
                </button>

                <button
                  onClick={() => handleItemClick(onManagePng)}
                  className="sidebar-item w-full text-left"
                  disabled={!isConnected || !isGdrLoaded}
                >
                  <Users className="w-5 h-5" />
                  <span>{t("sidebar.manage_rpg")}</span>
                </button>
              </div>
              
              <Separator className="my-2 bg-border/50" />

              <div className="px-4 py-2">
                <p className="text-xs uppercase text-muted-foreground font-semibold tracking-wider">{t("sidebar.nav_data")}</p>
                
                <button
                    onClick={() => handleItemClick(onManageModels)}
                    className="sidebar-item w-full text-left"
                    disabled={!isConnected}
                  >
                    <BrainCircuit className="w-5 h-5" />
                    <span>{t("sidebar.manage_models")}</span>
                </button>

                <button
                    onClick={() => handleItemClick(onManageProactiveMemory)}
                    className="sidebar-item w-full text-left"
                    disabled={!isConnected}
                  >
                    <BrainCog className="w-5 h-5" />
                    <span>{t("sidebar.proactive_memory")}</span>
                </button>
              </div>
            </div>

            <Separator className="bg-border/50" />

            <div className="p-2">
              <button
                onClick={() => handleItemClick(onEditProfile)}
                className="sidebar-item w-full text-left"
              >
                <User className="w-5 h-5" />
                <span>{t("sidebar.your_profile")}</span>
              </button>
              <button
                onClick={() => handleItemClick(onSettings)}
                className="sidebar-item w-full text-left"
              >
                <Settings className="w-5 h-5" />
                <span>{t("sidebar.settings")}</span>
              </button>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
};