// Place search + activation (ADR-029) as plain functions: query rules, the debouncer, the
// honest copy for every outcome, and the activation call itself. Screens only lay it out.
// The client never calls a geocoder: names come from our own GET /api/v1/places (rule #14).
import type { AreaOut, PlaceAreaResponse } from "../../../packages/api-contract/schema";
import { ApiError, apiGet, apiPost } from "./api";

export const MIN_QUERY = 2;
export const DEBOUNCE_MS = 300;

// Trimmed, single-spaced; null = too short to search (the server needs >= 2 characters).
export function searchQuery(raw: string): string | null {
  const q = raw.trim().replace(/\s+/g, " ");
  return q.length >= MIN_QUERY ? q : null;
}

export const placesPath = (q: string, limit = 10): string => `/api/v1/places?q=${encodeURIComponent(q)}&limit=${limit}`;

// Trailing-edge debounce with cancel (the screen cancels on unmount / a new query).
export function debounce<A extends unknown[]>(fn: (...args: A) => void, ms: number) {
  let timer: ReturnType<typeof setTimeout> | undefined;
  return {
    call(...args: A) {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), ms);
    },
    cancel() {
      clearTimeout(timer);
      timer = undefined;
    },
  };
}

// ---- copy (no technicalities, spec §41) -----------------------------------------------------

export const SEARCH_HINT = "Wpisz co najmniej 2 litery nazwy miejscowości.";
export const SEARCH_ERROR = "Nie udało się wyszukać miejscowości. Sprawdź połączenie z internetem i spróbuj ponownie.";
export const emptyResultMessage = (q: string): string =>
  `Nie znaleziono miejscowości „${q}”. Sprawdź pisownię albo wpisz pierwsze litery nazwy.`;

// Shown on Start when the place has no weather polling (capacity/budget/expired): the weather
// and pollen cards are empty for a known reason, not because something broke (ADR-026/029).
export const POLLING_OFF_NOTICE =
  "Pogoda i pyłki dla tej miejscowości są chwilowo niedostępne. Powietrze może pochodzić ze stacji w okolicy.";

export const EXPIRED_AREA_MESSAGE = "Wybrana miejscowość nie jest już dostępna. Wybierz ją ponownie.";

export function activationFailureMessage(err: unknown): string {
  if (err instanceof ApiError && (err.status === 429 || err.status === 503)) {
    return "Nie udało się teraz włączyć danych dla tej miejscowości. Spróbuj za chwilę albo wybierz inną.";
  }
  if (err instanceof ApiError) return "Nie udało się ustawić tej miejscowości. Spróbuj ponownie.";
  return "Nie udało się połączyć z serwerem. Sprawdź internet i spróbuj ponownie.";
}

// ---- activation -----------------------------------------------------------------------------

export type Activation =
  // `limited`: the area exists but weather is not polled (capacity_reached / budget_exhausted /
  // inactive): continue to Start, which says so (POLLING_OFF_NOTICE) from the live dashboard.
  | { kind: "proceed"; area: AreaOut; limited: boolean }
  | { kind: "failed"; message: string };

export function interpretActivation(res: PlaceAreaResponse): Activation {
  if (!res.area) return { kind: "failed", message: activationFailureMessage(null) };
  return { kind: "proceed", area: res.area, limited: res.polling !== "active" };
}

// POST /places/{id}/activate; on 429/503 the area may already exist from an earlier choice,
// and the read-only GET /places/{id} says so without creating anything. If it does, go on
// (limited); if not, fail with an honest message. Throws only when `signal` was aborted.
export async function activatePlace(placeId: number, signal?: AbortSignal): Promise<Activation> {
  try {
    return interpretActivation(await apiPost<PlaceAreaResponse>(`/api/v1/places/${placeId}/activate`, signal));
  } catch (err) {
    if (signal?.aborted) throw err;
    if (err instanceof ApiError && (err.status === 429 || err.status === 503)) {
      try {
        const known = interpretActivation(await apiGet<PlaceAreaResponse>(`/api/v1/places/${placeId}`, signal));
        if (known.kind === "proceed") return { ...known, limited: true };
      } catch {
        // fall through to the failure message
      }
    }
    return { kind: "failed", message: activationFailureMessage(err) };
  }
}
