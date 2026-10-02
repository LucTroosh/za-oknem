// Welcome screen content + scrim (asset pack v2, docs/ui/asset-implementation-v2.md §4-§8).
// Pure data/functions so the copy and the contrast are unit-tested; the screen only lays it out.
import { type Palette, contrastRatio } from "./theme";

export const WELCOME_COPY = {
  brand: "Za Oknem",
  headline: "Sprawdź, co dzieje się wokół Ciebie",
  cta: "Zaczynamy",
  ctaHint: "Przechodzi do wyboru lokalizacji",
  privacy: "Bez konta. Bez profilowania.",
} as const;

// Lightweight domain cues (no water: no source yet). Icons are from the one vector library.
export const WELCOME_DOMAINS = [
  { label: "Powietrze", icon: "speedometer-outline" },
  { label: "Pogoda", icon: "partly-sunny-outline" },
  { label: "Pyłki", icon: "flower-outline" },
  { label: "Alerty", icon: "notifications-outline" },
] as const;

// The photo stays the same in both themes; only the scrim changes. Scrim base colour is the
// theme background, so text tokens keep their designed contrast on it.
// Layout: a short fade zone (photo -> panel) ABOVE the text block, then a constant-alpha panel
// behind ALL the text. Contrast is guaranteed (and tested) for the panel alpha only.
export const SCRIM_TEXT_ALPHA = 0.93;
export const SCRIM_FADE_HEIGHT = 96;
export const SCRIM_FADE_STEPS = 24;

// Smoothstep 0 -> SCRIM_TEXT_ALPHA: no visible banding, no hard edge at either end.
export const SCRIM_FADE_ALPHAS: number[] = Array.from({ length: SCRIM_FADE_STEPS }, (_, i) => {
  const t = (i + 0.5) / SCRIM_FADE_STEPS;
  return Math.round(SCRIM_TEXT_ALPHA * t * t * (3 - 2 * t) * 1000) / 1000;
});

export function scrimColor(p: Palette, alpha: number): string {
  const n = (i: number) => parseInt(p.bg.slice(1 + i * 2, 3 + i * 2), 16);
  return `rgba(${n(0)}, ${n(1)}, ${n(2)}, ${alpha})`;
}

function mix(fg: string, bg: string, a: number): string {
  const ch = (h: string, i: number) => parseInt(h.slice(1 + i * 2, 3 + i * 2), 16);
  const out = [0, 1, 2].map((i) => Math.round(ch(fg, i) * a + ch(bg, i) * (1 - a)));
  return `#${out.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

// Effective background of the text area over the worst-case photo pixel (pure black / white).
export function scrimWorstCases(p: Palette): string[] {
  return [mix(p.bg, "#000000", SCRIM_TEXT_ALPHA), mix(p.bg, "#ffffff", SCRIM_TEXT_ALPHA)];
}

// Every (text, scrim-over-photo) contrast the screen relies on, worst case.
export function welcomeContrasts(p: Palette): { name: string; ratio: number }[] {
  const out: { name: string; ratio: number }[] = [];
  for (const bg of scrimWorstCases(p)) {
    out.push({ name: "text", ratio: contrastRatio(p.text, bg) });
    out.push({ name: "textSecondary", ratio: contrastRatio(p.textSecondary, bg) });
    out.push({ name: "accent", ratio: contrastRatio(p.accent, bg) });
  }
  out.push({ name: "onAccent/accent", ratio: contrastRatio(p.onAccent, p.accent) });
  return out;
}
