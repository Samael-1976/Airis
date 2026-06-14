// frontend_mobile/src/components/GenesisDialog.tsx
// v1.0 - RITO DELLA GENESI ISOLATO
// Gestisce la selezione dei PNG iniziali per un nuovo mondo GDR.
// LEGGE A0099: Invarianza strutturale garantita.
// LEGGE A0120: Scrollbar Flexbox Rigido applicato.

import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Sparkles, CheckSquare, Square } from "lucide-react";
import { useTranslation } from "@/contexts/TranslationContext";

interface GenesisDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  availablePngs: string[];
  onStart: (selectedPngs: string[]) => void;
  onCancel: () => void;
}

export const GenesisDialog = ({
  open,
  onOpenChange,
  availablePngs,
  onStart,
  onCancel,
}: GenesisDialogProps) => {
  const { t } = useTranslation();
  const [selectedPngs, setSelectedPngs] = useState<string[]>([]);

  // Reset della selezione quando il dialogo si apre
  useEffect(() => {
    if (open) {
      setSelectedPngs([]);
    }
  }, [open]);

  const handleSelectAll = () => {
    setSelectedPngs([...availablePngs]);
  };

  const handleDeselectAll = () => {
    setSelectedPngs([]);
  };

  const handleToggle = (png: string, checked: boolean) => {
    if (checked) {
      setSelectedPngs((prev) => [...prev, png]);
    } else {
      setSelectedPngs((prev) => prev.filter((p) => p !== png));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent 
        className="sm:max-w-md border-primary/20 bg-background/95 backdrop-blur-xl flex flex-col h-[70dvh] sm:h-[500px] max-h-[90dvh]"
        onPointerDownOutside={(e) => e.preventDefault()} 
        onEscapeKeyDown={(e) => e.preventDefault()}
      >
        <DialogHeader className="shrink-0">
          <DialogTitle className="text-primary flex items-center gap-2">
            <Sparkles className="w-5 h-5" /> {t("genesis_dialog.title")}
          </DialogTitle>
          <DialogDescription>
            {t("genesis_dialog.desc")}
          </DialogDescription>
        </DialogHeader>

        {/* Tasti di selezione rapida */}
        {availablePngs.length > 0 && (
          <div className="flex gap-2 mt-2 shrink-0">
            <Button variant="secondary" size="sm" className="flex-1 h-8 text-xs" onClick={handleSelectAll}>
              <CheckSquare className="w-3 h-3 mr-2" /> {t("genesis_dialog.select_all")}
            </Button>
            <Button variant="outline" size="sm" className="flex-1 h-8 text-xs" onClick={handleDeselectAll}>
              <Square className="w-3 h-3 mr-2" /> {t("genesis_dialog.deselect_all")}
            </Button>
          </div>
        )}

        {/* Area di Scroll (Protocollo Flexbox Rigido) */}
        <div className="flex-1 relative min-h-0 border border-border/50 rounded-md mt-2 bg-muted/10">
          <div className="absolute inset-0 overflow-y-scroll custom-scrollbar p-3">
            <div className="space-y-3">
              {availablePngs.map((png) => (
                <div 
                  key={png} 
                  className="flex items-center space-x-3 bg-background/50 p-3 rounded-md border border-white/5 hover:border-primary/30 transition-colors cursor-pointer"
                  onClick={() => handleToggle(png, !selectedPngs.includes(png))}
                >
                  <Checkbox 
                    id={`genesis-${png}`} 
                    checked={selectedPngs.includes(png)}
                    onCheckedChange={(checked) => handleToggle(png, !!checked)}
                    onClick={(e) => e.stopPropagation()} // Evita doppio trigger
                  />
                  <Label 
                    htmlFor={`genesis-${png}`} 
                    className="flex-1 cursor-pointer font-medium text-sm"
                    onClick={(e) => e.preventDefault()} // Lascia gestire al div padre
                  >
                    {png.replace(/_/g, ' ')}
                  </Label>
                </div>
              ))}
              {availablePngs.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-8 italic">
                  {t("genesis_dialog.no_pngs")}
                </p>
              )}
            </div>
          </div>
        </div>

        <DialogFooter className="mt-4 shrink-0 flex-row justify-between gap-2 sm:justify-end">
          <Button variant="outline" className="flex-1 sm:flex-none" onClick={() => {
            onOpenChange(false);
            onCancel();
          }}>
            {t("genesis_dialog.btn_cancel")}
          </Button>
          <Button 
            className="flex-1 sm:flex-none bg-primary hover:bg-primary/90 text-white"
            onClick={() => {
              onOpenChange(false);
              onStart(selectedPngs);
            }}
          >
            {t("genesis_dialog.btn_start")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};