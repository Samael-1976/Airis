import { ServerConfig } from "@/types";

export const getBaseUrl = (config: ServerConfig | null): string => {
  // CASO 1: Sviluppo (npm run dev su porta 3000)
  // Qui il frontend è su 3000 e il backend su 8080, servono CORS e URL completo.
  if (window.location.port === "3000") {
    if (config && config.ip) {
      const protocol = config.protocol === 'wss' ? 'https' : 'http';
      return `${protocol}://${config.ip}:${config.port}`;
    }
    return "http://127.0.0.1:8080";
  }
  
  // CASO 2: Produzione / Ngrok / LAN (Porta 8080 o 443/80 via tunnel)
  // Il frontend è servito dallo stesso server Python.
  // Restituiamo stringa vuota per usare percorsi relativi (es. "/api/...")
  // Questo impedisce di aggiungere :8080 a un URL ngrok che è già corretto.
  return "";
};

export const getHeaders = (token?: string | null) => {
  const headers: Record<string, string> = {
    "ngrok-skip-browser-warning": "true",
    // Non forziamo Content-Type qui perché FormData (upload) non lo vuole,
    // lo aggiungeremo manualmente dove serve JSON.
  };

  // --- [NUOVO v10.20] INIEZIONE TOKEN DI SICUREZZA (SANTUARIO BLINDATO) ---
  // Se il token è passato esplicitamente, usalo. Altrimenti cerca nel localStorage.
  const authToken = token || localStorage.getItem("airis_auth_token");
  
  if (authToken) {
      headers["Authorization"] = `Bearer ${authToken}`;
  }

  return headers;
};