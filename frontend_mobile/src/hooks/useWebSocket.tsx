import { useState, useEffect, useRef, useCallback } from "react";
import { WebSocketMessage, ConnectionStatus, ServerConfig } from "@/types";
import { useTranslation } from "@/contexts/TranslationContext";

export const useWebSocket = (config: ServerConfig | null, customUrl?: string, customToken?: string) => {
  const { t } = useTranslation();
  const[status, setStatus] = useState<ConnectionStatus>("disconnected");
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const heartbeatInterval = useRef<NodeJS.Timeout | null>(null);
  const [latestMessage, setLatestMessage] = useState<WebSocketMessage | null>(null);
  
  const shouldReconnect = useRef<boolean>(true);
  const isMounted = useRef<boolean>(true);
  const connectionAttempts = useRef<number>(0);
  const lastPongTime = useRef<number>(Date.now()); // [FIX CRITICO] Tracciamento Heartbeat

  const disconnect = useCallback(() => {
    console.log(t("main_js.ws_disconnect_called"));
    shouldReconnect.current = false;
    
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    
    if (heartbeatInterval.current) {
      clearInterval(heartbeatInterval.current);
      heartbeatInterval.current = null;
    }
    
    if (ws.current) {
      console.log(t("main_js.ws_manual_close"));
      
      // --- [FIX CRITICO] ISOLAMENTO ISTANZA SOCKET ---
      // Salviamo il riferimento esatto al socket prima di sganciarlo da React.
      // Questo previene errori di scope se l'evento onopen scatta dopo che ws.current è diventato null.
      const socketToClose = ws.current;
      ws.current = null;
      
      socketToClose.onclose = null;
      socketToClose.onerror = null;
      socketToClose.onmessage = null;
      
      // Se è OPEN, chiudiamo subito.
      if (socketToClose.readyState === WebSocket.OPEN) {
        socketToClose.onopen = null;
        socketToClose.close();
      } 
      // Se è CONNECTING, aspettiamo che si apra e poi lo chiudiamo, 
      // altrimenti il browser lancia il warning "WebSocket is closed before the connection is established".
      else if (socketToClose.readyState === WebSocket.CONNECTING) {
        socketToClose.onopen = () => {
          socketToClose.close();
        };
      } else {
        socketToClose.onopen = null;
      }
    }
    
    setStatus("disconnected");
  }, [t]);

  const connect = useCallback(() => {
    console.log(t("main_js.ws_connect_called"));
    // EARLY RETURN: Non connettersi se non montato o senza config
    if (!isMounted.current || !config) {
      console.log(t("main_js.ws_connect_aborted"));
      return;
    }

    if (
      ws.current &&
      (ws.current.readyState === WebSocket.OPEN ||
        ws.current.readyState === WebSocket.CONNECTING)
    ) {
      console.log(t("main_js.ws_already_connected"));
      return;
    }

    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }

    // --- RECUPERO TOKEN ---
    const token = customToken || localStorage.getItem("airis_auth_token");
    if (!token) {
      console.warn(t("main_js.ws_token_missing"));
      setStatus("disconnected");
      
      // Riprova dopo 1 secondo (per dare tempo al check trusted di completarsi)
      // Ma solo per i primi 5 tentativi per evitare loop infiniti
      if (shouldReconnect.current && isMounted.current && connectionAttempts.current < 5) {
        connectionAttempts.current += 1;
        reconnectTimeout.current = setTimeout(() => {
          console.log(t("main_js.ws_retry_auth", { attempt: connectionAttempts.current }));
          connect();
        }, 1000);
      } else if (connectionAttempts.current >= 5) {
        console.error(t("main_js.ws_max_attempts"));
        setStatus("error");
      }
      return;
    }

    // Reset tentativi se abbiamo un token
    connectionAttempts.current = 0;

    // VERIFICA VALIDITÀ TOKEN
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const exp = payload.exp * 1000;
      const now = Date.now();
      
      if (exp <= now) {
        console.error(t("main_js.ws_token_expired"));
        setStatus("error");
        localStorage.removeItem("airis_auth_token");
        setTimeout(() => {
          window.location.reload();
        }, 500);
        return;
      }
      
      const minutesLeft = Math.floor((exp - now) / 1000 / 60);
      console.log(t("main_js.ws_token_valid", { minutes: minutesLeft }));
    } catch (e) {
      console.error(t("main_js.ws_token_malformed"), e);
      setStatus("error");
      localStorage.removeItem("airis_auth_token");
      return;
    }

    let url = "";

    // LOGICA URL UNIFICATA
    if (customUrl) {
      url = customUrl;
      console.log(t("main_js.ws_custom_url", { url }));
    } else if (window.location.port === "3000") {
      // SVILUPPO: Usa config o localhost:8080
      if (config.ip) {
        const protocol = config.protocol === "wss" ? "wss" : "ws";
        url = `${protocol}://${config.ip}:${config.port}/ws`;
      } else {
        url = "ws://127.0.0.1:8080/ws";
      }
      console.log(t("main_js.ws_dev_url", { url }));
    } else {
      // PRODUZIONE / NGROK: Usa l'host della pagina corrente
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host;
      url = `${protocol}//${host}/ws`;
      console.log(t("main_js.ws_prod_url", { url }));
    }

    // --- INIEZIONE TOKEN NELLA QUERY STRING ---
    url += `?token=${token}`;

    setStatus("connecting");
    shouldReconnect.current = true;

    try {
      const protocols = ["ngrok-skip-browser-warning"];
      ws.current = new WebSocket(url, protocols);
    } catch (error) {
      console.error(t("main_js.ws_instantiation_error"), error);
      setStatus("error");
      return;
    }

    ws.current.onopen = () => {
      console.log(t("main_js.ws_connected"));
      setStatus("connected");
      lastPongTime.current = Date.now(); // Reset timer al connect

      // Heartbeat
      if (heartbeatInterval.current) {
        clearInterval(heartbeatInterval.current);
      }
      heartbeatInterval.current = setInterval(() => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
          ws.current.send(JSON.stringify({ type: "ping" }));
          
          // --- [FIX CRITICO] DEAD SOCKET DETECTION ---
          // Se non riceviamo un pong da 25 secondi, l'OS mobile ha ucciso il socket in background.
          // Chiudiamo forzatamente per innescare la riconnessione immediata.
          if (Date.now() - lastPongTime.current > 25000) {
              console.warn("WebSocket timeout: nessun pong ricevuto dal server. Forzo riconnessione.");
              ws.current.close(4000, "Heartbeat timeout");
          }
        }
      }, 10000);
    };

    ws.current.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        
        // --- [FIX CRITICO] HEARTBEAT ATTIVO ---
        if (message.type === "pong") {
            lastPongTime.current = Date.now();
            return; // Non passiamo il pong al resto dell'app per non causare re-render inutili
        }
        
        setLatestMessage(message);
      } catch (error) {
        console.error(t("main_js.ws_parsing_error"), error);
      }
    };

    ws.current.onerror = (error) => {
      console.error(t("main_js.ws_socket_error"), error);
    };

    ws.current.onclose = (e) => {
      console.log(t("main_js.ws_closed_code", { code: e.code }));

      // GESTIONE CODICI DI CHIUSURA
      if (e.code === 1008 || e.code === 1002) {
        console.error(t("main_js.ws_policy_violation"));
        setStatus("error");
        shouldReconnect.current = false;
        localStorage.removeItem("airis_auth_token");
        setTimeout(() => {
          window.location.reload();
        }, 1000);
        return;
      }

      setStatus("disconnected");
      ws.current = null;

      if (heartbeatInterval.current) {
        clearInterval(heartbeatInterval.current);
        heartbeatInterval.current = null;
      }

      // Riconnessione automatica solo se il componente è ancora montato
      if (shouldReconnect.current && isMounted.current) {
        reconnectTimeout.current = setTimeout(() => {
          console.log(t("main_js.ws_reconnect_attempt"));
          connect();
        }, 3000);
      }
    };
  },[config, customUrl, customToken]);

  // --- [FIX CRITICO] STABILIZZAZIONE DIPENDENZE ---
  // Estraiamo i valori primitivi per evitare che la ricreazione dell'oggetto config
  // da parte del componente padre inneschi un ciclo infinito di disconnect/connect.
  const configDep = config ? `${config.protocol}://${config.ip}:${config.port}` : "null";

  useEffect(() => {
    isMounted.current = true;
    shouldReconnect.current = true;
    connectionAttempts.current = 0;
    
    // IMPORTANTE: Connetti solo se c'è un config valido o un customUrl
    if (config || customUrl) {
      connect();
    }
    
    return () => {
      isMounted.current = false;
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configDep, customUrl, customToken, connect, disconnect]); // Reagisci ai cambiamenti reali

  const sendMessage = useCallback((message: string) => {
    console.log(t("main_js.ws_send_message_called"));
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      try {
        ws.current.send(message);
      } catch (error) {
        console.error(t("main_js.ws_send_error"), error);
      }
    } else {
      console.warn(t("main_js.ws_not_ready"));
    }
  }, []);

  return { status, latestMessage, connect, disconnect, sendMessage };
};