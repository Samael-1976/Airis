// frontend_mobile/src/components/SessionHistoryDialog.tsx
// v7.6 - AUTH HEADER FIX (SANTUARIO BLINDATO)
// FIX: Sostituito l'header manuale con getHeaders() per includere il token JWT.
// Questo risolve il problema della Session History vuota su rete esterna (Ngrok).
// MANTENUTO: Bulk Actions, Rename, Delete, Select All.
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
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { ChatSession, ServerConfig } from "@/types";
import { toast } from "@/components/ui/sonner";
import { Loader2, Trash2, Edit, Check, X, CheckSquare, Square } from "lucide-react";
import { format } from "date-fns";
import { getBaseUrl, getHeaders } from "@/lib/api";
import { useTranslation } from "@/contexts/TranslationContext";

interface SessionHistoryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  serverConfig: ServerConfig | null;
  onLoadSession: (sessionId: string) => void;
}

export const SessionHistoryDialog = ({
  open,
  onOpenChange,
  serverConfig,
  onLoadSession,
}: SessionHistoryDialogProps) => {
  const { t } = useTranslation();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  
  // --- STATI PER SELEZIONE MULTIPLA (UNIVERSALE) ---
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [bulkConfirmOpen, setBulkConfirmOpen] = useState(false);

  const fetchSessions = async () => {
    setIsLoading(true);
    const baseUrl = getBaseUrl(serverConfig);
    // --- FIX v7.6: USO GETHEADERS() PER AUTH TOKEN ---
    const headers = getHeaders();

    try {
      const response = await fetch(`${baseUrl}/api/sessions`, { headers });
      if (!response.ok) throw new Error(t("session_history.err_fetch_failed"));
      const data: ChatSession[] = await response.json();
      setSessions(data);
      setSelectedIds([]); // Reset selezione al caricamento
    } catch (error: any) {
      toast.error(t("session_history.error_load"), { description: error.message });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchSessions();
    }
  }, [open, serverConfig]);

  // --- LOGICA SELEZIONE ---
  const toggleSelect = (id: string) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    if (selectedIds.length === sessions.length && sessions.length > 0) {
      setSelectedIds([]);
    } else {
      setSelectedIds(sessions.map(s => s.id));
    }
  };

  // --- LOGICA CANCELLAZIONE MASSIVA (API v62.2) ---
  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return;
    
    setIsBulkDeleting(true);
    const baseUrl = getBaseUrl(serverConfig);
    // --- FIX v7.6: USO GETHEADERS() PER AUTH TOKEN ---
    const headers = { 
      ...getHeaders(),
      "Content-Type": "application/json" 
    };

    try {
      const response = await fetch(`${baseUrl}/api/sessions/bulk-delete`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ session_ids: selectedIds }),
      });

      if (!response.ok) throw new Error(t("session_history.err_bulk_delete_failed"));
      
      const result = await response.json();
      toast.success(t("session_history.toast_bulk_deleted"), { description: result.message });
      setBulkConfirmOpen(false);
      await fetchSessions();
    } catch (error: any) {
      toast.error(t("session_history.error_delete"), { description: error.message });
    } finally {
      setIsBulkDeleting(false);
    }
  };

  // --- LOGICA RINOMINA E CANCELLAZIONE SINGOLA ---
  const handleRenameClick = (session: ChatSession) => {
    setEditingSessionId(session.id);
    setNewName(session.name);
  };

  const handleCancelRename = () => {
    setEditingSessionId(null);
    setNewName("");
  };

  const handleSaveRename = async () => {
    if (!editingSessionId || !newName.trim()) return;
    const baseUrl = getBaseUrl(serverConfig);
    // --- FIX v7.6: USO GETHEADERS() PER AUTH TOKEN ---
    const headers = { ...getHeaders(), "Content-Type": "application/json" };

    try {
      const response = await fetch(`${baseUrl}/api/sessions/${editingSessionId}`, {
        method: 'PUT',
        headers: headers,
        body: JSON.stringify({ name: newName.trim() }),
      });
      if (!response.ok) throw new Error(t("session_history.err_rename_failed"));
      toast.success(t("session_history.toast_renamed"));
      setEditingSessionId(null);
      await fetchSessions();
    } catch (error: any) {
      toast.error(t("session_history.error_rename"), { description: error.message });
    }
  };

  const handleDeleteSingle = async (sessionId: string) => {
    const baseUrl = getBaseUrl(serverConfig);
    // --- FIX v7.6: USO GETHEADERS() PER AUTH TOKEN ---
    const headers = getHeaders();

    try {
      const response = await fetch(`${baseUrl}/api/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: headers
      });
      if (!response.ok) throw new Error(t("session_history.err_delete_failed"));
      toast.success(t("session_history.toast_deleted"));
      await fetchSessions();
    } catch (error: any) {
      toast.error(t("session_history.error_delete"), { description: error.message });
    }
  };

  const handleLoad = (sessionId: string) => {
    onLoadSession(sessionId);
    onOpenChange(false);
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] flex flex-col p-0 gap-0">
          <DialogHeader className="p-6 pb-2">
            <DialogTitle>{t("session_history.title")}</DialogTitle>
            <DialogDescription>
              {t("session_history.description")}
            </DialogDescription>
          </DialogHeader>
          
          <div className="flex-1 min-h-0 px-2">
            {isLoading ? (
              <div className="flex items-center justify-center h-32">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
              </div>
            ) : sessions.length === 0 ? (
              <div className="flex items-center justify-center h-32">
                <p className="text-muted-foreground">{t("session_history.no_sessions")}</p>
              </div>
            ) : (
              <ScrollArea className="h-[60vh] pr-4">
                <div className="space-y-3 pb-4 pl-4">
                  {sessions.map((session) => (
                    <div
                      key={session.id}
                      className="group flex items-start gap-3 p-3 rounded-lg border border-border/50 bg-card/50 hover:bg-accent/50 transition-colors"
                    >
                      {/* CHECKBOX SELEZIONE (A SINISTRA) */}
                      <div className="pt-1">
                        <Checkbox 
                          checked={selectedIds.includes(session.id)}
                          onCheckedChange={() => toggleSelect(session.id)}
                        />
                      </div>

                      <div className="flex-1 min-w-0">
                        {editingSessionId === session.id ? (
                          <div className="flex items-center gap-2">
                            <Input
                              value={newName}
                              onChange={(e) => setNewName(e.target.value)}
                              onKeyDown={(e) => e.key === 'Enter' && handleSaveRename()}
                              className="h-8 text-sm"
                              autoFocus
                            />
                            <Button size="icon" variant="ghost" className="h-8 w-8" onClick={handleSaveRename}><Check className="w-4 h-4 text-green-500" /></Button>
                            <Button size="icon" variant="ghost" className="h-8 w-8" onClick={handleCancelRename}><X className="w-4 h-4 text-red-500" /></Button>
                          </div>
                        ) : (
                          <div className="flex flex-col">
                            {/* NOME SESSIONE (CLICK PER CARICARE) */}
                            <p 
                              className="font-bold truncate text-sm cursor-pointer hover:text-primary transition-colors"
                              onClick={() => handleLoad(session.id)}
                            >
                              {session.name}
                            </p>
                            
                            {/* DATA E ORA */}
                            <p className="text-[10px] text-muted-foreground mt-0.5">
                              {format(new Date(session.last_access_date * 1000), "PPP p")}
                            </p>

                            {/* ICONE AZIONE (SOTTO AL NOME, ALLINEATE A SINISTRA PER FIX OVERFLOW) */}
                            <div className="flex items-center gap-4 mt-2">
                              <button 
                                onClick={() => handleRenameClick(session)}
                                className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-primary transition-colors"
                              >
                                <Edit className="w-3.5 h-3.5" /> {t("session_history.rename")}
                              </button>
                              <button 
                                onClick={() => handleDeleteSingle(session.id)}
                                className="flex items-center gap-1 text-[11px] text-red-400/80 hover:text-red-500 transition-colors"
                              >
                                <Trash2 className="w-3.5 h-3.5" /> {t("session_history.delete")}
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>

          {/* FOOTER CON PULSANTI BULK (DISPONIBILI SU DESKTOP E MOBILE) */}
          <DialogFooter className="p-6 pt-4 border-t bg-muted/5 flex flex-col sm:flex-row gap-3">
            <div className="flex flex-1 gap-2">
              {/* TASTO DELETE MULTIPLO */}
              <Button 
                variant="destructive" 
                className="flex-1 sm:flex-none"
                disabled={selectedIds.length === 0 || isBulkDeleting}
                onClick={() => setBulkConfirmOpen(true)}
              >
                {isBulkDeleting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Trash2 className="w-4 h-4 mr-2" />}
                {t("session_history.delete_count", { count: selectedIds.length })}
              </Button>

              {/* TASTO SELECT ALL */}
              <Button 
                variant="outline" 
                className="flex-1 sm:flex-none"
                onClick={handleSelectAll}
                disabled={sessions.length === 0}
              >
                {selectedIds.length === sessions.length && sessions.length > 0 ? <Square className="w-4 h-4 mr-2" /> : <CheckSquare className="w-4 h-4 mr-2" />}
                {selectedIds.length === sessions.length && sessions.length > 0 ? t("session_history.deselect_all") : t("session_history.select_all")}
              </Button>
            </div>

            <Button variant="ghost" onClick={() => onOpenChange(false)} className="w-full sm:w-auto">
              {t("session_history.close")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* DIALOG DI CONFERMA CANCELLAZIONE DI MASSA */}
      <AlertDialog open={bulkConfirmOpen} onOpenChange={setBulkConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("session_history.confirm_title")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("session_history.confirm_desc", { count: selectedIds.length })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("session_history.confirm_cancel")}</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleBulkDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t("session_history.confirm_action")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};