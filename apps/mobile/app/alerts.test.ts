import { describe, expect, it } from "vitest";

import { alertAreasLabel } from "./alerts";

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
