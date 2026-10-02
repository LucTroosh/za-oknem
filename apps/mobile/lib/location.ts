// The one thing the app remembers on the device (spec §3): ONE active location + whether the
// onboarding was finished. Pure logic only (serialise / parse / validate); the AsyncStorage
// calls live in lib/storage.ts. No account, no profile, and the coordinates are the CENTRE of
// the chosen place (public data of the places registry) - never the user's position.
// Versioned: an unknown or corrupt record parses to the defaults, so the app always starts.
import type { AreaOut, PlaceOut } from "../../../packages/api-contract/schema";
import { type ThemePref, parseThemePref } from "./theme";

export const SETTINGS_KEY = "za-oknem/settings";
export const SETTINGS_VERSION = 1;

export type ActiveLocation = {
  geoAreaId: number;
  // null for a seeded city picked from /areas (no registry entry behind it).
  placeId: number | null;
  // Short name for the header ("Gliwice") and the long label for the picker ("Gliwice, pow. ...").
  name: string;
  label: string;
  latitude: number;
  longitude: number;
  // The registry's attribution string (GeoNames, CC BY 4.0) sent with the place; shown verbatim
  // under Settings > Źródła. null for seeded cities and for records saved before this field.
  attribution: string | null;
};

// `theme` is optional in the stored record (older installs have none): missing -> "system", so
// no version bump and no reset of an existing install. A `topics` field written by an earlier
// build (the removed "Co chcesz sledzic?" step, production UI v1) is simply ignored on read and
// dropped on the next write: every available module is always shown.
export type Settings = {
  onboardingDone: boolean;
  location: ActiveLocation | null;
  theme: ThemePref;
};

export const DEFAULT_SETTINGS: Settings = { onboardingDone: false, location: null, theme: "system" };

export function serializeSettings(s: Settings): string {
  return JSON.stringify({
    v: SETTINGS_VERSION,
    onboardingDone: s.onboardingDone,
    location: s.location,
    theme: s.theme,
  });
}

const isObject = (x: unknown): x is Record<string, unknown> => typeof x === "object" && x !== null && !Array.isArray(x);
const posInt = (x: unknown): x is number => typeof x === "number" && Number.isInteger(x) && x > 0;
const text = (x: unknown): x is string => typeof x === "string" && x.trim() !== "";
const inRange = (x: unknown, lim: number): x is number => typeof x === "number" && Number.isFinite(x) && Math.abs(x) <= lim;

function parseLocation(x: unknown): ActiveLocation | null {
  if (!isObject(x)) return null;
  const { geoAreaId, placeId, name, label, latitude, longitude } = x;
  if (!posInt(geoAreaId) || !text(name) || !text(label) || !inRange(latitude, 90) || !inRange(longitude, 180)) return null;
  if (placeId !== null && !posInt(placeId)) return null;
  const attribution = text(x.attribution) ? x.attribution : null;
  return { geoAreaId, placeId, name, label, latitude, longitude, attribution };
}

// Anything unreadable -> defaults (the user sees Welcome again, never a crash). A readable
// record with a damaged location keeps `onboardingDone` (the user chooses a place again, but
// does not see Welcome again).
export function parseSettings(raw: string | null | undefined): Settings {
  if (typeof raw !== "string") return DEFAULT_SETTINGS;
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return DEFAULT_SETTINGS;
  }
  if (!isObject(data) || data.v !== SETTINGS_VERSION) return DEFAULT_SETTINGS;
  return {
    onboardingDone: data.onboardingDone === true,
    location: parseLocation(data.location),
    theme: parseThemePref(data.theme),
  };
}

// Reads through `read` with a time limit. A read ERROR or a timeout is not "no record": the
// result is flagged `ok:false` and the caller must not overwrite what may still be stored
// (the defaults are returned only so the app can start, rule #1).
export async function readSettings(
  read: () => Promise<string | null>,
  timeoutMs: number,
): Promise<{ settings: Settings; ok: boolean }> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const raw = await Promise.race([
      read(),
      new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new Error("timeout")), timeoutMs);
      }),
    ]);
    return { settings: parseSettings(raw), ok: true };
  } catch {
    // A fresh copy: callers tell "read from storage" apart by `ok`, never by object identity.
    return { settings: { ...DEFAULT_SETTINGS }, ok: false };
  } finally {
    clearTimeout(timer);
  }
}

// Re-activate at most once per `minMs` (TTL is days; this only keeps a long-open app alive).
export const REACTIVATE_MIN_MS = 60 * 60 * 1000;
export function shouldReactivate(last: number | null, now: number, minMs = REACTIVATE_MIN_MS): boolean {
  return last === null || now - last >= minMs;
}

export function locationFromPlace(place: PlaceOut, area: AreaOut, attribution: string | null): ActiveLocation {
  return {
    geoAreaId: area.geo_area_id,
    placeId: place.place_id,
    name: place.name,
    label: place.label,
    latitude: place.latitude,
    longitude: place.longitude,
    attribution,
  };
}

export function locationFromArea(area: AreaOut): ActiveLocation {
  return {
    geoAreaId: area.geo_area_id,
    placeId: null,
    name: area.name,
    label: area.name,
    latitude: area.latitude,
    longitude: area.longitude,
    attribution: null,
  };
}

// App start: the activation answer is the authority on the place (a later GeoNames import may
// have corrected the name, a restored database may have recreated the area under another id).
// Replaces the remembered location only if it is still that place; same object back when
// nothing changed (no needless write).
export function refreshLocation(s: Settings, placeId: number, next: ActiveLocation): Settings {
  const cur = s.location;
  if (cur === null || cur.placeId !== placeId) return s;
  const same =
    cur.geoAreaId === next.geoAreaId &&
    cur.name === next.name &&
    cur.label === next.label &&
    cur.latitude === next.latitude &&
    cur.longitude === next.longitude &&
    cur.attribution === next.attribution;
  return same ? s : { ...s, location: next };
}

// Forget the location only if it is still `geoAreaId` (same object back otherwise): a late
// "gone" answer for a place the user has already left must not wipe the new choice.
export function dropLocationIf(s: Settings, geoAreaId: number): Settings {
  return s.location?.geoAreaId === geoAreaId ? { ...s, location: null } : s;
}

// ---- routing guard --------------------------------------------------------------------------

export type Entry = "tabs" | "welcome" | "location";

// Where a route must send the user instead of rendering (null = render). Welcome never comes
// back after the onboarding; with no usable location the picker is the only way on.
// `welcomeSeen` (in memory only: the user pressed the Welcome CTA in this run) lets the first
// run into the picker; a deep link straight to /location on a fresh install still sees Welcome.
export function entryRedirect(s: Settings, entry: Entry, welcomeSeen = false): "/welcome" | "/location" | "/" | null {
  if (entry === "location") return s.onboardingDone || welcomeSeen ? null : "/welcome";
  if (!s.onboardingDone) return entry === "welcome" ? null : "/welcome";
  if (s.location === null) return "/location";
  return entry === "welcome" ? "/" : null;
}
