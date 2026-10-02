import { describe, expect, it } from "vitest";

import { DARK, LIGHT } from "./theme";
import { SCRIM_FADE_ALPHAS, SCRIM_TEXT_ALPHA, WELCOME_COPY, WELCOME_DOMAINS, scrimColor, welcomeContrasts } from "./welcome";

describe("welcome copy (contract §4)", () => {
  it("uses the approved strings", () => {
    expect(WELCOME_COPY.headline).toBe("Sprawdź, co dzieje się wokół Ciebie");
    expect(WELCOME_COPY.privacy).toBe("Bez konta. Bez profilowania.");
    expect(WELCOME_COPY.cta).toBe("Zaczynamy");
    expect(WELCOME_DOMAINS.map((d) => d.label)).toEqual(["Powietrze", "Pogoda", "Pyłki", "Alerty"]);
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
    expect(scrimColor(LIGHT, 0.5)).toBe("rgba(234, 240, 243, 0.5)");
    expect(scrimColor(DARK, 1)).toBe("rgba(12, 21, 26, 1)");
  });
  for (const [name, p] of [["light", LIGHT], ["dark", DARK]] as const) {
    it(`${name}: text is AA over the scrim on the worst-case photo pixel`, () => {
      for (const { name: n, ratio } of welcomeContrasts(p)) expect(ratio, n).toBeGreaterThanOrEqual(4.5);
    });
  }
});
