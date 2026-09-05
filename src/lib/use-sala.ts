import { useCallback, useEffect, useState } from "react";
import { audienceApi, audienceWsUrl } from "./audience-api";
import type { SalaPlateia } from "./audience-types";

export type SalaConnection = "conectando" | "conectado" | "offline";
function createParticipantId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  }
  // The ID only deduplicates anonymous votes within one transient room. This
  // fallback keeps HTTP/LAN browsers working when Web Crypto is unavailable.
  return `participant-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

export function participantIdFor(code: string) {
  const key = `citygrid-audience-${code}`;
  let value = localStorage.getItem(key);
  if (!value) {
    value = createParticipantId();
    localStorage.setItem(key, value);
  }
  return value;
}
export function useSala(code: string, participantId?: string) {
  const [sala, setSala] = useState<SalaPlateia | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [status, setStatus] = useState<SalaConnection>("conectando");
  const load = useCallback(async () => {
    try {
      setSala(await audienceApi.get(code));
      setErro(null);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Sala indisponível");
    }
  }, [code]);
  useEffect(() => {
    let active = true;
    let socket: WebSocket | undefined;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let delay = 800;
    const connect = () => {
      if (!active) return;
      setStatus("conectando");
      socket = new WebSocket(audienceWsUrl(code, participantId));
      socket.onopen = () => {
        delay = 800;
        setStatus("conectado");
      };
      socket.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as { sala?: SalaPlateia };
          if (data.sala) {
            setSala(data.sala);
            setErro(null);
          }
        } catch {
          setErro("Atualização de sala inválida");
        }
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        if (!active) return;
        setStatus("offline");
        retry = setTimeout(connect, delay);
        delay = Math.min(8000, delay * 1.8);
      };
    };
    void load();
    connect();
    const poll = setInterval(() => void load(), 7000);
    return () => {
      active = false;
      clearInterval(poll);
      if (retry) clearTimeout(retry);
      socket?.close();
    };
  }, [code, load, participantId]);
  return { sala, setSala, erro, status, refresh: load };
}
