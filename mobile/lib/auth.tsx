/**
 * Auth context provider and useAuth() hook.
 * Manages JWT storage, login, logout, and current user state.
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { apiFetch, setStoredToken, clearStoredToken, getStoredToken } from "./api";
import type { User, TokenResponse } from "./types";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    try {
      const token = await getStoredToken();
      if (!token) {
        setUser(null);
        return;
      }
      const me = await apiFetch<User>("/api/v1/auth/me", { method: "GET" });
      setUser(me);
    } catch {
      // Token expired or invalid
      await clearStoredToken();
      setUser(null);
    }
  }, []);

  useEffect(() => {
    fetchUser().finally(() => setIsLoading(false));
  }, [fetchUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokenResponse = await apiFetch<TokenResponse>(
        "/api/v1/auth/login",
        {
          method: "POST",
          body: { username: email, password },
          formEncoded: true,
          noAuth: true,
        }
      );
      await setStoredToken(tokenResponse.access_token);
      await fetchUser();
    },
    [fetchUser]
  );

  const logout = useCallback(async () => {
    await clearStoredToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: user !== null,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
