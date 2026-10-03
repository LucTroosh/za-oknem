import type { NeighborhoodOut } from "../../../packages/api-contract/schema";

// "Twoja okolica" (ADR-032): historical / long-term / register data about the selected location.
// NOT live data and NOT alerts (rule #7): no freshness badge, no advice, no thresholds. Every
// section says where the data comes from, which period it covers and what it applies to; "no data
// for this place" and "we could not read the data" are different screens (rule #1, #8).
// The server composes the attribution text; the client only shows it.
export type NeighborhoodBlock = NeighborhoodOut;
type Section = NeighborhoodOut["sections"][number];

export const ENTRY_TITLE = "Twoja okolica";
export const ENTRY_VALUE = "Hałas i inne dane o okolicy";
export const SCREEN_INTRO = "Dane historyczne i długoterminowe o wybranej lokalizacji. To nie jest stan na dziś ani ostrzeżenie.";

const CATEGORY_LABEL: Record<string, string> = {
  Droga: "Hałas drogowy",
  Lotnisko: "Hałas lotniczy",
  Przemysł: "Hałas przemysłowy",
  Kolej: "Hałas kolejowy",
};

// The entry is shown only when the deployment reports at least one switched-on section.
export const entryVisible = (b: NeighborhoodBlock | null): boolean => b !== null && b.enabled === true && b.sections.length > 0;

// Shape check at the boundary: an older / different backend must not crash the screen.
export function neighborhoodView(raw: unknown): NeighborhoodBlock | null {
  const b = raw as Partial<NeighborhoodBlock> | null;
  if (!b || typeof b !== "object" || typeof b.enabled !== "boolean" || !Array.isArray(b.sections)) return null;
  return b as NeighborhoodBlock;
}

const pl = (n: number, digits = 1): string => n.toFixed(digits).replace(".", ",");

// dd.mm.yyyy from an ISO day, without going through Date (no timezone shift of a plain calendar day).
export function formatDay(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  return m ? `${m[3]}.${m[2]}.${m[1]}` : iso;
}

export function periodText(p: { from: string; to: string; precision: string } | null | undefined): string | null {
  if (!p) return null;
  if (p.precision === "unknown") return null;
  if (p.precision === "year") return p.from.slice(0, 4) === p.to.slice(0, 4) ? p.from.slice(0, 4) : `${p.from.slice(0, 4)}–${p.to.slice(0, 4)}`;
  return p.from === p.to ? formatDay(p.from) : `${formatDay(p.from)} – ${formatDay(p.to)}`;
}

export const distanceText = (km: number): string => (km < 0.1 ? "w tym samym miejscu" : `ok. ${pl(km)} km od wybranej lokalizacji`);

export type MeasurementRow = { label: string; value: string; note: string | null };
export type ItemView = { key: string; title: string; place: string; distance: string; period: string | null; purpose: string | null; rows: MeasurementRow[] };
export type SectionView = {
  id: string;
  title: string;
  kind: "data" | "empty" | "failed";
  headline: string;
  body: string | null;
  period: string | null;
  retrievalNotice: string | null;
  items: ItemView[];
  limitations: string[];
  attribution: string;
  sourceUrl: string;
  licenseUrl: string;
};

export const DEGRADED_NOTICE = "Ostatnie pobranie danych się nie powiodło. Pokazujemy dane pobrane wcześniej.";

const HEADLINE: Record<Section["availability"], string> = {
  available: "Najbliższe punkty pomiarowe",
  no_coverage: "W pobliżu nie ma punktu pomiarowego",
  no_records: "Brak zapisów dla tej lokalizacji",
  unavailable: "Dane chwilowo niedostępne",
  pending_verification: "Źródło w trakcie weryfikacji",
};

// "przekroczenie" is the source's own number; 0 / null is NOT turned into "within the norm" (we do not
// know the limit), only a positive value is mentioned, as stated.
function measurementRow(m: { period_of_day: string; value_db: number; exceedance_db: number | null }): MeasurementRow {
  const note = m.exceedance_db !== null && m.exceedance_db > 0 ? `przekroczenie wg źródła: ${pl(m.exceedance_db)} dB` : null;
  return { label: m.period_of_day, value: `${pl(m.value_db)} dB`, note };
}

export function sectionView(s: Section): SectionView {
  const items: ItemView[] = s.items.map((i) => ({
    key: `${i.category}-${i.point_code}`,
    title: CATEGORY_LABEL[i.category] ?? `Hałas: ${i.category}`,
    place: [i.locality, i.gmina].filter((x): x is string => !!x).join(", ") || i.voivodeship,
    distance: distanceText(i.distance_km),
    period: periodText({ from: i.period_from, to: i.period_to, precision: "date" }),
    purpose: i.purpose,
    rows: i.measurements.map(measurementRow),
  }));
  const kind = s.availability === "available" && items.length > 0 ? "data" : s.availability === "unavailable" ? "failed" : "empty";
  return {
    id: s.id,
    title: s.title,
    kind,
    headline: HEADLINE[s.availability],
    body: s.message,
    period: periodText(s.source_period),
    retrievalNotice: s.retrieval_status === "degraded" ? DEGRADED_NOTICE : null,
    items,
    limitations: s.limitations,
    attribution: s.attribution,
    sourceUrl: s.source_url,
    licenseUrl: s.license_url,
  };
}
