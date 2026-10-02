import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiGet, apiPost } from "./api";

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

describe("apiPost / ApiError", () => {
  it("POSTs without a body and resolves with the JSON", async () => {
    const f = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ polling: "active" }) });
    vi.stubGlobal("fetch", f);

    await expect(apiPost("/api/v1/places/1/activate")).resolves.toEqual({ polling: "active" });
    expect(f.mock.calls[0][1].method).toBe("POST");
  });

  it("rejects with an ApiError that carries the status", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 429 }));

    const err = await apiPost("/api/v1/places/1/activate").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(429);
  });
});

describe("request timeout", () => {
  const hang = () => (_url: string, init: { signal: AbortSignal }) =>
    new Promise((_res, rej) => init.signal.addEventListener("abort", () => rej(new Error("aborted"))));
  it("a hung request rejects after the timeout", async () => {
    vi.stubGlobal("fetch", hang());
    await expect(apiGet("/api/v1/x", undefined, 20)).rejects.toThrow("aborted");
  });
  it("the caller's abort still cancels", async () => {
    vi.stubGlobal("fetch", hang());
    const c = new AbortController();
    const p = apiGet("/api/v1/x", c.signal, 5000);
    c.abort();
    await expect(p).rejects.toThrow("aborted");
  });
});
