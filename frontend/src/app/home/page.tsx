// SEPEHR Frontend — Home Page (Crisis Dashboard)

"use client";

import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { BottomNav } from "@/components/layout/BottomNav";
import { AlertBanner } from "@/components/alerts/AlertBanner";
import { ConnectivityBar } from "@/components/layout/ConnectivityBar";
import { useAlertStore, useConnectivityStore } from "@/stores/alertStore";
import { useMessengerStore } from "@/stores/messengerStore";
import { useAuthStore } from "@/stores/authStore";
import { get } from "@/lib/api";
import type { EmergencyAlert, NewsPost, Conversation } from "@/types";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";

export default function HomePage() {
  const { user } = useAuthStore();
  const { alerts, setAlerts } = useAlertStore();
  const { conversations } = useMessengerStore();
  const { status: connectivityStatus } = useConnectivityStore();

  // Fetch active alerts
  const { data: alertsData } = useQuery({
    queryKey: ["alerts", "active"],
    queryFn: () => get<EmergencyAlert[]>("/api/v1/alerts?active_only=true&limit=5"),
    onSuccess: setAlerts,
    refetchInterval: 30000, // Poll every 30s
    staleTime: 15000,
  } as any);

  // Fetch latest news
  const { data: latestNews } = useQuery({
    queryKey: ["news", "home"],
    queryFn: () => get<NewsPost[]>("/api/v1/news/posts?limit=5"),
    staleTime: 60000,
  });

  const activeAlerts = (alertsData || alerts).filter((a) => a.is_active);
  const criticalAlerts = activeAlerts.filter((a) => a.severity === "critical");
  const recentConversations = conversations.slice(0, 3);

  const greeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "صبح بخیر";
    if (hour < 17) return "ظهر بخیر";
    return "عصر بخیر";
  };

  return (
    <div className="min-h-screen bg-bg">
      <ConnectivityBar />

      {/* Header */}
      <div className="px-4 pt-14 pb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-primary-subtle text-sm">{greeting()}</p>
            <h1 className="text-xl font-semibold text-primary">
              {user?.display_name || "کاربر"}
            </h1>
          </div>
          <div className="w-10 h-10 rounded-full bg-accent-dim flex items-center justify-center border border-accent/20">
            <span className="text-accent font-semibold text-sm">
              {user?.display_name?.charAt(0) || "؟"}
            </span>
          </div>
        </div>
      </div>

      <div className="px-4 pb-24 space-y-6">
        {/* ── Critical Alerts Banner ── */}
        <AnimatePresence>
          {criticalAlerts.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
            >
              {criticalAlerts.slice(0, 2).map((alert) => (
                <AlertBanner key={alert.id} alert={alert} />
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── All Alerts Section ── */}
        {activeAlerts.length > 0 && (
          <Section
            title="هشدارهای فعال"
            count={activeAlerts.length}
            href="/home/alerts"
          >
            <div className="space-y-2">
              {activeAlerts.slice(0, 3).map((alert, i) => (
                <motion.div
                  key={alert.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className={`rounded-xl p-3.5 border ${getSeverityClass(alert.severity)}`}
                >
                  <div className="flex items-start gap-3">
                    <SeverityIcon severity={alert.severity} />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm leading-snug">{alert.title}</p>
                      <p className="text-xs opacity-70 mt-0.5 line-clamp-2">{alert.content}</p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </Section>
        )}

        {/* ── Latest News ── */}
        <Section title="آخرین اخبار" href="/news">
          <div className="space-y-2">
            {latestNews && latestNews.length > 0 ? (
              latestNews.map((post, i) => (
                <motion.div
                  key={post.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                >
                  <Link href={`/news/${post.id}`}>
                    <div className="glass-card p-3.5 hover:bg-bg-elevated transition-colors">
                      <div className="flex gap-3">
                        {post.cover_image_url && (
                          <div className="w-16 h-16 rounded-xl overflow-hidden bg-bg-elevated flex-shrink-0">
                            <img
                              src={post.cover_image_url}
                              alt=""
                              className="w-full h-full object-cover"
                            />
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium leading-snug line-clamp-2">
                            {post.title}
                          </p>
                          {post.summary && (
                            <p className="text-xs text-primary-subtle mt-1 line-clamp-2">
                              {post.summary}
                            </p>
                          )}
                          <p className="text-[10px] text-primary-subtle mt-1.5">
                            {post.published_at
                              ? formatDistanceToNow(new Date(post.published_at), {
                                  addSuffix: true,
                                })
                              : ""}
                          </p>
                        </div>
                      </div>
                    </div>
                  </Link>
                </motion.div>
              ))
            ) : (
              <EmptyState icon="📰" text="خبری یافت نشد" />
            )}
          </div>
        </Section>

        {/* ── Recent Messages ── */}
        <Section title="پیام‌های اخیر" href="/messenger">
          <div className="space-y-2">
            {recentConversations.length > 0 ? (
              recentConversations.map((conv, i) => (
                <motion.div
                  key={conv.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                >
                  <Link href={`/messenger/${conv.id}`}>
                    <div className="glass-card p-3.5 hover:bg-bg-elevated transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-accent-dim flex items-center justify-center flex-shrink-0 text-sm font-semibold text-accent">
                          {(conv.name || "؟").charAt(0)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <p className="text-sm font-medium">{conv.name || "مکالمه"}</p>
                            {conv.last_message_at && (
                              <span className="text-[10px] text-primary-subtle">
                                {formatDistanceToNow(new Date(conv.last_message_at), {
                                  addSuffix: false,
                                })}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-primary-subtle truncate mt-0.5">
                            {conv.last_message?.content_preview || "..."}
                          </p>
                        </div>
                        {conv.unread_count > 0 && (
                          <span className="min-w-[20px] h-5 px-1.5 rounded-full bg-accent text-white text-[10px] font-semibold flex items-center justify-center">
                            {conv.unread_count}
                          </span>
                        )}
                      </div>
                    </div>
                  </Link>
                </motion.div>
              ))
            ) : (
              <EmptyState icon="💬" text="مکالمه‌ای موجود نیست" />
            )}
          </div>
        </Section>

        {/* ── System Status ── */}
        <Section title="وضعیت سیستم">
          <div className="glass-card p-4">
            <div className="grid grid-cols-2 gap-3">
              <StatusItem
                label="اتصال شبکه"
                value={connectivityStatus === "online" ? "متصل" : "قطع"}
                color={connectivityStatus === "online" ? "success" : "danger"}
              />
              <StatusItem label="سرور" value="فعال" color="success" />
              <StatusItem label="پیام‌رسانی" value="عملیاتی" color="success" />
              <StatusItem label="نقشه" value="آفلاین موجود" color="warning" />
            </div>
          </div>
        </Section>
      </div>

      <BottomNav />
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function Section({
  title,
  count,
  href,
  children,
}: {
  title: string;
  count?: number;
  href?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <h2 className="font-semibold text-primary">{title}</h2>
          {count !== undefined && count > 0 && (
            <span className="min-w-[20px] h-5 px-1.5 rounded-full bg-danger/20 text-danger text-[10px] font-semibold flex items-center justify-center">
              {count}
            </span>
          )}
        </div>
        {href && (
          <Link href={href} className="text-xs text-accent">
            همه
          </Link>
        )}
      </div>
      {children}
    </div>
  );
}

function StatusItem({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: "success" | "danger" | "warning";
}) {
  const colors = {
    success: "text-success",
    danger: "text-danger",
    warning: "text-warning",
  };
  const dots = {
    success: "bg-success",
    danger: "bg-danger",
    warning: "bg-warning animate-pulse",
  };
  return (
    <div className="flex items-center gap-2">
      <div className={`w-1.5 h-1.5 rounded-full ${dots[color]}`} />
      <div>
        <p className="text-[10px] text-primary-subtle">{label}</p>
        <p className={`text-xs font-medium ${colors[color]}`}>{value}</p>
      </div>
    </div>
  );
}

function EmptyState({ icon, text }: { icon: string; text: string }) {
  return (
    <div className="glass-card p-6 flex flex-col items-center gap-2 text-center">
      <span className="text-2xl">{icon}</span>
      <p className="text-sm text-primary-subtle">{text}</p>
    </div>
  );
}

function getSeverityClass(severity: string) {
  const map: Record<string, string> = {
    info: "bg-accent-dim border-accent/30 text-accent",
    warning: "bg-warning-muted border-warning/30 text-warning",
    danger: "bg-danger-muted border-danger/30 text-danger",
    critical:
      "bg-danger-muted border-danger/50 text-danger shadow-danger-glow animate-alert-pulse",
  };
  return map[severity] || map.info;
}

function SeverityIcon({ severity }: { severity: string }) {
  const icons: Record<string, string> = {
    info: "ℹ",
    warning: "⚠",
    danger: "🚨",
    critical: "🔴",
  };
  return (
    <span className="text-base flex-shrink-0 mt-0.5">{icons[severity] || "ℹ"}</span>
  );
}
