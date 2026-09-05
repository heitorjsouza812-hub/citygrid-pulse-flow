import type { PlacarCidade as Placar } from "@/lib/audience-types";
export function PlacarCidade({ placar, compacto = false }: { placar: Placar; compacto?: boolean }) {
  const items = [
    ["Estabilidade", placar.estabilidade],
    ["Reserva", placar.reserva],
    ["Custos", placar.controle_custos],
    ["Satisfação", placar.satisfacao],
  ] as const;
  return (
    <section
      className={`audience-score ${compacto ? "is-compact" : ""}`}
      aria-label="Placar da cidade"
    >
      <div className="audience-score-total">
        <span>DESEMPENHO</span>
        <strong>{placar.pontuacao_geral.toFixed(0)}%</strong>
      </div>
      {items.map(([name, value]) => (
        <div className="audience-score-item" key={name}>
          <span>{name}</span>
          <b>{value.toFixed(0)}</b>
          <i>
            <em style={{ width: `${value}%` }} />
          </i>
        </div>
      ))}
    </section>
  );
}
