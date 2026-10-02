// Design tokens (TASK-12.1 foundation). Pure data + pure functions: no react-native import,
// so the palettes can be unit-tested (contrast, theme.test.ts). The hook is components/useTheme.ts.
//
// Direction: "okno" - a calm, cool, slightly misty light theme and a deep blue-night dark
// theme; the only saturated colours carry meaning (good / warning / danger / freshness).
// Colour is never the only carrier of meaning: every status also has a glyph and a word.
import type { FreshnessState } from "./freshness";

export type Scheme = "light" | "dark";

// TASK-12.19: the user's choice. "system" = follow the phone live (the default).
export type ThemePref = "system" | "light" | "dark";
export const THEME_PREFS: readonly ThemePref[] = ["system", "light", "dark"];
export const THEME_LABEL: Record<ThemePref, string> = { system: "Systemowy", light: "Jasny", dark: "Ciemny" };

// Unknown/garbage from storage -> "system" (fail safe: never a surprise forced theme).
export function parseThemePref(x: unknown): ThemePref {
  return x === "light" || x === "dark" ? x : "system";
}

// What to hand to Appearance.setColorScheme: null clears the override (follows the system).
export function themeOverride(p: ThemePref): Scheme | null {
  return p === "light" || p === "dark" ? p : null;
}

export type Palette = {
  bg: string;
  surface: string;
  // Raised surface on top of `surface` (hero strips, segmented tracks): production UI v1.
  elevated: string;
  border: string;
  text: string;
  textSecondary: string;
  // Dimmed = old/missing value (still readable, AA); weaker than textSecondary.
  dim: string;
  // Primary teal (production UI v1 §3). `accent` is the name the whole app already uses.
  accent: string;
  onAccent: string;
  good: string;
  warning: string;
  danger: string;
  info: string;
  goodBg: string;
  warningBg: string;
  dangerBg: string;
  infoBg: string;
  neutralBg: string;
  // Domain tints (quick status tiles, domain icon containers): AA text colour on its own tint.
  airFg: string;
  airBg: string;
  weatherFg: string;
  weatherBg: string;
  pollenFg: string;
  pollenBg: string;
  uvFg: string;
  uvBg: string;
  // Freshness statuses (ADR-012): text colours on `surface`.
  fresh: string;
  recent: string;
  stale: string;
  unavailable: string;
};

// Production UI v1 (docs/ui/production-ui-v1.md §3). The spec's saturated accents (#3FAE52,
// #E89B25, #E8554E, #F6B61D ...) are < 4.5:1 as TEXT on their tints, so they live only as the
// tint/container hues; every text and icon colour below is the AA-safe variant of the same hue
// (theme.test.ts proves it). Colour is never the only carrier of a status: each has a glyph + word.
export const LIGHT: Palette = {
  bg: "#f4f8fa",
  surface: "#ffffff",
  elevated: "#eef4f7",
  border: "#e4ecef",
  text: "#102a3a",
  textSecondary: "#5e7180",
  dim: "#5f6f7c",
  accent: "#087b69",
  onAccent: "#ffffff",
  good: "#1f7a33",
  warning: "#8a5300",
  danger: "#b3261e",
  info: "#1f63a8",
  goodBg: "#eaf8ea",
  warningBg: "#fff5df",
  dangerBg: "#fff0ee",
  infoBg: "#e6f1fb",
  neutralBg: "#eef3f6",
  airFg: "#1b7a47",
  airBg: "#e8f7ee",
  weatherFg: "#8a5a00",
  weatherBg: "#fff1cc",
  pollenFg: "#4a7a12",
  pollenBg: "#ecf6dc",
  uvFg: "#8a5300",
  uvBg: "#fff4e0",
  fresh: "#1f7a33",
  recent: "#1f63a8",
  stale: "#8a5300",
  unavailable: "#5f6f7c",
};

// Deep blue-green, not pure black; same semantic relationships.
export const DARK: Palette = {
  bg: "#0c171b",
  surface: "#142328",
  elevated: "#1a2b31",
  border: "#27393f",
  text: "#eef5f6",
  textSecondary: "#a8bac1",
  dim: "#93a8b0",
  accent: "#5ed4bd",
  onAccent: "#06241f",
  good: "#7ad98c",
  warning: "#f4be5e",
  danger: "#ff9a93",
  info: "#8cc4f5",
  goodBg: "#12301c",
  warningBg: "#3a2b0d",
  dangerBg: "#3e1920",
  infoBg: "#142b40",
  neutralBg: "#1a2b31",
  airFg: "#7ad9a0",
  airBg: "#143326",
  weatherFg: "#f6c65a",
  weatherBg: "#3a2d0a",
  pollenFg: "#a5d96a",
  pollenBg: "#27360f",
  uvFg: "#f7b955",
  uvBg: "#3a2b0d",
  fresh: "#7ad98c",
  recent: "#8cc4f5",
  stale: "#f4be5e",
  unavailable: "#93a8b0",
};

export type Domain = "air" | "weather" | "pollen" | "uv";

// Icon colour + tint for a domain container / tile.
export function domainColors(p: Palette, d: Domain): { fg: string; bg: string } {
  switch (d) {
    case "air":
      return { fg: p.airFg, bg: p.airBg };
    case "weather":
      return { fg: p.weatherFg, bg: p.weatherBg };
    case "pollen":
      return { fg: p.pollenFg, bg: p.pollenBg };
    default:
      return { fg: p.uvFg, bg: p.uvBg };
  }
}

