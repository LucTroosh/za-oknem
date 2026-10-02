import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// TASK-12.16 acceptance: no bathing-site / drinking-water UI exists in production code
// (ADR-021, ADR-028: no source yet, so no "coming soon" and no mock either).
const ROOTS = ["app", "components"];
const FORBIDDEN = /kąpiel|kapiel|bathing|woda pitna|wody pitnej|drinking/i;

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? files(p) : /\.tsx?$/.test(n) ? [p] : [];
  });
}

describe("no bathing-water / drinking-water UI", () => {
  it("has no such wording in screens and components", () => {
    const hits = ROOTS.flatMap(files).filter((f) => FORBIDDEN.test(readFileSync(f, "utf8")));
    expect(hits).toEqual([]);
  });
});
