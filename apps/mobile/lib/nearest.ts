import type { NearestPlaceResponse, PlaceOut } from "../../../packages/api-contract/schema";
import { apiPostJson } from "./api";

// "Użyj mojej lokalizacji" = ONE foreground position read, sent once to our own backend, which
// answers with the nearest place of its registry (POST /places/nearest, ADR-029). The user then
// confirms or ignores it. Nothing is stored; no background location, no account (rule #11).
export type NearestState =
  | { kind: "idle" }
  | { kind: "locating" }
  | { kind: "found"; place: PlaceOut; distanceKm: number; attribution: string }
  | { kind: "denied"; canAskAgain: boolean }
  | { kind: "unavailable" }
  | { kind: "out_of_range" }
  | { kind: "error" };

export type Position = { latitude: number; longitude: number };

export type NearestDeps = {
  requestPermission: () => Promise<{ granted: boolean; canAskAgain: boolean }>;
  getPosition: () => Promise<Position>;
  lookup: (position: Position) => Promise<NearestPlaceResponse>;
};

export async function findNearestPlace(deps: NearestDeps): Promise<NearestState> {
  let permission: { granted: boolean; canAskAgain: boolean };
  try {
    permission = await deps.requestPermission();
  } catch {
    return { kind: "unavailable" };
  }
  if (!permission.granted) return { kind: "denied", canAskAgain: permission.canAskAgain };
  let position: Position;
  try {
    position = await deps.getPosition();
  } catch {
    return { kind: "unavailable" }; // location services off / no fix
  }
  try {
    const res = await deps.lookup(position);
    if (res.status === "found" && res.place && res.distance_km !== null) {
      return { kind: "found", place: res.place, distanceKm: res.distance_km, attribution: res.attribution };
    }
    return { kind: "out_of_range" };
  } catch {
    return { kind: "error" };
  }
}

export const lookupNearest = (position: Position, signal?: AbortSignal): Promise<NearestPlaceResponse> =>
  apiPostJson<NearestPlaceResponse>("/api/v1/places/nearest", position, signal);

export const NEAREST_PRIVACY = "Lokalizacja jest użyta jednorazowo, tylko do znalezienia miejscowości. Nie zapisujemy jej ani nie śledzimy w tle.";

export function distanceText(km: number): string {
  return km < 1 ? "mniej niż 1 km od Ciebie" : `ok. ${Math.round(km)} km od Ciebie`;
}

export function nearestMessage(state: NearestState): string | null {
  switch (state.kind) {
    case "denied":
      return state.canAskAgain
        ? "Bez zgody na lokalizację nie znajdziemy najbliższej miejscowości. Możesz wpisać nazwę ręcznie."
        : "Zgoda na lokalizację jest wyłączona. Włącz ją w ustawieniach telefonu albo wpisz nazwę miejscowości.";
    case "unavailable":
      return "Nie udało się ustalić położenia. Sprawdź, czy lokalizacja w telefonie jest włączona, albo wpisz nazwę miejscowości.";
    case "out_of_range":
      return "Nie znaleźliśmy miejscowości w pobliżu (obsługujemy Polskę). Wpisz nazwę ręcznie.";
    case "error":
      return "Nie udało się sprawdzić najbliższej miejscowości. Sprawdź połączenie i spróbuj ponownie.";
    default:
      return null;
  }
}
