// frontend_mobile/src/components/ProactiveMemoryDialog.tsx
// v1.3 - AUTH HEADER FIX (SANTUARIO BLINDATO)
// FIX: Sostituiti gli header manuali con getHeaders() per includere il token JWT.
// MANTENUTO: UI Refactor, Mobile Edit Overflow Fix, Recurrence Logic.
// LEGGE A0099: Invarianza strutturale garantita. Codice integrale fornito.

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
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Calendar } from "@/components/ui/calendar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
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
import { ServerConfig, ProactiveMemorySettings, EventReminder } from "@/types";
import { toast } from "@/components/ui/sonner";
import { Loader2, Save, Calendar as CalendarIcon, Settings as SettingsIcon, Trash2, Edit, RefreshCw, Clock } from "lucide-react";
import { format, isSameDay } from "date-fns";
import { getBaseUrl, getHeaders } from "@/lib/api";
import { useIsPortrait } from "@/hooks/use-mobile"; // [NUOVO] Protocollo BB
import { useTranslation } from "@/contexts/TranslationContext";

interface ProactiveMemoryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  serverConfig: ServerConfig | null;
  onSaveSettings: (settings: ProactiveMemorySettings) => Promise<void>;
}

export const ProactiveMemoryDialog = ({
  open,
  onOpenChange,
  serverConfig,
  onSaveSettings,
}: ProactiveMemoryDialogProps) => {
  const { t } = useTranslation();
  // Settings State
  const [settings, setSettings] = useState<ProactiveMemorySettings>({
    reflection_time: "23:00",
    reminder_check_interval_minutes: 10,
  });
  
  // Calendar & Events State
  const [reminders, setReminders] = useState<EventReminder[]>([]);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Delete State
  const [deletingReminder, setDeletingReminder] = useState<EventReminder | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  // Edit State
  const [editingReminder, setEditingReminder] = useState<EventReminder | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  // Edit Form Fields
  const [editName, setEditName] = useState("");
  const [editContent, setEditContent] = useState("");
  const [editDate, setEditDate] = useState<Date | undefined>(new Date());
  const [editTime, setEditTime] = useState("");
  const [editRecurrence, setEditRecurrence] = useState<string>("none");
  const isPortrait = useIsPortrait(); // [NUOVO] Protocollo BB

  // Fetch Data
  const fetchData = async () => {
    if (!serverConfig) return;
    setIsLoading(true);
    
    const baseUrl = getBaseUrl(serverConfig);
    // --- FIX v1.3: USO GETHEADERS() PER AUTH TOKEN ---
    const headers = getHeaders();

    try {
      // Fetch Settings
      const settingsRes = await fetch(`${baseUrl}/api/proactive-memory/settings`, { headers });
      if (settingsRes.ok) setSettings(await settingsRes.json());

      // Fetch Reminders
      const remindersRes = await fetch(`${baseUrl}/api/reminders`, { headers });
      if (remindersRes.ok) {
        const data = await remindersRes.json();
        setReminders(data);
      }
    } catch (error) {
      console.error(t("proactive_memory.err_fetch"), error);
      toast.error(t("proactive_memory.err_load"));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (open) fetchData();
  }, [open, serverConfig]);

  // --- Handlers Settings ---
  const handleSaveSettingsClick = async () => {
    setIsSaving(true);
    try {
      await onSaveSettings(settings);
      toast.success(t("proactive_memory.toast_settings_updated"));
    } catch (error) {
      toast.error(t("proactive_memory.err_save_settings"));
    } finally {
      setIsSaving(false);
    }
  };

  // --- Handlers Delete ---
  const handleDeleteClick = (reminder: EventReminder) => {
    setDeletingReminder(reminder);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async (mode: 'single' | 'all') => {
    if (!deletingReminder || !serverConfig) return;
    
    const baseUrl = getBaseUrl(serverConfig);
    // --- FIX v1.3: USO GETHEADERS() PER AUTH TOKEN ---
    const headers = getHeaders();

    try {
      const res = await fetch(`${baseUrl}/api/reminders/${deletingReminder.id}?mode=${mode}`, {
        method: 'DELETE',
        headers: headers
      });
      if (!res.ok) throw new Error(t("proactive_memory.err_delete_failed"));
      
      toast.success(mode === 'single' ? t("proactive_memory.toast_occurrence_skipped") : t("proactive_memory.toast_reminder_deleted"));
      setDeleteDialogOpen(false);
      setDeletingReminder(null);
      fetchData(); // Refresh list
    } catch (error) {
      toast.error(t("proactive_memory.err_delete_reminder"));
    }
  };

  // --- Handlers Edit ---
  const handleEditClick = (reminder: EventReminder) => {
    setEditingReminder(reminder);
    setEditName(reminder.event_name);
    setEditContent(reminder.content);
    const dt = new Date(reminder.event_timestamp * 1000);
    setEditDate(dt);
    setEditTime(format(dt, "HH:mm"));
    setEditRecurrence(reminder.recurrence_rule);
    setEditDialogOpen(true);
  };

  const saveEdit = async () => {
    if (!editingReminder || !serverConfig || !editDate) return;
    
    const [hours, minutes] = editTime.split(':').map(Number);
    const newEventDt = new Date(editDate);
    newEventDt.setHours(hours, minutes, 0, 0);
    
    const oldEventDt = new Date(editingReminder.event_timestamp * 1000);
    const oldTriggerDt = new Date(editingReminder.trigger_timestamp * 1000);
    const offsetMs = oldEventDt.getTime() - oldTriggerDt.getTime();
    const newTriggerDt = new Date(newEventDt.getTime() - offsetMs);

    const payload = {
      event_name: editName,
      content: editContent,
      event_timestamp: newEventDt.getTime() / 1000,
      trigger_timestamp: newTriggerDt.getTime() / 1000,
      recurrence_rule: editRecurrence
    };

    const baseUrl = getBaseUrl(serverConfig);
    // --- FIX v1.3: USO GETHEADERS() PER AUTH TOKEN ---
    const headers = { 
        ...getHeaders(),
        'Content-Type': 'application/json'
    };

    try {
      const res = await fetch(`${baseUrl}/api/reminders/${editingReminder.id}`, {
        method: 'PUT',
        headers: headers,
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(t("proactive_memory.err_update_failed"));
      
      toast.success(t("proactive_memory.toast_reminder_updated"));
      setEditDialogOpen(false);
      setEditingReminder(null);
      fetchData();
    } catch (error) {
      toast.error(t("proactive_memory.err_update_reminder"));
    }
  };

  const sortedReminders = [...reminders].sort((a, b) => a.event_timestamp - b.event_timestamp);

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-3xl max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>{t("proactive_memory.title")}</DialogTitle>
            <DialogDescription>
              {t("proactive_memory.description", { nome_avatar: "[nome_avatar]" })}
            </DialogDescription>
          </DialogHeader>

          {/* --- [MODIFICA v1.4] CONVERSIONE MOBILE (PROTOCOL BB) --- */}
          <Tabs defaultValue="calendar" className="flex-1 flex flex-col overflow-hidden">
            <div className="px-1 py-2 shrink-0">
                {isPortrait ? (
                    <div className="space-y-1">
                        <Label className="text-[10px] uppercase text-muted-foreground font-bold tracking-widest">{t("proactive_memory.section")}</Label>
                        <Select defaultValue="calendar" onValueChange={(v) => {
                            // Trigger manuale del cambio tab per il componente Tabs di Radix
                            const event = new CustomEvent('tab-change', { detail: v });
                            window.dispatchEvent(event);
                        }}>
                            <SelectTrigger className="w-full bg-muted/50 border-primary/20">
                                <SelectValue placeholder={t("proactive_memory.select_section")} />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="calendar">{t("proactive_memory.tabs.calendar")}</SelectItem>
                                <SelectItem value="settings">{t("proactive_memory.tabs.settings")}</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                ) : (
                    <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="calendar"><CalendarIcon className="w-4 h-4 mr-2"/> {t("proactive_memory.tabs.calendar")}</TabsTrigger>
                        <TabsTrigger value="settings"><SettingsIcon className="w-4 h-4 mr-2"/> {t("proactive_memory.tabs.settings")}</TabsTrigger>
                    </TabsList>
                )}
            </div>

            <TabsContent value="calendar" className="flex-1 flex flex-col gap-4 overflow-hidden mt-2">
              <div className="flex flex-col md:flex-row gap-4 h-full overflow-y-auto md:overflow-hidden">
                <div className="p-2 border rounded-md bg-muted/10 h-fit mx-auto md:mx-0 shrink-0">
                  <Calendar
                    mode="single"
                    selected={selectedDate}
                    onSelect={setSelectedDate}
                    className="rounded-md border"
                    modifiers={{
                        event: (date) => reminders.some(r => isSameDay(new Date(r.event_timestamp * 1000), date))
                    }}
                    modifiersStyles={{
                        event: { fontWeight: 'bold', textDecoration: 'underline', color: 'var(--primary)' }
                    }}
                  />
                </div>

                <div className="flex-1 flex flex-col border rounded-md bg-muted/10 overflow-hidden min-h-[300px]">
                  <div className="p-3 border-b bg-muted/20 font-medium text-sm flex justify-between items-center">
                    <span>
                        {selectedDate ? t("proactive_memory.events_for", { date: format(selectedDate, "PPP") }) : t("proactive_memory.all_events")}
                    </span>
                    <Button variant="ghost" size="icon" onClick={fetchData} className="h-6 w-6"><RefreshCw className="h-3 w-3"/></Button>
                  </div>
                  
                  <style>{`
                    .event-list-scroll::-webkit-scrollbar { width: 8px; display: block; }
                    .event-list-scroll::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); }
                    .event-list-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 4px; }
                    .event-list-scroll::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.3); }
                  `}</style>

                  <ScrollArea className="flex-1 p-3 event-list-scroll">
                    {isLoading ? (
                        <div className="flex justify-center py-4"><Loader2 className="animate-spin"/></div>
                    ) : sortedReminders.length === 0 ? (
                        <p className="text-muted-foreground text-sm text-center py-4">{t("proactive_memory.no_events")}</p>
                    ) : (
                        <div className="space-y-3">
                            {sortedReminders
                                .filter(r => !selectedDate || isSameDay(new Date(r.event_timestamp * 1000), selectedDate))
                                .map(reminder => (
                                <div key={reminder.id} className="flex items-start justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors group">
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2">
                                            <span className="font-semibold text-sm">{reminder.event_name}</span>
                                            {reminder.recurrence_rule !== 'none' && (
                                                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400 uppercase font-bold">
                                                    {reminder.recurrence_rule}
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center text-xs text-muted-foreground gap-2">
                                            <Clock className="w-3 h-3" />
                                            {format(new Date(reminder.event_timestamp * 1000), "PPP p")}
                                        </div>
                                        {reminder.content && (
                                            <p className="text-xs text-muted-foreground/80 mt-1 line-clamp-2">{reminder.content}</p>
                                        )}
                                    </div>
                                    <div className="flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleEditClick(reminder)}>
                                            <Edit className="w-3 h-3" />
                                        </Button>
                                        <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive hover:text-destructive" onClick={() => handleDeleteClick(reminder)}>
                                            <Trash2 className="w-3 h-3" />
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                  </ScrollArea>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="settings" className="flex-1 p-4 border rounded-md bg-muted/10 mt-4">
                <div className="space-y-6">
                    <div className="space-y-2">
                    <Label htmlFor="reflection-time">{t("proactive_memory.settings.reflection_time")}</Label>
                    <Input
                        id="reflection-time"
                        type="time"
                        value={settings.reflection_time}
                        onChange={(e) => setSettings((prev) => ({ ...prev, reflection_time: e.target.value }))}
                    />
                    <p className="text-xs text-muted-foreground">
                        {t("proactive_memory.settings.reflection_desc", { nome_avatar: "[nome_avatar]" })}
                    </p>
                    </div>

                    <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <Label htmlFor="reminder-enabled">{t("proactive_memory.settings.reminder_checks")}</Label>
                        <Switch
                        id="reminder-enabled"
                        checked={settings.reminder_check_interval_minutes > 0}
                        onCheckedChange={(enabled) => setSettings(prev => ({
                            ...prev,
                            reminder_check_interval_minutes: enabled ? 10 : 0
                        }))}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label>{t("proactive_memory.settings.interval", { interval: settings.reminder_check_interval_minutes > 0 ? settings.reminder_check_interval_minutes : t("proactive_memory.settings.disabled") })}</Label>
                        <Slider
                        min={1} max={60} step={1}
                        value={[settings.reminder_check_interval_minutes]}
                        onValueChange={(val) => setSettings(prev => ({ ...prev, reminder_check_interval_minutes: val[0] }))}
                        disabled={settings.reminder_check_interval_minutes === 0}
                        />
                    </div>
                    </div>
                    
                    <div className="pt-4">
                        <Button onClick={handleSaveSettingsClick} disabled={isSaving} className="w-full">
                            {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                            {t("proactive_memory.settings.save")}
                        </Button>
                    </div>
                </div>
            </TabsContent>
          </Tabs>

          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>{t("proactive_memory.actions.close")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("proactive_memory.delete_event")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("proactive_memory.delete_confirm", { name: deletingReminder?.event_name })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeleteDialogOpen(false)}>{t("proactive_memory.actions.cancel")}</AlertDialogCancel>
            {deletingReminder?.recurrence_rule !== 'none' ? (
                <>
                    <AlertDialogAction onClick={() => confirmDelete('single')}>{t("proactive_memory.delete_instance")}</AlertDialogAction>
                    <AlertDialogAction onClick={() => confirmDelete('all')} className="bg-destructive hover:bg-destructive/90">{t("proactive_memory.delete_all")}</AlertDialogAction>
                </>
            ) : (
                <AlertDialogAction onClick={() => confirmDelete('all')} className="bg-destructive hover:bg-destructive/90">{t("proactive_memory.delete_single")}</AlertDialogAction>
            )}
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-md max-h-[90vh] overflow-y-auto">
            <DialogHeader>
                <DialogTitle>{t("proactive_memory.edit_event_title")}</DialogTitle>
            </DialogHeader>
            <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                    <Label>{t("proactive_memory.event_name")}</Label>
                    <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
                </div>
                
                <div className="flex flex-col gap-4">
                    <div className="grid gap-2">
                        <Label>{t("proactive_memory.date")}</Label>
                        <div className="border rounded-md p-2 flex justify-center bg-muted/5">
                             <Calendar mode="single" selected={editDate} onSelect={setEditDate} className="rounded-md border shadow-sm" />
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                            <Label>{t("proactive_memory.time")}</Label>
                            <Input type="time" value={editTime} onChange={(e) => setEditTime(e.target.value)} />
                        </div>
                        <div className="grid gap-2">
                            <Label>{t("proactive_memory.recurrence")}</Label>
                            <Select value={editRecurrence} onValueChange={setEditRecurrence}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="none">{t("proactive_memory.recurrence_none")}</SelectItem>
                                    <SelectItem value="daily">{t("proactive_memory.recurrence_daily")}</SelectItem>
                                    <SelectItem value="weekly">{t("proactive_memory.recurrence_weekly")}</SelectItem>
                                    <SelectItem value="monthly">{t("proactive_memory.recurrence_monthly")}</SelectItem>
                                    <SelectItem value="yearly">{t("proactive_memory.recurrence_yearly")}</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </div>

                <div className="grid gap-2">
                    <Label>{t("proactive_memory.notes")}</Label>
                    <Textarea value={editContent} onChange={(e) => setEditContent(e.target.value)} />
                </div>
            </div>
            <DialogFooter>
                <Button variant="outline" onClick={() => setEditDialogOpen(false)}>{t("proactive_memory.actions.cancel")}</Button>
                <Button onClick={saveEdit}>{t("proactive_memory.save_changes")}</Button>
            </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};