// SEPEHR Frontend — Axios API Client

import axios, {
  AxiosError,
  AxiosInstance,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";
import type { APIError, TokenResponse } from "@/types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Token Storage ─────────────────────────────────────────────────────────────
// Access token in memory (never localStorage), refresh token via API

let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

// ── API Client ────────────────────────────────────────────────────────────────

export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true, // For refresh token cookie
});

// ── Request Interceptor: Attach token ─────────────────────────────────────────

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor: Handle 401 / Token refresh ──────────────────────────

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError<APIError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      originalRequest.url !== "/api/v1/auth/refresh"
    ) {
      originalRequest._retry = true;

      try {
        if (!refreshPromise) {
          refreshPromise = refreshAccessToken();
        }
        const newToken = await refreshPromise;
        refreshPromise = null;

        if (newToken) {
          setAccessToken(newToken);
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
          }
          return apiClient(originalRequest);
        }
      } catch {
        refreshPromise = null;
        handleAuthFailure();
      }
    }

    return Promise.reject(error);
  }
);

async function refreshAccessToken(): Promise<string | null> {
  // Refresh token is stored in a HttpOnly cookie, sent automatically
  const stored = getStoredRefreshToken();
  if (!stored) return null;

  const response = await axios.post<TokenResponse>(
    `${BASE_URL}/api/v1/auth/refresh`,
    { refresh_token: stored },
    { withCredentials: true }
  );

  const { access_token, refresh_token } = response.data;
  setAccessToken(access_token);
  storeRefreshToken(refresh_token);
  return access_token;
}

function handleAuthFailure() {
  setAccessToken(null);
  clearRefreshToken();
  // Redirect to login
  if (typeof window !== "undefined") {
    window.location.href = "/auth/login";
  }
}

// ── Refresh Token Storage (sessionStorage — cleared on tab close) ──────────────

const REFRESH_TOKEN_KEY = "sepehr_rt";

export function storeRefreshToken(token: string) {
  if (typeof window !== "undefined") {
    sessionStorage.setItem(REFRESH_TOKEN_KEY, token);
  }
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(REFRESH_TOKEN_KEY);
}

export function clearRefreshToken() {
  if (typeof window !== "undefined") {
    sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

// ── Typed API helpers ─────────────────────────────────────────────────────────

export async function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const response = await apiClient.get<T>(url, { params });
  return response.data;
}

export async function post<T>(url: string, data?: unknown): Promise<T> {
  const response = await apiClient.post<T>(url, data);
  return response.data;
}

export async function patch<T>(url: string, data?: unknown): Promise<T> {
  const response = await apiClient.patch<T>(url, data);
  return response.data;
}

export async function del<T>(url: string): Promise<T> {
  const response = await apiClient.delete<T>(url);
  return response.data;
}

export async function upload<T>(
  url: string,
  formData: FormData,
  onProgress?: (percent: number) => void
): Promise<T> {
  const response = await apiClient.post<T>(url, formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    },
  });
  return response.data;
}
