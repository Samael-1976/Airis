import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useEffect } from "react";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import { useTranslation } from "./contexts/TranslationContext"; // [NUOVO]

const queryClient = new QueryClient();

const App = () => {
  // --- [NUOVO] INIEZIONE TEMA GLOBALE AL BOOT ---
  useEffect(() => {
    const applyThemeToDom = (theme: any) => {
      const root = document.documentElement;
      if (!theme) {
        // Ripristina i default di Airis Pink rimuovendo gli stili inline
        root.style.removeProperty('--background');
        root.style.removeProperty('--foreground');
        root.style.removeProperty('--primary');
        root.style.removeProperty('--primary-foreground');
        root.style.removeProperty('--secondary');
        root.style.removeProperty('--secondary-foreground');
        root.style.removeProperty('--muted');
        root.style.removeProperty('--muted-foreground');
        root.style.removeProperty('--accent');
        root.style.removeProperty('--accent-foreground');
        root.style.removeProperty('--card');
        root.style.removeProperty('--card-foreground');
        root.style.removeProperty('--border');
        return;
      }
      
      Object.entries(theme).forEach(([key, value]) => {
        root.style.setProperty(`--${key}`, value as string);
      });
    };

    // 1. Carica al boot dal localStorage
    try {
      const storedProfile = localStorage.getItem("airis_user_profile");
      if (storedProfile) {
        const profile = JSON.parse(storedProfile);
        if (profile.theme) {
          applyThemeToDom(profile.theme);
        }
      }
    } catch (e) {
      console.error("Errore caricamento tema:", e);
    }

    // 2. Ascolta gli aggiornamenti in tempo reale da UiThemesTab
    const handleThemeUpdate = (e: any) => {
      applyThemeToDom(e.detail);
    };
    window.addEventListener('airis-theme-update', handleThemeUpdate);

    return () => window.removeEventListener('airis-theme-update', handleThemeUpdate);
  }, []);

  return (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      {/* FIX: Aggiunto basename dinamico e Future Flags per React Router v7 */}
      <BrowserRouter 
        basename={import.meta.env.BASE_URL}
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <Routes>
          <Route path="/" element={<Index />} />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
  );
};

export default App;