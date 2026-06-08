// SEPEHR Frontend — Alert Store & Connectivity Store

import { create } from "zustand";
import type { EmergencyAlert, ConnectivityStatus, AppNotification } from "@/types";

// ── Alert Store ───────────────────────────────────────────────────────────────

interface AlertState {
  alerts: EmergencyAlert[];
  hasNewAlert: boolean;

  setAlerts: (alerts: EmergencyAlert[]) => void;
  addAlert: (alert: EmergencyAlert) => void;
  dismissNewAlert: () => void;
  deactivateAlert: (id: string) => void;
}

export const useAlertStore = create<AlertState>()((set) => ({
  alerts: [],
  hasNewAlert: false,

  setAlerts: (alerts) => set({ alerts }),

  addAlert: (alert) =>
    set((state) => ({
      alerts: [alert, ...state.alerts.filter((a) => a.id !== alert.id)],
      hasNewAlert: true,
    })),

  dismissNewAlert: () => set({ hasNewAlert: false }),

  deactivateAlert: (id) =>
    set((state) => ({
      alerts: state.alerts.map((a) =>
        a.id === id ? { ...a, is_active: false } : a
      ),
    })),
}));

// ── Connectivity Store ────────────────────────────────────────────────────────

interface ConnectivityState {
  status: ConnectivityStatus;
  lastOnline: string | null;
  wsConnected: boolean;

  setStatus: (status: ConnectivityStatus) => void;
  setWsConnected: (connected: boolean) => void;
}

export const useConnectivityStore = create<ConnectivityState>()((set) => ({
  status: "online",
  lastOnline: null,
  wsConnected: false,

  setStatus: (status) =>
    set((state) => ({
      status,
      lastOnline:
        status === "offline"
          ? new Date().toISOString()
          : state.lastOnline,
    })),

  setWsConnected: (connected) => set({ wsConnected: connected }),
}));

// ── Notifications Store ───────────────────────────────────────────────────────

interface NotificationState {
  notifications: AppNotification[];
  unreadCount: number;

  addNotification: (notification: Omit<AppNotification, "id" | "timestamp" | "read">) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clearAll: () => void;
}

export const useNotificationStore = create<NotificationState>()((set) => ({
  notifications: [],
  unreadCount: 0,

  addNotification: (notification) =>
    set((state) => {
      const newNotif: AppNotification = {
        ...notification,
        id: crypto.randomUUID(),
        timestamp: new Date().toISOString(),
        read: false,
      };
      return {
        notifications: [newNotif, ...state.notifications].slice(0, 100), // Keep last 100
        unreadCount: state.unreadCount + 1,
      };
    }),

  markAsRead: (id) =>
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      ),
      unreadCount: Math.max(0, state.unreadCount - 1),
    })),

  markAllAsRead: () =>
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),

  clearAll: () => set({ notifications: [], unreadCount: 0 }),
}));
