// frontend_mobile/src/components/ProfileDialog.tsx
// v119.0 - DECOUPLED VOICE & LANGUAGE
// FIX: Rimossa la dipendenza tra Lingua Preferita e Voce.
// ORA: La lingua imposta il cervello. La voce è selezionabile liberamente da tutte le lingue disponibili.
// LEGGE A0099: Invarianza strutturale garantita.

import { useState, useEffect, useRef } from "react";
import { UserProfile, AvailableLanguages, ServerConfig } from "@/types";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
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
  SelectGroup,
  SelectLabel
} from "@/components/ui/select";
import { Loader2, User, Languages, Music4, Users, Mail, Phone, Calendar, Power, Upload } from "lucide-react";
import { toast } from "@/components/ui/sonner";
import { getBaseUrl, getHeaders } from "@/lib/api";
import { useTranslation } from "@/contexts/TranslationContext";
import { cn } from "@/lib/utils"; // [NUOVO] Aggiunto per gestire i colori dinamici del pulsante

interface ProfileDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  profile: UserProfile | null;
  serverConfig: ServerConfig | null;
  onSave: (profile: UserProfile, imageFile: File | null) => void;
  isConnected: boolean; // [NUOVO]
  onConnect: () => void; //[NUOVO]
}

const COUNTRY_CODES =[
  { code: "+39", country: "IT", flag: "🇮🇹" },
  { code: "+1", country: "US", flag: "🇺🇸" },
  { code: "+44", country: "UK", flag: "🇬🇧" },
  { code: "+33", country: "FR", flag: "🇫🇷" },
  { code: "+49", country: "DE", flag: "🇩🇪" },
  { code: "+34", country: "ES", flag: "🇪🇸" },
  { code: "+81", country: "JP", flag: "🇯🇵" },
  { code: "+86", country: "CN", flag: "🇨🇳" },
  { code: "+7", country: "RU", flag: "🇷🇺" },
  { code: "+55", country: "BR", flag: "🇧🇷" },
  { code: "+91", country: "IN", flag: "🇮🇳" },
];

// Mappa per trasformare i codici dei file (es. 'it') in etichette eleganti per la UI
const BRAIN_LANGUAGE_NAMES: Record<string, string> = {
  ar: "🇸🇦 العربية (Arabic)",
  br: "🇧🇷 Português (BR)",
  cn: "🇨🇳 中文 (Chinese)",
  de: "🇩🇪 Deutsch",
  en: "🇬🇧 English",
  es: "🇪🇸 Español",
  fr: "🇫🇷 Français",
  in: "🇮🇳 हिन्दी (Hindi)",
  it: "🇮🇹 Italiano",
  jp: "🇯🇵 日本語 (Japanese)",
  kr: "🇰🇷 한국어 (Korean)",
  nl: "🇳🇱 Nederlands",
  pl: "🇵🇱 Polski",
  ru: "🇷🇺 Русский"
};

// Helper per generare dinamicamente i nomi delle lingue custom
const getLanguageLabel = (code: string) => {
  // 1. Se è una lingua ufficiale di Airis, usa l'etichetta con la bandiera
  if (BRAIN_LANGUAGE_NAMES[code]) return BRAIN_LANGUAGE_NAMES[code];
  
  // 2. Se è una lingua custom (es. 'fi'), risolvila dinamicamente tramite le API del browser
  try {
    const displayNames = new Intl.DisplayNames([navigator.language], { type: 'language' });
    const name = displayNames.of(code);
    return name ? name.charAt(0).toUpperCase() + name.slice(1) : code.toUpperCase();
  } catch (e) {
    return code.toUpperCase();
  }
};

