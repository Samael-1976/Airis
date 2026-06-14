// frontend_mobile/src/components/SkillEditorDialog.tsx
// v2.0 - SKILL EDITOR (JSON PROTOCOL)
// Editor visuale per le Skills del Demiurgo.
// Gestisce la creazione di file JSON con grammatica GBNF.
// LEGGE A0099: Invarianza strutturale garantita.

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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Loader2, Save, Wand2, FileJson, Code, FileText } from "lucide-react";
import { getHeaders } from "@/lib/api";
import { useTranslation } from "@/contexts/TranslationContext";

export interface SkillMetadata {
    filename: string;
    name: string;
    description: string;
    parameters: any;
}

interface SkillEditorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  skillToEdit: SkillMetadata | null;
  serverUrl: string;
  // [AGGIORNATO v124.3] onSave ora accetta anche il tipo (skill o tool)
  onSave: (filename: string, fullContent: string, type: 'skill' | 'tool') => Promise<void>;
  onAutoGenerate: (name: string, description: string) => Promise<string>;
  // [NUOVO v124.3] Prop per determinare il modo operativo
  mode?: 'skill' | 'tool';
}

export const SkillEditorDialog = ({
  open,
  onOpenChange,
  skillToEdit,
  serverUrl,
  onSave,
  onAutoGenerate,
  mode = 'skill' // Default a skill per retrocompatibilità
}: SkillEditorDialogProps) => {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [jsonContent, setJsonContent] = useState("");
  
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  // Reset o Caricamento Dati
  useEffect(() => {
    if (open) {
      if (skillToEdit) {
        setName(skillToEdit.name);
        setDescription(skillToEdit.description);
        fetchSkillContent(skillToEdit.filename);
      } else {
        // Nuovo
        setName("");
        setDescription("");
        setJsonContent(JSON.stringify({
            name: "new_skill",
            category: "skill",
            description: t("skill_editor.default_description"),
            parameters: {
                type: "object",
                properties: {
                    task_description: { type: "string" }
                },
                required: ["task_description"]
            }
        }, null, 2));
      }
    }
  }, [open, skillToEdit]);

  const fetchSkillContent = async (filename: string) => {
      setIsLoading(true);
      try {
          const headers = getHeaders();
          // [AGGIORNATO v124.3] Endpoint dinamico basato sul modo (skills o tools)
          const endpoint = mode === 'skill' ? 'skills' : 'tools';
          const res = await fetch(`${serverUrl}/api/${endpoint}/${filename}`, { headers });
          
          if (!res.ok) throw new Error(t("skill_editor.err_load_failed", { mode }));
          const data = await res.json();
          
          // Il backend restituisce { content: "stringa json" }
          setJsonContent(data.content || "{}");
      } catch (error) {
          console.error(t("skill_editor.err_fetch"), error);
          toast.error(t("skill_editor.error_loading_content"));
      } finally {
          setIsLoading(false);
      }
  };

  const handleGenerate = async () => {
      // Placeholder per futura generazione AI del JSON/GBNF
      toast.info(t("skill_editor.toast_ai_coming_soon"));
  };

  const handleSave = async () => {
      if (!name.trim()) {
          toast.error(t("skill_editor.error_name"));
          return;
      }

      // Validazione JSON
      try {
          const parsed = JSON.parse(jsonContent);
          // [FIX v124.3] Per i Tools nativi, il campo name potrebbe essere dentro 'function'
          const hasName = parsed.name || (parsed.function && parsed.function.name);
          const hasDesc = parsed.description || (parsed.function && parsed.function.description);
          
          if (!hasName || !hasDesc) {
              toast.error(t("skill_editor.error_json_content"));
              return;
          }
      } catch (e) {
          toast.error(t("skill_editor.error_json_format"));
          return;
      }

      setIsSaving(true);
      try {
          // Il filename è basato sul nome (normalizzato)
          const filename = skillToEdit ? skillToEdit.filename : `${name.trim().toLowerCase().replace(/\s+/g, '_')}.json`;
          
          // [AGGIORNATO v124.3] Passa il modo al callback onSave
          await onSave(filename, jsonContent, mode);
          onOpenChange(false);
      } catch (error: any) {
          toast.error(t("skill_editor.error_save"), { description: error.message });
      } finally {
          setIsSaving(false);
      }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {skillToEdit ? t("skill_editor.title_edit") : t("skill_editor.title_create")} {mode === 'skill' ? t("skill_editor.skill") : t("skill_editor.tool")} (JSON)
          </DialogTitle>
          <DialogDescription>
            {t("skill_editor.description")}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto p-1 pr-2 custom-scrollbar space-y-4">
            <style>{`
                .custom-scrollbar::-webkit-scrollbar { width: 8px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: hsl(var(--muted)); border-radius: 4px; }
            `}</style>

            {isLoading ? (
                <div className="flex items-center justify-center h-40">
                    <Loader2 className="w-8 h-8 animate-spin text-primary" />
                </div>
            ) : (
                <>
                    <div className="grid grid-cols-1 gap-4">
                        <div className="space-y-2">
                            <Label>{t("skill_editor.label_name")}</Label>
                            <Input 
                                value={name} 
                                onChange={(e) => setName(e.target.value)} 
                                placeholder={t("skill_editor.placeholder_name")} 
                                className="font-mono"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>{t("skill_editor.label_desc")}</Label>
                            <Input 
                                value={description} 
                                onChange={(e) => setDescription(e.target.value)} 
                                placeholder={t("skill_editor.placeholder_desc")} 
                            />
                        </div>
                    </div>

                    <div className="space-y-2 flex-1 flex flex-col min-h-[400px]">
                        <div className="flex justify-between items-center">
                            <Label className="flex items-center gap-2">
                                <FileJson className="w-4 h-4" /> {t("skill_editor.label_json")}
                            </Label>
                            <Button 
                                size="sm" 
                                variant="secondary" 
                                onClick={handleGenerate} 
                                disabled={true} // Disabilitato per ora
                                className="h-7 text-xs bg-purple-600 hover:bg-purple-700 text-white opacity-50 cursor-not-allowed"
                            >
                                <Wand2 className="w-3 h-3 mr-1" />
                                {t("skill_editor.ai_generate")}
                            </Button>
                        </div>
                        <Textarea 
                            value={jsonContent} 
                            onChange={(e) => setJsonContent(e.target.value)} 
                            className="flex-1 font-mono text-xs bg-muted/30 min-h-[400px] resize-none"
                            placeholder="{ ... }"
                        />
                    </div>
                </>
            )}
        </div>

        <DialogFooter className="pt-4 border-t">
          <Button variant="outline" onClick={() => onOpenChange(false)}>{t("skill_editor.cancel")}</Button>
          <Button onClick={handleSave} disabled={isSaving || isLoading}>
            {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
            {isSaving ? t("skill_editor.saving") : t("skill_editor.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};