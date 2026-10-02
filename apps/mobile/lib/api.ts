// Shared API base URL + fetch wrapper. Single source of truth so every screen
// configures the backend connection the same way (previously duplicated inline).
//
// Android emulator: 10.0.2.2, iOS simulator/web: localhost. Override with
// EXPO_PUBLIC_API_URL when running on a physical device (your machine's LAN IP).
export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

// Carries the HTTP status so callers can tell "gone" (404) from "busy" (429/503); the message
// is for logs only and is never shown to the user.
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(method: "GET" | "POST", path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, method === "GET" ? { signal } : { method, signal });
  if (!res.ok) throw new ApiError(res.status, `${method} ${path} -> ${res.status}`);
  return res.json();
}

export const apiGet = <T>(path: string, signal?: AbortSignal): Promise<T> => request<T>("GET", path, signal);
export const apiPost = <T>(path: string, signal?: AbortSignal): Promise<T> => request<T>("POST", path, signal);
