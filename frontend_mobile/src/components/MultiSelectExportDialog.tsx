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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Download, CheckSquare, Square, Upload } from "lucide-react";
import { toast } from "sonner";
import { getHeaders } from "@/lib/api";
import { useTranslation } from "@/contexts/TranslationContext";

interface MultiSelectExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  exportType: 'pure' | 'world';
  serverUrl: string;
  onExport: (type: 'pure' | 'world', avatars: string[], lore?: string) => Promise<void>;
  onImport: () => void;
}

export const MultiSelectExportDialog = ({
  open,
  onOpenChange,
  exportType,
  serverUrl,
  onExport,
  onImport,
}: MultiSelectExportDialogProps) => {
  const { t } = useTranslation();
  const [availableAvatars, setAvailableAvatars] = useState<string[]>([]);
  const [availableLores, setAvailableLores] = useState<string[]>([]);
  const [selectedAvatars, setSelectedAvatars] = useState<string[]>([]);
  const [selectedLore, setSelectedLore] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    if (open) {
      setIsLoading(true);
      
      const headers = getHeaders();

      const fetchData = async () => {
        try {
          const avatarsRes = await fetch(`${serverUrl}/api/exportable-items?item_type=avatar`, { headers });
          if (!avatarsRes.ok) throw new Error(t("export_dialog.err_fetch_avatars"));
          const avatars = await avatarsRes.json();
          setAvailableAvatars(avatars);
          setSelectedAvatars([]); 

          if (exportType === 'world') {
            const loresRes = await fetch(`${serverUrl}/api/exportable-items?item_type=lore`, { headers });
            if (!loresRes.ok) throw new Error(t("export_dialog.err_fetch_worlds"));
            const lores = await loresRes.json();
            setAvailableLores(lores);
            if (lores.length > 0) setSelectedLore(lores[0]);
          }
        } catch (error) {
          console.error(t("export_dialog.err_fetch"), error);
          toast.error(t("export_dialog.error_load"));
        } finally {
          setIsLoading(false);
        }
      };
      fetchData();
    }
  }, [open, serverUrl, exportType]);

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
      toast.warning(t("export_dialog.warning_avatar"));
      return;
    }
    if (exportType === 'world' && !selectedLore) {
      toast.warning(t("export_dialog.warning_world"));
      return;
    }

    setIsExporting(true);
    try {
      await onExport(exportType, selectedAvatars, selectedLore);
      onOpenChange(false);
    } catch (error) {
      // Error handling done in parent
    } finally {
      setIsExporting(false);
    }
  };
  
  const handleImportClick = () => {
      onImport();
      onOpenChange(false);
  };

  const isAllSelected = availableAvatars.length > 0 && selectedAvatars.length === availableAvatars.length;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {exportType === 'pure' ? t("export_dialog.title_pure") : t("export_dialog.title_world")}
          </DialogTitle>
          <DialogDescription>
            {t("export_dialog.description")}
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : (
          <div className="flex-1 flex flex-col gap-4 py-4 overflow-hidden">
            
            {exportType === 'world' && (
              <div className="space-y-2">
                <Label>{t("export_dialog.select_world")}</Label>
                <Select value={selectedLore} onValueChange={setSelectedLore}>
                  <SelectTrigger>
                    <SelectValue placeholder={t("export_dialog.placeholder_world")} />
                  </SelectTrigger>
                  <SelectContent>
                    {availableLores.map(lore => (
                      <SelectItem key={lore} value={lore}>{lore}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="flex items-center justify-between">
              <Label>{t("export_dialog.select_avatars", { selected: selectedAvatars.length, total: availableAvatars.length })}</Label>
              <Button variant="ghost" size="sm" onClick={handleSelectAll} className="h-8 px-2 text-xs">
                {isAllSelected ? (
                  <>
                    <Square className="w-3 h-3 mr-1" /> {t("export_dialog.deselect_all")}
                  </>
                ) : (
                  <>
                    <CheckSquare className="w-3 h-3 mr-1" /> {t("export_dialog.select_all")}
                  </>
                )}
              </Button>
            </div>

            <div className="flex-1 border rounded-md bg-muted/10 overflow-hidden">
              <ScrollArea className="h-[300px] p-4">
                <div className="grid grid-cols-1 gap-3">
                  {availableAvatars.map(avatar => (
                    <div key={avatar} className="flex items-center space-x-3 p-2 rounded hover:bg-muted/50 transition-colors">
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
                    <p className="text-sm text-muted-foreground text-center py-4">{t("export_dialog.no_avatars")}</p>
                  )}
                </div>
              </ScrollArea>
            </div>
          </div>
        )}

        {/* FOOTER RESPONSIVE: Flex-col su mobile, Flex-row su desktop */}
        <DialogFooter className="flex flex-col sm:flex-row gap-2 sm:justify-between">
          <Button variant="outline" onClick={() => onOpenChange(false)} className="w-full sm:w-auto">
            {t("export_dialog.cancel")}
          </Button>
          
          <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
             <Button variant="secondary" onClick={handleImportClick} className="w-full sm:w-auto">
                <Upload className="mr-2 h-4 w-4" /> {t("export_dialog.import")}
             </Button>
             <Button onClick={handleExportClick} disabled={isLoading || isExporting || selectedAvatars.length === 0} className="w-full sm:w-auto">
                {isExporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                {isExporting ? t("export_dialog.exporting") : t("export_dialog.export")}
             </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};