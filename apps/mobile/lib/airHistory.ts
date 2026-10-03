import type { AirHistoryResponse } from "../../../packages/api-contract/schema";

export type AirHistory = AirHistoryResponse;
export const AIR_PARAMS: readonly AirHistory["param"][] = ["PM2.5", "PM10", "NO2", "SO2", "O3", "CO", "C6H6"];

// Position by elapsed time, not array index: missing hours stay empty, including across DST.
export function historyBars(data: AirHistory) {
  const start = Date.parse(data.window_start);
  const end = Date.parse(data.window_end);
  if (data.kind !== "measurement_history" || !Number.isFinite(start) || !Number.isFinite(end) || end <= start || !Array.isArray(data.points)) {
    throw new Error("Invalid air history");
  }
  const points = data.points.map((p) => {
    const time = Date.parse(p.observed_at);
    if (!Number.isFinite(time) || time < start || time > end || !Number.isFinite(p.value) || p.value < 0) throw new Error("Invalid air measurement");
    return { ...p, x: (time - start) / (end - start) };
  });
  const max = Math.max(1, ...points.map((p) => p.value));
  return { max, points: points.map((p) => ({ ...p, height: p.value / max })) };
}
