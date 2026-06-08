// SEPEHR Frontend — Bottom Navigation

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { useAlertStore } from "@/stores/alertStore";
import { useMessengerStore } from "@/stores/messengerStore";

const navItems = [
  {
    href: "/home",
    label: "خانه",
    labelEn: "Home",
    icon: (active: boolean) => (
      <svg className="w-6 h-6" fill={active ? "currentColor" : "none"} viewBox="0 0 24 24">
        <path
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={active ? 0 : 1.5}
          d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z"
        />
        {active ? null : (
          <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 21V12h6v9" />
        )}
      </svg>
    ),
  },
  {
    href: "/messenger",
    label: "پیام",
    labelEn: "Messenger",
    icon: (active: boolean) => (
      <svg className="w-6 h-6" fill={active ? "currentColor" : "none"} viewBox="0 0 24 24">
        <path
          stroke={active ? "none" : "currentColor"}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
        />
      </svg>
    ),
  },
  {
    href: "/news",
    label: "خبر",
    labelEn: "News",
    icon: (active: boolean) => (
      <svg className="w-6 h-6" fill={active ? "currentColor" : "none"} viewBox="0 0 24 24">
        <path
          stroke={active ? "none" : "currentColor"}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"
        />
      </svg>
    ),
  },
  {
    href: "/map",
    label: "نقشه",
    labelEn: "Map",
    icon: (active: boolean) => (
      <svg className="w-6 h-6" fill={active ? "currentColor" : "none"} viewBox="0 0 24 24">
        <path
          stroke={active ? "none" : "currentColor"}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6-13l6 3m0 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4"
        />
      </svg>
    ),
  },
];

export function BottomNav() {
  const pathname = usePathname();
  const { alerts } = useAlertStore();
  const { conversations } = useMessengerStore();

  const activeAlerts = alerts.filter((a) => a.is_active).length;
  const totalUnread = conversations.reduce((sum, c) => sum + (c.unread_count || 0), 0);

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-bg-surface/90 backdrop-blur-xl border-t border-border bottom-nav-height">
      <div className="flex items-center justify-around h-16">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            pathname.startsWith(item.href + "/");

          const badge =
            item.href === "/home"
              ? activeAlerts
              : item.href === "/messenger"
              ? totalUnread
              : 0;

          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex flex-col items-center gap-1 px-4 py-1 relative"
            >
              <div className="relative">
                <motion.div
                  animate={{
                    color: isActive ? "#4F8CFF" : "#6B7585",
                    scale: isActive ? 1.05 : 1,
                  }}
                  transition={{ duration: 0.15 }}
                >
                  {item.icon(isActive)}
                </motion.div>

                {badge > 0 && (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-danger text-white text-[10px] font-semibold flex items-center justify-center leading-none"
                  >
                    {badge > 99 ? "99+" : badge}
                  </motion.span>
                )}
              </div>

              <span
                className={`text-[10px] font-medium transition-colors ${
                  isActive ? "text-accent" : "text-primary-subtle"
                }`}
              >
                {item.label}
              </span>

              {isActive && (
                <motion.div
                  layoutId="nav-indicator"
                  className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-accent rounded-full"
                />
              )}
            </Link>
          );
        })}
      </div>
      {/* Safe area padding */}
      <div className="h-safe bg-bg-surface/90" />
    </nav>
  );
}
