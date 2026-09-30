import { describe, expect, it } from "vitest";

import { type AlertItem, alertAreasLabel, alertKey } from "./alerts";

describe("alertAreasLabel", () => {
  it("joins unique voivodeship names", () => {
    expect(
      alertAreasLabel([
        { wojewodztwo: "wielkopolskie" },
        { wojewodztwo: "wielkopolskie" },
        { wojewodztwo: "łódzkie" },
      ]),
    ).toBe("wielkopolskie, łódzkie");
  });

  it("skips entries without a usable name instead of guessing", () => {
    expect(alertAreasLabel([{ wojewodztwo: null }, { powiat: "x" }, {}])).toBe("");
  });
});

describe("alertKey", () => {
  it("differs for the same external_id from another source or revision", () => {
    const base = { external_id: "31", source: "imgw_warningshydro", published_at: "t1" };
    const keys = new Set(
      [base, { ...base, source: "imgw_warningsmeteo" }, { ...base, published_at: "t2" }].map(
        (a) => alertKey(a as AlertItem),
      ),
    );
    expect(keys.size).toBe(3);
  });
});
