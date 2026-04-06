/**
 * API client for CRECE backend.
 * Reads base URL from EXPO_PUBLIC_API_URL env var.
 * Attaches JWT from SecureStore to every authenticated request.
 */

import * as SecureStore from "expo-secure-store";
import Constants from "expo-constants";

const BASE_URL =
  Constants.expoConfig?.extra?.apiUrl ??
  process.env.EXPO_PUBLIC_API_URL ??
  "http://localhost:8002";

const TOKEN_KEY = "crece_access_token";

// ── Token helpers ───────────────────────────────────────

export async function getStoredToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function setStoredToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function clearStoredToken(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}

// ── Generic fetch wrapper ───────────────────────────────

interface FetchOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /**
   * If true, sends as application/x-www-form-urlencoded
   * (needed for OAuth2 login endpoint).
   */
  formEncoded?: boolean;
  /** Skip attaching the Authorization header. */
  noAuth?: boolean;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    const msg =
      typeof detail === "string"
        ? detail
        : (detail as { detail?: string })?.detail ?? `HTTP ${status}`;
    super(msg);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export async function apiFetch<T>(
  path: string,
  options: FetchOptions = {}
): Promise<T> {
  const { body, formEncoded, noAuth, headers: extraHeaders, ...rest } = options;

  const headers: Record<string, string> = {
    ...(extraHeaders as Record<string, string>),
  };

  // Attach JWT
  if (!noAuth) {
    const token = await getStoredToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  let processedBody: string | undefined;

  if (body !== undefined) {
    if (formEncoded && typeof body === "object" && body !== null) {
      headers["Content-Type"] = "application/x-www-form-urlencoded";
      processedBody = new URLSearchParams(
        body as Record<string, string>
      ).toString();
    } else {
      headers["Content-Type"] = "application/json";
      processedBody = JSON.stringify(body);
    }
  }

  const url = `${BASE_URL}${path}`;

  const response = await fetch(url, {
    ...rest,
    headers,
    body: processedBody,
  });

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }
    throw new ApiError(response.status, detail);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

// ── Convenience methods ─────────────────────────────────

export const api = {
  get: <T>(path: string, opts?: FetchOptions) =>
    apiFetch<T>(path, { ...opts, method: "GET" }),

  post: <T>(path: string, body?: unknown, opts?: FetchOptions) =>
    apiFetch<T>(path, { ...opts, method: "POST", body }),

  patch: <T>(path: string, body?: unknown, opts?: FetchOptions) =>
    apiFetch<T>(path, { ...opts, method: "PATCH", body }),

  delete: <T>(path: string, opts?: FetchOptions) =>
    apiFetch<T>(path, { ...opts, method: "DELETE" }),
};
