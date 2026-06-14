import { ServerConfig, UserProfile } from "@/types";

const SERVER_CONFIG_KEY = "airis_server_config";
const USER_PROFILE_KEY = "airis_user_profile";

// Helper per sanitizzazione aggressiva dell'IP
// Rimuove protocolli, slash finali e spazi che causano errori su iOS
const sanitizeIp = (ip: string): string => {
  if (!ip) return "";
  return ip
    .replace(/^(https?|wss?):\/\//, '') // Rimuove http://, https://, ws://, wss://
    .replace(/\/$/, '')                 // Rimuove slash finale
    .trim();                            // Rimuove spazi
};

export const saveServerConfig = (config: ServerConfig) => {
  try {
    const cleanConfig = { ...config };
    if (cleanConfig.ip) {
        cleanConfig.ip = sanitizeIp(cleanConfig.ip);
    }
    localStorage.setItem(SERVER_CONFIG_KEY, JSON.stringify(cleanConfig));
  } catch (error) {
    console.error("Error saving server config to localStorage:", error);
  }
};

export const loadServerConfig = (): ServerConfig | null => {
  try {
    const stored = localStorage.getItem(SERVER_CONFIG_KEY);
    if (stored) {
      const config = JSON.parse(stored);
      
      // FIX CRITICO: Sanitizzazione in lettura.
      // Se nel localStorage c'è un IP sporco (es. con http://), lo puliamo al volo
      // prima che venga passato a WebSocket o fetch, prevenendo il crash su iOS.
      if (config.ip) {
          config.ip = sanitizeIp(config.ip);
      }
      
      return config;
    }
  } catch (error) {
    console.error("Error parsing server config from localStorage:", error);
    // Se i dati sono corrotti, li rimuoviamo per evitare fallimenti futuri
    localStorage.removeItem(SERVER_CONFIG_KEY);
  }
  return null;
};

export const saveUserProfile = (profile: UserProfile) => {
  try {
    localStorage.setItem(USER_PROFILE_KEY, JSON.stringify(profile));
  } catch (error) {
    console.error("Error saving user profile to localStorage:", error);
  }
};

export const loadUserProfile = (): UserProfile | null => {
  try {
    const stored = localStorage.getItem(USER_PROFILE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.error("Error parsing user profile from localStorage:", error);
    localStorage.removeItem(USER_PROFILE_KEY);
  }
  return null;
};