import { afterEach, describe, expect, it, vi } from "vitest";

import { apiGet } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiGet", () => {
  it("resolves with the parsed JSON body on a 200", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ hello: "world" }) }),
    );

    await expect(apiGet("/api/v1/health")).resolves.toEqual({ hello: "world" });
  });

  it("rejects when the response is not ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));

    await expect(apiGet("/api/v1/health")).rejects.toThrow("503");
  });
});
