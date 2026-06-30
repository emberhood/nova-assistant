"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useNovaStore } from "@/lib/store";
import type { PanelId, WsMessage } from "@/lib/types";

const PANEL_ROUTES: Record<PanelId, string> = {
  dashboard: "/",
  calendar: "/calendar",
  budget: "/budget",
};

function getWsUrl() {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
  if (typeof window === "undefined") return "";
  return `ws://${window.location.hostname}:8000/ws`;
}

// Mounted once in the root layout. Owns the websocket connection that
// streams Nova's live state, plus the initial data fetch + 30-min refresh.
export default function NovaProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const wsRef = useRef<WebSocket | null>(null);

  // Initial fetch + auto-refresh every 30 minutes
  useEffect(() => {
    useNovaStore.getState().refreshUserData();

    const id = setInterval(() => {
      useNovaStore.getState().refreshUserData();
    }, 30 * 60 * 1000);

    return () => clearInterval(id);
  }, []);

  // WebSocket for real-time Nova state
  useEffect(() => {
    let cancelled = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (cancelled) return;
      try {
        const ws = new WebSocket(getWsUrl());

        ws.onmessage = (e) => {
          const msg: WsMessage = JSON.parse(e.data);
          const store = useNovaStore.getState();

          switch (msg.type) {
            case "nova_state":
              store.setNovaState(msg.payload);
              if (msg.heard) store.setLastHeard(msg.heard);
              if (msg.text) store.setLastResponse(msg.text);
              break;
            case "navigate":
              router.push(PANEL_ROUTES[msg.tab]);
              break;
            case "set_user":
              store.setActiveUser(msg.user);
              if (msg.user === "shared") router.push("/");
              break;
            case "refresh_calendar":
              store.invalidateCalCache(store.activeUser);
              store.refreshUserData(store.activeUser);
              break;
          }
        };

        ws.onclose = () => {
          if (!cancelled) retryTimer = setTimeout(connect, 3000);
        };

        wsRef.current = ws;
      } catch {
        if (!cancelled) retryTimer = setTimeout(connect, 3000);
      }
    };

    connect();
    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      wsRef.current?.close();
    };
  }, [router]);

  return <>{children}</>;
}
