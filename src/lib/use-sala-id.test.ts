// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { participantIdFor } from "./use-sala";

describe("participantIdFor", () => {
  afterEach(() => {
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("creates a valid persistent participant id when HTTP omits crypto.randomUUID", () => {
    vi.stubGlobal("crypto", {
      getRandomValues: (bytes: Uint8Array) => {
        for (let index = 0; index < bytes.length; index += 1) bytes[index] = index;
        return bytes;
      },
    });

    const id = participantIdFor("CG-HTTP");
    expect(id).toMatch(/^[A-Za-z0-9_-]{8,96}$/);
    expect(participantIdFor("CG-HTTP")).toBe(id);
  });
});
