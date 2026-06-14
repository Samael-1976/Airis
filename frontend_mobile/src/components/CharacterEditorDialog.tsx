// frontend_mobile/src/components/CharacterEditorDialog.tsx
// v5.7 - SUPREME SCROLLBAR & MOBILE FLOW FIX
// FIX: Risolto il blocco dello scroll su mobile implementando un contenitore scorrevole unico per il corpo.
// FIX: Applicato il Protocollo Flexbox Rigido (Absolute Inset) al Main Body per forzare la comparsa della scrollbar.
// FIX: Garantita la visibilità della barra rosa Airis tramite CSS iniettato.
// MANTENUTO: Ogni singolo commento, logica di filtraggio, handler e import originale.
// LEGGE A0099: Invarianza strutturale garantita. Codice integrale fornito.

import { useState, useEffect, useRef } from "react";
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
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectGroup,
  SelectLabel,
  SelectSeparator
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox"; // [FIX CRITICO] Import aggiunto nel posto giusto
import { ServerConfig, AvailableLanguages } from "@/types";
import { toast } from "sonner";
import { Loader2, Sparkles, Edit, Upload, Music4, UserCog, Plus, Trash2, X, BrainCircuit, Save, RefreshCw, Swords, BookOpen, Shield, Wand2 } from "lucide-react";
import { getBaseUrl, getHeaders } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/contexts/TranslationContext";

interface CharacterEditorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  type: "PG" | "PNG" | "AVATAR";
  characterId?: string;
  serverConfig: ServerConfig | null;
  onSave: (characterData: any, imageFile: File | null) => void;
  onAutofill: (url: string) => void;
  autofillData: any | null;
  onGuildCommand?: (cmd: string, payload?: any) => void; // [NUOVO]
}

// Struttura Tratto Personalità
interface PersonalityTrait {
    valore: number;
    desc_min: string;
    desc_max: string;
}

// Struttura Preset
interface PersonalityPresets {
    [key: string]: { [trait: string]: number };
}

// --- DEFINIZIONE COSTANTE DEI 17 TRATTI BASE ---
const ALL_BASE_TRAITS: Record<string, [string, string]> = {
    "Acidità": ["character_editor.traits.acidita_min", "character_editor.traits.acidita_max"],
    "Amicizia": ["character_editor.traits.amicizia_min", "character_editor.traits.amicizia_max"],
    "Audacia": ["character_editor.traits.audacia_min", "character_editor.traits.audacia_max"],
    "Carisma": ["character_editor.traits.carisma_min", "character_editor.traits.carisma_max"],
    "Emotività": ["character_editor.traits.emotivita_min", "character_editor.traits.emotivita_max"],
    "Espansività": ["character_editor.traits.espansivita_min", "character_editor.traits.espansivita_max"],
    "Freddezza": ["character_editor.traits.freddezza_min", "character_editor.traits.freddezza_max"],
    "Gelosia": ["character_editor.traits.gelosia_min", "character_editor.traits.gelosia_max"],
    "Lealtà": ["character_editor.traits.lealta_min", "character_editor.traits.lealta_max"],
    "Libidine": ["character_editor.traits.libidine_min", "character_editor.traits.libidine_max"],
    "Loquacità": ["character_editor.traits.loquacita_min", "character_editor.traits.loquacita_max"],
    "Protettiva": ["character_editor.traits.protettiva_min", "character_editor.traits.protettiva_max"],
    "Seduzione": ["character_editor.traits.seduzione_min", "character_editor.traits.seduzione_max"],
    "Sfrontatezza": ["character_editor.traits.sfrontatezza_min", "character_editor.traits.sfrontatezza_max"],
    "Socialità": ["character_editor.traits.socialita_min", "character_editor.traits.socialita_max"],
    "Stabilità": ["character_editor.traits.stabilita_min", "character_editor.traits.stabilita_max"],
    "Timidezza": ["character_editor.traits.timidezza_min", "character_editor.traits.timidezza_max"]
};

// Liste per il raggruppamento nel dropdown
const FEMALE_PRESETS = ["Tsundere", "Kuudere", "Dandere", "Genki", "Oneesan", "Wild", "Yandere"];
const MALE_PRESETS = ["Ore-Sama", "Stoic", "Shy Boy", "Jock/Bro", "Mentor/Daddy", "Primal", "Possessive"];

// --- [NUOVO v15.0] SEZIONI CORE PROTETTE ---
const CORE_SECTIONS =["dati_anagrafici", "essenza_e_anima", "dati_fisici_ed_estetici", "dettagli_intimi"];

// --- COMPONENTE IBRIDO PER DROPDOWN/TESTO LIBERO (FIX RE-RENDER AMNESIA) ---
const HybridInput = ({ value, onChange, options, placeholder }: { value: string, onChange: (v: string) => void, options: string[], placeholder: string }) => {
    const { t } = useTranslation(); // Importiamo il traduttore internamente
    const isValueCustom = value !== "" && !options.includes(value);
    const [forceCustom, setForceCustom] = useState(false);

    const showInput = isValueCustom || forceCustom;

    if (showInput) {
        return (
            <div className="flex gap-1">
                <Input 
                    value={value} 
                    onChange={e => onChange(e.target.value)} 
                    className="h-7 text-xs flex-1" 
                    placeholder={placeholder} 
                    autoFocus
                />
                <Button 
                    variant="ghost" 
                    size="icon" 
                    className="h-7 w-7 shrink-0" 
                    onClick={() => { 
                        setForceCustom(false); 
                        onChange(options[0] || ""); 
                    }}
                >
                    <X className="w-3 h-3"/>
                </Button>
            </div>
        );
    }
    return (
        <Select value={value} onValueChange={v => {
            if (v === "custom") { 
                setForceCustom(true); 
                onChange(""); 
            }
            else {
                onChange(v);
            }
        }}>
            <SelectTrigger className="h-7 text-xs"><SelectValue placeholder={placeholder} /></SelectTrigger>
            <SelectContent>
                {options.map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}
                <SelectItem value="custom" className="font-bold text-primary">{t("character_editor.rpg.custom_option")}</SelectItem>
            </SelectContent>
        </Select>
    );
};

