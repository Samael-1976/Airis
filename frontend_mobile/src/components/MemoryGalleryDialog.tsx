// frontend_mobile/src/components/MemoryGalleryDialog.tsx
// v2.1 - AUTH HEADER FIX (SANTUARIO BLINDATO)
// FIX: Aggiunti headers di autenticazione a handleDownloadImage per superare il SecurityMiddleware.
// FIX: Consolidato l'uso di getHeaders() in fetchData, handleDeleteSession e saveSessionEdit.
// MANTENUTO: Mnemosyne Protocol (Temporal Grouping), Download, Delete, Preview, Chronicles.
// LEGGE A0099: Invarianza strutturale garantita. Codice integrale fornito.

import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "@/contexts/TranslationContext";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"; // [FIX] Import Mancante
import { Label } from "@/components/ui/label"; // [FIX] Import Mancante
import { 
  Loader2, 
  Image as ImageIcon,
  BookOpen, 
  Download, 
  Trash2, 
  Edit, 
  Save, 
  X, 
  Play, 
  FileText,
  Calendar,
  Clock
} from "lucide-react";
import { toast } from "sonner";
import { getBaseUrl, getHeaders } from "@/lib/api";
import { ServerConfig } from "@/types";
import { format, isToday, isYesterday, isThisWeek, isThisMonth, isThisYear } from "date-fns";
import { useIsPortrait } from "@/hooks/use-mobile"; // [NUOVO] Protocollo BB

interface GalleryImage {
  name: string;
  url: string;
  type: 'image' | 'video';
  timestamp: number;
}

interface GallerySession {
  id: string;
  name: string;
  date: number;
  summary: string;
}

interface MemoryGalleryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  serverConfig: ServerConfig | null;
  onDeleteFile: (filename: string) => void; 
}

