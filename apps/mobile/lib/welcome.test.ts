import { describe, expect, it } from "vitest";

import { DARK, LIGHT } from "./theme";
import {
  BOTTOM_VEIL,
  BRAND_GAP,
  CAPSULE_ALPHA,
  WELCOME_CTA,
  FOOTER_CHIP_ALPHA,
  TOP_VEIL,
  VEIL_STEPS,
  WELCOME_COPY,
  WELCOME_DOMAINS,
  WELCOME_TYPE,
  heroFrame,
  scrimColor,
  veilAlphas,
  welcomeContrasts,
  welcomeDomainColumns,
  welcomeTintColors,
} from "./welcome";

describe("welcome copy", () => {
  it("uses the approved strings", () => {
    expect(WELCOME_COPY.brand).toBe("Za Oknem");
    expect(WELCOME_COPY.headline).toBe("Sprawdź, co u Ciebie słychać");
    expect(WELCOME_COPY.privacy).toBe("Bez konta. Bez reklam.");
    expect(WELCOME_COPY.cta).toBe("Zaczynamy");
    // "Alergeny" is only the Welcome label of the pollen domain.
    expect(WELCOME_DOMAINS.map((d) => d.label)).toEqual(["Powietrze", "Pogoda", "Alergeny", "Alerty"]);
    expect(WELCOME_DOMAINS.map((d) => d.icon)).toEqual(["leaf", "partly-sunny", "flower", "alert-circle"]);
  });
  it("capsule is one row of four, 2 x 2 at an enlarged system font", () => {
    expect(welcomeDomainColumns(1)).toBe(4);
    expect(welcomeDomainColumns(1.15)).toBe(4);
    expect(welcomeDomainColumns(1.3)).toBe(2);
    expect(welcomeDomainColumns(2)).toBe(2);
  });
  it("domain colours: air green, weather amber, allergens light green, alerts red (never blue: reserved for Water)", () => {
    for (const p of [LIGHT, DARK]) {
      expect(welcomeTintColors(p, "air")).toEqual({ fg: p.airFg, bg: p.airBg });
      expect(welcomeTintColors(p, "weather")).toEqual({ fg: p.weatherFg, bg: p.weatherBg });
      expect(welcomeTintColors(p, "pollen")).toEqual({ fg: p.pollenFg, bg: p.pollenBg });
      expect(welcomeTintColors(p, "danger")).toEqual({ fg: p.danger, bg: p.dangerBg });
    }
    expect(WELCOME_DOMAINS).toHaveLength(4); // no Water on Welcome yet
  });
  it("dark CTA is calmer than the mint accent but keeps a dark label", () => {
    expect(WELCOME_CTA.dark(DARK).bg).not.toBe(DARK.accent);
    expect(WELCOME_CTA.light(LIGHT).bg).toBe(LIGHT.accent);
  });
  it("light capsule is slightly translucent, dark is the opaque elevated surface", () => {
    expect(CAPSULE_ALPHA.light).toBeLessThan(1);
    expect(CAPSULE_ALPHA.dark).toBe(1);
  });
});

describe("welcome typography", () => {
  it("brand name is the strongest line, the eyebrow a lighter supporting line", () => {
    expect(WELCOME_TYPE.brand.fontSize).toBeGreaterThanOrEqual(36);
    expect(WELCOME_TYPE.brand.fontSize).toBeLessThanOrEqual(42);
    expect(WELCOME_TYPE.eyebrow.fontSize).toBeGreaterThanOrEqual(16);
    expect(WELCOME_TYPE.eyebrow.fontSize).toBeLessThanOrEqual(18);
    expect(WELCOME_TYPE.brand.fontSize).toBeGreaterThan(WELCOME_TYPE.eyebrow.fontSize * 2);
    expect(WELCOME_TYPE.brand.fontFamily).toBe("NunitoSans_800ExtraBold");
    expect(WELCOME_TYPE.eyebrow.fontFamily).toBe("NunitoSans_600SemiBold");
    expect(BRAND_GAP).toBe(10); // +6 over the previous 4
  });
});

describe("hero framing (panorama, not clouds)", () => {
  const phones: [number, number][] = [[360, 740], [390, 844], [412, 915], [320, 568], [430, 932], [600, 960]];
  it("always covers the whole screen (no empty edge)", () => {
    for (const [w, h] of phones) {
      const f = heroFrame(w, h);
      expect(f.left).toBeLessThanOrEqual(0);
      expect(f.top).toBeLessThanOrEqual(0);
      expect(f.left + f.width).toBeGreaterThanOrEqual(w - 0.5);
      expect(f.top + f.height).toBeGreaterThanOrEqual(h - 0.5);
    }
  });
  it("shows roughly 35-40% sky and 60-65% city / river / greenery on typical phones", () => {
    for (const [w, h] of [[360, 740], [390, 844], [412, 915], [430, 932]] as [number, number][]) {
      const sky = heroFrame(w, h).horizonY / h;
      expect(sky, `${w}x${h}`).toBeGreaterThan(0.33);
      expect(sky, `${w}x${h}`).toBeLessThan(0.42);
    }
  });
});

describe("veils", () => {
  it("fade monotonically from the solid edge to nothing", () => {
    for (const max of [TOP_VEIL.light, TOP_VEIL.dark, BOTTOM_VEIL.light, BOTTOM_VEIL.dark]) {
      const a = veilAlphas(max, 0.6);
      expect(a).toHaveLength(VEIL_STEPS);
      for (let i = 1; i < a.length; i++) expect(a[i]).toBeLessThanOrEqual(a[i - 1]);
      expect(a[0]).toBe(max);
      expect(a.at(-1)).toBeLessThan(0.01);
    }
  });
  it("dark veils are ~15-20% lighter than before (warm sunset kept)", () => {
    expect(TOP_VEIL.dark).toBeLessThanOrEqual(0.66 * 0.87);
    expect(TOP_VEIL.dark).toBeGreaterThanOrEqual(0.66 * 0.78);
    expect(BOTTOM_VEIL.dark).toBeLessThanOrEqual(0.55 * 0.85);
  });
  it("stay subtle: no big white patch over the panorama", () => {
    expect(BOTTOM_VEIL.light).toBeLessThanOrEqual(0.35);
    expect(TOP_VEIL.light).toBeLessThanOrEqual(0.4);
    expect(FOOTER_CHIP_ALPHA).toBeLessThan(1);
  });
  it("is the theme background with alpha", () => {
    expect(scrimColor(LIGHT, 0.5)).toBe("rgba(244, 248, 250, 0.5)");
    expect(scrimColor(DARK, 1)).toBe("rgba(12, 23, 27, 1)");
  });
});

describe("contrast (AA, worst-case photo pixel)", () => {
  for (const [name, p, scheme] of [["light", LIGHT, "light"], ["dark", DARK, "dark"]] as const) {
    it(`${name}: all Welcome text and icons are AA`, () => {
      for (const { name: n, ratio } of welcomeContrasts(p, scheme)) expect(ratio, n).toBeGreaterThanOrEqual(4.5);
    });
  }
});
