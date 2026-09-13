import { describe, expect, it } from "vitest";

import { BRAND_DESTINATION, HEADER_LINKS, HEADER_NAV_CLASS } from "./Header";

describe("Header navigation", () => {
  it("expõe somente Mapa, Recomendações e Plateia e leva a marca ao mapa", () => {
    expect(BRAND_DESTINATION).toBe("/mapa");
    expect(HEADER_LINKS.map(({ label, to }) => ({ label, to }))).toEqual([
      { label: "Mapa", to: "/mapa" },
      { label: "Recomendações", to: "/decisoes" },
      { label: "Plateia", to: "/apresentador" },
    ]);
  });

  it("mantém as três abas navegáveis em telas estreitas", () => {
    expect(HEADER_NAV_CLASS).not.toMatch(/hidden/);
    expect(HEADER_NAV_CLASS).toContain("w-full");
  });
});