export const ProfileDialog = ({
  open,
  onOpenChange,
  profile,
  serverConfig,
  onSave,
  isConnected,
  onConnect,
}: ProfileDialogProps) => {
  const { t, changeLanguage } = useTranslation(); // [FIX] Aggiunto changeLanguage
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [mobilePrefix, setMobilePrefix] = useState("+39");
  const[mobileNumber, setMobileNumber] = useState("");
  const[age, setAge] = useState("");
  const[birthDate, setBirthDate] = useState(""); // CARICAMENTO
  const [gender, setGender] = useState("unspecified");
  const[bio, setBio] = useState("");
  const [preferredLanguage, setPreferredLanguage] = useState("it");
  const [preferredVoice, setPreferredVoice] = useState("");
  
  // --- [NUOVO] STATI IMMAGINE PROFILO ---
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Stati separati per Lingue del Cervello e Voci TTS
  const [brainLanguages, setBrainLanguages] = useState<string[]>([]);
  const[languages, setLanguages] = useState<AvailableLanguages>({});
  const [loadingLanguages, setLoadingLanguages] = useState(false);

  useEffect(() => {
    if (profile && open) {
      setName(profile.name || "");
      setEmail(profile.email || "");
      setAge(profile.age || "");
      setBirthDate(profile.birthDate || ""); // CARICAMENTO
      setGender(profile.gender || "unspecified");
      setBio(profile.bio || "");
      setPreferredLanguage(profile.preferredLanguage || "it");
      setPreferredVoice(profile.preferredVoice || "");

      // --- [NUOVO] CARICAMENTO IMMAGINE PROFILO ---
      if (profile.avatar && serverConfig) {
          const serverUrl = getBaseUrl(serverConfig);
          const fullUrl = profile.avatar.startsWith('/') ? `${serverUrl}${profile.avatar}` : profile.avatar;
          setImagePreview(fullUrl);
      } else {
          setImagePreview(null);
      }
      setImageFile(null);

      // Logica per estrarre prefisso e numero
      if (profile.mobileNumber) {
          const foundPrefix = COUNTRY_CODES.find(c => profile.mobileNumber?.startsWith(c.code));
          if (foundPrefix) {
              setMobilePrefix(foundPrefix.code);
              setMobileNumber(profile.mobileNumber.slice(foundPrefix.code.length).trim());
          } else {
              setMobileNumber(profile.mobileNumber);
          }
      } else {
          setMobileNumber("");
          setMobilePrefix("+39");
      }
    }
  }, [profile, open, serverConfig]);

  useEffect(() => {
    if (open && serverConfig) {
      setLoadingLanguages(true);
      
      const serverUrl = getBaseUrl(serverConfig);
      const headers = getHeaders();

      // Fetch parallelo per Lingue del Cervello e Voci TTS
      Promise.all([
        fetch(`${serverUrl}/api/brain/languages`, { headers }).then(res => res.json()),
        fetch(`${serverUrl}/api/tts/languages`, { headers }).then(res => res.json())
      ])
      .then(([brainData, ttsData]) => {
          // 1. Imposta le lingue del cervello
          if (brainData && brainData.languages) {
              setBrainLanguages(brainData.languages);
          }

          // 2. Imposta le voci TTS
          setLanguages(ttsData);
          
          //[FIX CRITICO] Usa il valore dal profilo direttamente per evitare race conditions di stato
          const targetVoice = profile?.preferredVoice || preferredVoice;
          const allVoices = Object.values(ttsData as AvailableLanguages).flatMap(l => l.voices);
          const isVoiceValid = allVoices.some(v => v.id === targetVoice);
          
          if (!targetVoice || !isVoiceValid) {
              // Fallback sulla prima voce disponibile se quella salvata non esiste
              const firstLang = Object.keys(ttsData)[0];
              if (firstLang) {
                  setPreferredVoice(ttsData[firstLang].default_voice);
              }
          } else {
              setPreferredVoice(targetVoice);
          }
      })
      .catch((error) => {
          console.error(t("profile_dialog.err_fetch_langs_log"), error);
          toast.warning(t("profile_dialog.err_load_langs"), {
            description: t("profile_dialog.err_load_langs_desc"),
          });
          // Fallback di sicurezza
          setBrainLanguages(["it", "en"]);
          setLanguages({
            it: { name: "🇮🇹 Italian", kokoro_code: "i", voices:[{ id: "if_sara.pt", name: "if_sara", gender: "Female" }], default_voice: "if_sara.pt" },
          });
      })
      .finally(() => {
          setLoadingLanguages(false);
      });
    }
  },[open, serverConfig]);

  const handleLanguageChange = (langCode: string) => {
    setPreferredLanguage(langCode);
    // NON cambiamo più la voce automaticamente quando cambia la lingua del cervello.
    // L'utente può volere cervello IT e voce ES.
  };

  // --- [NUOVO] HANDLER IMMAGINE ---
  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const handleSave = () => {
    if (!name.trim()) {
      toast.error(t("profile_dialog.error_name_required"));
      return;
    }

    const fullMobile = mobileNumber.trim() ? `${mobilePrefix} ${mobileNumber.trim()}` : "";

    const updatedProfile: UserProfile = {
      name: name.trim(),
      email: email.trim(),
      mobileNumber: fullMobile,
      age: age.trim() || undefined,
      birthDate: birthDate.trim() || undefined, // SALVATAGGIO
      gender: gender,
      bio: bio.trim() || undefined,
      preferredLanguage,
      preferredVoice,
      avatar: profile?.avatar // Manteniamo l'URL vecchio, verrà aggiornato dal server se c'è un nuovo file
    };

    // Aggiorna immediatamente la lingua della UI nel frontend
    changeLanguage(preferredLanguage);

    onSave(updatedProfile, imageFile);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t("profile_dialog.title")}</DialogTitle>
          <DialogDescription>
            {t("profile_dialog.description")}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* --- [NUOVO] UPLOAD IMMAGINE CIRCOLARE --- */}
          <div className="flex justify-center mb-6">
              <div className="w-32 h-32 rounded-full overflow-hidden border-2 border-dashed border-muted-foreground/20 flex items-center justify-center bg-muted/10 relative group">
                  {imagePreview ? (
                      <img src={imagePreview} alt="Profile Preview" className="w-full h-full object-cover" />
                  ) : (
                      <div className="text-center text-muted-foreground">
                          <User className="w-10 h-10 mx-auto mb-1 opacity-50" />
                      </div>
                  )}
                  <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center cursor-pointer" onClick={() => fileInputRef.current?.click()}>
                      <Button variant="secondary" size="sm" className="pointer-events-none">
                          <Upload className="mr-2 h-4 w-4" /> {t("profile_dialog.change_image")}
                      </Button>
                  </div>
                  <input type="file" ref={fileInputRef} className="hidden" accept="image/*" onChange={handleImageChange} />
              </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="name">{t("profile_dialog.name")}</Label>
            <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-muted-foreground" />
                <Input 
                    id="name" 
                    name="name"
                    placeholder={t("profile_dialog.name_placeholder")} 
                    value={name} 
                    onChange={(e) => setName(e.target.value)} 
                />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">{t("profile_dialog.email")}</Label>
            <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-muted-foreground" />
                <Input 
                    id="email" 
                    name="email"
                    type="email" 
                    placeholder={t("profile_dialog.email_placeholder")} 
                    value={email} 
                    onChange={(e) => setEmail(e.target.value)} 
                />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="mobile">{t("profile_dialog.mobile")}</Label>
            <div className="flex items-center gap-2">
                <Phone className="w-4 h-4 text-muted-foreground" />
                <div className="flex gap-2 w-full">
                    <Select value={mobilePrefix} onValueChange={setMobilePrefix} name="mobilePrefix">
                        <SelectTrigger className="w-[110px]">
                            <SelectValue placeholder="+39" />
                        </SelectTrigger>
                        <SelectContent>
                            {COUNTRY_CODES.map((c) => (
                                <SelectItem key={c.code} value={c.code}>
                                    <span className="mr-2">{c.flag}</span> {c.code}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Input 
                        id="mobile" 
                        name="mobileNumber"
                        type="tel" 
                        placeholder={t("profile_dialog.mobile_placeholder")} 
                        value={mobileNumber} 
                        onChange={(e) => setMobileNumber(e.target.value)} 
                        className="flex-1"
                    />
                </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
                <Label htmlFor="age">{t("profile_dialog.age")}</Label>
                <Input 
                    id="age" 
                    name="age"
                    type="text" 
                    placeholder={t("profile_dialog.age_placeholder")} 
                    value={age} 
                    onChange={(e) => setAge(e.target.value)} 
                />
            </div>
            <div className="space-y-2">
                <Label htmlFor="birthDate">{t("profile_dialog.birth_date")}</Label>
                <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-muted-foreground" />
                    <Input 
                        id="birthDate" 
                        name="birthDate"
                        type="date" 
                        value={birthDate} 
                        onChange={(e) => setBirthDate(e.target.value)} 
                    />
                </div>
            </div>
          </div>

          <div className="space-y-2">
              <Label htmlFor="gender">{t("profile_dialog.gender")}</Label>
              <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-muted-foreground" />
                  <Select value={gender} onValueChange={setGender} name="gender">
                      <SelectTrigger id="gender"><SelectValue placeholder={t("profile_dialog.gender_placeholder")} /></SelectTrigger>
                      <SelectContent>
                          <SelectItem value="unspecified">{t("profile_dialog.gender_options.unspecified")}</SelectItem>
                          <SelectItem value="male">{t("profile_dialog.gender_options.male")}</SelectItem>
                          <SelectItem value="female">{t("profile_dialog.gender_options.female")}</SelectItem>
                          <SelectItem value="non_binary">{t("profile_dialog.gender_options.non_binary")}</SelectItem>
                          <SelectItem value="genderfluid">{t("profile_dialog.gender_options.genderfluid")}</SelectItem>
                          <SelectItem value="agender">{t("profile_dialog.gender_options.agender")}</SelectItem>
                          <SelectItem value="other">{t("profile_dialog.gender_options.other")}</SelectItem>
                      </SelectContent>
                  </Select>
              </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="bio">{t("profile_dialog.bio")}</Label>
            <Textarea 
                id="bio" 
                name="bio"
                placeholder={t("profile_dialog.bio_placeholder")} 
                value={bio} 
                onChange={(e) => setBio(e.target.value)} 
                rows={4} 
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="language">{t("profile_dialog.brain_lang")}</Label>
             <div className="flex items-center gap-2">
                <Languages className="w-4 h-4 text-muted-foreground" />
                {loadingLanguages ? (
                  <div className="flex items-center gap-2 p-2.5 border rounded-md w-full">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm text-muted-foreground">{t("profile_dialog.loading_langs")}</span>
                  </div>
                ) : (
                    <Select value={preferredLanguage} onValueChange={handleLanguageChange} disabled={brainLanguages.length === 0} name="language">
                      <SelectTrigger id="language"><SelectValue placeholder={t("profile_dialog.brain_lang_placeholder")} /></SelectTrigger>
                      <SelectContent>
                        {brainLanguages.map((code) => (
                          <SelectItem key={code} value={code}>
                            {getLanguageLabel(code)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                )}
            </div>
            <p className="text-[10px] text-muted-foreground">{t("profile_dialog.brain_lang_desc")}</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="voice">{t("profile_dialog.voice_identity")}</Label>
             <div className="flex items-center gap-2">
                <Music4 className="w-4 h-4 text-muted-foreground" />
                <Select value={preferredVoice} onValueChange={setPreferredVoice} disabled={Object.keys(languages).length === 0} name="voice">
                    <SelectTrigger id="voice"><SelectValue placeholder={t("profile_dialog.voice_identity_placeholder")} /></SelectTrigger>
                    <SelectContent>
                        {/* Raggruppamento per Lingua */}
                        {Object.entries(languages).map(([langCode, langInfo]) => (
                            <SelectGroup key={langCode}>
                                <SelectLabel className="text-xs font-bold text-muted-foreground uppercase tracking-wider bg-muted/50 px-2 py-1">
                                    {langInfo.name}
                                </SelectLabel>
                                {langInfo.voices.map((voice) => (
                                <SelectItem key={voice.id} value={voice.id} className="pl-4">
                                  {voice.name} <span className="text-xs text-muted-foreground ml-2">({voice.gender.startsWith('[') ? t(voice.gender.slice(1, -1)) : voice.gender})</span>
                                </SelectItem>
                              ))}
                            </SelectGroup>
                        ))}
                    </SelectContent>
                </Select>
            </div>
            <p className="text-[10px] text-muted-foreground">{t("profile_dialog.voice_identity_desc")}</p>
          </div>
        </div>

        <DialogFooter className="sm:justify-between w-full">
          <Button
            variant="ghost"
            onClick={onConnect}
            className={cn(
              "mr-auto", 
              isConnected ? "text-green-500 hover:text-green-600 hover:bg-green-500/10" : "text-red-500 hover:text-red-600 hover:bg-red-500/10"
            )}
          >
            <Power className="w-4 h-4 mr-2" />
            {isConnected ? t("sidebar.disconnect") : t("sidebar.connect")}
          </Button>
          <div className="flex gap-2 mt-2 sm:mt-0">
            <Button variant="outline" onClick={() => onOpenChange(false)}>{t("profile_dialog.cancel")}</Button>
            <Button onClick={handleSave} disabled={!name.trim()}>{t("profile_dialog.save")}</Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};