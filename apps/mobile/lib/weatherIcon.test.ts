import { describe, expect, it } from "vitest";

import { weatherIcon } from "./weatherIcon";

describe("weatherIcon", () => {
  it("maps WMO codes to glyphs", () => {
    expect(weatherIcon(0)).toBe("sunny");
    expect(weatherIcon(2)).toBe("partly-sunny");
    expect(weatherIcon(3)).toBe("cloudy");
    expect(weatherIcon(61)).toBe("rainy");
    expect(weatherIcon(81)).toBe("rainy");
    expect(weatherIcon(73)).toBe("snow");
    expect(weatherIcon(95)).toBe("thunderstorm");
    expect(weatherIcon(45)).toBe("cloud-outline");
  });
  it("unknown codes have no icon", () => {
    expect(weatherIcon(7)).toBeNull();
    expect(weatherIcon(Number.NaN)).toBeNull();
  });
});
