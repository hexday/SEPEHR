// SEPEHR Frontend — Connectivity Status Bar

"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useConnectivityStore } from "@/stores/alertStore";

export function ConnectivityBar() {
  const { status } = useConnectivityStore();
  const isOffline = status === "offline";
  const isDegraded = status === "degraded";

  return (
    <AnimatePresence>
      {(isOffline || isDegraded) && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className={`fixed top-0 left-0 right-0 z-50 overflow-hidden ${
            isOffline ? "bg-danger/90" : "bg-warning/90"
          } backdrop-blur-sm`}
        >
          <div className="pt-safe flex items-center justify-center gap-2 py-2 px-4">
            <div
              className={`w-1.5 h-1.5 rounded-full ${
                isOffline ? "bg-white" : "bg-white animate-pulse"
              }`}
            />
            <p className="text-white text-xs font-medium">
              {isOffline
                ? "اتصال اینترنت قطع است — حالت آفلاین"
                : "اتصال ناپایدار — داده‌ها ممکن است قدیمی باشند"}
            </p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
