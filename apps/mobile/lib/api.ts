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

export const REQUEST_TIMEOUT_MS = 15_000;

// A hung connection must end in an error the screen can show ("Spróbuj ponownie"), never in a
// spinner without a way out. The timeout aborts a private controller that also follows the
// caller's `signal`; a timeout therefore looks like a failed request, not like a cancellation.
async function request<T>(method: "GET" | "POST", path: string, signal?: AbortSignal, timeoutMs = REQUEST_TIMEOUT_MS): Promise<T> {
  const ctrl = new AbortController();
  const onAbort = () => ctrl.abort();
  if (signal?.aborted) ctrl.abort();
  signal?.addEventListener("abort", onAbort);
  const timer = setTimeout(onAbort, timeoutMs);
  try {
    const res = await fetch(`${API_URL}${path}`, method === "GET" ? { signal: ctrl.signal } : { method, signal: ctrl.signal });
    if (!res.ok) throw new ApiError(res.status, `${method} ${path} -> ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  }
}

export const apiGet = <T>(path: string, signal?: AbortSignal, timeoutMs?: number): Promise<T> =>
  request<T>("GET", path, signal, timeoutMs);
export const apiPost = <T>(path: string, signal?: AbortSignal, timeoutMs?: number): Promise<T> =>
  request<T>("POST", path, signal, timeoutMs);
