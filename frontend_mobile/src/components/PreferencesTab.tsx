// frontend_mobile/src/components/PreferencesTab.tsx
import React from "react";
import { useTranslation } from "@/contexts/TranslationContext";
import { cn } from "@/lib/utils";
import { Globe, Sparkles, Clock } from "lucide-react";

interface PreferencesTabProps {
  avatars: string[];
  allAvatarData: Record<string, any>;
  enrichedRpgWorlds: any[];
  selectedAvatar: string;
  selectedRpg: string;
  onSelectAvatar: (avatar: string) => void;
  onSelectRpg: (rpg: string) => void;
  serverUrl: string;
}

export const PreferencesTab: React.FC<PreferencesTabProps> = ({
  avatars,
  allAvatarData,
  enrichedRpgWorlds,
  selectedAvatar,
  selectedRpg,
  onSelectAvatar,
  onSelectRpg,
  serverUrl
}) => {
  const { t } = useTranslation();

  const formatDate = (timestamp: number) => {
    if (!timestamp) return t("preferences_tab.never_played", { defaultValue: "Mai giocato" });
    return new Date(timestamp).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="flex flex-col md:flex-row h-full w-full gap-4 p-4 overflow-y-auto md:overflow-hidden custom-scrollbar">
      
      {/* COLONNA ANIME */}
      <div className="flex flex-col flex-none md:flex-1 h-[400px] md:h-full border border-border/50 rounded-xl bg-muted/5 overflow-hidden">
        <div className="p-3 border-b border-border/50 bg-muted/20 shrink-0">
          <h3 className="font-bold text-sm text-primary flex items-center gap-2">
            <Sparkles className="w-4 h-4" /> {t("preferences_tab.anime_title", { defaultValue: "Anime" })}
          </h3>
        </div>
        
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
          {avatars.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground text-xs italic py-10">
                {t("character_manager.no_avatars_found", { defaultValue: "Nessun avatar trovato." })}
            </div>
          ) : (
            avatars.map((avatarName) => {
              const isSelected = selectedAvatar.toLowerCase() === avatarName.toLowerCase();
              const avatarData = allAvatarData[avatarName.toLowerCase()];
              const imgUrl = avatarData?.ai_base_avatar_url 
                ? (avatarData.ai_base_avatar_url.startsWith('http') 
                    ? avatarData.ai_base_avatar_url 
                    : `${serverUrl.replace(/\/$/, '')}/${avatarData.ai_base_avatar_url.replace(/^\//, '')}`) 
                : null;

              return (
                <div 
                  key={avatarName}
                  onClick={() => onSelectAvatar(avatarName)}
                  className={cn(
                    "flex flex-col items-center justify-center p-4 rounded-xl border-2 cursor-pointer transition-all duration-200 shrink-0",
                    isSelected 
                      ? "border-primary bg-primary/10 shadow-[0_0_15px_rgba(233,30,99,0.2)]" 
                      : "border-transparent bg-background/50 hover:bg-muted/50 hover:border-primary/30"
                  )}
                >
                  <h4 className={cn("font-bold text-lg mb-4", isSelected ? "text-primary" : "text-foreground")}>
                    {avatarName.charAt(0).toUpperCase() + avatarName.slice(1)}
                  </h4>
                  <div className={cn(
                    "w-32 h-32 rounded-full overflow-hidden border-4 transition-all duration-200",
                    isSelected ? "border-primary" : "border-muted"
                  )}>
                    {imgUrl ? (
                      <img src={imgUrl} alt={avatarName} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full bg-muted flex items-center justify-center text-muted-foreground">
                        No Image
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* COLONNA RPG */}
      <div className="flex flex-col flex-none md:flex-1 h-[400px] md:h-full border border-border/50 rounded-xl bg-muted/5 overflow-hidden">
        <div className="p-3 border-b border-border/50 bg-muted/20 shrink-0">
          <h3 className="font-bold text-sm text-primary flex items-center gap-2">
            <Globe className="w-4 h-4" /> {t("preferences_tab.rpg_title", { defaultValue: "RPG" })}
          </h3>
        </div>
        
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
          
          {/* CARD STANDARD MODE */}
          <div 
            onClick={() => onSelectRpg("STANDARD")}
            className={cn(
              "flex flex-col p-4 rounded-xl border-2 cursor-pointer transition-all duration-200 shrink-0",
              selectedRpg === "STANDARD" 
                ? "border-primary bg-primary/10 shadow-[0_0_15px_rgba(233,30,99,0.2)]" 
                : "border-border/50 bg-background/50 hover:bg-muted/50 hover:border-primary/30"
            )}
          >
            <h4 className={cn("font-bold text-md mb-2", selectedRpg === "STANDARD" ? "text-primary" : "text-foreground")}>
              {t("preferences_tab.standard_mode", { defaultValue: "Realtà Condivisa (Modalità Standard)" })}
            </h4>
            <p className="text-xs text-muted-foreground italic">
              {t("preferences_tab.standard_desc", { defaultValue: "Nessun mondo GDR attivo. L'Anima interagirà come assistente personale nel mondo reale." })}
            </p>
          </div>

          {/* CARDS GDR */}
          {enrichedRpgWorlds.length === 0 ? (
              <div className="flex items-center justify-center py-10 text-muted-foreground text-xs italic">
                  Nessun mondo GDR trovato.
              </div>
          ) : (
              enrichedRpgWorlds.map((world) => {
                const isSelected = selectedRpg === world.id;
                return (
                  <div 
                    key={world.id}
                    onClick={() => onSelectRpg(world.id)}
                    className={cn(
                      "flex flex-col p-4 rounded-xl border-2 cursor-pointer transition-all duration-200 shrink-0",
                      isSelected 
                        ? "border-primary bg-primary/10 shadow-[0_0_15px_rgba(233,30,99,0.2)]" 
                        : "border-border/50 bg-background/50 hover:bg-muted/50 hover:border-primary/30"
                    )}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h4 className={cn("font-bold text-md", isSelected ? "text-primary" : "text-foreground")}>
                        {world.title}
                      </h4>
                    </div>
                    
                    <div className="flex items-center gap-1 text-[10px] text-muted-foreground mb-3">
                      <Clock className="w-3 h-3" />
                      <span>{t("preferences_tab.last_played", { defaultValue: "Ultima sessione:" })} {formatDate(world.last_played)}</span>
                    </div>

                    {world.description && (
                      <div className="text-xs text-foreground/80 leading-relaxed line-clamp-4">
                        <span className="font-bold opacity-50 mr-1">{t("preferences_tab.backstory", { defaultValue: "**STORIA PREGRESSA:**" })}</span>
                        {world.description}
                      </div>
                    )}
                  </div>
                );
              })
          )}

        </div>
      </div>

    </div>
  );
};