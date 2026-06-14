// frontend_mobile/src/components/DemiurgeSettingsTab.tsx
// v1.7 - GATEKEEPER UI LOCK
// ADD: Controllo is_labour_loaded per bloccare l'attivazione del Demiurgo.
// ADD: Alert visivo in caso di Labour Brain (270M) mancante.
// MANTENUTO: Master Switch, Groq/OpenRouter fetch, API Key validation.
// LEGGE A0099: Invarianza strutturale garantita. Codice integrale fornito.

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Loader2, Save, RefreshCw, AlertTriangle, Terminal, Shield, Zap, Power, ShieldAlert, HardDrive } from "lucide-react";
import { toast } from "sonner";
import { ServerConfig, DemiurgeConfig } from "@/types";
import { getBaseUrl, getHeaders } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/contexts/TranslationContext";

interface DemiurgeSettingsTabProps {
  serverConfig: ServerConfig | null;
}

const PROVIDERS = (t: any) => [
  { value: "groq", label: t("demiurge.provider_groq") },
  { value: "openrouter", label: t("demiurge.provider_openrouter") },
  { value: "labour", label: t("demiurge.provider_labour") },
];

export const DemiurgeSettingsTab = ({ serverConfig }: DemiurgeSettingsTabProps) => {
  const { t } = useTranslation();
  const[config, setConfig] = useState<DemiurgeConfig>({
    enabled: false,
    provider: "groq",
    model: "llama-3.3-70b-versatile",
    api_key: "",
    api_base: "",
    auto_run: true,
    safe_mode: false,
    labour_model_on_cpu: true // [NUOVO v52.0]
  });
  
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [labourModels, setLabourModels] = useState<string[]>([]); // [NUOVO v52.0]
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [modelError, setModelError] = useState<string | null>(null);
  
  // --- [MODIFICA v116.0] COSCIENZA UNIFICATA ---
  // Il flag isLabourLoaded è ora rimosso poiché il 12B gestisce tutto.

  const baseUrl = getBaseUrl(serverConfig);
  const headers = { ...getHeaders(), "Content-Type": "application/json" };

  // Caricamento configurazione iniziale e stato Labour
  useEffect(() => {
    if (serverConfig) {
      setIsLoading(true);
      
      // Eseguiamo fetch paralleli per config e stato modelli
      Promise.all([
          fetch(`${baseUrl}/api/settings/demiurge`, { headers }).then(res => res.json()),
          fetch(`${baseUrl}/api/models`, { headers }).then(res => res.json())
      ])
      .then(([demiurgeData, modelsData]) => {
          setConfig(demiurgeData);
          // [NUOVO v52.0] Caricamento modelli operaio
          setLabourModels(modelsData.models.labour_models || []);
          
          // ---[MODIFICA v116.0] RIMOZIONE SYNC GATEKEEPER ---

          // Se il provider è Groq o OpenRouter, prova a caricare i modelli se abbiamo una chiave
          if ((demiurgeData.provider === "groq" || demiurgeData.provider === "openrouter") && 
              demiurgeData.api_key && !demiurgeData.api_key.includes("IL_TUO")) {
             if (!availableModels.includes(demiurgeData.model)) {
                 setAvailableModels([demiurgeData.model]);
             }
          }
      })
      .catch(err => {
          console.error(t("demiurge.error_load"), err);
          toast.error(t("demiurge.error_load"));
      })
      .finally(() => setIsLoading(false));
    }
  }, [serverConfig]);

  // --- LOGICA AUTO-FILL API KEY ---
  const handleProviderChange = async (val: string) => {
      setConfig(prev => ({ ...prev, provider: val }));
      setAvailableModels([]); 
      setModelError(null);

      // [NUOVO v52.0] Gestione selezione automatica modello locale
      if (val === "labour") {
          if (labourModels.length > 0 && !labourModels.includes(config.model)) {
              setConfig(prev => ({ ...prev, model: labourModels[0], provider: val }));
          }
          return;
      }

      if (serverConfig) {
          try {
              const res = await fetch(`${baseUrl}/api/settings/demiurge/api-key?provider=${val}`, { headers });
              if (res.ok) {
                  const data = await res.json();
                  if (data.api_key && !data.api_key.includes("IL_TUO")) {
                      setConfig(prev => ({ ...prev, api_key: data.api_key }));
                      toast.success(t("demiurge.toast_key_restored", { provider: val.toUpperCase() }));
                  } else {
                      setConfig(prev => ({ ...prev, api_key: "" }));
                      toast.warning(t("demiurge.toast_no_key", { provider: val.toUpperCase() }));
                  }
              }
          } catch (error) {
              console.error(t("demiurge.error_fetch_key"), error);
          }
      }
  };

  const fetchGroqModels = async () => {
    if (!config.api_key || config.api_key.includes("IL_TUO")) {
        toast.error(t("demiurge.api_key"));
        return;
    }
    
    setIsLoadingModels(true);
    setModelError(null);
    
    try {
        const res = await fetch(`${baseUrl}/api/settings/demiurge/available-models?api_key=${encodeURIComponent(config.api_key)}`, { headers });
        if (!res.ok) throw new Error(t("demiurge.error_fetch_groq"));
        
        const models = await res.json();
        
        if (Array.isArray(models) && models.length > 0) {
            setAvailableModels(models);
            toast.success(t("demiurge.toast_models_loaded", { count: models.length, provider: "Groq" }));
            if (!models.includes(config.model)) {
                setModelError(t("demiurge.err_model_unavailable", { model: config.model }));
            }
        } else {
            setAvailableModels([]);
            toast.warning(t("demiurge.toast_no_models", { provider: "Groq" }));
        }
    } catch (error: any) {
        console.error(t("demiurge.error_fetch_models"), error);
        toast.error(t("demiurge.error_fetch"), { description: error.message });
    } finally {
        setIsLoadingModels(false);
    }
  };

  const fetchOpenRouterModels = async () => {
    if (!config.api_key || config.api_key.includes("IL_TUO")) {
        toast.error(t("demiurge.api_key"));
        return;
    }

    setIsLoadingModels(true);
    setModelError(null);
    
    try {
        const res = await fetch(`${baseUrl}/api/settings/demiurge/available-models/openrouter?api_key=${encodeURIComponent(config.api_key)}`, { headers });
        if (!res.ok) throw new Error(t("demiurge.error_fetch"));
        
        const models = await res.json();
        
        if (Array.isArray(models) && models.length > 0) {
            setAvailableModels(models);
            toast.success(t("demiurge.toast_models_loaded", { count: models.length, provider: "OpenRouter" }));
        } else {
            setAvailableModels([]);
            toast.warning(t("demiurge.toast_no_models", { provider: "OpenRouter" }));
        }
    } catch (error: any) {
        console.error(t("demiurge.error_fetch_models"), error);
        toast.error(t("demiurge.error_fetch"), { description: error.message });
    } finally {
        setIsLoadingModels(false);
    }
  };

  const handleSave = async (updatedConfig?: DemiurgeConfig) => {
    const configToSave = updatedConfig || config;
    setIsSaving(true);
    try {
        const res = await fetch(`${baseUrl}/api/settings/demiurge`, {
            method: 'POST',
            headers,
            body: JSON.stringify(configToSave)
        });
        
        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || t("demiurge.error_save"));
        }
        
        toast.success(t("demiurge.success_save"));
        if (configToSave.enabled) {
            toast.info(t("demiurge.mutual_exclusion"));
        }
        setModelError(null); 
    } catch (error: any) {
        toast.error(t("demiurge.error_save"), { description: error.message });
    } finally {
        setIsSaving(false);
    }
  };

  const handleMasterToggle = (checked: boolean) => {
      const newConfig = { ...config, enabled: checked };
      setConfig(newConfig);
      handleSave(newConfig);
  };

  return (
    <div className="space-y-6 p-4 max-w-2xl mx-auto">
        <div className="space-y-1 border-b border-white/10 pb-2">
            <h3 className="text-lg font-medium flex items-center gap-2 text-purple-400">
                <Terminal className="w-5 h-5" /> {t("demiurge.title")}
            </h3>
            <p className="text-xs text-muted-foreground">
                {t("demiurge.description")}
            </p>
        </div>

        {isLoading ? (
            <div className="flex justify-center py-8"><Loader2 className="animate-spin" /></div>
        ) : (
            <div className="space-y-4">
                
                {/* MASTER SWITCH */}
                <div className={cn(
                    "flex items-center justify-between p-4 border rounded-lg transition-all",
                    config.enabled ? "bg-purple-500/10 border-purple-500/40" : "bg-muted/10 border-border/50"
                )}>
                    <div className="space-y-0.5">
                        <Label className="text-base flex items-center gap-2">
                            <Power className={cn("w-4 h-4", config.enabled ? "text-green-500" : "text-muted-foreground")} />
                            {t("demiurge.enable")}
                        </Label>
                        <p className="text-xs text-muted-foreground">
                            {t("demiurge.enable_desc")}
                        </p>
                    </div>
                    <Switch 
                        checked={config.enabled} 
                        onCheckedChange={handleMasterToggle} 
                    />
                </div>

                <div className={cn(
                    "space-y-4 transition-all duration-300", 
                    !config.enabled && "opacity-40 pointer-events-none blur-[1px]"
                )}>
                    {/* PROVIDER SELECTION */}
                    <div className="space-y-2">
                        <Label>{t("demiurge.provider")}</Label>
                        <Select 
                            value={config.provider} 
                            onValueChange={handleProviderChange}
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {PROVIDERS(t).map(p => (
                                    <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* API KEY */}
                    {config.provider !== 'labour' && (
                        <div className="space-y-2 animate-in fade-in">
                            <Label>{t("demiurge.api_key")}</Label>
                            <Input 
                                type="password" 
                                value={config.api_key} 
                                onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
                                placeholder={t("demiurge.api_key")}
                            />
                        </div>
                    )}

                    {/* MODEL SELECTION */}
                    <div className="space-y-2">
                        <Label>{t("demiurge.model_name")}</Label>
                        <div className="flex gap-2">
                            <div className="flex-1">
                                <Select 
                                    value={config.model} 
                                    onValueChange={(val) => setConfig({ ...config, model: val })}
                                >
                                    <SelectTrigger className={modelError ? "border-red-500" : ""}>
                                        <SelectValue placeholder={t("demiurge.select_model")} />
                                    </SelectTrigger>
                                    <SelectContent className="max-h-[300px]">
                                        {/* [NUOVO v52.0] Switch tra modelli remoti e locali */}
                                        {config.provider === "labour" ? (
                                            labourModels.map(m => (
                                                <SelectItem key={m} value={m}>{m}</SelectItem>
                                            ))
                                        ) : (
                                            availableModels.map(m => (
                                                <SelectItem key={m} value={m}>{m}</SelectItem>
                                            ))
                                        )}
                                        
                                        {config.provider !== "labour" && !availableModels.includes(config.model) && config.model && (
                                            <SelectItem value={config.model}>{t("demiurge.current_model", { model: config.model })}</SelectItem>
                                        )}
                                    </SelectContent>
                                </Select>
                            </div>

                            {config.provider === "groq" && (
                                <Button 
                                    variant="outline" 
                                    size="icon" 
                                    onClick={fetchGroqModels} 
                                    disabled={isLoadingModels || !config.api_key || config.api_key.includes("IL_TUO")}
                                    title={t("demiurge.model_name")}
                                >
                                    {isLoadingModels ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                                </Button>
                            )}

                            {config.provider === "openrouter" && (
                                <Button 
                                    variant="outline" 
                                    size="icon" 
                                    onClick={fetchOpenRouterModels} 
                                    disabled={isLoadingModels || !config.api_key || config.api_key.includes("IL_TUO")}
                                    title={t("demiurge.model_name")}
                                >
                                    {isLoadingModels ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                                </Button>
                            )}
                        </div>
                        {modelError && (
                            <Alert variant="destructive" className="py-2">
                                <AlertTriangle className="h-4 w-4" />
                                <AlertTitle>{t("demiurge.invalid_model")}</AlertTitle>
                                <AlertDescription className="text-xs">{modelError}</AlertDescription>
                            </Alert>
                        )}
                    </div>

                    {/* SETTINGS SWITCHES */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                        <div className="flex items-center justify-between p-3 border rounded-lg bg-muted/10">
                            <div className="space-y-0.5">
                                <Label className="flex items-center gap-2"><Zap className="w-4 h-4 text-yellow-400" /> {t("demiurge.auto_run")}</Label>
                                <p className="text-xs text-muted-foreground">{t("demiurge.auto_run_desc")}</p>
                            </div>
                            <Switch 
                                checked={config.auto_run} 
                                onCheckedChange={(c) => setConfig({ ...config, auto_run: c })} 
                            />
                        </div>

                        <div className="flex items-center justify-between p-3 border rounded-lg bg-muted/10">
                            <div className="space-y-0.5">
                                <Label className="flex items-center gap-2"><Shield className="w-4 h-4 text-green-400" /> {t("demiurge.safe_mode")}</Label>
                                <p className="text-xs text-muted-foreground">{t("demiurge.safe_mode_desc")}</p>
                            </div>
                            <Switch 
                                checked={config.safe_mode} 
                                onCheckedChange={(c) => setConfig({ ...config, safe_mode: c })} 
                            />
                        </div>

                        {/* [NUOVO v52.0] Switch Esecuzione CPU (Solo per Labour) */}
                        {config.provider === "labour" && (
                            <div className="flex items-center justify-between p-3 border rounded-lg bg-blue-500/5 border-blue-500/20 col-span-full animate-in slide-in-from-top-2">
                                <div className="space-y-0.5">
                                    <Label className="flex items-center gap-2 text-blue-400">
                                        <HardDrive className="w-4 h-4" /> {t("demiurge.cpu_exec")}
                                    </Label>
                                    <p className="text-[10px] text-muted-foreground">{t("demiurge.cpu_exec_desc")}</p>
                                </div>
                                <Switch 
                                    checked={config.labour_model_on_cpu} 
                                    onCheckedChange={(c) => setConfig({ ...config, labour_model_on_cpu: c })} 
                                />
                            </div>
                        )}
                    </div>
                </div>

                <div className="pt-4">
                    <Button 
                        onClick={() => handleSave()} 
                        disabled={isSaving} 
                        className="w-full bg-purple-600 hover:bg-purple-700"
                    >
                        {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                        {t("demiurge.save")}
                    </Button>
                </div>

            </div>
        )}
    </div>
  );
};