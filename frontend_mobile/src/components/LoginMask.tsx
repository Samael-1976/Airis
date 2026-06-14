// frontend_mobile/src/components/LoginMask.tsx
// v1.0 - BOOTSTRAP AUTH INTERFACE (SANTUARIO BLINDATO)
// NEW: Gestione dinamica Setup Mode (Stato Vergine) vs Login Mode.
// NEW: Validazione doppia password per la consacrazione dell'Admin.
// LEGGE A0099: Invarianza strutturale garantita. Codice integrale fornito.

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Lock, User, KeyRound, ShieldCheck, Loader2, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { getBaseUrl } from "@/lib/api";
import { ServerConfig } from "@/types";
import { useTranslation } from "@/contexts/TranslationContext";

interface LoginMaskProps {
  onLoginSuccess: (token: string) => void;
  serverConfig: ServerConfig | null;
}

export const LoginMask = ({ onLoginSuccess, serverConfig }: LoginMaskProps) => {
  const { t } = useTranslation();
  const [isSetupMode, setIsSetupMode] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Form State
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const baseUrl = getBaseUrl(serverConfig);

  // 1. Rilevamento Stato del Santuario (Bootstrap Protocol)
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        // L'endpoint /api/auth/status è in whitelist nel middleware
        const res = await fetch(`${baseUrl}/api/auth/status`, {
            headers: { "ngrok-skip-browser-warning": "true" }
        });
        if (res.ok) {
          const data = await res.json();
          setIsSetupMode(data.setup_mode);
        }
      } catch (error) {
        console.error(t("login_mask.err_status_check"), error);
        toast.error(t("login_mask.error_connection"), { description: t("login_mask.error_connection_desc") });
      } finally {
        setIsLoading(false);
      }
    };
    checkAuthStatus();
  }, [baseUrl]);

  // 2. Gestione Login Standard
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
        toast.warning(t("login_mask.warn_fill_fields"));
        return;
    }

    setIsSubmitting(true);
    try {
        const res = await fetch(`${baseUrl}/api/auth/login`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true"
            },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || t("login_mask.err_access_denied"));
        }

        toast.success(t("login_mask.toast_access_granted"), { description: t("login_mask.toast_welcome_back") });
        onLoginSuccess(data.access_token);

    } catch (error: any) {
        toast.error(t("login_mask.error_login"), { description: error.message });
    } finally {
        setIsSubmitting(false);
    }
  };

  // 3. Gestione Consacrazione Primo Amministratore (Setup Mode)
  const handleSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password || !confirmPassword) {
        toast.warning(t("login_mask.warn_fill_fields"));
        return;
    }
    if (password !== confirmPassword) {
        toast.error(t("login_mask.err_pass_mismatch"));
        return;
    }
    if (password.length < 8) {
        toast.error(t("login_mask.err_pass_weak"), { description: t("login_mask.err_pass_min_chars") });
        return;
    }

    setIsSubmitting(true);
    try {
        const res = await fetch(`${baseUrl}/api/auth/setup`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true"
            },
            body: JSON.stringify({ 
                username, 
                password, 
                confirm_password: confirmPassword 
            })
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || t("login_mask.error_setup"));
        }

        toast.success(t("login_mask.toast_sanctuary_secured"), { description: t("login_mask.toast_admin_created") });
        setIsSetupMode(false); // Passa alla modalità login
        setPassword("");
        setConfirmPassword("");

    } catch (error: any) {
        toast.error(t("login_mask.error_setup"), { description: error.message });
    } finally {
        setIsSubmitting(false);
    }
  };

  if (isLoading) {
      return (
          <div className="flex h-screen w-full items-center justify-center bg-background">
              <div className="flex flex-col items-center gap-4">
                  <Loader2 className="w-12 h-12 animate-spin text-primary" />
                  <p className="text-sm text-muted-foreground animate-pulse">{t("login_mask.loading")}</p>
              </div>
          </div>
      );
  }

  return (
    <div className="flex h-screen w-full items-center justify-center bg-background p-4 overflow-hidden">
        {/* Sfondo decorativo sfocato */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-background to-background pointer-events-none" />
        
        <Card className="w-full max-w-md border-primary/20 shadow-2xl bg-card/50 backdrop-blur-xl relative z-10 animate-in fade-in zoom-in-95 duration-500">
            <CardHeader className="space-y-1 text-center">
                <div className="mx-auto bg-primary/10 p-4 rounded-full w-fit mb-4 shadow-inner">
                    {isSetupMode ? (
                        <ShieldCheck className="w-10 h-10 text-primary animate-pulse" />
                    ) : (
                        <Lock className="w-10 h-10 text-primary" />
                    )}
                </div>
                <CardTitle className="text-3xl font-bold tracking-tight text-foreground">
                    {isSetupMode ? t("login_mask.setup_title") : t("login_mask.login_title")}
                </CardTitle>
                <CardDescription className="text-muted-foreground text-base">
                    {isSetupMode 
                        ? t("login_mask.setup_desc") 
                        : t("login_mask.login_desc")}
                </CardDescription>
            </CardHeader>
            
            <form onSubmit={isSetupMode ? handleSetup : handleLogin}>
                <CardContent className="space-y-5">
                    <div className="space-y-2">
                        <Label htmlFor="username" className="text-sm font-semibold uppercase tracking-wider opacity-70">{t("login_mask.username")}</Label>
                        <div className="relative group">
                            <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
                            <Input 
                                id="username" 
                                placeholder={isSetupMode ? t("login_mask.username_placeholder_setup") : t("login_mask.username_placeholder_login")} 
                                className="pl-10 bg-background/50 border-primary/10 focus:border-primary/50 transition-all h-11" 
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                autoComplete="username"
                                autoFocus
                            />
                        </div>
                    </div>
                    
                    <div className="space-y-2">
                        <Label htmlFor="password" id="password-label" className="text-sm font-semibold uppercase tracking-wider opacity-70">{t("login_mask.password")}</Label>
                        <div className="relative group">
                            <KeyRound className="absolute left-3 top-3 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
                            <Input 
                                id="password" 
                                type="password" 
                                placeholder="••••••••" 
                                className="pl-10 bg-background/50 border-primary/10 focus:border-primary/50 transition-all h-11" 
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                autoComplete={isSetupMode ? "new-password" : "current-password"}
                            />
                        </div>
                    </div>

                    {isSetupMode && (
                        <div className="space-y-2 animate-in slide-in-from-top-4 fade-in duration-300">
                            <Label htmlFor="confirm" className="text-sm font-semibold uppercase tracking-wider opacity-70">{t("login_mask.confirm_password")}</Label>
                            <div className="relative group">
                                <KeyRound className="absolute left-3 top-3 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
                                <Input 
                                    id="confirm" 
                                    type="password" 
                                    placeholder="••••••••" 
                                    className="pl-10 bg-background/50 border-primary/10 focus:border-primary/50 transition-all h-11" 
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    autoComplete="new-password"
                                />
                            </div>
                            <div className="flex items-start gap-2 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20 mt-2">
                                <AlertTriangle className="w-4 h-4 text-yellow-500 shrink-0 mt-0.5" />
                                <p className="text-[11px] text-yellow-200/80 leading-tight">
                                    {t("login_mask.security_note")}
                                </p>
                            </div>
                        </div>
                    )}
                </CardContent>
                
                <CardFooter className="pt-2">
                    <Button 
                        className="w-full h-12 text-lg font-bold bg-primary hover:bg-primary/90 text-white shadow-lg shadow-primary/20 transition-all active:scale-[0.98]" 
                        disabled={isSubmitting} 
                        type="submit"
                    >
                        {isSubmitting ? (
                            <>
                                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                {isSetupMode ? t("login_mask.button_submitting_setup") : t("login_mask.button_submitting_login")}
                            </>
                        ) : (
                            isSetupMode ? t("login_mask.button_setup") : t("login_mask.button_login")
                        )}
                    </Button>
                </CardFooter>
            </form>
        </Card>
        
        {/* Footer agnostico */}
        <div className="absolute bottom-6 text-center w-full">
            <p className="text-[10px] text-muted-foreground uppercase tracking-[0.2em] opacity-50">
                {t("login_mask.footer")}
            </p>
        </div>
    </div>
  );
};