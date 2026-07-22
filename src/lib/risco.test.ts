import { describe, expect, it } from "vitest";
import { aneelFreq, classificarTHDInstantaneo } from "./risco";

describe("classificação de qualidade elétrica", () => {
  it("distingue a faixa normal da faixa de retorno pós-distúrbio", () => {
    expect(aneelFreq(60)).toBe("verde");
    expect(aneelFreq(59.8)).toBe("amarelo");
    expect(aneelFreq(59.4)).toBe("vermelho");
  });

  it("trata THD instantâneo como proxy experimental de 10% em baixa tensão", () => {
    expect(classificarTHDInstantaneo(4.9)).toBe("verde");
    expect(classificarTHDInstantaneo(8)).toBe("amarelo");
    expect(classificarTHDInstantaneo(10)).toBe("amarelo");
    expect(classificarTHDInstantaneo(10.1)).toBe("vermelho");
  });
});
