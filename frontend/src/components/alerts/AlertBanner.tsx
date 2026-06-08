// SEPEHR Frontend — Alert Banner Component

"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { EmergencyAlert } from "@/types";

const SEVERITY_CONFIG = {
  info: {
    bg: "bg-accent-dim",
    border: "border-accent/30",
    text: "text-accent",
    icon: "ℹ️",
    label: "اطلاعیه",
  },
  warning: {
    bg: "bg-warning-muted",
    border: "border-warning/40",
    text: "text-warning",
    icon: "⚠️",
    label: "هشدار",
  },
  danger: {
    bg: "bg-danger-muted",
    border: "border-danger/40",
    text: "text-danger",
    icon: "🚨",
    label: "خطر",
  },
  critical: {
    bg: "bg-danger-muted",
    border: "border-danger/60",
    text: "text-danger",
    icon: "🔴",
    label: "بحرانی",
  },
};

interface AlertBannerProps {
  alert: EmergencyAlert;
  dismissible?: boolean;
}

export function AlertBanner({ alert, dismissible = true }: AlertBannerProps) {
  const [dismissed, setDismissed] = useState(false);
  const config = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.info;

  return (
    <AnimatePresence>
      {!dismissed && (
        <motion.div
          initial={{ opacity: 0, height: 0, marginBottom: 0 }}
          animate={{ opacity: 1, height: "auto", marginBottom: 8 }}
          exit={{ opacity: 0, height: 0, marginBottom: 0 }}
          transition={{ duration: 0.2 }}
          className={`rounded-2xl border ${config.bg} ${config.border} overflow-hidden ${
            alert.severity === "critical" ? "animate-alert-pulse shadow-danger-glow" : ""
          }`}
        >
          <div className="p-3.5 flex items-start gap-3">
            <span className="text-lg flex-shrink-0">{config.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span
                  className={`text-[10px] font-bold uppercase tracking-wide ${config.text}`}
                >
                  {config.label}
                </span>
              </div>
              <p className={`text-sm font-semibold leading-snug ${config.text}`}>
                {alert.title}
              </p>
              <p className={`text-xs mt-1 leading-relaxed opacity-80 ${config.text}`}>
                {alert.content}
              </p>
              {alert.expires_at && (
                <p className={`text-[10px] mt-1.5 opacity-60 ${config.text}`}>
                  انقضا:{" "}
                  {new Date(alert.expires_at).toLocaleString("fa-IR", {
                    hour: "2-digit",
                    minute: "2-digit",
                    month: "short",
                    day: "numeric",
                  })}
                </p>
              )}
            </div>
            {dismissible && (
              <button
                onClick={() => setDismissed(true)}
                className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity ${config.text}`}
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
                  <path
                    stroke="currentColor"
                    strokeLinecap="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ── Full-screen critical alert overlay ───────────────────────────────────────

interface CriticalAlertOverlayProps {
  alert: EmergencyAlert;
  onDismiss: () => void;
}

export function CriticalAlertOverlay({
  alert,
  onDismiss,
}: CriticalAlertOverlayProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-sm flex items-end p-4"
    >
      <motion.div
        initial={{ y: 100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 100, opacity: 0 }}
        transition={{ type: "spring", damping: 25 }}
        className="w-full bg-bg-card border border-danger/50 rounded-3xl overflow-hidden shadow-danger-glow"
      >
        {/* Red top strip */}
        <div className="h-1 bg-danger w-full animate-alert-pulse" />

        <div className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-full bg-danger/20 border border-danger/40 flex items-center justify-center flex-shrink-0">
              <span className="text-2xl">🔴</span>
            </div>
            <div>
              <p className="text-xs font-bold text-danger uppercase tracking-widest mb-0.5">
                هشدار بحرانی
              </p>
              <h2 className="text-lg font-bold text-primary leading-tight">
                {alert.title}
              </h2>
            </div>
          </div>

          <p className="text-sm text-primary-muted leading-relaxed mb-6">
            {alert.content}
          </p>

          <button
            onClick={onDismiss}
            className="w-full h-12 rounded-2xl bg-danger text-white font-semibold text-sm"
          >
            متوجه شدم
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
