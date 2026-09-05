import type { OpcaoSala } from "@/lib/audience-types";

function optionSymbol(id: string) {
  if (id.includes("baterias")) return "⚡";
  if (id.includes("reduzir")) return "↘";
  if (id.includes("isolar")) return "◉";
  if (id.includes("norte")) return "↑";
  if (id.includes("sul")) return "↓";
  if (id.includes("leste")) return "→";
  if (id.includes("oeste")) return "←";
  if (id.includes("centro")) return "◆";
  if (id.includes("aeroporto")) return "✈";
  if (id.includes("hospital")) return "✚";
  return "●";
}

export function CartaoOpcaoVoto({
  option,
  selected,
  disabled,
  onClick,
}: {
  option: OpcaoSala;
  selected?: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={`audience-vote-card ${selected ? "is-selected" : ""}`}
      onClick={onClick}
      disabled={disabled}
      aria-pressed={selected}
      aria-label={option.label}
    >
      <span className="audience-vote-symbol" aria-hidden="true">
        {optionSymbol(option.id)}
      </span>
      <span>
        <strong>{option.label}</strong>
        {option.detail && <small>{option.detail}</small>}
      </span>
      <span className="audience-vote-pick">{selected ? "Escolhido" : "Escolher"}</span>
    </button>
  );
}

export function PainelVotacao({
  step,
  question,
  options,
  selected,
  disabled,
  onVote,
  counts,
  visible,
}: {
  step?: string;
  question: string;
  options: OpcaoSala[];
  selected?: string;
  disabled?: boolean;
  onVote: (id: string) => void;
  counts: Record<string, number>;
  visible: boolean;
}) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  return (
    <section className="audience-voting" aria-live="polite">
      <div className="audience-vote-intro">
        {step && <p>{step}</p>}
        <h2>{question}</h2>
        <span>Escolha uma opção para ajudar a cidade.</span>
      </div>
      <div className="audience-vote-options">
        {options.map((option) => (
          <div key={option.id}>
            <CartaoOpcaoVoto
              option={option}
              selected={selected === option.id}
              disabled={disabled}
              onClick={() => onVote(option.id)}
            />
            {visible && (
              <div
                className="audience-vote-bar"
                aria-label={`${option.label}: ${total ? Math.round(((counts[option.id] || 0) / total) * 100) : 0}%`}
              >
                <i style={{ width: `${total ? ((counts[option.id] || 0) / total) * 100 : 0}%` }} />
                <span>{total ? Math.round(((counts[option.id] || 0) / total) * 100) : 0}%</span>
              </div>
            )}
          </div>
        ))}
      </div>
      {!visible && <p className="audience-muted">As escolhas aparecem ao final da rodada.</p>}
    </section>
  );
}
