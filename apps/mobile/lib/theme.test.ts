import { describe, expect, it } from "vitest";

import { DARK, LIGHT, TEXT_PAIRS, THEME_LABEL, THEME_PREFS, contrastRatio, freshnessColor, paletteFor, parseThemePref, themeOverride, toneColors } from "./theme";

describe("contrastRatio", () => {
  it("matches the WCAG reference values", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 5);
    expect(contrastRatio("#ffffff", "#ffffff")).toBeCloseTo(1, 5);
    expect(contrastRatio("#777777", "#ffffff")).toBeCloseTo(4.48, 1);
  });
});

describe("palettes", () => {
  for (const [name, palette] of [
    ["light", LIGHT],
    ["dark", DARK],
  ] as const) {
    for (const [fg, bg] of TEXT_PAIRS) {
      it(`${name}: ${fg} on ${bg} is >= 4.5:1`, () => {
        expect(contrastRatio(palette[fg], palette[bg])).toBeGreaterThanOrEqual(4.5);
      });
    }
  }

  it("light and dark are real hex colours of the same shape", () => {
    expect(Object.keys(LIGHT).sort()).toEqual(Object.keys(DARK).sort());
    for (const v of [...Object.values(LIGHT), ...Object.values(DARK)]) {
      expect(v).toMatch(/^#[0-9a-f]{6}$/);
    }
  });

  it("picks dark only for 'dark' (unknown scheme -> light)", () => {
    expect(paletteFor("dark")).toBe(DARK);
    expect(paletteFor("light")).toBe(LIGHT);
    expect(paletteFor(null)).toBe(LIGHT);
    expect(paletteFor(undefined)).toBe(LIGHT);
  });

  it("freshness states and tones resolve to palette colours", () => {
    expect(freshnessColor(DARK, "FRESH")).toBe(DARK.fresh);
    expect(freshnessColor(DARK, "RECENT")).toBe(DARK.recent);
    expect(freshnessColor(DARK, "STALE")).toBe(DARK.stale);
    expect(freshnessColor(DARK, "UNAVAILABLE")).toBe(DARK.unavailable);
    expect(toneColors(LIGHT, "danger")).toEqual({ fg: LIGHT.danger, bg: LIGHT.dangerBg });
    expect(toneColors(LIGHT, "neutral").bg).toBe(LIGHT.neutralBg);
  });
});

describe("theme choice", () => {
  it("offers Systemowy / Jasny / Ciemny, system first", () => {
    expect(THEME_PREFS.map((p) => THEME_LABEL[p])).toEqual(["Systemowy", "Jasny", "Ciemny"]);
  });
  it("system clears the override (follows the phone live), light/dark force a scheme", () => {
    expect(themeOverride("system")).toBeNull();
    expect(themeOverride("light")).toBe("light");
    expect(themeOverride("dark")).toBe("dark");
  });
  it("parses only known values", () => {
    expect(parseThemePref("dark")).toBe("dark");
    expect(parseThemePref("light")).toBe("light");
    expect(parseThemePref("system")).toBe("system");
    expect(parseThemePref(undefined)).toBe("system");
    expect(parseThemePref("sepia")).toBe("system");
  });
  it("a forced scheme gives the matching palette", () => {
    expect(paletteFor(themeOverride("dark"))).toBe(DARK);
    expect(paletteFor(themeOverride("light"))).toBe(LIGHT);
  });
});
