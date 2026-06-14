// frontend_mobile/src/components/UiThemesTab.tsx
// v1.0 - UI THEMES EDITOR
// Gestisce la personalizzazione dei colori dell'interfaccia con preview in tempo reale.
// LEGGE A0099: Invarianza strutturale garantita.
// LEGGE A0120: Scrollbar e Sicurezza applicate.

import React, { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ThemeConfig } from "@/types";
import { useTranslation } from "@/contexts/TranslationContext";
import { Paintbrush, RotateCcw, Save } from "lucide-react";

interface UiThemesTabProps {
  currentTheme?: ThemeConfig;
  onSaveTheme: (theme: ThemeConfig) => void;
  onRestoreDefault: () => void;
}

// --- HELPER: CONVERSIONE COLORI ---
// Tailwind usa HSL (es. "222.2 84% 4.9%"). Gli input HTML usano HEX (es. "#0a0a0a").
const hslToHex = (hslStr: string): string => {
  if (!hslStr) return "#000000";
  const [hStr, sStr, lStr] = hslStr.split(" ");
  const h = parseFloat(hStr);
  const s = parseFloat(sStr.replace("%", "")) / 100;
  const l = parseFloat(lStr.replace("%", "")) / 100;

  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  let r = 0, g = 0, b = 0;

  if (0 <= h && h < 60) { r = c; g = x; b = 0; }
  else if (60 <= h && h < 120) { r = x; g = c; b = 0; }
  else if (120 <= h && h < 180) { r = 0; g = c; b = x; }
  else if (180 <= h && h < 240) { r = 0; g = x; b = c; }
  else if (240 <= h && h < 300) { r = x; g = 0; b = c; }
  else if (300 <= h && h < 360) { r = c; g = 0; b = x; }

  const toHex = (n: number) => {
    const hex = Math.round((n + m) * 255).toString(16);
    return hex.length === 1 ? "0" + hex : hex;
  };

  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
};

const hexToHsl = (hex: string): string => {
  let r = parseInt(hex.slice(1, 3), 16) / 255;
  let g = parseInt(hex.slice(3, 5), 16) / 255;
  let b = parseInt(hex.slice(5, 7), 16) / 255;

  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h = 0, s = 0, l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
    }
    h /= 6;
  }

  return `${(h * 360).toFixed(1)} ${(s * 100).toFixed(1)}% ${(l * 100).toFixed(1)}%`;
};

// --- PRESET TEMATICI ---
const PRESETS: Record<string, ThemeConfig> = {
  "airis_default": {
    background: "222.2 84% 4.9%",
    foreground: "210 40% 98%",
    primary: "340 82% 52%",
    "primary-foreground": "210 40% 98%",
    secondary: "217.2 32.6% 17.5%",
    "secondary-foreground": "210 40% 98%",
    muted: "217.2 32.6% 17.5%",
    "muted-foreground": "215 20.2% 65.1%",
    accent: "340 82% 52%",
    "accent-foreground": "210 40% 98%",
    card: "222.2 84% 4.9%",
    "card-foreground": "210 40% 98%",
    border: "217.2 32.6% 17.5%"
  },
  "cyberpunk": {
    background: "270 50% 5%",
    foreground: "150 100% 70%",
    primary: "310 100% 60%",
    "primary-foreground": "0 0% 100%",
    secondary: "200 100% 30%",
    "secondary-foreground": "150 100% 70%",
    muted: "270 40% 10%",
    "muted-foreground": "150 50% 50%",
    accent: "180 100% 50%",
    "accent-foreground": "0 0% 0%",
    card: "270 50% 5%",
    "card-foreground": "150 100% 70%",
    border: "310 100% 60%"
  },
  "abyss": {
    background: "220 50% 2%",
    foreground: "210 40% 90%",
    primary: "210 100% 40%",
    "primary-foreground": "0 0% 100%",
    secondary: "220 40% 10%",
    "secondary-foreground": "210 40% 90%",
    muted: "220 40% 8%",
    "muted-foreground": "210 20% 60%",
    accent: "210 100% 50%",
    "accent-foreground": "0 0% 100%",
    card: "220 50% 2%",
    "card-foreground": "210 40% 90%",
    border: "220 40% 15%"
  }
};

