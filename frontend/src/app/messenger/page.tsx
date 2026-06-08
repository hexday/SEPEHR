// SEPEHR Frontend — Messenger Page

"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { BottomNav } from "@/components/layout/BottomNav";
import { useMessengerStore } from "@/stores/messengerStore";
import { get } from "@/lib/api";
import type { Conversation } from "@/types";

export default function MessengerPage() {
  const { conversations, setConversations } = useMessengerStore();

  const { data, isLoading } = useQuery({
    queryKey: ["conversations"],
    queryFn: () => get<Conversation[]>("/api/v1/messenger/conversations"),
    onSuccess: setConversations,
    staleTime: 10000,
  } as any);

  const displayConversations = data || conversations;

  return (
    <div className="min-h-screen bg-bg">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-bg/80 backdrop-blur-xl border-b border-border">
        <div className="flex items-center justify-between px-4 pt-14 pb-4">
          <h1 className="text-xl font-semibold">پیام‌ها</h1>
          <Link
            href="/messenger/new"
            className="w-9 h-9 rounded-xl bg-accent flex items-center justify-center"
          >
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24">
              <path
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
          </Link>
        </div>
      </div>

      <div className="content-pb">
        {isLoading ? (
          <ConversationSkeleton />
        ) : displayConversations.length === 0 ? (
          <EmptyMessenger />
        ) : (
          <div className="divide-y divide-border">
            {displayConversations.map((conv, i) => (
              <motion.div
                key={conv.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
              >
                <ConversationRow conversation={conv} />
              </motion.div>
            ))}
          </div>
        )}
      </div>

      <BottomNav />
    </div>
  );
}

function ConversationRow({ conversation: conv }: { conversation: Conversation }) {
  const isGroup = conv.type === "group";
  const initials = (conv.name || "؟").charAt(0);
  const lastTime = conv.last_message_at
    ? formatDistanceToNow(new Date(conv.last_message_at), { addSuffix: false })
    : "";

  return (
    <Link href={`/messenger/${conv.id}`}>
      <div className="flex items-center gap-3 px-4 py-3.5 hover:bg-bg-surface/50 transition-colors active:bg-bg-card">
        {/* Avatar */}
        <div className="relative flex-shrink-0">
          <div className="w-12 h-12 rounded-full bg-accent-dim border border-accent/15 flex items-center justify-center">
            {conv.avatar_url ? (
              <img
                src={conv.avatar_url}
                alt=""
                className="w-full h-full rounded-full object-cover"
              />
            ) : (
              <span className="text-accent font-semibold text-base">{initials}</span>
            )}
          </div>
          {isGroup && (
            <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full bg-bg-surface border border-border flex items-center justify-center">
              <svg className="w-2.5 h-2.5 text-primary-subtle" fill="currentColor" viewBox="0 0 24 24">
                <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
              </svg>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <span className="font-medium text-sm text-primary truncate">
              {conv.name || "مکالمه"}
            </span>
            <span className="text-[10px] text-primary-subtle flex-shrink-0 ml-2">
              {lastTime}
            </span>
          </div>
          <div className="flex items-center justify-between mt-0.5">
            <p className="text-xs text-primary-subtle truncate">
              {conv.last_message?.is_deleted
                ? "پیام حذف شد"
                : conv.last_message?.content_preview || "هنوز پیامی نیست"}
            </p>
            {conv.unread_count > 0 && (
              <span className="min-w-[18px] h-[18px] px-1 rounded-full bg-accent text-white text-[10px] font-bold flex items-center justify-center flex-shrink-0 ml-2">
                {conv.unread_count > 99 ? "99+" : conv.unread_count}
              </span>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}

function ConversationSkeleton() {
  return (
    <div className="divide-y divide-border">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 px-4 py-3.5">
          <div className="w-12 h-12 rounded-full shimmer flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="h-3.5 w-32 rounded shimmer" />
            <div className="h-3 w-48 rounded shimmer" />
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyMessenger() {
  return (
    <div className="flex flex-col items-center justify-center px-8 pt-24 text-center">
      <div className="w-20 h-20 rounded-3xl bg-accent-dim flex items-center justify-center mb-6">
        <svg className="w-10 h-10 text-accent" fill="none" viewBox="0 0 24 24">
          <path
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
      </div>
      <h2 className="text-lg font-semibold mb-2">مکالمه‌ای وجود ندارد</h2>
      <p className="text-sm text-primary-subtle mb-8">
        برای شروع، یک مکالمه جدید ایجاد کنید
      </p>
      <Link
        href="/messenger/new"
        className="px-6 py-3 rounded-xl bg-accent text-white font-medium text-sm"
      >
        شروع مکالمه
      </Link>
    </div>
  );
}
