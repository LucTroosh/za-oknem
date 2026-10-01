// Design tokens (TASK-12.1 foundation). Pure data + pure functions: no react-native import,
// so the palettes can be unit-tested (contrast, theme.test.ts). The hook is components/useTheme.ts.
//
// Direction: "okno" - a calm, cool, slightly misty light theme and a deep blue-night dark
// theme; the only saturated colours carry meaning (good / warning / danger / freshness).
// Colour is never the only carrier of meaning: every status also has a glyph and a word.
import type { FreshnessState } from "./freshness";

export type Scheme = "light" | "dark";

export type Palette = {
  bg: string;
  surface: string;
  border: string;
  text: string;
  textSecondary: string;
  // Dimmed = old/missing value (still readable, AA); weaker than textSecondary.
  dim: string;
  accent: string;
  onAccent: string;
  good: string;
  warning: string;
  danger: string;
  goodBg: string;
  warningBg: string;
  dangerBg: string;
  neutralBg: string;
  // Freshness statuses (ADR-012): text colours on `surface`.
  fresh: string;
  recent: string;
  stale: string;
  unavailable: string;
};

// good/danger keep the category colours used before (#2e7d32 / #b00020, AirIndexBadge).
// warning moves #b26a00 -> #8a5300 (the pollen cards already used it): #b26a00 is < 4.5:1.
export const LIGHT: Palette = {
  bg: "#eaf0f3",
  surface: "#ffffff",
  border: "#c5d1d8",
  text: "#13222a",
  textSecondary: "#44545e",
  dim: "#59666f",
  accent: "#0b5d7a",
  onAccent: "#ffffff",
  good: "#2e7d32",
  warning: "#8a5300",
  danger: "#b00020",
  goodBg: "#eef7ef",
  warningBg: "#fdf0d5",
  dangerBg: "#fbe6e9",
  neutralBg: "#e3eaee",
  fresh: "#2e7d32",
  recent: "#235f8c",
  stale: "#8a5300",
  unavailable: "#59666f",
};

export const DARK: Palette = {
  bg: "#0c151a",
  surface: "#15222a",
  border: "#2b3c46",
  text: "#e6eef2",
  textSecondary: "#a8b8c2",
  dim: "#93a3ad",
  accent: "#6cc4e3",
  onAccent: "#06242e",
  good: "#6fd08a",
  warning: "#f0b454",
  danger: "#ff8a9b",
  goodBg: "#12301c",
  warningBg: "#3a2b0d",
  dangerBg: "#3e1920",
  neutralBg: "#1d2d36",
  fresh: "#6fd08a",
  recent: "#7cc0ee",
  stale: "#f0b454",
  unavailable: "#93a3ad",
};

// useColorScheme() may return null/undefined (unknown) -> light.
export function paletteFor(scheme: string | null | undefined): Palette {
  return scheme === "dark" ? DARK : LIGHT;
}

export type Tone = "good" | "warning" | "danger" | "neutral";

// Text colour + tinted background for a status block (verdict, banners).
export function toneColors(p: Palette, tone: Tone): { fg: string; bg: string } {
  switch (tone) {
    case "good":
      return { fg: p.good, bg: p.goodBg };
    case "warning":
      return { fg: p.warning, bg: p.warningBg };
    case "danger":
      return { fg: p.danger, bg: p.dangerBg };
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
export const TEXT_PAIRS: ReadonlyArray<readonly [keyof Palette, keyof Palette]> = [
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

// Font sizes in dp; RN scales them with the user's font setting (allowFontScaling default).
// Nothing below 12: attributions used to be 10.
export const typo = {
  display: { fontSize: 28, lineHeight: 34, fontWeight: "700" },
  title: { fontSize: 20, lineHeight: 26, fontWeight: "600" },
  heading: { fontSize: 17, lineHeight: 23, fontWeight: "600" },
  body: { fontSize: 15, lineHeight: 21, fontWeight: "400" },
  strong: { fontSize: 15, lineHeight: 21, fontWeight: "600" },
  caption: { fontSize: 13, lineHeight: 18, fontWeight: "400" },
  micro: { fontSize: 12, lineHeight: 16, fontWeight: "400" },
} as const;

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;

// Different radii on purpose: the verdict is the biggest surface, chips are pills.
export const radius = { sm: 6, md: 12, lg: 20, pill: 999 } as const;

export const MIN_TOUCH = 44;

export type Theme = { scheme: Scheme; colors: Palette };
