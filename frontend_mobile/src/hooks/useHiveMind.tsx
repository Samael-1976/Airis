import { useState, useEffect } from 'react';
import { ServerConfig, HiveDevice } from '@/types';
import { getBaseUrl, getHeaders } from '@/lib/api';
import { useTranslation } from "@/contexts/TranslationContext";

export const useHiveMind = (serverConfig: ServerConfig | null) => {
  const { t } = useTranslation();
  const [deviceId, setDeviceId] = useState<string>("");
  const [deviceInfo, setDeviceInfo] = useState<HiveDevice | null>(null);
  const [isRegistered, setIsRegistered] = useState(false);

  // 1. Inizializzazione ID Locale (Persistente)
  useEffect(() => {
    let id = localStorage.getItem("airis_device_id");
    if (!id) {
      // Fallback per browser che non supportano crypto.randomUUID
      if (typeof crypto !== 'undefined' && crypto.randomUUID) {
        id = crypto.randomUUID();
      } else {
        id = 'dev-' + Math.random().toString(36).substr(2, 9);
      }
      localStorage.setItem("airis_device_id", id);
    }
    setDeviceId(id);
  }, []);

  // 2. Heartbeat & Sync Loop
  useEffect(() => {
    if (!serverConfig || !deviceId) return;

    const baseUrl = getBaseUrl(serverConfig);
    const headers = getHeaders();

    const sync = async () => {
      try {
        // A. Invio Heartbeat (Sono vivo!)
        await fetch(`${baseUrl}/api/hive/heartbeat`, {
            method: 'POST',
            headers: { ...headers, 'Content-Type': 'application/json' },
            body: JSON.stringify({ device_id: deviceId })
        });

        // B. Recupero Info su se stessi (Chi sono? Sono registrato?)
        const res = await fetch(`${baseUrl}/api/hive/devices`, { headers });
        if (res.ok) {
            const data = await res.json();
            const devices = data.devices || {};
            
            if (devices[deviceId]) {
                setDeviceInfo(devices[deviceId]);
                setIsRegistered(true);
            } else {
                setIsRegistered(false);
                setDeviceInfo(null);
            }
        }
      } catch (e) {
        console.error(t("hive_dashboard.err_sync"), e);
      }
    };

    // Esegui subito all'avvio
    sync();

    // Loop ogni 10 secondi per mantenere lo stato online
    const interval = setInterval(sync, 10000);

    return () => clearInterval(interval);
  }, [serverConfig, deviceId]);

  return {
    deviceId,
    deviceType: deviceInfo?.type || 'mobile', // Default 'mobile' se non registrato
    deviceName: deviceInfo?.name || t("hive_dashboard.no_devices"),
    isRegistered
  };
};