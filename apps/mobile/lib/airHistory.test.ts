import { expect, it } from "vitest";

import { type AirHistory, formatHistoryTime, historyBars } from "./airHistory";

it("plots elapsed time across DST, leaves gaps empty, preserves zero and rejects invalid measurements", () => {
  const data = {
    kind: "measurement_history",
    window_start: "2026-10-25T00:00:00Z",
    window_end: "2026-10-25T04:00:00Z",
    points: [
      { observed_at: "2026-10-25T02:00:00+02:00", value: 0 },
      { observed_at: "2026-10-25T02:00:00+01:00", value: 10 },
      { observed_at: "2026-10-25T03:00:00Z", value: 20 },
    ],
  } as AirHistory;
  expect(historyBars(data)).toMatchObject({ max: 20, points: [{ x: 0, height: 0 }, { x: 0.25, height: 0.5 }, { x: 0.75, height: 1 }] });
  expect(historyBars({ ...data, points: [] })).toEqual({ max: 1, points: [] });
  for (const value of [-1, NaN, Infinity]) {
    expect(() => historyBars({ ...data, points: [{ ...data.points[0], value }] })).toThrow();
  }
  for (const observed_at of ["bad date", "2026-10-24T23:00:00Z", "2026-10-25T05:00:00Z"]) {
    expect(() => historyBars({ ...data, points: [{ observed_at, value: 1 }] })).toThrow();
  }
  expect(() => historyBars({ ...data, window_end: data.window_start })).toThrow();
});

it("distinguishes both occurrences of the local hour when clocks go back", () => {
  const before = process.env.TZ;
  process.env.TZ = "Europe/Warsaw";
  try {
    const first = formatHistoryTime("2026-10-25T00:00:00Z");
    const second = formatHistoryTime("2026-10-25T01:00:00Z");
    expect(first).toContain("02:00");
    expect(second).toContain("02:00");
    expect(first).not.toEqual(second);
  } finally {
    if (before === undefined) delete process.env.TZ;
    else process.env.TZ = before;
  }
});
