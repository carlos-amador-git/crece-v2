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
    // Backend uses OAuth2 password flow (form-encoded, username field)
    const formData = new URLSearchParams();
    formData.append("username", credentials.email);
    formData.append("password", credentials.password);

    const BASE_URL =
      process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8002/api/v1";
    const res = await fetch(`${BASE_URL}/auth/login/`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail ?? "Credenciales inválidas");
    }
    const tokens: AuthTokens = await res.json();
    localStorage.setItem("crece_access_token", tokens.access_token);
    if (tokens.refresh_token) {
      localStorage.setItem("crece_refresh_token", tokens.refresh_token);
    }
    // Set cookie for server-side middleware auth check
    document.cookie = `crece_access_token=${tokens.access_token}; path=/; max-age=${60 * 60 * 24}; SameSite=Lax`;
    const userData = await api.get<User>("/auth/me");
    setUser(userData);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("crece_access_token");
    localStorage.removeItem("crece_refresh_token");
    // Clear server-side auth cookie
    document.cookie = "crece_access_token=; path=/; max-age=0";
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
