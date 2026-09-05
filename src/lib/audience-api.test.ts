import { afterEach, describe, expect, it, vi } from "vitest";
import { audienceApi } from "./audience-api";

describe("audienceApi.delete", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("fecha e remove uma sala usando a credencial do apresentador", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ ok: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await audienceApi.delete("CG-4321", "presenter-token");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/salas/CG-4321",
      expect.objectContaining({
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          "X-Presenter-Token": "presenter-token",
        },
      }),
    );
  });
});