export const MemoryGalleryDialog = ({
  open,
  onOpenChange,
  serverConfig,
  onDeleteFile
}: MemoryGalleryDialogProps) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState("visuals");
  const [images, setImages] = useState<GalleryImage[]>([]);
  const [sessions, setSessions] = useState<GallerySession[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editSummary, setEditSummary] = useState("");

  const [previewImage, setPreviewImage] = useState<GalleryImage | null>(null);
  const isPortrait = useIsPortrait(); // [NUOVO] Protocollo BB

  const fetchData = async () => {
    if (!serverConfig) return;
    setIsLoading(true);
    const baseUrl = getBaseUrl(serverConfig);
    // --- FIX v2.1: USO GETHEADERS() PER AUTH TOKEN ---
    const headers = getHeaders();

    try {
      if (activeTab === "visuals") {
        const res = await fetch(`${baseUrl}/api/gallery/images`, { headers });
        if (res.ok) setImages(await res.json());
      } else {
        const res = await fetch(`${baseUrl}/api/gallery/sessions`, { headers });
        if (res.ok) setSessions(await res.json());
      }
    } catch (error) {
      console.error(t("memory_gallery.err_fetch"), error);
      toast.error(t("memory_gallery.toasts.fetch_error"));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (open) fetchData();
  }, [open, activeTab, serverConfig]);

  const groupedImages = useMemo(() => {
      const groups: Record<string, GalleryImage[]> = {};
      
      images.forEach(img => {
          const date = new Date(img.timestamp * 1000);
          let key = format(date, "MMMM yyyy"); 

          if (isToday(date)) key = t("memory_gallery.today");
          else if (isYesterday(date)) key = t("memory_gallery.yesterday");
          else if (isThisWeek(date)) key = t("memory_gallery.this_week");
          else if (isThisMonth(date)) key = t("memory_gallery.this_month");
          else if (isThisYear(date)) key = format(date, "MMMM");
          else key = format(date, "yyyy");

          if (!groups[key]) groups[key] = [];
          groups[key].push(img);
      });

      const order = [t("memory_gallery.today"), t("memory_gallery.yesterday"), t("memory_gallery.this_week"), t("memory_gallery.this_month")];
      const sortedKeys = Object.keys(groups).sort((a, b) => {
          const idxA = order.indexOf(a);
          const idxB = order.indexOf(b);
          if (idxA !== -1 && idxB !== -1) return idxA - idxB;
          if (idxA !== -1) return -1;
          if (idxB !== -1) return 1;
          return b.localeCompare(a); 
      });

      return sortedKeys.map(key => ({ title: key, items: groups[key] }));
  }, [images]);

  const handleDownloadImage = async (img: GalleryImage) => {
      try {
          // --- FIX v2.1: AGGIUNTI HEADERS PER DOWNLOAD SICURO ---
          const response = await fetch(img.url, { headers: getHeaders() });
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = img.name;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
          toast.success(t("memory_gallery.toasts.download_started"));
      } catch (e) {
          toast.error(t("memory_gallery.toasts.download_failed"));
      }
  };

  const handleDeleteImageClick = (img: GalleryImage) => {
      if (confirm(t("memory_gallery.toasts.delete_confirm_image", { name: img.name }))) {
          onDeleteFile(img.name);
          setImages(prev => prev.filter(i => i.name !== img.name));
          if (previewImage?.name === img.name) setPreviewImage(null);
      }
  };

  const handleDownloadSession = (session: GallerySession) => {
      const element = document.createElement("a");
      const file = new Blob([`SESSION: ${session.name}\nDATE: ${format(new Date(session.date * 1000), "PPP")}\n\nSUMMARY:\n${session.summary}`], {type: 'text/plain'});
      element.href = URL.createObjectURL(file);
      element.download = `session_${session.id}.txt`;
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
      toast.success(t("memory_gallery.toasts.session_downloaded"));
  };

  const handleDeleteSession = async (sessionId: string) => {
      if (!serverConfig || !confirm(t("memory_gallery.toasts.delete_confirm_session"))) return;
      
      const baseUrl = getBaseUrl(serverConfig);
      // --- FIX v2.1: USO GETHEADERS() PER AUTH TOKEN ---
      const headers = getHeaders();

      try {
          const res = await fetch(`${baseUrl}/api/sessions/${sessionId}`, { method: 'DELETE', headers });
          if (res.ok) {
              toast.success(t("memory_gallery.toasts.session_deleted"));
              setSessions(prev => prev.filter(s => s.id !== sessionId));
          } else {
              throw new Error(t("memory_gallery.err_delete_failed"));
          }
      } catch (e) {
          toast.error(t("memory_gallery.toasts.session_delete_failed"));
      }
  };

  const startEditingSession = (session: GallerySession) => {
      setEditingSessionId(session.id);
      setEditName(session.name);
      setEditSummary(session.summary || "");
  };

  const saveSessionEdit = async () => {
      if (!serverConfig || !editingSessionId) return;
      
      const baseUrl = getBaseUrl(serverConfig);
      // --- FIX v2.1: USO GETHEADERS() PER AUTH TOKEN ---
      const headers = { ...getHeaders(), "Content-Type": "application/json" };

      try {
          const res = await fetch(`${baseUrl}/api/sessions/${editingSessionId}`, {
              method: 'PUT',
              headers,
              body: JSON.stringify({ 
                  name: editName,
                  narrative_buffer: editSummary
              })
          });
          
          if (res.ok) {
              toast.success(t("memory_gallery.toasts.session_updated"));
              setSessions(prev => prev.map(s => s.id === editingSessionId ? { ...s, name: editName, summary: editSummary } : s));
              setEditingSessionId(null);
          } else {
              throw new Error(t("memory_gallery.err_update_failed"));
          }
      } catch (e) {
          toast.error(t("memory_gallery.toasts.session_update_failed"));
      }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-4xl max-h-[90vh] h-[90vh] flex flex-col overflow-hidden p-0 gap-0">
        <DialogHeader className="p-6 pb-2 bg-muted/10 border-b shrink-0">
          <DialogTitle className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-primary" />
              {t("memory_gallery.title")}
          </DialogTitle>
          <DialogDescription>
            {t("memory_gallery.description")}
          </DialogDescription>
        </DialogHeader>

        <style>{`
            .gallery-scrollbar {
                overflow-y: auto !important;
                scrollbar-width: auto !important;
                scrollbar-color: hsl(340 82% 52%) hsl(220 15% 10%) !important;
            }
            .gallery-scrollbar::-webkit-scrollbar {
                width: 12px !important;
                height: 12px !important;
                display: block !important;
                background-color: hsl(220 15% 10%);
            }
            .gallery-scrollbar::-webkit-scrollbar-track {
                background: hsl(220 15% 10%) !important;
                border-left: 1px solid hsl(220 15% 20%);
            }
            .gallery-scrollbar::-webkit-scrollbar-thumb {
                background-color: hsl(340 82% 52%) !important;
                border-radius: 6px;
                border: 2px solid hsl(220 15% 10%);
            }
            .gallery-scrollbar::-webkit-scrollbar-thumb:hover {
                background-color: hsl(340 82% 60%) !important;
            }
        `}</style>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden min-h-0">
            {/* --- [MODIFICA v2.2] CONVERSIONE MOBILE (PROTOCOL BB) --- */}
            <div className="px-6 pt-2 shrink-0">
                {isPortrait ? (
                    <div className="space-y-1">
                        <Label className="text-[10px] uppercase text-muted-foreground font-bold tracking-widest">Gallery Type</Label>
                        <Select value={activeTab} onValueChange={setActiveTab}>
                            <SelectTrigger className="w-full bg-muted/50 border-primary/20">
                                <SelectValue placeholder={t("memory_gallery.select.placeholder")} />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="visuals">{t("memory_gallery.tabs.visuals")}</SelectItem>
                                <SelectItem value="chronicles">{t("memory_gallery.tabs.chronicles")}</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                ) : (
                    <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="visuals"><ImageIcon className="w-4 h-4 mr-2"/> {t("memory_gallery.tabs.visuals")}</TabsTrigger>
                        <TabsTrigger value="chronicles"><FileText className="w-4 h-4 mr-2"/> {t("memory_gallery.tabs.chronicles")}</TabsTrigger>
                    </TabsList>
                )}
            </div>

            <div className="flex-1 overflow-hidden p-0 min-h-0 relative flex flex-col">
                {isLoading ? (
                    <div className="h-full flex items-center justify-center">
                        <Loader2 className="w-8 h-8 animate-spin text-primary" />
                    </div>
                ) : (
                    <>
                        <TabsContent value="visuals" className="flex-1 min-h-0 m-0 p-0 data-[state=active]:flex flex-col md:flex-row">
                            <div className="flex-1 p-4 gallery-scrollbar min-h-0">
                                {images.length === 0 ? (
                                    <div className="text-center text-muted-foreground py-10">{t("memory_gallery.visuals.empty")}</div>
                                ) : (
                                    <div className="space-y-6 pb-4">
                                        {groupedImages.map((group) => (
                                            <div key={group.title} className="space-y-3">
                                                <div className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm py-2 px-1 border-b border-border/50 flex items-center gap-2">
                                                    <Calendar className="w-4 h-4 text-primary" />
                                                    <h3 className="text-sm font-bold uppercase tracking-wider text-foreground/80">{group.title}</h3>
                                                    <span className="text-xs text-muted-foreground ml-auto">{group.items.length} {t("memory_gallery.visuals.items")}</span>
                                                </div>
                                                
                                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                                                    {group.items.map((img) => (
                                                        <div 
                                                            key={img.name} 
                                                            className="group relative aspect-square rounded-lg overflow-hidden border border-border/50 bg-black/20 cursor-pointer hover:border-primary/50 transition-all"
                                                            onClick={() => setPreviewImage(img)}
                                                        >
                                                            {img.type === 'video' ? (
                                                                <div className="w-full h-full flex items-center justify-center bg-muted">
                                                                    <Play className="w-8 h-8 text-white/50" />
                                                                </div>
                                                            ) : (
                                                                <img src={img.url} alt={img.name} className="w-full h-full object-cover" loading="lazy" />
                                                            )}
                                                            
                                                            <div className="absolute inset-x-0 bottom-0 p-2 bg-gradient-to-t from-black/90 to-transparent opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity flex items-center justify-center gap-4 z-10">
                                                                <Button size="icon" variant="secondary" className="h-8 w-8 rounded-full shadow-md" title={t("memory_gallery.visuals.download")} onClick={(e) => { e.stopPropagation(); handleDownloadImage(img); }}>
                                                                    <Download className="w-4 h-4" />
                                                                </Button>
                                                                <Button size="icon" variant="destructive" className="h-8 w-8 rounded-full shadow-md" title={t("memory_gallery.visuals.delete")} onClick={(e) => { e.stopPropagation(); handleDeleteImageClick(img); }}>
                                                                    <Trash2 className="w-4 h-4" />
                                                                </Button>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {previewImage && (
                                <div className="w-1/3 border-l bg-muted/10 p-4 hidden md:flex flex-col gap-4 shrink-0 overflow-y-auto gallery-scrollbar">
                                    <div className="aspect-video bg-black rounded-lg overflow-hidden flex items-center justify-center border border-border shrink-0">
                                        {previewImage.type === 'video' ? (
                                            <video src={previewImage.url} controls className="max-w-full max-h-full" />
                                        ) : (
                                            <img src={previewImage.url} alt="Preview" className="max-w-full max-h-full object-contain" />
                                        )}
                                    </div>
                                    <div className="space-y-2">
                                        <Label className="text-xs text-muted-foreground">{t("memory_gallery.visuals.filename")}</Label>
                                        <p className="text-sm font-mono break-all">{previewImage.name}</p>
                                        <Label className="text-xs text-muted-foreground">{t("memory_gallery.visuals.date")}</Label>
                                        <p className="text-sm">{format(new Date(previewImage.timestamp * 1000), "PPP p")}</p>
                                    </div>
                                    <div className="mt-auto flex gap-2 pt-4">
                                        <Button className="flex-1" variant="outline" onClick={() => handleDownloadImage(previewImage)}>
                                            <Download className="w-4 h-4 mr-2" /> {t("memory_gallery.visuals.download")}
                                        </Button>
                                        <Button className="flex-1" variant="destructive" onClick={() => handleDeleteImageClick(previewImage)}>
                                            <Trash2 className="w-4 h-4 mr-2" /> {t("memory_gallery.visuals.delete")}
                                        </Button>
                                    </div>
                                    <Button variant="ghost" className="w-full" onClick={() => setPreviewImage(null)}>{t("memory_gallery.visuals.preview_close")}</Button>
                                </div>
                            )}
                        </TabsContent>

                        <TabsContent value="chronicles" className="flex-1 min-h-0 m-0 p-0 data-[state=active]:flex flex-col">
                            <div className="flex-1 p-4 gallery-scrollbar min-h-0">
                                {sessions.length === 0 ? (
                                    <div className="text-center text-muted-foreground py-10">{t("memory_gallery.chronicles.empty")}</div>
                                ) : (
                                    <div className="space-y-4 pb-4">
                                        {sessions.map((session) => (
                                            <Card key={session.id} className="bg-card/50 border-border/50">
                                                <CardContent className="p-4 space-y-3">
                                                    <div className="flex justify-between items-start">
                                                        <div className="space-y-1 flex-1">
                                                            {editingSessionId === session.id ? (
                                                                <div className="flex gap-2 items-center">
                                                                    <Input 
                                                                        value={editName} 
                                                                        onChange={(e) => setEditName(e.target.value)} 
                                                                        className="h-8 text-sm font-bold"
                                                                    />
                                                                    <Button size="icon" variant="ghost" className="h-8 w-8 text-green-500" onClick={saveSessionEdit}><Save className="w-4 h-4" /></Button>
                                                                    <Button size="icon" variant="ghost" className="h-8 w-8 text-red-500" onClick={() => setEditingSessionId(null)}><X className="w-4 h-4" /></Button>
                                                                </div>
                                                            ) : (
                                                                <h4 className="font-bold text-lg flex items-center gap-2">
                                                                    {session.name}
                                                                    <Button size="icon" variant="ghost" className="h-6 w-6 text-muted-foreground hover:text-primary" onClick={() => startEditingSession(session)}>
                                                                        <Edit className="w-3 h-3" />
                                                                    </Button>
                                                                </h4>
                                                            )}
                                                            <div className="flex items-center text-xs text-muted-foreground gap-2">
                                                                <Clock className="w-3 h-3" />
                                                                {format(new Date(session.date * 1000), "PPP p")}
                                                            </div>
                                                        </div>
                                                        <div className="flex gap-1">
                                                            <Button size="sm" variant="outline" onClick={() => handleDownloadSession(session)}>
                                                                <Download className="w-4 h-4 mr-2" /> {t("memory_gallery.chronicles.save")}
                                                            </Button>
                                                            <Button size="sm" variant="destructive" onClick={() => handleDeleteSession(session.id)}>
                                                                <Trash2 className="w-4 h-4" />
                                                            </Button>
                                                        </div>
                                                    </div>
                                                    
                                                    <div className="bg-muted/30 p-3 rounded-md border border-border/30">
                                                        {editingSessionId === session.id ? (
                                                            <Textarea 
                                                                value={editSummary}
                                                                onChange={(e) => setEditSummary(e.target.value)}
                                                                className="min-h-[100px] text-sm font-serif leading-relaxed bg-background/50"
                                                                placeholder={t("memory_gallery.chronicles.edit_placeholder")}
                                                            />
                                                        ) : (
                                                            <p className="text-sm text-foreground/90 whitespace-pre-wrap font-serif leading-relaxed">
                                                                {session.summary || t("memory_gallery.chronicles.no_summary")}
                                                            </p>
                                                        )}
                                                    </div>
                                                </CardContent>
                                            </Card>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </TabsContent>
                    </>
                )}
            </div>
        </Tabs>

        <DialogFooter className="p-4 border-t bg-muted/5 shrink-0">
          <Button variant="outline" onClick={() => onOpenChange(false)}>{t("memory_gallery.actions.close")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};