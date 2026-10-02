// Welcome screen content, hero framing and veils (asset pack v2, docs/ui/asset-implementation-v2.md
// §4-§8). Pure data/functions so the copy, the crop and the contrast are unit-tested; the screen only
// lays it out.
import { type Palette, contrastRatio, domainColors, toneColors } from "./theme";

export const WELCOME_COPY = {
  brand: "Za Oknem",
  headline: "Sprawdź, co u Ciebie słychać",
  cta: "Zaczynamy",
  ctaHint: "Przechodzi do wyboru lokalizacji",
  privacy: "Bez konta. Bez reklam.",
} as const;

// Four domain cues in one soft capsule (no water: no source yet). Labels are PRESENTATION only:
// "Alergeny" is the Welcome wording of the pollen domain, nothing in the logic is renamed. Icons
// are from the one vector library; `tint` picks the domain colour (alerts use the neutral info tint,
// not a severity colour).
export const WELCOME_DOMAINS = [
  { label: "Powietrze", icon: "leaf", tint: "air" },
  { label: "Pogoda", icon: "partly-sunny", tint: "weather" },
  { label: "Alergeny", icon: "flower", tint: "pollen" },
  { label: "Alerty", icon: "alert-circle", tint: "info" },
] as const;

export type WelcomeTint = (typeof WELCOME_DOMAINS)[number]["tint"];

export function welcomeTintColors(p: Palette, tint: WelcomeTint): { fg: string; bg: string } {
  return tint === "info" ? toneColors(p, "info") : domainColors(p, tint);
}

// One row of four at normal font size; 2 x 2 once the system font is enlarged so labels never clip.
export const welcomeDomainColumns = (fontScale: number): 2 | 4 => (fontScale >= 1.3 ? 2 : 4);

// ---- hero framing ----------------------------------------------------------------------------
// The approved photo (1242 x 2688) is half sky. Plain `cover` shows all of it, so the panorama
// (city, river, greenery) ends up under the text. Instead the same file is zoomed and anchored to a
// window that starts below the top of the sky: about 38% of the screen is sky, the rest is the city,
// the river and the foliage. Same asset, same brand direction - only the crop changes.
export const HERO_SIZE = { width: 1242, height: 2688 } as const;
export const HERO_HORIZON = 0.52; // horizon line, as a fraction of the photo height
export const HERO_ZOOM = 1.28; // on top of `cover`
export const HERO_WINDOW = { x: 0.06, y: 0.22 } as const; // top-left of the visible window (fractions)

export type HeroFrame = { width: number; height: number; left: number; top: number; horizonY: number };

export function heroFrame(screenW: number, screenH: number): HeroFrame {
  const cover = Math.max(screenW / HERO_SIZE.width, screenH / HERO_SIZE.height);
  const width = HERO_SIZE.width * cover * HERO_ZOOM;
  const height = HERO_SIZE.height * cover * HERO_ZOOM;
  // Never leave an empty edge: the frame always covers the screen.
  const left = Math.min(0, Math.max(screenW - width, -HERO_WINDOW.x * width));
  const top = Math.min(0, Math.max(screenH - height, -HERO_WINDOW.y * height));
  return { width, height, left, top, horizonY: top + HERO_HORIZON * height };
}

// ---- veils -----------------------------------------------------------------------------------
// Two light veils in the theme background colour replace the old white fade: a top one behind the
// brand text (over the sky) and a short bottom one that only blends the photo into the screen edge.
// Capsule and CTA are solid surfaces, the footer sits on its own translucent chip, so the panorama
// stays visible. Veils are stacks of strips (no gradient dependency).
export const TOP_VEIL = { light: 0.34, dark: 0.66 } as const; // plateau alpha behind the brand text
export const TOP_VEIL_HEIGHT = 320;
export const TOP_VEIL_PLATEAU = 0.6; // fraction of the height at full alpha, then a smooth fade
export const BOTTOM_VEIL = { light: 0.3, dark: 0.55 } as const;
export const BOTTOM_VEIL_HEIGHT = 240;
export const VEIL_STEPS = 64;
export const FOOTER_CHIP_ALPHA = 0.96;

const smooth = (t: number) => t * t * (3 - 2 * t);

// Alpha per strip, ordered from the veil's solid edge to its faded edge.
export function veilAlphas(max: number, plateau = 0): number[] {
  return Array.from({ length: VEIL_STEPS }, (_, i) => {
    const t = (i + 0.5) / VEIL_STEPS;
    const f = t <= plateau ? 1 : 1 - smooth((t - plateau) / (1 - plateau));
    return Math.round(max * f * 1000) / 1000;
  });
}

export function scrimColor(p: Palette, alpha: number): string {
  const n = (i: number) => parseInt(p.bg.slice(1 + i * 2, 3 + i * 2), 16);
  return `rgba(${n(0)}, ${n(1)}, ${n(2)}, ${alpha})`;
}

// The footer chip: the theme surface at FOOTER_CHIP_ALPHA (translucent, so it belongs to the photo).
export function footerChipColor(p: Palette): string {
  const n = (i: number) => parseInt(p.surface.slice(1 + i * 2, 3 + i * 2), 16);
  return `rgba(${n(0)}, ${n(1)}, ${n(2)}, ${FOOTER_CHIP_ALPHA})`;
}

function mix(fg: string, bg: string, a: number): string {
  const ch = (h: string, i: number) => parseInt(h.slice(1 + i * 2, 3 + i * 2), 16);
  const out = [0, 1, 2].map((i) => Math.round(ch(fg, i) * a + ch(bg, i) * (1 - a)));
  return `#${out.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

// Luminance-equivalent grays of the sampled extremes of the photo (relative luminance measured on
// welcome-hero-1242x2688.jpg over the area the brand text can occupy: darkest sky 0.239, brightest
// cloud 0.948). Contrast is checked against both, so any pixel in between is covered. If the asset
// is ever replaced, re-measure and update these.
export const SKY_EXTREMES = { darkest: "#868686", brightest: "#f9f9f9" } as const;
// ... and of the foliage/water strip behind the footer chip: from near black to bright highlights.
export const FOOTER_ZONE_EXTREMES = { darkest: "#000000", brightest: "#d9d9d9" } as const;

// Every (text, background) contrast the screen relies on, worst case.
export function welcomeContrasts(p: Palette, scheme: "light" | "dark"): { name: string; ratio: number }[] {
  const out: { name: string; ratio: number }[] = [];
  const veil = TOP_VEIL[scheme];
  for (const px of Object.values(SKY_EXTREMES)) {
    const bg = mix(p.bg, px, veil);
    out.push({ name: `brand over sky ${px}`, ratio: contrastRatio(p.text, bg) });
    out.push({ name: `headline over sky ${px}`, ratio: contrastRatio(p.text, bg) });
  }
  for (const px of Object.values(FOOTER_ZONE_EXTREMES)) {
    out.push({ name: `footer over chip ${px}`, ratio: contrastRatio(p.textSecondary, mix(p.surface, px, FOOTER_CHIP_ALPHA)) });
  }
  out.push({ name: "onAccent/accent", ratio: contrastRatio(p.onAccent, p.accent) });
  // The capsule is a solid surface (not photo-dependent): label + icons on it.
  for (const tint of WELCOME_DOMAINS.map((d) => d.tint)) {
    const c = welcomeTintColors(p, tint);
    out.push({ name: `icon ${tint}`, ratio: contrastRatio(c.fg, c.bg) });
  }
  out.push({ name: "capsule label", ratio: contrastRatio(p.text, scheme === "dark" ? p.elevated : p.surface) });
  return out;
}
