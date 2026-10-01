// Shared API base URL + fetch wrapper. Single source of truth so every screen
// configures the backend connection the same way (previously duplicated inline).
//
// Android emulator: 10.0.2.2, iOS simulator/web: localhost. Override with
// EXPO_PUBLIC_API_URL when running on a physical device (your machine's LAN IP).
export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return res.json();
}
