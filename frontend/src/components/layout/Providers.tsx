// SEPEHR Frontend — Providers Component

"use client";

import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useAuthStore } from "@/stores/authStore";
import { useConnectivityStore } from "@/stores/alertStore";
import { useWebSocket } from "@/hooks/useWebSocket";
import { getStoredRefreshToken, get, setAccessToken, storeRefreshToken } from "@/lib/api";
import type { User, TokenResponse } from "@/types";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      gcTime: 5 * 60 * 1000, // 5 minutes
      retry: (failureCount, error: unknown) => {
        const status = (error as { response?: { status?: number } })?.response?.status;
        // Don't retry on auth errors
        if (status === 401 || status === 403) return false;
        return failureCount < 2;
      },
      refetchOnWindowFocus: false,
    },
  },
});

function AuthInitializer({ children }: { children: React.ReactNode }) {
  const { setAuth, setLoading, logout } = useAuthStore();
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    const init = async () => {
      const refreshToken = getStoredRefreshToken();
      if (!refreshToken) {
        setLoading(false);
        setInitialized(true);
        return;
      }

      try {
        // Try to refresh tokens on app load
        const tokens = await get<TokenResponse>("/api/v1/auth/refresh", {
          refresh_token: refreshToken,
        });
        // After refresh, get user profile
        setAccessToken(tokens.access_token);
        storeRefreshToken(tokens.refresh_token);
        const user = await get<User>("/api/v1/auth/me");
        setAuth(user, tokens.access_token, tokens.refresh_token);
      } catch {
        logout();
      } finally {
        setInitialized(true);
      }
    };

    init();
  }, []);

  if (!initialized) {
    return (
      <div className="fixed inset-0 bg-bg flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-accent/20 flex items-center justify-center">
            <svg className="w-7 h-7 text-accent" fill="none" viewBox="0 0 24 24">
              <path
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2v-4M9 21H5a2 2 0 01-2-2v-4m0 0h18"
              />
            </svg>
          </div>
          <div className="text-primary-subtle text-sm">سپهر در حال بارگذاری...</div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

function ConnectivityMonitor() {
  const { setStatus } = useConnectivityStore();

  useEffect(() => {
    const handleOnline = () => setStatus("online");
    const handleOffline = () => setStatus("offline");

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // Set initial status
    setStatus(navigator.onLine ? "online" : "offline");

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [setStatus]);

  return null;
}

function WSProvider({ children }: { children: React.ReactNode }) {
  useWebSocket(); // Initialize WebSocket connection
  return <>{children}</>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthInitializer>
        <ConnectivityMonitor />
        <WSProvider>
          {children}
        </WSProvider>
      </AuthInitializer>
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
