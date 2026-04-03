"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { createElement } from "react";
import type { User, AuthTokens, LoginCredentials } from "@/lib/api/types";
import { api, ApiError } from "@/lib/api/client";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    const token = localStorage.getItem("crece_access_token");
    if (!token) {
      setIsLoading(false);
      return;
    }
    try {
      const userData = await api.get<User>("/auth/me");
      setUser(userData);
    } catch {
      localStorage.removeItem("crece_access_token");
      localStorage.removeItem("crece_refresh_token");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const login = useCallback(async (credentials: LoginCredentials) => {
    const tokens = await api.post<AuthTokens>("/auth/login", credentials);
    localStorage.setItem("crece_access_token", tokens.access_token);
    localStorage.setItem("crece_refresh_token", tokens.refresh_token);
    const userData = await api.get<User>("/auth/me");
    setUser(userData);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("crece_access_token");
    localStorage.removeItem("crece_refresh_token");
    setUser(null);
    window.location.href = "/login";
  }, []);

  return createElement(
    AuthContext.Provider,
    {
      value: {
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
      },
    },
    children
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