// Card elevation (§15): low-opacity, wide-blur shadow + Android elevation in light mode; in dark
// mode the elevated surface does the separation and the shadow is dropped. No hard outlines.
export function elevation(scheme: Scheme, level: 1 | 2 = 1): Record<string, unknown> {
  if (scheme === "dark") return {};
  return level === 2
    ? { shadowColor: "#0b2a3a", shadowOpacity: 0.1, shadowRadius: 18, shadowOffset: { width: 0, height: 6 }, elevation: 4 }
    : { shadowColor: "#0b2a3a", shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 3 }, elevation: 2 };
}

// useColorScheme() may return null/undefined (unknown) -> light.
export function paletteFor(scheme: string | null | undefined): Palette {
  return scheme === "dark" ? DARK : LIGHT;
}

export type Tone = "good" | "warning" | "danger" | "info" | "neutral";

// Text colour + tinted background for a status block (verdict, banners).
export function toneColors(p: Palette, tone: Tone): { fg: string; bg: string } {
  switch (tone) {
    case "good":
      return { fg: p.good, bg: p.goodBg };
    case "warning":
      return { fg: p.warning, bg: p.warningBg };
    case "danger":
      return { fg: p.danger, bg: p.dangerBg };
    case "info":
      return { fg: p.info, bg: p.infoBg };
    default:
      return { fg: p.textSecondary, bg: p.neutralBg };
  }
}

export function freshnessColor(p: Palette, state: FreshnessState): string {
  switch (state) {
    case "FRESH":
      return p.fresh;
    case "RECENT":
      return p.recent;
    case "STALE":
      return p.stale;
    default:
      return p.unavailable;
  }
}

// Every (foreground, background) pair the UI really uses; theme.test.ts requires >= 4.5:1
// for each in both palettes (WCAG AA, normal text).
export const TEXT_PAIRS: readonly (readonly [keyof Palette, keyof Palette])[] = [
  ["text", "bg"],
  ["text", "surface"],
  ["textSecondary", "bg"],
  ["textSecondary", "surface"],
  ["dim", "surface"],
  ["accent", "bg"],
  ["accent", "surface"],
  ["onAccent", "accent"],
  ["fresh", "surface"],
  ["recent", "surface"],
  ["stale", "surface"],
  ["unavailable", "surface"],
  ["good", "surface"],
  ["good", "bg"],
  ["warning", "bg"],
  ["danger", "bg"],
  ["warning", "surface"],
  ["danger", "surface"],
  ["good", "goodBg"],
  ["warning", "warningBg"],
  ["danger", "dangerBg"],
  ["textSecondary", "neutralBg"],
  ["text", "goodBg"],
  ["text", "warningBg"],
  ["text", "dangerBg"],
  ["text", "neutralBg"],
  ["text", "elevated"],
  ["textSecondary", "elevated"],
  ["accent", "elevated"],
  ["info", "infoBg"],
  ["info", "surface"],
  ["text", "infoBg"],
  ["airFg", "airBg"],
  ["weatherFg", "weatherBg"],
  ["pollenFg", "pollenBg"],
  ["uvFg", "uvBg"],
  ["text", "airBg"],
  ["text", "weatherBg"],
  ["text", "pollenBg"],
  ["text", "uvBg"],
  ["textSecondary", "airBg"],
  ["textSecondary", "weatherBg"],
  ["textSecondary", "pollenBg"],
  ["textSecondary", "uvBg"],
  ["dim", "bg"],
];

function channel(hex: string, i: number): number {
  const v = parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16) / 255;
  return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  return 0.2126 * channel(hex, 0) + 0.7152 * channel(hex, 1) + 0.0722 * channel(hex, 2);
}

// WCAG 2.x contrast ratio of two #rrggbb colours (1..21).
export function contrastRatio(fg: string, bg: string): number {
  const [a, b] = [luminance(fg), luminance(bg)].sort((x, y) => y - x);
  return (a + 0.05) / (b + 0.05);
}

// Production UI v1 §3 typography (dp; RN scales them with the user's font setting). Nothing below 12.
export const typo = {
  hero: { fontSize: 30, lineHeight: 36, fontWeight: "800" },
  display: { fontSize: 28, lineHeight: 34, fontWeight: "800" },
  title: { fontSize: 22, lineHeight: 28, fontWeight: "700" },
  heading: { fontSize: 18, lineHeight: 24, fontWeight: "700" },
  cardTitle: { fontSize: 16, lineHeight: 22, fontWeight: "700" },
  strong: { fontSize: 15, lineHeight: 22, fontWeight: "600" },
  body: { fontSize: 15, lineHeight: 22, fontWeight: "400" },
  supporting: { fontSize: 14, lineHeight: 20, fontWeight: "400" },
  caption: { fontSize: 13, lineHeight: 18, fontWeight: "400" },
  meta: { fontSize: 12, lineHeight: 17, fontWeight: "500" },
  micro: { fontSize: 12, lineHeight: 16, fontWeight: "400" },
} as const;

export const space = { xs: 4, sm: 8, md: 12, lg: 16, ml: 20, xl: 24, xxl: 32 } as const;

// §3: hero / major 24, regular card 18, compact tile 16, inputs 16, pills 999.
export const radius = { sm: 8, md: 16, card: 18, lg: 20, hero: 24, pill: 999 } as const;

// Production UI v1: 48 x 48 dp minimum.
export const MIN_TOUCH = 48;

export type Theme = { scheme: Scheme; colors: Palette };
