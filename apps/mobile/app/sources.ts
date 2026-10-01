// Settings > "Źródła danych": the attribution strings the backend already sends with every
// block (TASK-7.1, source-registry.md) - listed verbatim, never reworded here. Order =
// first appearance, duplicates dropped (the same IMGW text arrives with alerts and hydro).
const isObject = (x: unknown): x is Record<string, unknown> =>
  typeof x === "object" && x !== null && !Array.isArray(x);

export function collectAttributions(dashboard: unknown): string[] {
  if (!isObject(dashboard)) return [];
  const blocks: unknown[] = [dashboard.alerts];
  if (Array.isArray(dashboard.areas)) {
    for (const area of dashboard.areas) {
      if (!isObject(area)) continue;
      blocks.push(area.air, area.weather, area.forecast, area.pollen);
    }
  }
  const out: string[] = [];
  for (const b of blocks) {
    const a = isObject(b) ? b.attribution : undefined;
    if (typeof a === "string" && a.trim() !== "" && !out.includes(a)) out.push(a);
  }
  return out;
}
