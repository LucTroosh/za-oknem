import { describe, expect, it } from "vitest";

import { homeAlertsBanner } from "./alertsBanner";

describe("homeAlertsBanner", () => {
  it("is silent only for a confirmed all-clear", () => {
    expect(homeAlertsBanner({ kind: "none-confirmed", sources: ["x"] }, 0)).toBeNull();
  });
  it("never claims an all-clear when the source is silent", () => {
    const b = homeAlertsBanner({ kind: "unavailable", lastSuccessAt: null }, 0);
    expect(b?.tone).toBe("neutral");
    expect(b?.text).toContain("niedostępne");
  });
  it("counts a healthy list and caveats an old one", () => {
    expect(homeAlertsBanner({ kind: "list" }, 3)?.text).toContain("3");
    expect(homeAlertsBanner({ kind: "list-maybe-outdated", lastSuccessAt: null }, 3)?.text).toContain("nieaktualna");
  });
});
