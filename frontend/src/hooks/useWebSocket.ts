// SEPEHR Frontend — WebSocket Hook

"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useAuthStore } from "@/stores/authStore";
import { useMessengerStore } from "@/stores/messengerStore";
import { useAlertStore } from "@/stores/alertStore";
import type { WSEvent, WSNewMessagePayload, WSTypingPayload, WSReadReceiptPayload, EmergencyAlert } from "@/types";

const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

type ConnectionState = "connecting" | "connected" | "disconnected" | "error";

const RECONNECT_DELAYS = [1000, 2000, 5000, 10000, 30000];

export function useWebSocket() {
  const { accessToken, isAuthenticated } = useAuthStore();
  const { addMessage, updateMessageStatus, setTyping } = useMessengerStore();
  const { addAlert } = useAlertStore();

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimerRef = useRef<NodeJS.Timeout | null>(null);

  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");

  const clearTimers = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
  }, []);

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const data: WSEvent = JSON.parse(event.data);

        switch (data.type) {
          case "connected":
            setConnectionState("connected");
            reconnectAttemptsRef.current = 0;
            break;

          case "ping":
            wsRef.current?.send(JSON.stringify({ type: "pong" }));
            break;

          case "new_message": {
            const payload = data.payload as WSNewMessagePayload;
            addMessage(payload.conversation_id, payload.message);
            // Show browser notification if tab not focused
            if (document.hidden && Notification.permission === "granted") {
              const senderName = payload.message.sender?.display_name || "New message";
              new Notification(senderName, {
                body: payload.message.content_preview || "New message",
                icon: "/icons/icon-192x192.png",
                tag: payload.conversation_id,
              });
            }
            break;
          }

          case "typing": {
            const payload = data.payload as WSTypingPayload;
            setTyping(payload.conversation_id, payload.user_id, true);
            // Clear typing indicator after 3 seconds
            setTimeout(() => {
              setTyping(payload.conversation_id, payload.user_id, false);
            }, 3000);
            break;
          }

          case "read_receipt": {
            const payload = data.payload as WSReadReceiptPayload;
            updateMessageStatus(payload.message_id, "read");
            break;
          }

          case "emergency_alert": {
            const alert = data.payload as EmergencyAlert;
            addAlert(alert);
            // Vibrate for critical alerts
            if (alert.severity === "critical" && navigator.vibrate) {
              navigator.vibrate([300, 100, 300, 100, 300]);
            }
            break;
          }

          default:
            break;
        }
      } catch {
        // Malformed message — ignore silently
      }
    },
    [addMessage, updateMessageStatus, setTyping, addAlert]
  );

  const connect = useCallback(() => {
    if (!accessToken || !isAuthenticated) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setConnectionState("connecting");

    const ws = new WebSocket(`${WS_BASE_URL}/ws?token=${accessToken}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionState("connected");
      reconnectAttemptsRef.current = 0;
      // Heartbeat to keep connection alive
      heartbeatTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 25000);
    };

    ws.onmessage = handleMessage;

    ws.onerror = () => {
      setConnectionState("error");
    };

    ws.onclose = (event) => {
      clearTimers();
      setConnectionState("disconnected");

      // Don't reconnect on explicit auth failures
      if (event.code === 4001 || event.code === 4003) {
        return;
      }

      // Exponential backoff reconnection
      const delay =
        RECONNECT_DELAYS[
          Math.min(reconnectAttemptsRef.current, RECONNECT_DELAYS.length - 1)
        ];
      reconnectAttemptsRef.current += 1;

      reconnectTimerRef.current = setTimeout(() => {
        connect();
      }, delay);
    };
  }, [accessToken, isAuthenticated, handleMessage, clearTimers]);

  const disconnect = useCallback(() => {
    clearTimers();
    if (wsRef.current) {
      wsRef.current.close(1000, "User logout");
      wsRef.current = null;
    }
    setConnectionState("disconnected");
  }, [clearTimers]);

  const sendTyping = useCallback((conversationId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "typing",
          payload: { conversation_id: conversationId },
        })
      );
    }
  }, []);

  const sendReadReceipt = useCallback(
    (conversationId: string, messageId: string) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: "read_receipt",
            payload: { conversation_id: conversationId, message_id: messageId },
          })
        );
      }
    },
    []
  );

  // Connect when authenticated
  useEffect(() => {
    if (isAuthenticated && accessToken) {
      connect();
    } else {
      disconnect();
    }
    return () => {
      clearTimers();
    };
  }, [isAuthenticated, accessToken]);

  // Reconnect on network recovery
  useEffect(() => {
    const handleOnline = () => {
      if (isAuthenticated && connectionState !== "connected") {
        reconnectAttemptsRef.current = 0;
        connect();
      }
    };
    window.addEventListener("online", handleOnline);
    return () => window.removeEventListener("online", handleOnline);
  }, [isAuthenticated, connectionState, connect]);

  return {
    connectionState,
    isConnected: connectionState === "connected",
    sendTyping,
    sendReadReceipt,
    disconnect,
    reconnect: connect,
  };
}
