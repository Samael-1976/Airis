// frontend_mobile/src/components/CognitiveModuleDialog.tsx
// v1.0 - COGNITIVE MODULE EDITOR
// Editor visuale per i Moduli Cognitivi di Airis.
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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { Loader2, Save, BrainCircuit, Activity, Tags } from "lucide-react";
import { getHeaders } from "@/lib/api";
import { CognitiveModule, ActivationCondition } from "@/types";
import { useTranslation } from "@/contexts/TranslationContext"; // IMPORT NECESSARIO

interface CognitiveModuleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  moduleToEdit: CognitiveModule | null;
  serverUrl: string;
  onSaveSuccess: () => void;
}

export const CognitiveModuleDialog = ({
  open,
  onOpenChange,
  moduleToEdit,
  serverUrl,
  onSaveSuccess,
}: CognitiveModuleDialogProps) => {
  const { t } = useTranslation();
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState<"identity" | "behavior" | "restriction" | "system">("behavior");
  const [context, setContext] = useState<"always" | "avatar" | "gdr">("always");
  const [priority, setPriority] = useState<number>(50);
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");
  
  // Bio-Cognitive Trigger States
  const [useTrigger, setUseTrigger] = useState(false);
  const [triggerVector, setTriggerVector] = useState("gelosia");
  const [triggerOperator, setTriggerOperator] = useState<">" | "<" | ">=" | "<=" | "==">(">");
  const [triggerThreshold, setTriggerThreshold] = useState<number>(80);

  const [isSaving, setIsSaving] = useState(false);

  // Helper per tradurre le stringhe dinamiche (Bypass Glitch Parentesi)
  const parseDynamicT = (text: string) => {
    if (!text || typeof text !== 'string') return text;
    const matchT = text.match(/^t\(\s*['"](.+?)['"]\s*\)$/);
    if (matchT && matchT[1]) return t(matchT[1]);
    
    const openB = String.fromCharCode(91);
    const closeB = String.fromCharCode(93);
    if (text.indexOf(openB) === 0 && text.endsWith(closeB)) return t(text.slice(1, -1).trim());
    return text;
  };

  useEffect(() => {
    if (open) {
      if (moduleToEdit) {
        setId(moduleToEdit.id);
        setName(parseDynamicT(moduleToEdit.name));
        setCategory(moduleToEdit.category);
        setContext(moduleToEdit.context);
        setPriority(moduleToEdit.priority);
        
        // Controlla se esiste una traduzione per il contenuto, altrimenti usa il raw
        const transKey = `cognitive_modules.${moduleToEdit.id}.content`;
        const translatedContent = t(transKey);
        const fallbackStr = String.fromCharCode(91) + transKey + String.fromCharCode(93);
        
        if (translatedContent && translatedContent !== fallbackStr) {
            setContent(translatedContent);
        } else {
            setContent(moduleToEdit.content);
        }
        
        setTags(moduleToEdit.tags.join(", "));
        
        if (moduleToEdit.activation_condition) {
          setUseTrigger(true);
          setTriggerVector(moduleToEdit.activation_condition.vector);
          setTriggerOperator(moduleToEdit.activation_condition.operator);
          setTriggerThreshold(moduleToEdit.activation_condition.threshold);
        } else {
          setUseTrigger(false);
        }
      } else {
        // Reset for new module
        setId("");
        setName("");
        setCategory("behavior");
        setContext("always");
        setPriority(50);
        setContent("");
        setTags("");
        setUseTrigger(false);
        setTriggerVector("gelosia");
        setTriggerOperator(">");
        setTriggerThreshold(80);
      }
    }
  }, [open, moduleToEdit]);

  const handleSave = async () => {
    if (!name.trim() || !content.trim()) {
      toast.error(t("cognitive_module.validation_error"));
      return;
    }

    // Auto-generate ID if empty
    const finalId = id.trim() || name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_');

    const moduleData: CognitiveModule = {
      id: finalId,
      name: name.trim(),
      category,
      context,
      content: content.trim(),
      is_active: moduleToEdit ? moduleToEdit.is_active : true, // Preserve active state if editing
      priority,
      tags: tags.split(",").map(t => t.trim()).filter(t => t.length > 0),
    };

    if (useTrigger) {
      moduleData.activation_condition = {
        vector: triggerVector.trim(),
        operator: triggerOperator,
        threshold: triggerThreshold,
      };
    }

    setIsSaving(true);
    try {
      const headers = { ...getHeaders(), "Content-Type": "application/json" };
      const res = await fetch(`${serverUrl}/api/cognitive/modules`, {
        method: "POST",
        headers,
        body: JSON.stringify(moduleData),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || t("cognitive_module.error_save"));
      }

      toast.success(t("cognitive_module.save_success"));
      onSaveSuccess();
      onOpenChange(false);
    } catch (error: any) {
      toast.error(t("cognitive_module.save_error"), { description: error.message });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl h-[90vh] flex flex-col p-0 gap-0 bg-background">
        <DialogHeader className="p-6 pb-4 border-b border-white/10 shrink-0">
          <DialogTitle className="flex items-center gap-2 text-primary">
            <BrainCircuit className="w-5 h-5" />
            {moduleToEdit ? t("cognitive_module.title_edit") : t("cognitive_module.title_new")}
          </DialogTitle>
          <DialogDescription>
            {t("cognitive_module.description")}
          </DialogDescription>
        </DialogHeader>

        {/* PROTOCOLLO FLEXBOX RIGIDO & SCROLL ETERNO */}
        <div className="flex-1 relative min-h-0">
          <div className="absolute inset-0 overflow-y-scroll custom-scrollbar p-6 space-y-6">
            
            {/* Basic Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>{t("cognitive_module.name_label")}</Label>
                <Input 
                  value={name} 
                  onChange={(e) => setName(e.target.value)} 
                  placeholder={t("cognitive_module.name_placeholder")} 
                />
              </div>
              <div className="space-y-2">
                <Label>{t("cognitive_module.id_label")}</Label>
                <Input 
                  value={id} 
                  onChange={(e) => setId(e.target.value)} 
                  placeholder={t("cognitive_module.id_placeholder")} 
                  disabled={!!moduleToEdit} // Cannot change ID once created
                  className="font-mono text-xs"
                />
              </div>
            </div>

            {/* Routing & Priority */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 border rounded-lg bg-muted/5">
              <div className="space-y-2">
                <Label>{t("cognitive_module.category_label")}</Label>
                <Select value={category} onValueChange={(v: any) => setCategory(v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="identity">{t("cognitive_module.category_identity")}</SelectItem>
                    <SelectItem value="behavior">{t("cognitive_module.category_behavior")}</SelectItem>
                    <SelectItem value="restriction">{t("cognitive_module.category_restriction")}</SelectItem>
                    <SelectItem value="system">{t("cognitive_module.category_system")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>{t("cognitive_module.context_label")}</Label>
                <Select value={context} onValueChange={(v: any) => setContext(v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="always">{t("cognitive_module.context_always")}</SelectItem>
                    <SelectItem value="avatar">{t("cognitive_module.context_avatar")}</SelectItem>
                    <SelectItem value="gdr">{t("cognitive_module.context_gdr")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>{t("cognitive_module.priority_label")}</Label>
                <Input 
                  type="number" 
                  min={1} max={100} 
                  value={priority} 
                  onChange={(e) => setPriority(parseInt(e.target.value) || 50)} 
                />
                <p className="text-[10px] text-muted-foreground">{t("cognitive_module.priority_hint")}</p>
              </div>
            </div>

            {/* Bio-Cognitive Trigger */}
            <div className="p-4 border rounded-lg border-pink-500/30 bg-pink-500/5 space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="flex items-center gap-2 text-pink-500">
                    <Activity className="w-4 h-4" /> {t("cognitive_module.trigger_label")}
                  </Label>
                  <p className="text-xs text-muted-foreground">{t("cognitive_module.trigger_desc")}</p>
                </div>
                <Switch checked={useTrigger} onCheckedChange={setUseTrigger} />
              </div>

              {useTrigger && (
                <div className="grid grid-cols-3 gap-2 animate-in fade-in slide-in-from-top-2">
                  <div className="space-y-1">
                    <Label className="text-[10px] uppercase">{t("cognitive_module.trigger_vector")}</Label>
                    <Input 
                      value={triggerVector} 
                      onChange={(e) => setTriggerVector(e.target.value)} 
                      placeholder={t("cognitive_module.trigger_vector_placeholder")} 
                      className="h-8 text-xs" 
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[10px] uppercase">{t("cognitive_module.trigger_operator")}</Label>
                    <Select value={triggerOperator} onValueChange={(v: any) => setTriggerOperator(v)}>
                      <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value=">">{`> (${t("cognitive_module.op_greater")})`}</SelectItem>
                        <SelectItem value="<">{`< (${t("cognitive_module.op_less")})`}</SelectItem>
                        <SelectItem value=">=">{`>= (${t("cognitive_module.op_greater_eq")})`}</SelectItem>
                        <SelectItem value="<=">{`<= (${t("cognitive_module.op_less_eq")})`}</SelectItem>
                        <SelectItem value="==">{`== (${t("cognitive_module.op_equal")})`}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[10px] uppercase">{t("cognitive_module.trigger_threshold")}</Label>
                    <Input type="number" value={triggerThreshold} onChange={(e) => setTriggerThreshold(parseInt(e.target.value) || 0)} className="h-8 text-xs" />
                  </div>
                </div>
              )}
            </div>

            {/* Content */}
            <div className="space-y-2 flex-1 flex flex-col">
              <Label>{t("cognitive_module.content_label")}</Label>
              <Textarea 
                value={content} 
                onChange={(e) => setContent(e.target.value)} 
                className="min-h-[250px] font-mono text-xs bg-background/50 resize-y"
                placeholder={t("cognitive_module.content_placeholder")}
              />
            </div>

            {/* Tags */}
            <div className="space-y-2">
              <Label className="flex items-center gap-2"><Tags className="w-4 h-4" /> {t("cognitive_module.tags_label")}</Label>
              <Input 
                value={tags} 
                onChange={(e) => setTags(e.target.value)} 
                placeholder={t("cognitive_module.tags_placeholder")}
              />
            </div>

          </div>
        </div>

        <DialogFooter className="p-4 border-t bg-muted/5 shrink-0">
          <Button variant="outline" onClick={() => onOpenChange(false)}>{t("cognitive_module.btn_cancel")}</Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
            {t("cognitive_module.btn_save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};