export const UiThemesTab = ({ currentTheme, onSaveTheme, onRestoreDefault }: UiThemesTabProps) => {
  const { t } = useTranslation();
  
  // Stato locale per la preview in tempo reale
  const [localTheme, setLocalTheme] = useState<ThemeConfig>(currentTheme || PRESETS["airis_default"]);
  const [selectedPreset, setSelectedPreset] = useState<string>("custom");

  // Sincronizza lo stato locale se il tema esterno cambia
  useEffect(() => {
    if (currentTheme) {
      setLocalTheme(currentTheme);
    }
  }, [currentTheme]);

  const handleColorChange = (key: keyof ThemeConfig, hexValue: string) => {
    const hslValue = hexToHsl(hexValue);
    setLocalTheme(prev => ({ ...prev, [key]: hslValue }));
    setSelectedPreset("custom");
  };

  const handleApplyPreset = (presetKey: string) => {
    setSelectedPreset(presetKey);
    if (PRESETS[presetKey]) {
      setLocalTheme(PRESETS[presetKey]);
    }
  };

  const handleSave = () => {
    onSaveTheme(localTheme);
  };

  // Genera stili inline per la preview
  const previewStyles = {
    backgroundColor: `hsl(${localTheme.background})`,
    color: `hsl(${localTheme.foreground})`,
    borderColor: `hsl(${localTheme.border})`
  };

  return (
    <div className="flex flex-col h-full py-4 max-w-4xl mx-auto w-full">
      
      {/* HEADER & PRESETS */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-white/10 pb-4 mb-4 shrink-0">
        <div className="space-y-1">
          <h3 className="text-lg font-medium flex items-center gap-2 text-primary">
            <Paintbrush className="w-5 h-5" /> {t("ui_themes.title")}
          </h3>
          <p className="text-xs text-muted-foreground">{t("ui_themes.desc")}</p>
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Select value={selectedPreset} onValueChange={handleApplyPreset}>
            <SelectTrigger className="w-full sm:w-[180px] h-8 text-xs">
              <SelectValue placeholder={t("ui_themes.select_preset")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="custom">{t("ui_themes.preset_custom")}</SelectItem>
              <SelectItem value="airis_default">Airis Pink (Default)</SelectItem>
              <SelectItem value="cyberpunk">Cyberpunk Neon</SelectItem>
              <SelectItem value="abyss">Abisso Scuro</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* PROTOCOLLO FLEXBOX RIGIDO & SCROLL ETERNO (Applicato al contenitore globale) */}
      <div className="flex-1 overflow-y-auto custom-scrollbar pr-2 min-h-[400px]">
          <div className="flex flex-col md:flex-row gap-6 pb-4">
            
            {/* LEFT: COLOR PICKERS */}
            <div className="w-full md:w-1/2 flex flex-col gap-4">
                <div className="border rounded-lg bg-muted/5 p-4 space-y-4">
                  
                  <div className="space-y-3">
                    <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{t("ui_themes.section_backgrounds")}</Label>
                    <ColorRow label={t("ui_themes.color_bg_main")} value={localTheme.background} onChange={(v) => handleColorChange("background", v)} />
                    <ColorRow label={t("ui_themes.color_bg_secondary")} value={localTheme.muted} onChange={(v) => handleColorChange("muted", v)} />
                    <ColorRow label={t("ui_themes.color_border")} value={localTheme.border} onChange={(v) => handleColorChange("border", v)} />
                  </div>

                  <div className="space-y-3 pt-4 border-t border-white/10">
                    <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{t("ui_themes.section_bubbles")}</Label>
                    <ColorRow label={t("ui_themes.color_bubble_user")} value={localTheme.primary} onChange={(v) => handleColorChange("primary", v)} />
                    <ColorRow label={t("ui_themes.color_text_user")} value={localTheme["primary-foreground"]} onChange={(v) => handleColorChange("primary-foreground", v)} />
                    <ColorRow label={t("ui_themes.color_bubble_ai")} value={localTheme.secondary} onChange={(v) => handleColorChange("secondary", v)} />
                    <ColorRow label={t("ui_themes.color_text_ai")} value={localTheme["secondary-foreground"]} onChange={(v) => handleColorChange("secondary-foreground", v)} />
                  </div>

                  <div className="space-y-3 pt-4 border-t border-white/10">
                    <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{t("ui_themes.section_accents")}</Label>
                    <ColorRow label={t("ui_themes.color_text_main")} value={localTheme.foreground} onChange={(v) => handleColorChange("foreground", v)} />
                    <ColorRow label={t("ui_themes.color_accent")} value={localTheme.accent} onChange={(v) => handleColorChange("accent", v)} />
                  </div>

                </div>
            </div>

            {/* RIGHT: LIVE PREVIEW */}
            <div className="w-full md:w-1/2 flex flex-col">
                <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">{t("ui_themes.live_preview")}</Label>
                <div 
                    className="min-h-[350px] rounded-lg border shadow-inner overflow-hidden flex flex-col transition-colors duration-300"
                    style={previewStyles}
                >
                    {/* Header Finto */}
                    <div className="p-3 border-b flex items-center gap-3 shrink-0" style={{ borderColor: `hsl(${localTheme.border})`, backgroundColor: `hsl(${localTheme.card})` }}>
                        <div className="w-8 h-8 rounded-full bg-gray-500/20 flex items-center justify-center overflow-hidden">
                            <span className="text-xs">AI</span>
                        </div>
                        <div className="flex-1">
                            <div className="h-3 w-24 rounded bg-gray-500/20 mb-1"></div>
                            <div className="h-2 w-16 rounded bg-gray-500/10"></div>
                        </div>
                        <Paintbrush className="w-4 h-4" style={{ color: `hsl(${localTheme.accent})` }} />
                    </div>

                    {/* Chat Finta */}
                    <div className="flex-1 p-4 space-y-4 overflow-y-auto flex flex-col justify-end">
                        {/* Bolla AI */}
                        <div className="flex items-end gap-2">
                            <div className="w-6 h-6 rounded-full bg-gray-500/20 shrink-0"></div>
                            <div 
                                className="p-3 rounded-2xl rounded-bl-none max-w-[80%] text-sm transition-colors duration-300"
                                style={{ backgroundColor: `hsl(${localTheme.secondary})`, color: `hsl(${localTheme["secondary-foreground"]})` }}
                            >
                                {t("ui_themes.preview_ai_msg")}
                            </div>
                        </div>

                        {/* Bolla Utente */}
                        <div className="flex items-end gap-2 justify-end">
                            <div 
                                className="p-3 rounded-2xl rounded-br-none max-w-[80%] text-sm transition-colors duration-300"
                                style={{ backgroundColor: `hsl(${localTheme.primary})`, color: `hsl(${localTheme["primary-foreground"]})` }}
                            >
                                {t("ui_themes.preview_user_msg")}
                            </div>
                            <div className="w-6 h-6 rounded-full bg-gray-500/20 shrink-0"></div>
                        </div>
                    </div>

                    {/* Input Finto */}
                    <div className="p-3 border-t shrink-0" style={{ borderColor: `hsl(${localTheme.border})`, backgroundColor: `hsl(${localTheme.muted})` }}>
                        <div className="h-10 rounded-full flex items-center px-4" style={{ backgroundColor: `hsl(${localTheme.background})`, border: `1px solid hsl(${localTheme.border})` }}>
                            <span className="text-xs opacity-50" style={{ color: `hsl(${localTheme.foreground})` }}>{t("ui_themes.preview_input")}</span>
                            <div className="ml-auto w-6 h-6 rounded-full flex items-center justify-center" style={{ backgroundColor: `hsl(${localTheme.primary})` }}>
                                <ArrowUpIcon className="w-3 h-3" style={{ color: `hsl(${localTheme["primary-foreground"]})` }} />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

          </div>
      </div>

      {/* FOOTER CONTROLS */}
      <div className="flex justify-between items-center pt-4 mt-4 border-t border-white/10 shrink-0">
        <Button variant="ghost" size="sm" onClick={onRestoreDefault} className="text-muted-foreground hover:text-destructive">
            <RotateCcw className="w-4 h-4 mr-2" /> {t("ui_themes.btn_restore")}
        </Button>
        <Button onClick={handleSave} className="bg-primary hover:bg-primary/90 text-white">
            <Save className="w-4 h-4 mr-2" /> {t("ui_themes.btn_save")}
        </Button>
      </div>

    </div>
  );
};

// Sotto-componente per la riga del colore
const ColorRow = ({ label, value, onChange }: { label: string, value: string, onChange: (hex: string) => void }) => {
    const hexValue = hslToHex(value);
    return (
        <div className="flex items-center justify-between p-2 rounded hover:bg-white/5 transition-colors">
            <Label className="text-xs cursor-pointer flex-1">{label}</Label>
            <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-muted-foreground uppercase w-16 text-right">{hexValue}</span>
                <div className="relative w-8 h-8 rounded overflow-hidden border border-white/20 shadow-sm cursor-pointer">
                    <input 
                        type="color" 
                        value={hexValue} 
                        onChange={(e) => onChange(e.target.value)}
                        className="absolute inset-[-10px] w-[50px] h-[50px] cursor-pointer"
                    />
                </div>
            </div>
        </div>
    );
};

const ArrowUpIcon = ({ className, style }: { className?: string, style?: React.CSSProperties }) => (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className} style={style}>
        <path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>
    </svg>
);