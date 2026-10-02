import { describe, expect, it } from "vitest";

import { severityTone } from "./alertSeverity";

describe("severityTone", () => {
  it("maps IMGW degrees: 3 danger, 1-2 warning", () => {
    expect(severityTone("3")).toBe("danger");
    expect(severityTone("2")).toBe("warning");
    expect(severityTone(" 1 ")).toBe("warning");
  });
  it("does not guess for unknown or missing degrees", () => {
    expect(severityTone("4")).toBe("neutral");
    expect(severityTone("")).toBe("neutral");
    expect(severityTone(null)).toBe("neutral");
  });
});
