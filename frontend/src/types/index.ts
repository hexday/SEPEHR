// SEPEHR Frontend — Core Domain Types

export type UserRole = "user" | "moderator" | "publisher" | "administrator";
export type MessageType = "text" | "voice" | "image" | "file" | "location" | "system";
export type MessageStatus = "sent" | "delivered" | "read" | "failed";
export type ConversationType = "direct" | "group";
export type MemberRole = "member" | "admin";
export type NewsPostStatus = "draft" | "published" | "archived";
export type AlertSeverity = "info" | "warning" | "danger" | "critical";
export type MapPointType =
  | "hospital"
  | "shelter"
  | "aid_center"
  | "safe_route"
  | "danger_zone"
  | "checkpoint"
  | "water"
  | "food";

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
  role: UserRole;
  is_active: boolean;
  last_seen: string | null;
  public_key: string | null;
  created_at?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// ── Messenger ─────────────────────────────────────────────────────────────────

export interface ConversationMember {
  user: User;
  role: MemberRole;
  joined_at: string;
  is_muted: boolean;
}

export interface Conversation {
  id: string;
  type: ConversationType;
  name: string | null;
  avatar_url: string | null;
  last_message_at: string | null;
  created_at: string;
  member_count: number;
  last_message: Message | null;
  unread_count: number;
  members?: ConversationMember[];
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_id: string;
  sender?: User;
  type: MessageType;
  content_encrypted: string | null;
  iv: string | null;
  content_preview: string | null;
  file_key: string | null;
  file_url: string | null;
  file_size: number | null;
  file_mime: string | null;
  file_name: string | null;
  latitude: number | null;
  longitude: number | null;
  reply_to_id: string | null;
  is_deleted: boolean;
  created_at: string;
  status: MessageStatus | null;
  // Client-side decrypted content
  content?: string;
}

export interface MessageListResponse {
  messages: Message[];
  has_more: boolean;
  cursor: string | null;
}

// ── News ──────────────────────────────────────────────────────────────────────

export interface NewsServer {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  icon_url: string | null;
  is_active: boolean;
  sort_order: number;
  category_count: number;
}

export interface NewsCategory {
  id: string;
  server_id: string;
  name: string;
  slug: string;
  description: string | null;
  color: string | null;
  sort_order: number;
}

export interface NewsPost {
  id: string;
  server_id: string;
  category_id: string | null;
  title: string;
  slug: string;
  summary: string | null;
  cover_image_url: string | null;
  content?: string;
  video_url?: string | null;
  status: NewsPostStatus;
  published_at: string | null;
  created_at: string;
  publisher?: User | null;
  category?: NewsCategory | null;
}

// ── Alerts ────────────────────────────────────────────────────────────────────

export interface EmergencyAlert {
  id: string;
  title: string;
  content: string;
  severity: AlertSeverity;
  area_geojson: object | null;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
}

// ── Map ───────────────────────────────────────────────────────────────────────

export interface MapPoint {
  id: string;
  name: string;
  type: MapPointType;
  latitude: number;
  longitude: number;
  description: string | null;
  contact: string | null;
  address: string | null;
  is_active: boolean;
  created_at: string;
}

// ── WebSocket Events ──────────────────────────────────────────────────────────

export type WSEventType =
  | "connected"
  | "ping"
  | "pong"
  | "new_message"
  | "typing"
  | "read_receipt"
  | "emergency_alert"
  | "error";

export interface WSEvent<T = unknown> {
  type: WSEventType;
  payload?: T;
}

export interface WSNewMessagePayload {
  conversation_id: string;
  message: Message;
}

export interface WSTypingPayload {
  user_id: string;
  conversation_id: string;
  timestamp: string;
}

export interface WSReadReceiptPayload {
  reader_id: string;
  message_id: string;
  conversation_id: string;
}

// ── API Responses ─────────────────────────────────────────────────────────────

export interface APIError {
  error: string;
  message: string;
  detail?: unknown;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// ── UI State ──────────────────────────────────────────────────────────────────

export type ConnectivityStatus = "online" | "offline" | "degraded";

export interface AppNotification {
  id: string;
  type: "alert" | "message" | "info" | "error";
  title: string;
  body?: string;
  timestamp: string;
  read: boolean;
  action_url?: string;
}
