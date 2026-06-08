// SEPEHR Frontend — Auth Store (Zustand)

import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { User } from "@/types";
import {
  setAccessToken,
  storeRefreshToken,
  clearRefreshToken,
  getStoredRefreshToken,
} from "@/lib/api";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  setAuth: (user: User, accessToken: string, refreshToken: string) => void;
  setUser: (user: User) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  subscribeWithSelector((set) => ({
    user: null,
    accessToken: null,
    isAuthenticated: false,
    isLoading: true,

    setAuth: (user, accessToken, refreshToken) => {
      setAccessToken(accessToken);
      storeRefreshToken(refreshToken);
      set({ user, accessToken, isAuthenticated: true, isLoading: false });
    },

    setUser: (user) => set({ user }),

    logout: () => {
      setAccessToken(null);
      clearRefreshToken();
      set({
        user: null,
        accessToken: null,
        isAuthenticated: false,
        isLoading: false,
      });
    },

    setLoading: (loading) => set({ isLoading: loading }),
  }))
);
