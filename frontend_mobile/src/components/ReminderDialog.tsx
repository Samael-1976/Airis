// frontend_mobile/src/components/ReminderDialog.tsx
// v1.1 - UI Refactor (Mobile Overflow Fix)

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
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { toast } from "@/components/ui/sonner";
import { BellPlus, CalendarIcon, Loader2 } from "lucide-react";
import { format, set } from "date-fns";
import { cn } from "@/lib/utils";
import { ReminderData } from "@/types";
import { useTranslation } from "@/contexts/TranslationContext";

interface ReminderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: ReminderData) => Promise<void>;
}

export const ReminderDialog = ({
  open,
  onOpenChange,
  onSave,
}: ReminderDialogProps) => {
  const { t } = useTranslation();
  const [eventName, setEventName] = useState("");
  const [eventDate, setEventDate] = useState<Date | undefined>(new Date());
  const [eventTime, setEventTime] = useState(format(new Date(), "HH:mm"));
  const [reminderDate, setReminderDate] = useState<Date | undefined>(new Date());
  const [reminderTime, setReminderTime] = useState(() => {
      const now = new Date();
      const eventDateTime = set(now, { hours: parseInt(format(now, "HH")), minutes: parseInt(format(now, "mm")) });
      const reminderDateTime = new Date(eventDateTime.getTime() - 15 * 60000);
      return format(reminderDateTime, "HH:mm");
  });
  const [recurrenceRule, setRecurrenceRule] = useState<'none' | 'daily' | 'weekly' | 'monthly' | 'yearly'>('none');
  const [notes, setNotes] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  // Reset state when dialog opens and set default times
  useEffect(() => {
    if (open) {
      const now = new Date();
      const eventDefaultTime = new Date(now.getTime() + 60 * 60000); // 1 hour from now
      const reminderDefaultTime = new Date(eventDefaultTime.getTime() - 15 * 60000); // 15 mins before event

      setEventName("");
      setEventDate(eventDefaultTime);
      setEventTime(format(eventDefaultTime, "HH:mm"));
      setReminderDate(reminderDefaultTime);
      setReminderTime(format(reminderDefaultTime, "HH:mm"));
      setRecurrenceRule("none");
      setNotes("");
    }
  }, [open]);

  const combineDateAndTime = (date: Date, time: string): Date => {
    const [hours, minutes] = time.split(':').map(Number);
    return set(date, { hours, minutes, seconds: 0, milliseconds: 0 });
  };

  const handleSave = async () => {
    if (!eventName.trim()) {
      toast.error(t("reminder_dialog.error_empty"));
      return;
    }
    if (!eventDate || !reminderDate) {
      toast.error(t("reminder_dialog.error_dates"));
      return;
    }

    const finalEventDate = combineDateAndTime(eventDate, eventTime);
    const finalReminderDate = combineDateAndTime(reminderDate, reminderTime);

    if (finalReminderDate > finalEventDate) {
      toast.error(t("reminder_dialog.error_time"));
      return;
    }

    setIsSaving(true);
    try {
      await onSave({
        eventName: eventName.trim(),
        eventDate: finalEventDate,
        notes: notes.trim(),
        reminderDate: finalReminderDate,
        recurrenceRule,
      });
      toast.success(t("reminder_dialog.success"));
      onOpenChange(false);
    } catch (error: any) {
      toast.error(t("reminder_dialog.error_save"), {
        description: error.message,
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("reminder_dialog.title")}</DialogTitle>
          <DialogDescription>
            {t("reminder_dialog.description")}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="event-name" className="text-right">
              {t("reminder_dialog.event_name")}
            </Label>
            <Input
              id="event-name"
              value={eventName}
              onChange={(e) => setEventName(e.target.value)}
              className="col-span-3"
              placeholder={t("reminder_dialog.event_name_placeholder")}
            />
          </div>

          {/* MODIFICA: Layout verticale per Data e Ora dell'Evento */}
          <div className="grid grid-cols-4 items-start gap-4">
            <Label className="text-right pt-2">{t("reminder_dialog.event_time")}</Label>
            <div className="col-span-3 flex flex-col gap-2">
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant={"outline"}
                    className={cn(
                      "w-full justify-start text-left font-normal",
                      !eventDate && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {eventDate ? format(eventDate, "PPP") : <span>{t("reminder_dialog.pick_date")}</span>}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={eventDate}
                    onSelect={setEventDate}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
              <Input
                type="time"
                value={eventTime}
                onChange={(e) => setEventTime(e.target.value)}
                className="w-full"
              />
            </div>
          </div>

          {/* MODIFICA: Layout verticale per Data e Ora del Promemoria */}
          <div className="grid grid-cols-4 items-start gap-4">
            <Label className="text-right pt-2">{t("reminder_dialog.reminder_time")}</Label>
            <div className="col-span-3 flex flex-col gap-2">
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant={"outline"}
                    className={cn(
                      "w-full justify-start text-left font-normal",
                      !reminderDate && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {reminderDate ? format(reminderDate, "PPP") : <span>{t("reminder_dialog.pick_date")}</span>}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={reminderDate}
                    onSelect={setReminderDate}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
              <Input
                type="time"
                value={reminderTime}
                onChange={(e) => setReminderTime(e.target.value)}
                className="w-full"
              />
            </div>
          </div>

          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="recurrence" className="text-right">
              {t("reminder_dialog.recurrence")}
            </Label>
            <Select onValueChange={(value: any) => setRecurrenceRule(value)} defaultValue={recurrenceRule}>
              <SelectTrigger className="col-span-3">
                <SelectValue placeholder={t("reminder_dialog.recurrence_placeholder")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">{t("reminder_dialog.recurrence_none")}</SelectItem>
                <SelectItem value="daily">{t("reminder_dialog.recurrence_daily")}</SelectItem>
                <SelectItem value="weekly">{t("reminder_dialog.recurrence_weekly")}</SelectItem>
                <SelectItem value="monthly">{t("reminder_dialog.recurrence_monthly")}</SelectItem>
                <SelectItem value="yearly">{t("reminder_dialog.recurrence_yearly")}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="notes" className="text-right">
              {t("reminder_dialog.notes")}
            </Label>
            <Textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="col-span-3"
              placeholder={t("reminder_dialog.notes_placeholder")}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>{t("reminder_dialog.cancel")}</Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BellPlus className="mr-2 h-4 w-4" />}
            {isSaving ? t("reminder_dialog.saving") : t("reminder_dialog.set_reminder")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};