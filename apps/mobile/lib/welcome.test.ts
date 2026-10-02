import { describe, expect, it } from "vitest";

import { DARK, LIGHT, contrastRatio } from "./theme";
import {
  BOTTOM_VEIL,
  BRAND_GAP,
  CAPSULE_ALPHA,
  LOCAL_SCRIM,
  LOCAL_SCRIM_LAYERS,
  LOGO_SIZE,
  WELCOME_TEXT,
  localScrimLayerAlpha,
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
    // dark keeps the shared red tone; light uses a darker red on a soft red
    expect(welcomeTintColors(DARK, "danger", "dark")).toEqual({ fg: DARK.danger, bg: DARK.dangerBg });
    expect(welcomeTintColors(LIGHT, "danger", "light").fg).toBe("#86100a");
    // dark mode keeps the shared tints
    expect(welcomeTintColors(DARK, "air", "dark")).toEqual({ fg: DARK.airFg, bg: DARK.airBg });
    expect(welcomeTintColors(DARK, "weather", "dark")).toEqual({ fg: DARK.weatherFg, bg: DARK.weatherBg });
    expect(WELCOME_DOMAINS).toHaveLength(4); // no Water on Welcome yet
  });
  it("light mode icons are stronger than the shared pastel tints (Weather above all)", () => {
    for (const tint of ["air", "weather", "pollen"] as const) {
      const strong = contrastRatio(welcomeTintColors(LIGHT, tint, "light").fg, welcomeTintColors(LIGHT, tint, "light").bg);
      const shared = welcomeTintColors(LIGHT, tint, "dark");
      expect(strong, tint).toBeGreaterThan(contrastRatio(shared.fg, shared.bg));
      expect(strong, tint).toBeGreaterThanOrEqual(7); // AAA for the symbol on its circle
    }
    const w = welcomeTintColors(LIGHT, "weather", "light");
    expect(contrastRatio(w.bg, LIGHT.surface)).toBeGreaterThan(contrastRatio(LIGHT.weatherBg, LIGHT.surface));
    const red = welcomeTintColors(LIGHT, "danger", "light");
    expect(contrastRatio(red.fg, red.bg)).toBeGreaterThanOrEqual(7);
  });
  it("dark CTA is calmer than the mint accent but keeps a dark label", () => {
    expect(WELCOME_CTA.dark(DARK).bg).not.toBe(DARK.accent);
    expect(WELCOME_CTA.light(LIGHT).bg).toBe(LIGHT.accent);
  });
  it("light capsule is milky/translucent (not pure white), dark is the opaque elevated surface", () => {
    expect(CAPSULE_ALPHA.light).toBeLessThan(0.9);
    expect(CAPSULE_ALPHA.dark).toBe(1);
  });
});

describe("welcome typography", () => {
  it("brand name is the strongest line, the eyebrow a lighter supporting line", () => {
    expect(WELCOME_TYPE.brand.fontSize).toBe(40);
    expect(WELCOME_TYPE.eyebrow.fontSize).toBe(18);
    expect(WELCOME_TYPE.brand.fontSize).toBeGreaterThan(WELCOME_TYPE.eyebrow.fontSize * 2);
    expect(WELCOME_TYPE.brand.fontFamily).toBe("Nunito_800ExtraBold");
    expect(WELCOME_TYPE.eyebrow.fontFamily).toBe("Nunito_600SemiBold");
    expect(WELCOME_TYPE.label.fontFamily).toBe("Nunito_700Bold");
    expect(BRAND_GAP).toBe(16); // +6 over the previous 10
    expect(LOGO_SIZE).toBeGreaterThanOrEqual(76 * 0.92);
    expect(LOGO_SIZE).toBeLessThanOrEqual(76 * 0.95); // ~5-8% smaller than 76
  });
  it("text colours are the specified ones", () => {
    expect(WELCOME_TEXT.light).toEqual({ brand: "#0F2F5C", intro: "#2F5385" });
    expect(WELCOME_TEXT.dark).toEqual({ brand: "#F4F7F8", intro: "#D7E0E4" });
  });
  it("the local scrim layers add up to the target alpha at the centre", () => {
    for (const total of [LOCAL_SCRIM.light, LOCAL_SCRIM.dark]) {
      const a = localScrimLayerAlpha(total);
      expect(1 - (1 - a) ** LOCAL_SCRIM_LAYERS).toBeCloseTo(total, 3);
    }
    expect(LOCAL_SCRIM.light).toBeLessThanOrEqual(0.4); // "very light"
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
  it("dark global veils are ~15% lighter than before (warm sunset kept)", () => {
    expect(TOP_VEIL.dark).toBeLessThanOrEqual(0.57 * 0.86);
    expect(TOP_VEIL.dark).toBeGreaterThanOrEqual(0.57 * 0.8);
    expect(BOTTOM_VEIL.dark).toBeLessThanOrEqual(0.45 * 0.86);
  });
  it("stay subtle: no big white patch over the panorama", () => {
    expect(BOTTOM_VEIL.light).toBeLessThanOrEqual(0.35);
    expect(TOP_VEIL.light).toBeLessThanOrEqual(0.4);
    expect(FOOTER_CHIP_ALPHA).toBeLessThan(0.7); // fainter than before: a hint, not a pill
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
