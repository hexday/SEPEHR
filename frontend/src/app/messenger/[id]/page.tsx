// SEPEHR Frontend — Conversation Chat View

"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { formatDistanceToNow, format } from "date-fns";
import { useMessengerStore } from "@/stores/messengerStore";
import { useAuthStore } from "@/stores/authStore";
import { useWebSocket } from "@/hooks/useWebSocket";
import { get, post } from "@/lib/api";
import type { Message, MessageListResponse } from "@/types";

export default function ConversationPage() {
  const params = useParams();
  const router = useRouter();
  const conversationId = params.id as string;
  const queryClient = useQueryClient();

  const { user } = useAuthStore();
  const { messages: allMessages, setMessages, addMessage, getTypingUsers } = useMessengerStore();
  const { sendTyping, sendReadReceipt } = useWebSocket();

  const [inputText, setInputText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const conversationMessages = allMessages[conversationId] || [];
  const typingUsers = getTypingUsers(conversationId);

  // Fetch messages (with infinite scroll upward)
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
    queryKey: ["messages", conversationId],
    queryFn: ({ pageParam }) =>
      get<MessageListResponse>(
        `/api/v1/messenger/conversations/${conversationId}/messages?limit=30${pageParam ? `&before_id=${pageParam}` : ""}`
      ),
    getNextPageParam: (lastPage) =>
      lastPage.has_more && lastPage.cursor ? lastPage.cursor : undefined,
    initialPageParam: undefined as string | undefined,
    onSuccess: (data) => {
      const allMsgs = data.pages.flatMap((p) => p.messages);
      setMessages(conversationId, allMsgs);
    },
  } as any);

  // Send message mutation
  const sendMutation = useMutation({
    mutationFn: (text: string) =>
      post<Message>(
        `/api/v1/messenger/conversations/${conversationId}/messages/text`,
        {
          content_encrypted: btoa(unescape(encodeURIComponent(text))), // Base64 — placeholder for real E2E
          iv: crypto.randomUUID().replace(/-/g, "").slice(0, 32),
          content_preview: text.slice(0, 256),
        }
      ),
    onMutate: async (text) => {
      // Optimistic update
      const optimistic: Message = {
        id: `optimistic-${Date.now()}`,
        conversation_id: conversationId,
        sender_id: user!.id,
        sender: user!,
        type: "text",
        content_encrypted: null,
        iv: null,
        content_preview: text,
        content: text,
        file_key: null,
        file_url: null,
        file_size: null,
        file_mime: null,
        file_name: null,
        latitude: null,
        longitude: null,
        reply_to_id: null,
        is_deleted: false,
        created_at: new Date().toISOString(),
        status: "sent",
      };
      addMessage(conversationId, optimistic);
      return { optimistic };
    },
    onSuccess: (realMessage, _text, context) => {
      // Replace optimistic message with real one
      const { updateMessage } = useMessengerStore.getState();
      updateMessage(context!.optimistic.id, realMessage);
    },
  });

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversationMessages.length]);

  // Mark latest message as read
  useEffect(() => {
    const last = conversationMessages[conversationMessages.length - 1];
    if (last && last.sender_id !== user?.id) {
      sendReadReceipt(conversationId, last.id);
    }
  }, [conversationMessages.length]);

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text || isSending) return;
    setInputText("");
    setIsSending(true);
    try {
      await sendMutation.mutateAsync(text);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputText(e.target.value);
    // Debounce typing indicator
    if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
    sendTyping(conversationId);
    typingTimeoutRef.current = setTimeout(() => {}, 2000);
  };

  return (
    <div className="flex flex-col h-screen bg-bg">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 pt-14 pb-3 bg-bg/80 backdrop-blur-xl border-b border-border">
        <button
          onClick={() => router.back()}
          className="w-8 h-8 flex items-center justify-center -ml-1 text-primary-subtle"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24">
            <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="w-9 h-9 rounded-full bg-accent-dim border border-accent/15 flex items-center justify-center flex-shrink-0">
          <span className="text-accent font-semibold text-sm">م</span>
        </div>
        <div className="flex-1">
          <p className="font-semibold text-sm">مکالمه</p>
          {typingUsers.length > 0 && (
            <p className="text-xs text-accent">در حال تایپ...</p>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
        {isFetchingNextPage && (
          <div className="text-center py-2">
            <div className="inline-block w-5 h-5 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
          </div>
        )}

        {conversationMessages.map((msg, idx) => {
          const isOwn = msg.sender_id === user?.id;
          const showTime =
            idx === 0 ||
            new Date(msg.created_at).getTime() -
              new Date(conversationMessages[idx - 1].created_at).getTime() >
              5 * 60 * 1000;

          return (
            <div key={msg.id}>
              {showTime && (
                <div className="text-center py-2">
                  <span className="text-[10px] text-primary-subtle bg-bg-surface px-2 py-0.5 rounded-full">
                    {format(new Date(msg.created_at), "HH:mm")}
                  </span>
                </div>
              )}
              <MessageBubble message={msg} isOwn={isOwn} />
            </div>
          );
        })}

        {/* Typing indicator */}
        <AnimatePresence>
          {typingUsers.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              className="flex items-end gap-2 mr-auto"
            >
              <div className="bg-bg-card rounded-2xl rounded-bl-md px-4 py-3 flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="w-1.5 h-1.5 bg-primary-subtle rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="px-4 py-3 pb-safe bg-bg/90 backdrop-blur-xl border-t border-border">
        <div className="flex items-center gap-2">
          {/* Attach button */}
          <button className="w-9 h-9 rounded-full bg-bg-card flex items-center justify-center text-primary-subtle flex-shrink-0">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24">
              <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
          </button>

          {/* Text input */}
          <div className="flex-1 bg-bg-card rounded-2xl px-4 py-2.5 border border-border focus-within:border-accent/40 transition-colors">
            <input
              ref={inputRef}
              type="text"
              value={inputText}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="پیام بنویسید..."
              className="w-full bg-transparent text-sm outline-none placeholder:text-primary-subtle/40"
              dir="rtl"
            />
          </div>

          {/* Send button */}
          <motion.button
            onClick={handleSend}
            disabled={!inputText.trim() || isSending}
            whileTap={{ scale: 0.9 }}
            className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 transition-colors ${
              inputText.trim()
                ? "bg-accent text-white"
                : "bg-bg-card text-primary-subtle"
            }`}
          >
            <svg className="w-4 h-4 rotate-180" fill="currentColor" viewBox="0 0 24 24">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </motion.button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({
  message: msg,
  isOwn,
}: {
  message: Message;
  isOwn: boolean;
}) {
  const displayText = msg.is_deleted
    ? "پیام حذف شد"
    : msg.content || msg.content_preview || "";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`flex ${isOwn ? "justify-end" : "justify-start"} mb-0.5`}
    >
      <div
        className={`max-w-[80%] px-3.5 py-2.5 rounded-2xl ${
          isOwn
            ? "bg-accent text-white rounded-br-md"
            : "bg-bg-card text-primary rounded-bl-md"
        } ${msg.is_deleted ? "opacity-50 italic" : ""}`}
      >
        {msg.type === "location" ? (
          <div className="flex items-center gap-2 text-sm">
            <span>📍</span>
            <span className={isOwn ? "text-white/90" : "text-primary-subtle"}>
              موقعیت مکانی
            </span>
          </div>
        ) : msg.type === "image" ? (
          <div className="rounded-xl overflow-hidden max-w-[240px]">
            <img src={msg.file_url || ""} alt="" className="w-full" />
          </div>
        ) : msg.type === "voice" ? (
          <VoiceMessage message={msg} isOwn={isOwn} />
        ) : (
          <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">{displayText}</p>
        )}

        <div className={`flex items-center gap-1 mt-1 ${isOwn ? "justify-end" : "justify-start"}`}>
          <span className={`text-[10px] ${isOwn ? "text-white/50" : "text-primary-subtle/50"}`}>
            {format(new Date(msg.created_at), "HH:mm")}
          </span>
          {isOwn && <StatusTick status={msg.status} />}
        </div>
      </div>
    </motion.div>
  );
}

function VoiceMessage({ message: msg, isOwn }: { message: Message; isOwn: boolean }) {
  return (
    <div className="flex items-center gap-2 min-w-[160px]">
      <button className={`w-8 h-8 rounded-full flex items-center justify-center ${isOwn ? "bg-white/20" : "bg-accent/20"}`}>
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path d="M8 5v14l11-7z" />
        </svg>
      </button>
      <div className="flex-1 h-1 bg-white/20 rounded-full overflow-hidden">
        <div className="w-0 h-full bg-white/60 rounded-full" />
      </div>
      <span className={`text-[10px] ${isOwn ? "text-white/60" : "text-primary-subtle"}`}>
        {msg.file_size ? `${Math.round(msg.file_size / 1024)}KB` : ""}
      </span>
    </div>
  );
}

function StatusTick({ status }: { status: string | null | undefined }) {
  if (status === "read") {
    return <span className="text-[10px] text-accent/80">✓✓</span>;
  }
  if (status === "delivered") {
    return <span className="text-[10px] text-white/50">✓✓</span>;
  }
  return <span className="text-[10px] text-white/40">✓</span>;
}
