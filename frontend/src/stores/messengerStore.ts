// SEPEHR Frontend — Messenger Store (Zustand)

import { create } from "zustand";
import type { Conversation, Message, MessageStatus } from "@/types";

interface TypingState {
  [conversationId: string]: Set<string>; // set of user IDs currently typing
}

interface MessengerState {
  conversations: Conversation[];
  messages: Record<string, Message[]>; // conversationId -> messages
  activeConversationId: string | null;
  typingUsers: TypingState;
  unreadCounts: Record<string, number>;

  setConversations: (conversations: Conversation[]) => void;
  addConversation: (conversation: Conversation) => void;
  updateConversation: (id: string, updates: Partial<Conversation>) => void;

  setMessages: (conversationId: string, messages: Message[]) => void;
  prependMessages: (conversationId: string, messages: Message[]) => void;
  addMessage: (conversationId: string, message: Message) => void;
  updateMessage: (messageId: string, updates: Partial<Message>) => void;
  deleteMessage: (messageId: string) => void;
  updateMessageStatus: (messageId: string, status: MessageStatus) => void;

  setActiveConversation: (id: string | null) => void;
  setTyping: (conversationId: string, userId: string, isTyping: boolean) => void;
  getTypingUsers: (conversationId: string) => string[];
  incrementUnread: (conversationId: string) => void;
  clearUnread: (conversationId: string) => void;
}

export const useMessengerStore = create<MessengerState>()((set, get) => ({
  conversations: [],
  messages: {},
  activeConversationId: null,
  typingUsers: {},
  unreadCounts: {},

  setConversations: (conversations) => set({ conversations }),

  addConversation: (conversation) =>
    set((state) => ({
      conversations: [
        conversation,
        ...state.conversations.filter((c) => c.id !== conversation.id),
      ],
    })),

  updateConversation: (id, updates) =>
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, ...updates } : c
      ),
    })),

  setMessages: (conversationId, messages) =>
    set((state) => ({
      messages: { ...state.messages, [conversationId]: messages },
    })),

  prependMessages: (conversationId, messages) =>
    set((state) => ({
      messages: {
        ...state.messages,
        [conversationId]: [
          ...messages,
          ...(state.messages[conversationId] || []),
        ],
      },
    })),

  addMessage: (conversationId, message) => {
    set((state) => {
      const existing = state.messages[conversationId] || [];
      // Deduplicate by ID
      if (existing.some((m) => m.id === message.id)) return state;

      const updated = [...existing, message];
      const { activeConversationId, unreadCounts } = state;

      // Increment unread if this isn't the active conversation
      const newUnread = { ...unreadCounts };
      if (activeConversationId !== conversationId) {
        newUnread[conversationId] = (newUnread[conversationId] || 0) + 1;
      }

      // Update conversation's last_message_at
      const updatedConversations = state.conversations.map((c) =>
        c.id === conversationId
          ? {
              ...c,
              last_message_at: message.created_at,
              last_message: message,
              unread_count: newUnread[conversationId] || 0,
            }
          : c
      );

      // Sort conversations by last activity
      updatedConversations.sort((a, b) => {
        const aTime = a.last_message_at || a.created_at;
        const bTime = b.last_message_at || b.created_at;
        return new Date(bTime).getTime() - new Date(aTime).getTime();
      });

      return {
        messages: { ...state.messages, [conversationId]: updated },
        unreadCounts: newUnread,
        conversations: updatedConversations,
      };
    });
  },

  updateMessage: (messageId, updates) =>
    set((state) => {
      const newMessages = { ...state.messages };
      for (const convId in newMessages) {
        newMessages[convId] = newMessages[convId].map((m) =>
          m.id === messageId ? { ...m, ...updates } : m
        );
      }
      return { messages: newMessages };
    }),

  deleteMessage: (messageId) =>
    set((state) => {
      const newMessages = { ...state.messages };
      for (const convId in newMessages) {
        newMessages[convId] = newMessages[convId].map((m) =>
          m.id === messageId
            ? { ...m, is_deleted: true, content: undefined, content_preview: "[deleted]" }
            : m
        );
      }
      return { messages: newMessages };
    }),

  updateMessageStatus: (messageId, status) => {
    const { updateMessage } = get();
    updateMessage(messageId, { status });
  },

  setActiveConversation: (id) => {
    set({ activeConversationId: id });
    if (id) {
      // Clear unread when activating conversation
      set((state) => ({
        unreadCounts: { ...state.unreadCounts, [id]: 0 },
        conversations: state.conversations.map((c) =>
          c.id === id ? { ...c, unread_count: 0 } : c
        ),
      }));
    }
  },

  setTyping: (conversationId, userId, isTyping) =>
    set((state) => {
      const current = new Set(state.typingUsers[conversationId] || []);
      if (isTyping) {
        current.add(userId);
      } else {
        current.delete(userId);
      }
      return {
        typingUsers: { ...state.typingUsers, [conversationId]: current },
      };
    }),

  getTypingUsers: (conversationId) => {
    const state = get();
    return Array.from(state.typingUsers[conversationId] || new Set());
  },

  incrementUnread: (conversationId) =>
    set((state) => ({
      unreadCounts: {
        ...state.unreadCounts,
        [conversationId]: (state.unreadCounts[conversationId] || 0) + 1,
      },
    })),

  clearUnread: (conversationId) =>
    set((state) => ({
      unreadCounts: { ...state.unreadCounts, [conversationId]: 0 },
    })),
}));
