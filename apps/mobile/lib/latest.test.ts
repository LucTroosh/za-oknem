import { describe, expect, it } from "vitest";

import { createLatestGuard } from "./latest";

describe("createLatestGuard", () => {
  it("only the most recently started request is latest", () => {
    const next = createLatestGuard();
    const first = next();
    expect(first()).toBe(true);
    const second = next();
    expect(first()).toBe(false);
    expect(second()).toBe(true);
  });
  it("a late response of an older request stays stale even after the newer one finished", () => {
    const next = createLatestGuard();
    const a = next();
    const b = next();
    expect(b()).toBe(true);
    expect(a()).toBe(false);
  });
});
