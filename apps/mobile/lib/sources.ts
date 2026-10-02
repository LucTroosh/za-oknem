// Settings > "Źródła danych": the attribution strings the backend already sends with every
// block (TASK-7.1, source-registry.md) - listed verbatim, never reworded here. Order =
// first appearance, duplicates dropped (the same IMGW text arrives with alerts and hydro).
const isObject = (x: unknown): x is Record<string, unknown> =>
  typeof x === "object" && x !== null && !Array.isArray(x);

// Adds the place registry's attribution (GeoNames, shown verbatim) when a place is chosen.
export function withPlaceSource(sources: string[], attribution: string | null | undefined): string[] {
  return attribution && attribution.trim() !== "" && !sources.includes(attribution) ? [...sources, attribution] : sources;
}

// `extra` = other blocks that carry an `attribution` (water levels, pollen calendar).
export function collectAttributions(dashboard: unknown, ...extra: unknown[]): string[] {
  const blocks: unknown[] = [];
  if (isObject(dashboard)) blocks.push(dashboard.alerts);
  if (isObject(dashboard) && Array.isArray(dashboard.areas)) {
    for (const area of dashboard.areas) {
      if (!isObject(area)) continue;
      blocks.push(area.air, area.weather, area.forecast, area.pollen);
    }
  }
  blocks.push(...extra);
  const out: string[] = [];
  for (const b of blocks) {
    const a = isObject(b) ? b.attribution : undefined;
    if (typeof a === "string" && a.trim() !== "" && !out.includes(a)) out.push(a);
  }
  return out;
}
