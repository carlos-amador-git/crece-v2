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

export interface OrgContext {
  id: number;
  nombre: string;
  slug: string;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  activeOrg: OrgContext | null;
  setActiveOrg: (org: OrgContext | null) => void;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeOrg, setActiveOrgState] = useState<OrgContext | null>(null);

  const setActiveOrg = useCallback((org: OrgContext | null) => {
    setActiveOrgState(org);
    if (org) {
      localStorage.setItem("crece_active_org_id", String(org.id));
      localStorage.setItem("crece_active_org", JSON.stringify(org));
    } else {
      localStorage.removeItem("crece_active_org_id");
      localStorage.removeItem("crece_active_org");
    }
  }, []);

  const syncOrg = useCallback((userData: User, storedOrg: OrgContext | null) => {
    const userOrg =
      userData.org_id && userData.org_nombre && userData.org_slug
        ? { id: userData.org_id, nombre: userData.org_nombre, slug: userData.org_slug }
        : null;

    // Logic:
    // 1. If not admin, ALWAYS force to user's primary org (no switching).
    // 2. If admin and no stored org, use user's primary org.
    // 3. If admin and stored org matches user's primary org ID, sync the name (cache update).
    // 4. Otherwise (admin with different stored org), keep the stored one (the switched org).
    
    if (userData.role !== "admin" || !storedOrg) {
      if (userOrg) {
        setActiveOrgState(userOrg);
        localStorage.setItem("crece_active_org_id", String(userOrg.id));
        localStorage.setItem("crece_active_org", JSON.stringify(userOrg));
      } else {
        setActiveOrgState(null);
        localStorage.removeItem("crece_active_org_id");
        localStorage.removeItem("crece_active_org");
      }
    } else if (userOrg && storedOrg.id === userOrg.id && storedOrg.nombre !== userOrg.nombre) {
      // Admin's own org name changed in DB
      setActiveOrgState(userOrg);
      localStorage.setItem("crece_active_org", JSON.stringify(userOrg));
    } else {
      setActiveOrgState(storedOrg);
    }
  }, []);

  const fetchUser = useCallback(async () => {
    const token = localStorage.getItem("crece_access_token");
    if (!token) {
      setIsLoading(false);
      return;
    }
    try {
      const userData = await api.get<User>("/auth/me");
      setUser(userData);

      // Restore active org from localStorage
      const storedRaw = localStorage.getItem("crece_active_org");
      let stored: OrgContext | null = null;
      if (storedRaw) {
        try {
          stored = JSON.parse(storedRaw);
        } catch {
          /* ignore */
        }
      }
      syncOrg(userData, stored);
    } catch {
      localStorage.removeItem("crece_access_token");
      localStorage.removeItem("crece_refresh_token");
      localStorage.removeItem("crece_active_org");
      localStorage.removeItem("crece_active_org_id");
    } finally {
      setIsLoading(false);
    }
  }, [syncOrg]);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      // Backend uses OAuth2 password flow (form-encoded, username field)
      const formData = new URLSearchParams();
      formData.append("username", credentials.email);
      formData.append("password", credentials.password);

      const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8002/api/v1";
      const res = await fetch(`${BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData.toString(),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail ?? "Credenciales inválidas");
      }
      const tokens: AuthTokens = await res.json();
      
      // Clear old state before setting new one to avoid leaks
      localStorage.removeItem("crece_active_org");
      localStorage.removeItem("crece_active_org_id");
      
      localStorage.setItem("crece_access_token", tokens.access_token);
      if (tokens.refresh_token) {
        localStorage.setItem("crece_refresh_token", tokens.refresh_token);
      }
      // Set cookie for server-side middleware auth check
      document.cookie = `crece_access_token=${tokens.access_token}; path=/; max-age=${
        60 * 60 * 24
      }; SameSite=Lax`;
      
      const userData = await api.get<User>("/auth/me");
      setUser(userData);
      syncOrg(userData, null); // Fresh login: no stored org should influence initial state
    },
    [syncOrg]
  );

  const logout = useCallback(() => {
    localStorage.removeItem("crece_access_token");
    localStorage.removeItem("crece_refresh_token");
    localStorage.removeItem("crece_active_org_id");
    localStorage.removeItem("crece_active_org");
    // Clear server-side auth cookie
    document.cookie = "crece_access_token=; path=/; max-age=0";
    setUser(null);
    setActiveOrgState(null);
    window.location.href = "/login";
  }, []);

  return createElement(
    AuthContext.Provider,
    {
      value: {
        user,
        isLoading,
        isAuthenticated: !!user,
        activeOrg,
        setActiveOrg,
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