export const CharacterEditorDialog = ({
  open,
  onOpenChange,
  type,
  characterId,
  serverConfig,
  onSave,
  onAutofill,
  autofillData,
  onGuildCommand,
}: CharacterEditorDialogProps) => {
  const { t } = useTranslation();
  // [FIX v5.7] CSS INIETTATO PER SCROLLBAR (DOGMA APPENDICE C)
  const scrollbarStyles = `
    .airis-editor-scrollbar::-webkit-scrollbar {
        width: 8px !important;
        display: block !important;
    }
    .airis-editor-scrollbar::-webkit-scrollbar-thumb {
        background-color: hsl(340 82% 52%) !important;
        border-radius: 10px !important;
    }
    .airis-editor-scrollbar::-webkit-scrollbar-track {
        background: hsl(220 15% 10%) !important;
    }
  `;

  const [formData, setFormData] = useState<any>({});
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isAutofilling, setIsAutofilling] = useState(false);
  const [sourceUrl, setSourceUrl] = useState("");
  
  // Stati per la gestione delle voci
  const [languages, setLanguages] = useState<AvailableLanguages>({});
  const [userLanguage, setUserLanguage] = useState<string>("it");
  const [loadingVoices, setLoadingVoices] = useState(false);
  
  // Stato per il nome utente reale (per sostituzione placeholder)
  const [realUserName, setRealUserName] = useState<string>("User");

  // --- STATI ANIMA FLUIDA ---
  const [personalityTraits, setPersonalityTraits] = useState<Record<string, PersonalityTrait>>({});
  const [presets, setPresets] = useState<PersonalityPresets>({});
  const [selectedPreset, setSelectedPreset] = useState<string>("");
  const [newTraitName, setNewTraitName] = useState("");
  const [newTraitMin, setNewTraitMin] = useState("");
  const [newTraitMax, setNewTraitMax] = useState("");
  const [isAddingTrait, setIsAddingTrait] = useState(false);

  // --- [NUOVO v15.0] STATI EDITING DINAMICO ---
  const [newSectionName, setNewSectionName] = useState("");
  const [isAddingSection, setIsAddingSection] = useState(false);
  const [isGeneratingRpg, setIsGeneratingRpg] = useState(false); // [NUOVO] Stato caricamento AI

  // --- STATI GILDA ---
  const [guilds, setGuilds] = useState<any[]>([]);
  const [isEditGuildOpen, setIsEditGuildOpen] = useState(false);
  const [isDeleteGuildOpen, setIsDeleteGuildOpen] = useState(false);
  const [isLeaveGuildOpen, setIsLeaveGuildOpen] = useState(false);
  const [editGuildName, setEditGuildName] = useState("");
  const [editGuildSymbol, setEditGuildSymbol] = useState("");
  const [newLeaderUid, setNewLeaderUid] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const isEditMode = !!characterId;

  // Helper per inizializzare tutti i tratti a 0
  const getInitialTraits = () => {
      const initial: Record<string, PersonalityTrait> = {};
      Object.entries(ALL_BASE_TRAITS).forEach(([name, descs]) => {
          initial[name] = { valore: 0, desc_min: descs[0], desc_max: descs[1] };
      });
      return initial;
  };

  // --- HELPER SOSTITUZIONE PLACEHOLDER (REGEX GOD TIER) ---
  const formatTextForDisplay = (text: string) => {
      if (!text || typeof text !== 'string') return text;
      // [FIX BUG CRITICO] Regex Schiacciasassi: 
      // 1. Cattura 1 o più graffe iniziali/finali.
      // 2. Ignora spazi, trattini o underscore anomali.
      // 3. \d* alla fine disintegra numeri incollati per errore (es. l'anomalia "1976").
      return text.replace(/\{+[\s]*(NOME|NAME)[\s_-]*(PG|USER)[\s]*\}+\d*/gi, realUserName);
  };

  const fetchGuilds = async () => {
    try {
      const res = await fetch(`https://airis-6a824-default-rtdb.europe-west1.firebasedatabase.app/gilde.json`);
      if (res.ok) {
        const data = await res.json() || {};
        setGuilds(Object.keys(data).map(key => ({ id: key, ...data[key] })));
      }
    } catch (e) {}
  };

  useEffect(() => {
    if (open) fetchGuilds();
  }, [open]);

  // Caricamento dati personaggio e preset
  useEffect(() => {
    if (open && serverConfig) {
      const serverUrl = getBaseUrl(serverConfig);
      const headers = getHeaders();

      // 0. Carica Profilo Utente per il nome reale
      fetch(`${serverUrl}/api/user_profile`, { headers })
          .then(res => res.json())
          .then(profile => {
              if (profile && profile.name) {
                  setRealUserName(profile.name);
              }
          })
          .catch(err => console.error(t("character_editor.err_load_user_profile"), err));

      // 1. Carica Preset Globali
      fetch(`${serverUrl}/api/personality/presets`, { headers })
          .then(res => res.json())
          .then(data => setPresets(data))
          .catch(err => console.error(t("character_editor.err_load_presets"), err));

      // 2. Carica Dati Personaggio (se edit mode)
      if (isEditMode) {
          setIsLoading(true);
          fetch(`${serverUrl}/api/characters/${characterId}?char_type=${type}`, { headers })
            .then((res) => {
              if (!res.ok) throw new Error(`Failed to fetch ${type} data`);
              return res.json();
            })
            .then((data) => {
              const cleanData = data.jsonData;
              if (cleanData.dati_anagrafici && !cleanData.dati_anagrafici.voce) {
                  cleanData.dati_anagrafici.voce = ""; 
              }
              setFormData(cleanData);
              
              // Carica Personalità Dinamica con Merge sui Default
              const loadedTraits = cleanData.personalita_dinamica || {};
              const mergedTraits = getInitialTraits();
              
              // Sovrascrivi i default con i dati caricati
              Object.entries(loadedTraits).forEach(([key, val]: [string, any]) => {
                  mergedTraits[key] = val;
              });
              
              setPersonalityTraits(mergedTraits);
              
              // Tenta di indovinare il preset dall'archetipo salvato
              const savedArchetype = cleanData.essenza_e_anima?.archetipo_attuale;
              if (savedArchetype && savedArchetype !== t("common.none")) {
                  const presetName = savedArchetype.split(' ')[0]; 
                  setSelectedPreset(presetName); 
              } else {
                  setSelectedPreset("Custom");
              }

              if (data.avatarUrl) {
                const fullUrl = data.avatarUrl.startsWith('/') ? `${serverUrl}${data.avatarUrl}` : data.avatarUrl;
                setImagePreview(fullUrl);
              } else {
                setImagePreview(null);
              }
              setImageFile(null);
            })
            .catch((error) => {
              console.error(t("character_editor.err_fetch_data", { type }), error);
              toast.error(t("character_editor.err_load_data", { type }));
              onOpenChange(false);
            })
            .finally(() => setIsLoading(false));
      } else {
          // Nuovo Personaggio: Template Vuoto
          setFormData({
            "dati_anagrafici": { 
                "nome_completo": "", 
                "genere": "unspecified", 
                "età_apparente": "", 
                "voce": "" 
            },
            "dati_fisici_ed_estetici": { 
                "descrizione_visiva": "",
                "altezza": "",
                "peso": "",
                "misure": "",
                "corporatura": ""
            },
            "dettagli_intimi": {
                "seno": "",
                "glutei": "",
                "genitali": "",
                "segni_particolari": ""
            },
            "essenza_e_anima": { 
                "essenza_fondamentale": "",
                "archetipo_attuale": t("common.none"), 
                "desideri_profondi": [],
                "paure_radicate":[]
            },
            "storia_": "",
            "relazioni_": {},
            "evoluzione_personale_": "",
            "scopo_attuale_nel_gdr":[],
            "scheda_rpg": {
              "dati_base": { "razza": t("character_editor.rpg.races.human"), "classe": t("character_editor.rpg.classes.fighter"), "livello": 1, "punti_esperienza": 0, "allineamento": t("character_editor.rpg.alignments.neutral") },
              "statistiche_core": {
                "forza": { "valore": 10, "modificatore": 0 },
                "destrezza": { "valore": 10, "modificatore": 0 },
                "costituzione": { "valore": 10, "modificatore": 0 },
                "intelligenza": { "valore": 10, "modificatore": 0 },
                "saggezza": { "valore": 10, "modificatore": 0 },
                "carisma": { "valore": 10, "modificatore": 0 }
              },
              "combattimento": { "hp_massimi": 10, "hp_attuali": 10, "classe_armatura": 10, "iniziativa": 0, "velocita": 9 },
              "equipaggiamento": { "armi": [], "inventario":[], "monete": { "oro": 0, "argento": 0, "rame": 0 } },
              "magia_e_privilegi": { "tratti_razziali": [], "privilegi_classe": [], "incantesimi":[] }
            }
          });
          setPersonalityTraits(getInitialTraits());
          setImagePreview(null);
          setImageFile(null);
          setSourceUrl("");
      }
    }
  }, [open, isEditMode, characterId, serverConfig, type]); 
  
  // Caricamento Lingue e Profilo Utente
  useEffect(() => {
      if (open && serverConfig) {
          setLoadingVoices(true);
          const serverUrl = getBaseUrl(serverConfig);
          const headers = getHeaders();
          
          Promise.all([
              fetch(`${serverUrl}/api/tts/languages`, { headers }).then(res => res.json()),
              fetch(`${serverUrl}/api/user_profile`, { headers }).then(res => res.json())
          ]).then(([langsData, profileData]) => {
              setLanguages(langsData);
              if (profileData && profileData.preferredLanguage) {
                  setUserLanguage(profileData.preferredLanguage);
              }
          }).catch(err => {
              console.error(t("character_editor.err_fetch_voice"), err);
          }).finally(() => setLoadingVoices(false));
      }
  }, [open, serverConfig]);

  useEffect(() => {
    if (autofillData) {
      // [FIX CRITICO] Gestione dell'errore per sbloccare lo spinner
      if (autofillData.error) {
          setIsAutofilling(false);
          return;
      }

      const currentVoice = formData?.dati_anagrafici?.voce || "";
      const newData = { ...autofillData.jsonData };
      
      if (newData.dati_anagrafici) {
          newData.dati_anagrafici.voce = currentVoice;
      }
      
      // --- [FIX CRITICO] DEEP MERGE ---
      // Lo shallow merge distruggeva le chiavi esistenti (es. genere, voce) se l'LLM le ometteva.
      // Ora uniamo i dati preservando la struttura originale.
      const mergedData = { ...formData };
      for (const key in newData) {
          if (typeof newData[key] === 'object' && !Array.isArray(newData[key]) && newData[key] !== null) {
              mergedData[key] = { ...mergedData[key], ...newData[key] };
          } else {
              mergedData[key] = newData[key];
          }
      }
      
      setFormData(mergedData);
      setImagePreview(null);
      setImageFile(null);
      toast.success(t("character_editor.toast_autofill_received"));
      setIsAutofilling(false);
    }
  },[autofillData]);

  // --- GESTIONE CAMPI STANDARD ---
  const handleInputChange = (section: string, key: string, value: string) => {
    setFormData((prev: any) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value,
      },
    }));
  };

  const handleObjectInputChange = (section: string, value: string) => {
      setFormData((prev: any) => ({
          ...prev,
          [section]: value 
      }));
  };

  // --- HANDLERS SCHEDA RPG ---
  const handleRpgChange = (section: string, key: string, value: any) => {
      setFormData((prev: any) => ({
          ...prev,
          scheda_rpg: {
              ...prev.scheda_rpg,
              [section]: {
                  ...prev.scheda_rpg?.[section],
                  [key]: value
              }
          }
      }));
  };

  const handleRpgStatChange = (stat: string, value: string) => {
      const numValue = parseInt(value) || 0;
      const mod = Math.floor((numValue - 10) / 2);
      setFormData((prev: any) => ({
          ...prev,
          scheda_rpg: {
              ...prev.scheda_rpg,
              statistiche_core: {
                  ...prev.scheda_rpg?.statistiche_core,
                  [stat]: { valore: numValue, modificatore: mod }
              }
          }
      }));
  };

  // --- HANDLERS ARMI RPG ---
  const handleAddWeapon = () => {
      setFormData((prev: any) => {
          const armi = prev.scheda_rpg?.equipaggiamento?.armi ||[];
          return {
              ...prev,
              scheda_rpg: {
                  ...prev.scheda_rpg,
                  equipaggiamento: {
                      ...prev.scheda_rpg?.equipaggiamento,
                      armi:[...armi, { nome: t("character_editor.rpg.new_weapon"), bonus_attacco: 0, danno: "1d6", tipo: "Semplice (Mischia)" }] // [FIX] Tipo coerente con la tendina
                  }
              }
          };
      });
  };

  const handleUpdateWeapon = (index: number, field: string, value: any) => {
      setFormData((prev: any) => {
          const armi =[...(prev.scheda_rpg?.equipaggiamento?.armi || [])];
          armi[index] = { ...armi[index], [field]: value };
          return {
              ...prev,
              scheda_rpg: {
                  ...prev.scheda_rpg,
                  equipaggiamento: {
                      ...prev.scheda_rpg?.equipaggiamento,
                      armi
                  }
              }
          };
      });
  };

  const handleDeleteWeapon = (index: number) => {
      setFormData((prev: any) => {
          const armi =[...(prev.scheda_rpg?.equipaggiamento?.armi || [])];
          armi.splice(index, 1);
          return {
              ...prev,
              scheda_rpg: {
                  ...prev.scheda_rpg,
                  equipaggiamento: {
                      ...prev.scheda_rpg?.equipaggiamento,
                      armi
                  }
              }
          };
      });
  };

  // --- HANDLERS ARMATURE RPG ---
  const handleAddArmor = () => {
      setFormData((prev: any) => {
          const armature = prev.scheda_rpg?.equipaggiamento?.armature ||[];
          return {
              ...prev,
              scheda_rpg: {
                  ...prev.scheda_rpg,
                  equipaggiamento: {
                      ...prev.scheda_rpg?.equipaggiamento,
                      armature:[...armature, { nome: t("character_editor.rpg.new_armor"), tipo: "Leggera", ca_bonus: "11", svantaggio_furtivita: false }]
                  }
              }
          };
      });
  };

  const handleUpdateArmor = (index: number, field: string, value: any) => {
      setFormData((prev: any) => {
          const armature =[...(prev.scheda_rpg?.equipaggiamento?.armature || [])];
          armature[index] = { ...armature[index], [field]: value };
          return {
              ...prev,
              scheda_rpg: {
                  ...prev.scheda_rpg,
                  equipaggiamento: {
                      ...prev.scheda_rpg?.equipaggiamento,
                      armature
                  }
              }
          };
      });
  };

  const handleDeleteArmor = (index: number) => {
      setFormData((prev: any) => {
          const armature =[...(prev.scheda_rpg?.equipaggiamento?.armature || [])];
          armature.splice(index, 1);
          return {
              ...prev,
              scheda_rpg: {
                  ...prev.scheda_rpg,
                  equipaggiamento: {
                      ...prev.scheda_rpg?.equipaggiamento,
                      armature
                  }
              }
          };
      });
  };

  // --- HANDLER AUTOCOMPILAZIONE AI ---
  const handleAutoGenerateRpgSheet = async () => {
      const razza = formData.scheda_rpg?.dati_base?.razza;
      const classe = formData.scheda_rpg?.dati_base?.classe;
      const livello = formData.scheda_rpg?.dati_base?.livello;
      
      if (!razza || !classe || !livello) {
          toast.error(t("character_editor.rpg.err_missing_base_data"));
          return;
      }
      
      setIsGeneratingRpg(true);
      try {
          const res = await fetch(`${getBaseUrl(serverConfig)}/api/rpg/generate-sheet`, {
              method: 'POST',
              headers: { ...getHeaders(), "Content-Type": "application/json" },
              body: JSON.stringify({ 
                  razza: String(razza), 
                  classe: String(classe), 
                  livello: Number(livello), 
                  lang: userLanguage || "it" 
              })
          });
          
          if (!res.ok) throw new Error(t("character_editor.rpg.err_generate"));
          const data = await res.json();
          
          // ---[FIX CRITICO] NORMALIZZAZIONE CHIAVI JSON E STRUTTURA ---
          // L'LLM spesso genera chiavi con la prima lettera maiuscola o con spazi (es. "Forza", "Hp Massimi").
          // Questa funzione ricorsiva normalizza tutte le chiavi in minuscolo con underscore,
          // garantendo il match perfetto con i campi della UI.
          const normalizeKeys = (obj: any): any => {
              if (Array.isArray(obj)) {
                  return obj.map(normalizeKeys);
              } else if (obj !== null && typeof obj === 'object') {
                  return Object.keys(obj).reduce((acc, key) => {
                      const cleanKey = key.toLowerCase().trim().replace(/\s+/g, '_');
                      acc[cleanKey] = normalizeKeys(obj[key]);
                      return acc;
                  }, {} as any);
              }
              return obj;
          };

          let sheetPayload = data.sheet;
          if (typeof sheetPayload === 'string') {
              try { sheetPayload = JSON.parse(sheetPayload); } catch(e) {}
          }
          
          // Ricerca profonda del payload reale (Bypass Allucinazioni di Wrapping)
          const findRealPayload = (obj: any): any => {
              if (!obj || typeof obj !== 'object') return obj;
              // Se troviamo le chiavi core, questo è il payload giusto
              if (obj.statistiche_core || obj.combattimento || obj.equipaggiamento || obj.magia_e_privilegi) return obj;
              // Altrimenti cerchiamo nei figli (es. obj.scheda_rpg, obj.personaggio, obj.sheet)
              for (const key in obj) {
                  const found = findRealPayload(obj[key]);
                  if (found && (found.statistiche_core || found.combattimento || found.equipaggiamento || found.magia_e_privilegi)) return found;
              }
              return obj;
          };
          
          sheetPayload = findRealPayload(sheetPayload);
          let normalizedSheet = normalizeKeys(sheetPayload);
          
          // --- [FIX STRUTTURALE] Normalizzazione Statistiche Core ---
          if (normalizedSheet.statistiche_core) {
              const stats = ["forza", "destrezza", "costituzione", "intelligenza", "saggezza", "carisma"];
              stats.forEach(stat => {
                  const statVal = normalizedSheet.statistiche_core[stat];
                  // Se è un numero o una stringa convertibile in numero (es. "15" o 15)
                  if (typeof statVal === 'number' || (typeof statVal === 'string' && !isNaN(Number(statVal)))) {
                      const val = Number(statVal);
                      normalizedSheet.statistiche_core[stat] = {
                          valore: val,
                          modificatore: Math.floor((val - 10) / 2)
                      };
                  } else if (typeof statVal === 'object' && statVal !== null) {
                      // Se è un oggetto, forziamo i valori a numero per evitare crash UI
                      statVal.valore = Number(statVal.valore) || 10;
                      statVal.modificatore = Number(statVal.modificatore) || Math.floor((statVal.valore - 10) / 2);
                  } else {
                      // Fallback totale
                      normalizedSheet.statistiche_core[stat] = { valore: 10, modificatore: 0 };
                  }
              });
          }

          // --- [FIX STRUTTURALE] Normalizzazione Combattimento (Anti-Valori Assurdi) ---
          if (normalizedSheet.combattimento) {
              const c = normalizedSheet.combattimento;
              c.hp_massimi = Math.min(Math.max(Number(c.hp_massimi) || 10, 1), 9999);
              c.hp_attuali = Math.min(Math.max(Number(c.hp_attuali) || c.hp_massimi, 0), c.hp_massimi);
              c.classe_armatura = Math.min(Math.max(Number(c.classe_armatura) || 10, 1), 50);
              c.iniziativa = Math.min(Math.max(Number(c.iniziativa) || 0, -10), 20);
              c.velocita = Math.min(Math.max(Number(c.velocita) || 9, 0), 100); // Cap a 100 per evitare 95000000000
          }
          
          setFormData((prev: any) => ({
              ...prev,
              scheda_rpg: {
                  ...prev.scheda_rpg,
                  ...normalizedSheet
              }
          }));
          toast.success(t("character_editor.rpg.success_generated"));
      } catch (e) {
          toast.error(t("character_editor.rpg.err_generate_failed"));
      } finally {
          setIsGeneratingRpg(false);
      }
  };

  // ---[AGGIORNATO v15.0] RIDENOMINAZIONE SEZIONI (CHIAVI JSON) ---
  const handleRenameSection = (oldKey: string, newName: string) => {
      if (CORE_SECTIONS.includes(oldKey)) {
          toast.warning(t("character_editor.warn_core_rename"));
          return;
      }
      const newKey = newName.trim().replace(/\s+/g, '_').toLowerCase();
      if (!newKey || newKey === oldKey) return;

      setFormData((prev: any) => {
          const newData = { ...prev };
          newData[newKey] = newData[oldKey];
          delete newData[oldKey];
          // Flag per l'executor per indicare una sostituzione totale della chiave
          if (typeof newData[newKey] === 'object') {
              newData[newKey] = { ...newData[newKey], _force_replace: true };
          }
          return newData;
      });
  };

  // --- [NUOVO v15.0] GESTIONE DINAMICA CAMPI E SEZIONI ---
  const handleAddSection = () => {
      if (!newSectionName.trim()) return;
      const key = newSectionName.trim().replace(/\s+/g, '_').toLowerCase();
      if (formData[key]) {
          toast.error(t("character_editor.err_section_exists"));
          return;
      }
      setFormData((prev: any) => ({ ...prev, [key]: {} }));
      setNewSectionName("");
      setIsAddingSection(false);
  };

  const handleDeleteSection = (section: string) => {
      if (CORE_SECTIONS.includes(section)) {
          toast.warning(t("character_editor.warn_core_delete"));
          return;
      }
      if (!confirm(t("character_editor.confirm_delete_section", { name: section }))) return;
      setFormData((prev: any) => {
          const next = { ...prev };
          delete next[section];
          return next;
      });
  };

  const handleAddFieldToSection = (section: string) => {
      setFormData((prev: any) => {
          const sectionData = { ...prev[section] };
          let newKey = "new_field";
          let counter = 1;
          while (sectionData[newKey]) {
              newKey = `new_field_${counter}`;
              counter++;
          }
          sectionData[newKey] = "";
          return { ...prev, [section]: sectionData };
      });
  };

  const handleRenameField = (section: string, oldKey: string, newName: string) => {
      const newKey = newName.trim().replace(/\s+/g, '_').toLowerCase();
      if (!newKey || newKey === oldKey) return;
      
      setFormData((prev: any) => {
          const sectionData = { ...prev[section] };
          if (sectionData[newKey]) return prev; // Evita collisioni
          
          const value = sectionData[oldKey];
          delete sectionData[oldKey];
          sectionData[newKey] = value;
          return { ...prev, [section]: sectionData };
      });
  };

  const handleDeleteField = (section: string, key: string) => {
      setFormData((prev: any) => {
          const sectionData = { ...prev[section] };
          delete sectionData[key];
          return { ...prev, [section]: sectionData };
      });
  };

  // --- GESTIONE DINAMICA DIZIONARI (es. Relazioni) ---
  const handleDictKeyChange = (section: string, oldKey: string, newKey: string) => {
      setFormData((prev: any) => {
          const sectionData = { ...prev[section] };
          const value = sectionData[oldKey];
          delete sectionData[oldKey];
          sectionData[newKey] = value;
          return { ...prev, [section]: sectionData };
      });
  };

  const handleDictValueChange = (section: string, key: string, newValue: string) => {
      setFormData((prev: any) => ({
          ...prev,
          [section]: {
              ...prev[section],
              [key]: newValue
          }
      }));
  };

  const handleDictDelete = (section: string, key: string) => {
      setFormData((prev: any) => {
          const sectionData = { ...prev[section] };
          delete sectionData[key];
          return { ...prev, [section]: sectionData };
      });
  };

  const handleDictAdd = (section: string) => {
      setFormData((prev: any) => {
          const sectionData = { ...prev[section] };
          let newKey = t("character_editor.add_relation");
          let counter = 1;
          while (sectionData[newKey]) {
              newKey = `${t("character_editor.add_relation")} ${counter}`;
              counter++;
          }
          sectionData[newKey] = "";
          return { ...prev, [section]: sectionData };
      });
  };

  // --- GESTIONE DINAMICA LISTE (es. Scopo, Desideri) ---
  const handleListChange = (section: string, index: number, newValue: string) => {
      setFormData((prev: any) => {
          const list = [...(prev[section] || [])];
          list[index] = newValue;
          return { ...prev, [section]: list };
      });
  };

  const handleListDelete = (section: string, index: number) => {
      setFormData((prev: any) => {
          const list = [...(prev[section] || [])];
          list.splice(index, 1);
          return { ...prev, [section]: list };
      });
  };

  const handleListAdd = (section: string) => {
      setFormData((prev: any) => {
          const list = [...(prev[section] || [])];
          list.push("");
          return { ...prev, [section]: list };
      });
  };
  
  // --- GESTIONE PERSONALITÀ DINAMICA (SLIDERS) ---
  
  const handleApplyPreset = (presetName: string) => {
      const presetValues = presets[presetName];
      if (!presetValues) return;

      const newTraits = getInitialTraits();
      
      Object.entries(presetValues).forEach(([trait, val]) => {
          if (newTraits[trait]) {
              newTraits[trait].valore = val;
          } else {
              newTraits[trait] = {
                  valore: val,
                  desc_min: "Basso",
                  desc_max: "Alto"
              };
          }
      });

      Object.entries(personalityTraits).forEach(([trait, data]) => {
          if (!newTraits[trait] && !ALL_BASE_TRAITS[trait]) {
              newTraits[trait] = data;
          }
      });

      setPersonalityTraits(newTraits);
      setSelectedPreset(presetName);
      
      setFormData((prev: any) => ({
          ...prev,
          essenza_e_anima: {
              ...prev.essenza_e_anima,
              archetipo_attuale: presetName
          }
      }));
      
      toast.success(t("character_editor.toast_preset_applied", { name: presetName }));
  };

  const handleTraitChange = (trait: string, newVal: number) => {
      setPersonalityTraits(prev => ({
          ...prev,
          [trait]: { ...prev[trait], valore: newVal }
      }));
      setSelectedPreset("Custom"); 
      
      setFormData((prev: any) => ({
          ...prev,
          essenza_e_anima: {
              ...prev.essenza_e_anima,
              archetipo_attuale: t("character_editor.custom_archetype")
          }
      }));
  };

  const handleTraitDelete = (trait: string) => {
      setPersonalityTraits(prev => {
          const next = { ...prev };
          delete next[trait];
          return next;
      });
  };

  const handleAddCustomTrait = () => {
      if (!newTraitName.trim()) {
          toast.error(t("character_editor.err_trait_name"));
          return;
      }
      if (!newTraitMin.trim() || !newTraitMax.trim()) {
          toast.error(t("character_editor.err_trait_descs"));
          return;
      }

      setPersonalityTraits(prev => ({
          ...prev,
          [newTraitName]: {
              valore: 0,
              desc_min: newTraitMin,
              desc_max: newTraitMax
          }
      }));
      
      setNewTraitName("");
      setNewTraitMin("");
      setNewTraitMax("");
      setIsAddingTrait(false);
      toast.success(t("character_editor.toast_trait_added", { name: newTraitName }));
  };

  const getDynamicAdjective = (val: number, min: string, max: string) => {
      if (val === 0) return t("character_editor.balanced");
      const intensity = Math.abs(val);
      const direction = val > 0 ? t(max) : t(min);
      
      if (intensity >= 9) return t("character_editor.intensity_extreme", { direction });
      if (intensity >= 7) return t("character_editor.intensity_very", { direction });
      if (intensity >= 4) return t("character_editor.intensity_quite", { direction });
      return t("character_editor.intensity_slightly", { direction });
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const handleAutofill = () => {
    if (!sourceUrl) return;
    setIsAutofilling(true);
    toast.info(t("character_editor.toast_autofill_request"));
    onAutofill(sourceUrl);
  };

  const handleSave = () => {
    const characterDataToSave = { 
        ...formData, 
        personalita_dinamica: personalityTraits
    };
    const finalData = isEditMode ? { ...characterDataToSave, id: characterId } : characterDataToSave;
    onSave(finalData, imageFile);
  };
  
  // --- LOGICA GILDA ---
  const charName = formData?.dati_anagrafici?.nome_completo || formData?.dati_anagrafici?.nome || "";
  const myGuild = guilds.find(g => g.membri && Object.values(g.membri).some((m: any) => String(m).trim().toLowerCase() === charName.trim().toLowerCase()));
  
  let isLeader = false;
  let myUid = "";
  let otherMembers: {uid: string, name: string}[] =[];

  if (myGuild && myGuild.membri) {
      const entry = Object.entries(myGuild.membri).find(([uid, name]) => String(name).trim().toLowerCase() === charName.trim().toLowerCase());
      if (entry) {
          myUid = entry[0];
          isLeader = myGuild.capo_gilda === myUid;
      }
      otherMembers = Object.entries(myGuild.membri)
          .filter(([uid, name]) => uid !== myUid)
          .map(([uid, name]) => ({ uid, name: String(name) }));
  }

  const handleEditGuild = () => {
      if (!editGuildName.trim()) return;
      if (onGuildCommand && myGuild) {
          onGuildCommand("GUILD_EDIT", { guild_id: myGuild.id, name: editGuildName, symbol: editGuildSymbol });
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

  const getCharacterName = () => {
      if (!formData?.dati_anagrafici) return t("character_editor.unknown");
      return formData.dati_anagrafici.nome_completo || formData.dati_anagrafici.nome || formData.dati_anagrafici.name || t("character_editor.unknown");
  };

  const isSaveDisabled = (!formData?.dati_anagrafici?.nome_completo && !formData?.dati_anagrafici?.nome) || isLoading || isAutofilling;
  const availableVoices = languages[userLanguage]?.voices || [];

  const renderValue = (value: any) => {
      if (typeof value === 'object' && value !== null) {
          return JSON.stringify(value, null, 2);
      }
      return formatTextForDisplay(String(value || ""));
  };

  const sortedTraits = Object.entries(personalityTraits).sort((a, b) => a[0].localeCompare(b[0]));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {/* [FIX v5.7] Altezza fissa h-[90vh] e flex-col per forzare il riempimento dello spazio */}
      <DialogContent className="sm:max-w-7xl h-[90vh] flex flex-col overflow-hidden p-0 gap-0 bg-background">
        <style>{scrollbarStyles}</style>
        
        <DialogHeader className="p-6 pb-2 bg-muted/10 border-b shrink-0 flex flex-row items-center justify-between">
          <div>
              <DialogTitle className="flex items-center gap-2">
                  {isEditMode ? <UserCog className="w-5 h-5 text-primary" /> : <Plus className="w-5 h-5 text-primary" />}
                  {isEditMode ? t("character_editor.edit_character", { name: getCharacterName() }) : t("character_editor.create_new", { type: type })}
              </DialogTitle>
              <DialogDescription>
                {t("character_editor.description")}
              </DialogDescription>
          </div>
        </DialogHeader>

        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-12 h-12 animate-spin text-primary" />
          </div>
        ) : (
          /* [FIX v5.7] PROTOCOLLO FLEXBOX RIGIDO: Unico contenitore scorrevole per SX e DX */
          <div className="flex-1 relative min-h-0">
            <div className="absolute inset-0 overflow-y-scroll airis-editor-scrollbar">
              <div className="flex flex-col md:flex-row min-h-full">
                
                {/* --- COLONNA SINISTRA: IMMAGINE + FLUID SOUL (35%) --- */}
                <div className="w-full md:w-[35%] border-r border-border/50 bg-background/50 p-6 space-y-6">
                    {/* Image */}
                    <div className="w-full aspect-square rounded-xl overflow-hidden border-2 border-dashed border-muted-foreground/20 flex items-center justify-center bg-muted/10 relative group">
                        {imagePreview ? (
                            <img src={imagePreview} alt="Avatar Preview" className="w-full h-full object-cover" />
                        ) : (
                            <div className="text-center text-muted-foreground">
                                <UserCog className="w-12 h-12 mx-auto mb-2 opacity-50" />
                                <span className="text-xs">{t("character_editor.no_image")}</span>
                            </div>
                        )}
                        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                            <Button variant="secondary" size="sm" onClick={() => fileInputRef.current?.click()}>
                                <Upload className="mr-2 h-4 w-4" /> {t("character_editor.change")}
                            </Button>
                        </div>
                        <input type="file" ref={fileInputRef} className="hidden" accept="image/*" onChange={handleImageChange} />
                    </div>

                    {/* FLUID SOUL ENGINE */}
                    <div className="space-y-4 pt-4 border-t border-border/50">
                        <div className="flex items-center justify-between mb-2">
                            <div>
                                <h3 className="text-sm font-bold flex items-center gap-2 text-primary">
                                    <BrainCircuit className="w-4 h-4" /> {t("character_editor.fluid_soul")}
                                </h3>
                                <p className="text-[10px] text-muted-foreground">{t("character_editor.dynamic_vectors")}</p>
                            </div>
                            <div className="flex items-center gap-1">
                                <Select value={selectedPreset} onValueChange={handleApplyPreset}>
                                    <SelectTrigger className="w-[140px] h-7 text-xs">
                                        <SelectValue placeholder={t("character_editor.preset")} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="Custom">{t("character_editor.custom")}</SelectItem>
                                        <SelectItem value="Neutro">{t("character_editor.neutral")}</SelectItem>
                                        <SelectSeparator />
                                        <SelectGroup>
                                            <SelectLabel className="text-[10px] uppercase text-muted-foreground">{t("character_editor.female")}</SelectLabel>
                                            {FEMALE_PRESETS.map(p => ( <SelectItem key={p} value={p}>{t(`character_editor.presets.female.${p.toLowerCase()}`)}</SelectItem> ))}
                                        </SelectGroup>
                                        <SelectSeparator />
                                        <SelectGroup>
                                            <SelectLabel className="text-[10px] uppercase text-muted-foreground">{t("character_editor.male")}</SelectLabel>
                                            {MALE_PRESETS.map(p => ( <SelectItem key={p} value={p}>{t(`character_editor.presets.male.${p.toLowerCase().replace(/\s+/g, '_')}`)}</SelectItem> ))}
                                        </SelectGroup>
                                    </SelectContent>
                                </Select>
                                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleApplyPreset(selectedPreset)} title="Re-apply">
                                    <RefreshCw className="w-3 h-3" />
                                </Button>
                            </div>
                        </div>

                        <div className="space-y-4">
                            {sortedTraits.map(([trait, data]) => (
                                <div key={trait} className="bg-card/50 p-3 rounded-lg border border-border/30">
                                    <div className="flex justify-between items-center mb-2">
                                        <span className="font-bold text-xs">{t(trait)}</span>
                                        <div className="flex items-center gap-2">
                                            <span className={cn(
                                                "text-[10px] px-1.5 py-0.5 rounded-full font-mono",
                                                data.valore > 0 ? "bg-red-500/10 text-red-500" : 
                                                data.valore < 0 ? "bg-blue-500/10 text-blue-500" : "bg-gray-500/10 text-gray-500"
                                            )}>
                                                {data.valore > 0 ? `+${data.valore}` : data.valore}
                                            </span>
                                            {!ALL_BASE_TRAITS[trait] && (
                                                <Button variant="ghost" size="icon" className="h-5 w-5 text-muted-foreground hover:text-destructive" onClick={() => handleTraitDelete(trait)}>
                                                    <Trash2 className="w-3 h-3" />
                                                </Button>
                                            )}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-[9px] text-muted-foreground w-10 text-right truncate">{t(data.desc_min)}</span>
                                        <Slider value={[data.valore]} min={-10} max={10} step={1} onValueChange={([val]) => handleTraitChange(trait, val)} className="flex-1" />
                                        <span className="text-[9px] text-muted-foreground w-10 truncate">{t(data.desc_max)}</span>
                                    </div>
                                    <div className="text-center mt-1">
                                        <span className="text-[10px] font-medium text-primary/80">
                                            {getDynamicAdjective(data.valore, data.desc_min, data.desc_max)}
                                        </span>
                                    </div>
                                </div>
                            ))}

                            {isAddingTrait ? (
                                <div className="bg-muted/30 p-3 rounded-lg border border-dashed border-primary/30 animate-in fade-in">
                                    <div className="space-y-2 mb-2">
                                        <div className="space-y-1">
                                            <Label className="text-[10px] text-muted-foreground">{t("character_editor.trait_name_label")}</Label>
                                            <Input placeholder={t("character_editor.trait_name_placeholder")} value={newTraitName} onChange={(e) => setNewTraitName(e.target.value)} className="text-xs h-7" />
                                        </div>
                                        <div className="grid grid-cols-2 gap-2">
                                            <div className="space-y-1">
                                                <Label className="text-[10px] text-muted-foreground">{t("character_editor.trait_min_label")}</Label>
                                                <Input placeholder={t("character_editor.trait_min_placeholder")} value={newTraitMin} onChange={(e) => setNewTraitMin(e.target.value)} className="text-xs h-7" />
                                            </div>
                                            <div className="space-y-1">
                                                <Label className="text-[10px] text-muted-foreground">{t("character_editor.trait_max_label")}</Label>
                                                <Input placeholder={t("character_editor.trait_max_placeholder")} value={newTraitMax} onChange={(e) => setNewTraitMax(e.target.value)} className="text-xs h-7" />
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex justify-end gap-2">
                                        <Button size="sm" variant="ghost" className="h-6 text-xs" onClick={() => setIsAddingTrait(false)}>{t("character_editor.cancel")}</Button>
                                        <Button size="sm" className="h-6 text-xs" onClick={handleAddCustomTrait} disabled={!newTraitName.trim() || !newTraitMin.trim() || !newTraitMax.trim()}>{t("character_editor.add")}</Button>
                                    </div>
                                </div>
                                ) : (
                                    <Button variant="outline" size="sm" className="w-full border-dashed text-xs h-8" onClick={() => setIsAddingTrait(true)}>
                                        <Plus className="w-3 h-3 mr-2" /> {t("character_editor.add_custom_trait")}
                                    </Button>
                            )}
                        </div>
                    </div>
                </div>

                {/* --- COLONNA DESTRA: FORM DATI STATICI E RPG (65%) --- */}
                <div className="w-full md:w-[65%] bg-muted/5 p-6">
                  <Tabs defaultValue="identity" className="w-full">
                    <TabsList className="grid w-full grid-cols-2 mb-4">
                        <TabsTrigger value="identity"><BookOpen className="w-4 h-4 mr-2"/> {t("character_editor.tab_identity")}</TabsTrigger>
                        <TabsTrigger value="rpg"><Swords className="w-4 h-4 mr-2"/> {t("character_editor.tab_rpg")}</TabsTrigger>
                    </TabsList>

                    {/* TAB 1: IDENTITÀ E LORE (Dinamico) - FIX SCROLL MOBILE */}
                    <TabsContent value="identity" className="m-0 mt-4 space-y-6">
                                {/* Autofill Bar */}
                                <div className="flex gap-2 mb-4">
                                    <Input 
                                        placeholder={t("character_editor.autofill_placeholder")} 
                                        value={sourceUrl} 
                                        onChange={(e) => setSourceUrl(e.target.value)} 
                                        className="text-xs h-9 bg-background"
                                    />
                                    <Button size="sm" variant="outline" onClick={handleAutofill} disabled={!sourceUrl || isAutofilling}>
                                        {isAutofilling ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                                    </Button>
                                </div>

                                {/* Form Fields (Dinamici v124.0 + v15.0) */}
                                {Object.entries(formData).map(([section, fields]) => (
                                    // [FIX BUG 02] Esclusione esplicita delle sezioni speciali dalla UI dinamica
                                    // FIX: Esclusione di guildName e guildSymbol per evitare che appaiano come campi di testo grezzi
                                    section !== 'personalita_dinamica' && section !== '_force_replace' && section !== 'vettori_emotivi' && section !== 'scheda_rpg' && section !== 'guildName' && section !== 'guildSymbol' && (
                                        <div key={section} className="space-y-3 bg-card p-4 rounded-xl border border-border/40 relative group/section">
                                            {/* [AGGIORNATO v15.0] Titolo Sezione Editabile & Delete */}
                                            <div className="flex items-center gap-2 border-b border-border/50 pb-2 mb-2">
                                                <Input
                                                    defaultValue={section.replace(/_/g, ' ').toUpperCase()}
                                                    onBlur={(e) => handleRenameSection(section, e.target.value)}
                                                    className={cn(
                                                        "h-6 w-fit min-w-[150px] font-bold text-xs uppercase tracking-wider bg-transparent border-none focus-visible:ring-1 focus-visible:ring-primary/30 p-0 hover:bg-white/5 transition-colors",
                                                        CORE_SECTIONS.includes(section) ? "text-primary cursor-default" : "text-foreground"
                                                    )}
                                                    readOnly={CORE_SECTIONS.includes(section)}
                                                    title={CORE_SECTIONS.includes(section) ? t("character_editor.core_section_protected") : t("character_editor.rename_section")}
                                                />
                                                {!CORE_SECTIONS.includes(section) && (
                                                    <>
                                                        <Edit className="w-3 h-3 text-muted-foreground opacity-0 group-hover/section:opacity-100 transition-opacity" />
                                                        <div className="flex-1" />
                                                        <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive opacity-0 group-hover/section:opacity-100 transition-opacity" onClick={() => handleDeleteSection(section)}>
                                                            <Trash2 className="w-3 h-3" />
                                                        </Button>
                                                    </>
                                                )}
                                            </div>
                                            
                                            {typeof fields === 'object' && fields !== null && !Array.isArray(fields) ? (
                                                <div className="space-y-4">
                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                        {Object.entries(fields).map(([key, value]) => (
                                                            <div key={key} className={cn("space-y-1 group/field relative", (key === 'descrizione_visiva' || key === 'storia_') ? "md:col-span-2" : "")}>
                                                                <div className="flex items-center justify-between">
                                                                    {/*[NUOVO v15.0] Chiave Editabile */}
                                                                    <Input 
                                                                        defaultValue={key.replace(/_/g, ' ')}
                                                                        onBlur={(e) => handleRenameField(section, key, e.target.value)}
                                                                        className="h-5 p-0 text-xs capitalize text-muted-foreground bg-transparent border-none focus-visible:ring-0 hover:text-primary w-fit"
                                                                    />
                                                                    <Button variant="ghost" size="icon" className="h-4 w-4 text-destructive opacity-0 group-hover/field:opacity-100" onClick={() => handleDeleteField(section, key)}>
                                                                        <X className="w-3 h-3" />
                                                                    </Button>
                                                                </div>
                                                                
                                                                {key === 'genere' || key === 'gender' ? (
                                                                    <Select value={String(value)} onValueChange={(v) => handleInputChange(section, key, v)}>
                                                                        <SelectTrigger className="h-9 text-sm"><SelectValue placeholder={t("character_editor.select_gender")} /></SelectTrigger>
                                                                        <SelectContent>
                                                                            <SelectItem value="Male">{t("character_editor.gender_male")}</SelectItem>
                                                                            <SelectItem value="Female">{t("character_editor.gender_female")}</SelectItem>
                                                                            <SelectItem value="Other">{t("character_editor.gender_other")}</SelectItem>
                                                                        </SelectContent>
                                                                    </Select>
                                                                ) : key === 'voce' || key === 'voice' ? (
                                                                    <Select value={String(value)} onValueChange={(v) => handleInputChange(section, key, v === "auto" ? "" : v)}>
                                                                        <SelectTrigger className="h-9 text-sm"><SelectValue placeholder={t("cognitive_module.auto")} /></SelectTrigger>
                                                                        <SelectContent>
                                                                            <SelectItem value="auto">{t("cognitive_module.auto")}</SelectItem>
                                                                            {availableVoices.map(v => <SelectItem key={v.id} value={v.id}>{v.name}</SelectItem>)}
                                                                        </SelectContent>
                                                                    </Select>
                                                                ) : key === 'archetipo_attuale' ? (
                                                                    <Input 
                                                                        value={String(value)} 
                                                                        readOnly 
                                                                        className="h-9 text-sm bg-muted/50 text-muted-foreground cursor-not-allowed border-dashed"
                                                                        title="Managed by Fluid Soul Engine"
                                                                    />
                                                                ) : (
                                                                    <Textarea 
                                                                        value={renderValue(value)} 
                                                                        onChange={(e) => handleInputChange(section, key, e.target.value)}
                                                                        className={cn(
                                                                            "text-sm bg-background/50",
                                                                            (key === 'dettagli_intimi' || key === 'paure_radicate' || key === 'desideri_profondi' || key === 'storia_') 
                                                                                ? "min-h-[8rem]" 
                                                                                : "min-h-[3.5rem]"
                                                                        )}
                                                                        rows={String(value).length > 80 ? 6 : 3}
                                                                    />
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                    <Button variant="ghost" size="sm" className="w-full h-6 text-[10px] border border-dashed opacity-50 hover:opacity-100" onClick={() => handleAddFieldToSection(section)}>
                                                        <Plus className="w-3 h-3 mr-1" /> {t("character_editor.add_field")}
                                                    </Button>
                                                </div>
                                            ) : Array.isArray(fields) ? (
                                                <div className="space-y-2">
                                                    {fields.map((item: string, idx: number) => (
                                                        <div key={idx} className="flex gap-2">
                                                            <Input value={formatTextForDisplay(item)} onChange={(e) => handleListChange(section, idx, e.target.value)} className="h-9 text-sm bg-background/50" />
                                                            <Button size="icon" variant="ghost" className="h-9 w-9 text-destructive" onClick={() => handleListDelete(section, idx)}><X className="w-4 h-4" /></Button>
                                                        </div>
                                                    ))}
                                                    <Button size="sm" variant="ghost" className="w-full h-8 text-xs border border-dashed" onClick={() => handleListAdd(section)}><Plus className="w-3 h-3 mr-1" /> {t("character_editor.add_item")}</Button>
                                                </div>
                                            ) : (
                                                section.includes('relazioni') ? (
                                                    <div className="space-y-3">
                                                        {Object.entries(fields).map(([key, value]) => (
                                                            key !== '_force_replace' && (
                                                            <div key={key} className="flex flex-col gap-2 p-3 border rounded-md bg-muted/10 relative group">
                                                                <div className="flex gap-2 items-center">
                                                                    <Input 
                                                                        key={`dict-key-${key}-${realUserName}`}
                                                                        defaultValue={formatTextForDisplay(key)} 
                                                                        onBlur={(e) => handleDictKeyChange(section, key, e.target.value)}
                                                                        className="font-bold h-8 text-sm w-1/2 bg-background/50 border-primary/20 focus:border-primary"
                                                                        placeholder={t("character_editor.char_name_placeholder")}
                                                                    />
                                                                    <div className="flex-1"></div>
                                                                    <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive" onClick={() => handleDictDelete(section, key)}>
                                                                        <Trash2 className="w-4 h-4" />
                                                                    </Button>
                                                                </div>
                                                                <Textarea 
                                                                    value={renderValue(value)} 
                                                                    onChange={(e) => handleDictValueChange(section, key, e.target.value)}
                                                                    className="text-sm bg-background/50 min-h-[60px]"
                                                                />
                                                            </div>
                                                            )
                                                        ))}
                                                        <Button variant="outline" size="sm" className="w-full border-dashed" onClick={() => handleDictAdd(section)}>
                                                            <Plus className="w-4 h-4 mr-2" /> {t("character_editor.add_relation")}
                                                        </Button>
                                                    </div>
                                                ) : (
                                                    <Textarea 
                                                        value={renderValue(fields)} 
                                                        onChange={(e) => handleObjectInputChange(section, e.target.value)}
                                                        className="text-sm min-h-[12rem] bg-background/50 font-serif leading-relaxed"
                                                    />
                                                )
                                            )}
                                        </div>
                                    )
                                ))}

                                {/* [NUOVO v15.0] ADD NEW SECTION BUTTON */}
                                <div className="pt-4 border-t border-border/50">
                                    {isAddingSection ? (
                                        <div className="flex gap-2 animate-in fade-in">
                                            <Input 
                                                placeholder={t("character_editor.new_section_placeholder")} 
                                                value={newSectionName} 
                                                onChange={(e) => setNewSectionName(e.target.value)}
                                                className="h-9 text-sm"
                                                autoFocus
                                            />
                                            <Button size="sm" onClick={handleAddSection} disabled={!newSectionName.trim()}>{t("character_editor.btn_add")}</Button>
                                            <Button size="sm" variant="ghost" onClick={() => setIsAddingSection(false)}>{t("character_editor.btn_cancel")}</Button>
                                        </div>
                                    ) : (
                                        <Button variant="outline" className="w-full border-dashed" onClick={() => setIsAddingSection(true)}>
                                            <Plus className="w-4 h-4 mr-2" /> {t("character_editor.add_new_section")}
                                        </Button>
                                    )}
                                </div>
                    </TabsContent>

                    {/* TAB 2: SCHEDA RPG (Hardcoded) - FIX SCROLL MOBILE */}
                    <TabsContent value="rpg" className="m-0 mt-4 space-y-6">
                                {formData.scheda_rpg ? (
                                    <div className="space-y-6">
                                        {/* DATI BASE & AUTO-GENERATE */}
                                        <div className="bg-card p-4 rounded-xl border border-border/40 space-y-4">
                                            <div className="flex items-center justify-between border-b border-border/50 pb-2">
                                                <h3 className="text-sm font-bold text-primary uppercase tracking-wider">{t("character_editor.rpg.base_data")}</h3>
                                                <Button size="sm" variant="secondary" className="h-7 text-xs bg-purple-600/20 text-purple-400 hover:bg-purple-600/40 border border-purple-500/30" onClick={handleAutoGenerateRpgSheet} disabled={isGeneratingRpg}>
                                                    {isGeneratingRpg ? <Loader2 className="w-3 h-3 mr-2 animate-spin" /> : <Wand2 className="w-3 h-3 mr-2" />}
                                                    {t("character_editor.rpg.btn_auto_generate")}
                                                </Button>
                                            </div>
                                            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                                                <div className="space-y-1">
                                                    <Label className="text-xs text-muted-foreground">{t("character_editor.rpg.race")}</Label>
                                                    <Select value={formData.scheda_rpg.dati_base?.razza || ""} onValueChange={(v) => handleRpgChange("dati_base", "razza", v)}>
                                                        <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                                                        <SelectContent>
                                                            {["human", "elf", "dwarf", "half_orc", "half_elf", "tiefling", "dragonborn", "kender"].map(r => <SelectItem key={r} value={t(`character_editor.rpg.races.${r}`)}>{t(`character_editor.rpg.races.${r}`)}</SelectItem>)}
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                                <div className="space-y-1">
                                                    <Label className="text-xs text-muted-foreground">{t("character_editor.rpg.class")}</Label>
                                                    <Select value={formData.scheda_rpg.dati_base?.classe || ""} onValueChange={(v) => handleRpgChange("dati_base", "classe", v)}>
                                                        <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                                                        <SelectContent>
                                                            {["barbarian", "bard", "cleric", "druid", "fighter", "rogue", "wizard", "monk", "paladin", "ranger", "sorcerer", "warlock"].map(c => <SelectItem key={c} value={t(`character_editor.rpg.classes.${c}`)}>{t(`character_editor.rpg.classes.${c}`)}</SelectItem>)}
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                                <div className="space-y-1">
                                                    <Label className="text-xs text-muted-foreground">{t("character_editor.rpg.level")}</Label>
                                                    <Input type="number" className="h-8 text-xs" value={formData.scheda_rpg.dati_base?.livello || 1} onChange={(e) => handleRpgChange("dati_base", "livello", parseInt(e.target.value) || 1)} />
                                                </div>
                                                <div className="space-y-1">
                                                    <Label className="text-xs text-muted-foreground">{t("character_editor.rpg.xp")}</Label>
                                                    <Input type="number" className="h-8 text-xs" value={formData.scheda_rpg.dati_base?.punti_esperienza || 0} onChange={(e) => handleRpgChange("dati_base", "punti_esperienza", parseInt(e.target.value) || 0)} />
                                                </div>
                                                <div className="space-y-1 col-span-2 md:col-span-1">
                                                    <Label className="text-xs text-muted-foreground">{t("character_editor.rpg.alignment")}</Label>
                                                    <HybridInput 
                                                        value={formData.scheda_rpg.dati_base?.allineamento || ""} 
                                                        onChange={(v) => handleRpgChange("dati_base", "allineamento", v)} 
                                                        options={[
                                                            t("character_editor.rpg.alignments.lawful_good"),
                                                            t("character_editor.rpg.alignments.neutral_good"),
                                                            t("character_editor.rpg.alignments.chaotic_good"),
                                                            t("character_editor.rpg.alignments.lawful_neutral"),
                                                            t("character_editor.rpg.alignments.neutral"),
                                                            t("character_editor.rpg.alignments.chaotic_neutral"),
                                                            t("character_editor.rpg.alignments.lawful_evil"),
                                                            t("character_editor.rpg.alignments.neutral_evil"),
                                                            t("character_editor.rpg.alignments.chaotic_evil")
                                                        ]}
                                                        placeholder={t("character_editor.rpg.alignment")}
                                                    />
                                                </div>
                                            </div>
                                        </div>

                                        {/* STATISTICHE CORE */}
                                        <div className="bg-card p-4 rounded-xl border border-border/40 space-y-4">
                                            <h3 className="text-sm font-bold text-primary uppercase tracking-wider border-b border-border/50 pb-2">{t("character_editor.rpg.core_stats")}</h3>
                                            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                                                {["forza", "destrezza", "costituzione", "intelligenza", "saggezza", "carisma"].map((stat) => {
                                                    const statData = formData.scheda_rpg.statistiche_core?.[stat] || { valore: 10, modificatore: 0 };
                                                    return (
                                                        <div key={stat} className="flex flex-col p-2 bg-muted/20 rounded-lg border border-white/5">
                                                            <Label className="text-[10px] uppercase text-center mb-2 text-muted-foreground">{t(`character_editor.rpg.${stat.substring(0,3)}`)}</Label>
                                                            <div className="flex items-center justify-center gap-2">
                                                                <Input 
                                                                    type="number" 
                                                                    className="h-10 w-14 text-center font-bold text-lg bg-background" 
                                                                    value={statData.valore} 
                                                                    onChange={(e) => handleRpgStatChange(stat, e.target.value)} 
                                                                />
                                                                <div className="h-10 w-10 flex items-center justify-center rounded-full bg-primary/20 text-primary font-bold text-sm border border-primary/30">
                                                                    {statData.modificatore > 0 ? `+${statData.modificatore}` : statData.modificatore}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>

                                        {/* COMBATTIMENTO */}
                                        <div className="bg-card p-4 rounded-xl border border-border/40 space-y-4">
                                            <h3 className="text-sm font-bold text-red-400 uppercase tracking-wider border-b border-red-500/20 pb-2 flex items-center gap-2">
                                                <Shield className="w-4 h-4" /> {t("character_editor.rpg.combat")}
                                            </h3>
                                            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                                                <div className="space-y-1">
                                                    <Label className="text-xs text-muted-foreground">{t("character_editor.rpg.hp_max")}</Label>
                                                    <Input type="number" className="h-8 text-xs font-bold text-green-400" value={formData.scheda_rpg.combattimento?.hp_massimi || 0} onChange={(e) => handleRpgChange("combattimento", "hp_massimi", parseInt(e.target.value) || 0)} />
                                                </div>
                                                <div className="space-y-1">
                                                    <Label className="text-xs text-muted-foreground">{t("character_editor.rpg.hp_current")}</Label>
                                                    <Input type="number" className="h-8 text-xs font-bold text-green-500" value={formData.scheda_rpg.combattimento?.hp_attuali || 0} onChange={(e) => handleRpgChange("combattimento", "hp_attuali", parseInt(e.target.value) || 0)} />
                                                </div>
                                                <div className="space-y-1">
                                                    <Label className="text-xs text-muted-foreground">{t("character_editor.rpg.ac")}</Label>
                                                    <Input type="number" className="h-8 text-xs font-bold text-blue-400" value={formData.scheda_rpg.combattimento?.classe_armatura || 10} onChange={(e) => handleRpgChange("combattimento", "classe_armatura", parseInt(e.target.value) || 10)} />
                                                </div>
                                                <div className="space-y-1">
                                                    <Label className="text-xs text-muted-foreground">{t("character_editor.rpg.initiative")}</Label>
                                                    <Input type="number" className="h-8 text-xs" value={formData.scheda_rpg.combattimento?.iniziativa || 0} onChange={(e) => handleRpgChange("combattimento", "iniziativa", parseInt(e.target.value) || 0)} />
                                                </div>
                                                <div className="space-y-1">
                                                    <Label className="text-xs text-muted-foreground">{t("character_editor.rpg.speed")}</Label>
                                                    <Input type="number" className="h-8 text-xs" value={formData.scheda_rpg.combattimento?.velocita || 9} onChange={(e) => handleRpgChange("combattimento", "velocita", parseInt(e.target.value) || 9)} />
                                                </div>
                                            </div>
                                        </div>

                                        {/* EQUIPAGGIAMENTO */}
                                        <div className="bg-card p-4 rounded-xl border border-border/40 space-y-4">
                                            <h3 className="text-sm font-bold text-yellow-400 uppercase tracking-wider border-b border-yellow-500/20 pb-2">{t("character_editor.rpg.equipment")}</h3>
                                            
                                            <div className="space-y-2">
                                                <Label className="text-xs text-muted-foreground">{t("character_editor.rpg.inventory")}</Label>
                                                <Textarea 
                                                    className="text-xs bg-background/50 min-h-[80px]" 
                                                    placeholder={t("character_editor.rpg.inventory_placeholder")}
                                                    value={(formData.scheda_rpg.equipaggiamento?.inventario ||[]).join('\n')}
                                                    onChange={(e) => handleRpgChange("equipaggiamento", "inventario", e.target.value.split('\n').filter(i => i.trim() !== ''))}
                                                />
                                            </div>

                                            <div className="grid grid-cols-3 gap-4 pt-2">
                                                <div className="space-y-1">
                                                    <Label className="text-[10px] uppercase text-yellow-500">{t("character_editor.rpg.gold")}</Label>
                                                    <Input type="number" className="h-8 text-xs" value={formData.scheda_rpg.equipaggiamento?.monete?.oro || 0} onChange={(e) => handleRpgChange("equipaggiamento", "monete", { ...formData.scheda_rpg.equipaggiamento?.monete, oro: parseInt(e.target.value) || 0 })} />
                                                </div>
                                                <div className="space-y-1">
                                                    <Label className="text-[10px] uppercase text-gray-400">{t("character_editor.rpg.silver")}</Label>
                                                    <Input type="number" className="h-8 text-xs" value={formData.scheda_rpg.equipaggiamento?.monete?.argento || 0} onChange={(e) => handleRpgChange("equipaggiamento", "monete", { ...formData.scheda_rpg.equipaggiamento?.monete, argento: parseInt(e.target.value) || 0 })} />
                                                </div>
                                                <div className="space-y-1">
                                                    <Label className="text-[10px] uppercase text-orange-600">{t("character_editor.rpg.copper")}</Label>
                                                    <Input type="number" className="h-8 text-xs" value={formData.scheda_rpg.equipaggiamento?.monete?.rame || 0} onChange={(e) => handleRpgChange("equipaggiamento", "monete", { ...formData.scheda_rpg.equipaggiamento?.monete, rame: parseInt(e.target.value) || 0 })} />
                                                </div>
                                            </div>

                                            {/* ARMI */}
                                            <div className="space-y-3 pt-4 border-t border-border/50">
                                                <div className="flex items-center justify-between">
                                                    <Label className="text-xs font-bold text-muted-foreground uppercase">{t("character_editor.rpg.weapons")}</Label>
                                                    <Button variant="outline" size="sm" className="h-7 text-xs" onClick={handleAddWeapon}>
                                                        <Plus className="w-3 h-3 mr-1" /> {t("character_editor.rpg.add_weapon")}
                                                    </Button>
                                                </div>
                                                <div className="space-y-2">
                                                    {(formData.scheda_rpg.equipaggiamento?.armi ||[]).map((arma: any, idx: number) => (
                                                        <div key={idx} className="flex flex-col gap-2 p-3 bg-background/50 border border-white/5 rounded-lg relative group">
                                                            <Button variant="ghost" size="icon" className="absolute top-1 right-1 h-6 w-6 text-destructive opacity-0 group-hover:opacity-100 transition-opacity" onClick={() => handleDeleteWeapon(idx)}>
                                                                <Trash2 className="w-3 h-3" />
                                                            </Button>
                                                            <div className="grid grid-cols-2 gap-2 pr-6">
                                                                <div className="space-y-1">
                                                                    <Label className="text-[10px] uppercase">{t("character_editor.rpg.weapon_name")}</Label>
                                                                    <Input className="h-7 text-xs" value={arma.nome} onChange={(e) => handleUpdateWeapon(idx, "nome", e.target.value)} />
                                                                </div>
                                                                <div className="space-y-1">
                                                                    <Label className="text-[10px] uppercase">{t("character_editor.rpg.type")}</Label>
                                                                    <HybridInput 
                                                                        value={arma.tipo} 
                                                                        onChange={(v) => handleUpdateWeapon(idx, "tipo", v)} 
                                                                        options={[t("character_editor.rpg.weapon_types.simple_melee"), t("character_editor.rpg.weapon_types.simple_ranged"), t("character_editor.rpg.weapon_types.martial_melee"), t("character_editor.rpg.weapon_types.martial_ranged"), t("character_editor.rpg.weapon_types.magic"), t("character_editor.rpg.weapon_types.firearm")]}
                                                                        placeholder={t("character_editor.rpg.weapon_type")}
                                                                    />
                                                                </div>
                                                                <div className="space-y-1">
                                                                    <Label className="text-[10px] uppercase">{t("character_editor.rpg.atk_bonus")}</Label>
                                                                    <Input type="number" className="h-7 text-xs" value={arma.bonus_attacco} onChange={(e) => handleUpdateWeapon(idx, "bonus_attacco", parseInt(e.target.value) || 0)} />
                                                                </div>
                                                                <div className="space-y-1">
                                                                    <Label className="text-[10px] uppercase">{t("character_editor.rpg.damage")}</Label>
                                                                    <HybridInput 
                                                                        value={arma.danno} 
                                                                        onChange={(v) => handleUpdateWeapon(idx, "danno", v)} 
                                                                        options={["1d4", "1d6", "1d8", "1d10", "1d12", "2d6", "1d4+1", "1d6+1", "1d8+1"]}
                                                                        placeholder={t("character_editor.rpg.damage_example")}
                                                                    />
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>

                                            {/* ARMATURE */}
                                            <div className="space-y-3 pt-4 border-t border-border/50">
                                                <div className="flex items-center justify-between">
                                                    <Label className="text-xs font-bold text-muted-foreground uppercase">{t("character_editor.rpg.armors")}</Label>
                                                    <Button variant="outline" size="sm" className="h-7 text-xs" onClick={handleAddArmor}>
                                                        <Plus className="w-3 h-3 mr-1" /> {t("character_editor.rpg.add_armor")}
                                                    </Button>
                                                </div>
                                                <div className="space-y-2">
                                                    {(formData.scheda_rpg.equipaggiamento?.armature ||[]).map((armatura: any, idx: number) => (
                                                        <div key={idx} className="flex flex-col gap-2 p-3 bg-background/50 border border-white/5 rounded-lg relative group">
                                                            <Button variant="ghost" size="icon" className="absolute top-1 right-1 h-6 w-6 text-destructive opacity-0 group-hover:opacity-100 transition-opacity" onClick={() => handleDeleteArmor(idx)}>
                                                                <Trash2 className="w-3 h-3" />
                                                            </Button>
                                                            <div className="grid grid-cols-2 gap-2 pr-6">
                                                                <div className="space-y-1">
                                                                    <Label className="text-[10px] uppercase">{t("character_editor.rpg.armor_name")}</Label>
                                                                    <Input className="h-7 text-xs" value={armatura.nome} onChange={(e) => handleUpdateArmor(idx, "nome", e.target.value)} />
                                                                </div>
                                                                <div className="space-y-1">
                                                                    <Label className="text-[10px] uppercase">{t("character_editor.rpg.type")}</Label>
                                                                    <HybridInput 
                                                                        value={armatura.tipo} 
                                                                        onChange={(v) => handleUpdateArmor(idx, "tipo", v)} 
                                                                        options={[t("character_editor.rpg.armor_types.light"), t("character_editor.rpg.armor_types.medium"), t("character_editor.rpg.armor_types.heavy"), t("character_editor.rpg.armor_types.shield"), t("character_editor.rpg.armor_types.magic")]}
                                                                        placeholder={t("character_editor.rpg.armor_type")}
                                                                    />
                                                                </div>
                                                                <div className="space-y-1">
                                                                    <Label className="text-[10px] uppercase">{t("character_editor.rpg.ca_bonus")}</Label>
                                                                    <Input className="h-7 text-xs" placeholder={t("character_editor.rpg.ca_example")} value={armatura.ca_bonus} onChange={(e) => handleUpdateArmor(idx, "ca_bonus", e.target.value)} />
                                                                </div>
                                                                <div className="space-y-1 flex items-center gap-2 pt-4">
                                                                    <Checkbox 
                                                                        id={`stealth-${idx}`}
                                                                        checked={armatura.svantaggio_furtivita} 
                                                                        onCheckedChange={(c) => handleUpdateArmor(idx, "svantaggio_furtivita", !!c)} 
                                                                    />
                                                                    <Label htmlFor={`stealth-${idx}`} className="text-[10px] uppercase cursor-pointer">{t("character_editor.rpg.stealth_disadvantage")}</Label>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>

                                        {/* MAGIA E PRIVILEGI */}
                                        <div className="bg-card p-4 rounded-xl border border-border/40 space-y-4">
                                            <h3 className="text-sm font-bold text-purple-400 uppercase tracking-wider border-b border-purple-500/20 pb-2 flex items-center gap-2">
                                                <Sparkles className="w-4 h-4" /> {t("character_editor.rpg.magic_traits")}
                                            </h3>
                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                                <div className="space-y-2">
                                                    <Label className="text-xs text-muted-foreground">{t("character_editor.rpg.racial_traits")}</Label>
                                                    <Textarea 
                                                        className="text-xs bg-background/50 min-h-[80px]" 
                                                        placeholder={t("character_editor.rpg.racial_traits_example")}
                                                        // FIX: Previene [object Object] se l'LLM genera oggetti invece di stringhe. Usa Array(0) per evitare glitch.
                                                        value={(formData.scheda_rpg.magia_e_privilegi?.tratti_razziali || Array(0)).map((i: any) => typeof i === 'object' ? (i.nome || JSON.stringify(i)) : i).join('\n')}
                                                        onChange={(e) => handleRpgChange("magia_e_privilegi", "tratti_razziali", e.target.value.split('\n').filter(i => i.trim() !== ''))}
                                                    />
                                                </div>
                                                <div className="space-y-2">
                                                    <Label className="text-xs text-muted-foreground">{t("character_editor.rpg.class_features")}</Label>
                                                    <Textarea 
                                                        className="text-xs bg-background/50 min-h-[80px]" 
                                                        placeholder={t("character_editor.rpg.class_features_example")}
                                                        // FIX: Previene [object Object] se l'LLM genera oggetti invece di stringhe. Usa Array(0) per evitare glitch.
                                                        value={(formData.scheda_rpg.magia_e_privilegi?.privilegi_classe || Array(0)).map((i: any) => typeof i === 'object' ? (i.nome || JSON.stringify(i)) : i).join('\n')}
                                                        onChange={(e) => handleRpgChange("magia_e_privilegi", "privilegi_classe", e.target.value.split('\n').filter(i => i.trim() !== ''))}
                                                    />
                                                </div>
                                                <div className="space-y-2">
                                                    <Label className="text-xs text-muted-foreground">{t("character_editor.rpg.spells")}</Label>
                                                    <Textarea 
                                                        className="text-xs bg-background/50 min-h-[80px]" 
                                                        placeholder={t("character_editor.rpg.spells_example")}
                                                        // FIX: Previene [object Object] se l'LLM genera oggetti invece di stringhe. Usa Array(0) per evitare glitch.
                                                        value={(formData.scheda_rpg.magia_e_privilegi?.incantesimi || Array(0)).map((i: any) => typeof i === 'object' ? (i.nome || JSON.stringify(i)) : i).join('\n')}
                                                        onChange={(e) => handleRpgChange("magia_e_privilegi", "incantesimi", e.target.value.split('\n').filter(i => i.trim() !== ''))}
                                                    />
                                                </div>
                                            </div>
                                        </div>

                                    </div>
                                ) : (
                                    <div className="flex flex-col items-center justify-center h-full text-muted-foreground space-y-4 py-10">
                                        <Swords className="w-12 h-12 opacity-20" />
                                        <p className="text-sm">{t("character_editor.rpg.no_sheet_found")}</p>
                                        <Button variant="outline" onClick={() => {
                                            const defaultRpg = {
                                                dati_base: { 
                                                    razza: t("character_editor.rpg.races.human"), 
                                                    classe: t("character_editor.rpg.classes.fighter"), 
                                                    livello: 1, 
                                                    punti_esperienza: 0, 
                                                    allineamento: t("character_editor.rpg.alignments.neutral") 
                                                },
                                                statistiche_core: {
                                                    forza: { valore: 10, modificatore: 0 }, destrezza: { valore: 10, modificatore: 0 },
                                                    costituzione: { valore: 10, modificatore: 0 }, intelligenza: { valore: 10, modificatore: 0 },
                                                    saggezza: { valore: 10, modificatore: 0 }, carisma: { valore: 10, modificatore: 0 }
                                                },
                                                combattimento: { hp_massimi: 10, hp_attuali: 10, classe_armatura: 10, iniziativa: 0, velocita: 9 },
                                                equipaggiamento: { armi:[], armature:[], inventario:[], monete: { oro: 0, argento: 0, rame: 0 } },
                                                magia_e_privilegi: { tratti_razziali:[], privilegi_classe: [], incantesimi:[] }
                                            };
                                            setFormData((prev: any) => ({ ...prev, scheda_rpg: defaultRpg }));
                                        }}>
                                            <Plus className="w-4 h-4 mr-2" /> {t("character_editor.rpg.init_sheet")}
                                        </Button>
                                    </div>
                                )}
                    </TabsContent>
                  </Tabs>
                </div>

              </div>
            </div>
          </div>
        )}

        <DialogFooter className="p-4 border-t bg-background z-20 shrink-0">
          <Button variant="outline" onClick={() => onOpenChange(false)}>{t("character_editor.cancel")}</Button>
          <Button onClick={handleSave} disabled={isSaveDisabled} className="bg-primary hover:bg-primary/90">
            {isLoading || isAutofilling ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
            {t("character_editor.save_character")}
          </Button>
        </DialogFooter>
      </DialogContent>

      {/* DIALOGS GILDA */}
      <Dialog open={isEditGuildOpen} onOpenChange={setIsEditGuildOpen}>
          <DialogContent className="sm:max-w-md z-[100]">
              <DialogHeader>
                  <DialogTitle>{t("character_editor.guild.edit_title")}</DialogTitle>
                  <DialogDescription className="hidden">{t("character_editor.guild.edit_title")}</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                  <div className="space-y-2">
                      <Label>{t("character_editor.guild.name_label")}</Label>
                      <Input value={editGuildName} onChange={e => setEditGuildName(e.target.value)} />
                  </div>
                  <div className="space-y-2">
                      <Label>{t("character_editor.guild.symbol_label")}</Label>
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
                              <Upload className="w-4 h-4 mr-2" /> {t("character_editor.guild.change_symbol")}
                          </Button>
                          {editGuildSymbol && <img src={editGuildSymbol} className="w-10 h-10 rounded-full border border-primary" alt="Preview" />}
                      </div>
                  </div>
              </div>
              <DialogFooter>
                  <Button variant="outline" onClick={() => setIsEditGuildOpen(false)}>{t("character_editor.guild.cancel")}</Button>
                  <Button onClick={handleEditGuild}>{t("character_editor.guild.save")}</Button>
              </DialogFooter>
          </DialogContent>
      </Dialog>

      <AlertDialog open={isDeleteGuildOpen} onOpenChange={setIsDeleteGuildOpen}>
          <AlertDialogContent className="z-[100]">
              <AlertDialogHeader>
                  <AlertDialogTitle>{t("character_editor.guild.delete_title")}</AlertDialogTitle>
                  <AlertDialogDescription>
                      {t("character_editor.guild.delete_desc")}
                  </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                  <AlertDialogCancel>{t("character_editor.guild.cancel")}</AlertDialogCancel>
                  <AlertDialogAction onClick={handleDeleteGuild} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">{t("character_editor.guild.delete_btn")}</AlertDialogAction>
              </AlertDialogFooter>
          </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={isLeaveGuildOpen} onOpenChange={setIsLeaveGuildOpen}>
          <AlertDialogContent className="z-[100]">
              <AlertDialogHeader>
                  <AlertDialogTitle>{t("character_editor.guild.leave_title")}</AlertDialogTitle>
                  <AlertDialogDescription>
                      {t("character_editor.guild.leave_desc")}
                      {isLeader && otherMembers.length > 0 && (
                          <div className="mt-4 space-y-2 text-left">
                              <Label className="text-foreground font-bold">{t("character_editor.guild.leader_warning")}</Label>
                              <Select value={newLeaderUid} onValueChange={setNewLeaderUid}>
                                  <SelectTrigger><SelectValue placeholder={t("character_editor.guild.select_new_leader")} /></SelectTrigger>
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
                  <AlertDialogCancel>{t("character_editor.guild.cancel")}</AlertDialogCancel>
                  <AlertDialogAction onClick={handleLeaveGuild} disabled={isLeader && !newLeaderUid} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">{t("character_editor.guild.leave_btn")}</AlertDialogAction>
              </AlertDialogFooter>
          </AlertDialogContent>
      </AlertDialog>
    </Dialog>
  );
};