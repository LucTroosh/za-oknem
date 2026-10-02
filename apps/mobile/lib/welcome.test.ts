import { describe, expect, it } from "vitest";

import { DARK, LIGHT } from "./theme";
import { SCRIM_FADE_ALPHAS, SCRIM_TEXT_ALPHA, WELCOME_COPY, WELCOME_DOMAINS, scrimColor, welcomeContrasts, welcomeDomainColumns, welcomeTintColors } from "./welcome";

describe("welcome copy (contract §4)", () => {
  it("uses the approved strings", () => {
    expect(WELCOME_COPY.brand).toBe("Za Oknem");
    expect(WELCOME_COPY.headline).toBe("Sprawdź, co słychać u Ciebie za oknem");
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
  it("every domain has its own tint; alerts use the neutral info tint, not a severity colour", () => {
    for (const p of [LIGHT, DARK]) {
      expect(welcomeTintColors(p, "air")).toEqual({ fg: p.airFg, bg: p.airBg });
      expect(welcomeTintColors(p, "info")).toEqual({ fg: p.info, bg: p.infoBg });
    }
  });
});

describe("scrim", () => {
  it("fades in monotonically and ends at the panel alpha", () => {
    for (let i = 1; i < SCRIM_FADE_ALPHAS.length; i++) expect(SCRIM_FADE_ALPHAS[i]).toBeGreaterThanOrEqual(SCRIM_FADE_ALPHAS[i - 1]);
    expect(SCRIM_FADE_ALPHAS[0]).toBeLessThan(0.01);
    expect(SCRIM_FADE_ALPHAS.at(-1)).toBeLessThanOrEqual(SCRIM_TEXT_ALPHA);
    expect(SCRIM_FADE_ALPHAS.at(-1)).toBeGreaterThan(SCRIM_TEXT_ALPHA - 0.01);
  });
  it("is the theme background with alpha", () => {
    expect(scrimColor(LIGHT, 0.5)).toBe("rgba(244, 248, 250, 0.5)");
    expect(scrimColor(DARK, 1)).toBe("rgba(12, 23, 27, 1)");
  });
  for (const [name, p] of [["light", LIGHT], ["dark", DARK]] as const) {
    it(`${name}: text is AA over the scrim on the worst-case photo pixel`, () => {
      for (const { name: n, ratio } of welcomeContrasts(p)) expect(ratio, n).toBeGreaterThanOrEqual(4.5);
    });
  }
});
