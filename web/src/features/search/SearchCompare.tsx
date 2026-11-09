import type { Dashboard, SearchMethod } from "../../app/types";
import { pct } from "../../shared/format";
import { chart, color, font } from "../../theme/tokens";

type Methods = Dashboard["claims"]["search"]["methods"];
type Key = keyof Methods;

const INDEX: { id: Key; label: string }[] = [
  { id: "marketing", label: "Shop copy (BM25)" },
  { id: "claims", label: "Authorised claims (BM25)" },
  { id: "hybrid", label: "Authorised claims + LSA vectors" },
];
const MEASURES: { id: keyof SearchMethod; label: string; better: string }[] = [
  { id: "recall_at_k", label: "Relevant products found", better: "higher is better" },
  { id: "precision_at_k", label: "Results that are relevant", better: "higher is better" },
  { id: "results_without_a_lawful_claim_for_the_need", label: "Results with nothing lawful to say", better: "lower is better" },
];

export function SearchCompare({ methods, k, queries }: { methods: Methods; k: number; queries: number }) {
  const barArea = chart.barArea;
  const groupH = INDEX.length * (chart.bar + chart.barGap) + chart.groupGap;
  const height = MEASURES.length * groupH;
  const width = chart.labelWidth + barArea + chart.valueRoom;
  return (
    <div className="figure">
      <h3>
        {queries} customer questions, top {k} results
      </h3>
      <div className="legend">
        {INDEX.map((i) => (
          <span key={i.id}>
            <i className="swatch" style={{ background: color.series[i.id] }} />
            {i.label}
          </span>
        ))}
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" style={{ maxWidth: width }} role="img" aria-label="Search quality by index">
        {MEASURES.map((ms, g) => (
          <g key={ms.id} transform={`translate(0 ${g * groupH})`}>
            <text x={0} y={chart.bar} fontSize={font.size.sm} fill={color.ink}>
              {ms.label}
            </text>
            <text x={0} y={chart.bar * 2 + chart.barGap} fontSize={font.size.xs} fill={color.muted}>
              {ms.better}
            </text>
            {INDEX.map((ix, i) => {
              const v = methods[ix.id][ms.id];
              const y = i * (chart.bar + chart.barGap);
              return (
                <g key={ix.id}>
                  <rect x={chart.labelWidth} y={y} width={Math.max(1, v * barArea)} height={chart.bar} rx={chart.barRadius} fill={color.series[ix.id]}>
                    <title>{`${ix.label}: ${pct(v)}`}</title>
                  </rect>
                  <text x={chart.labelWidth + v * barArea + chart.valueGap} y={y + chart.bar - chart.baseline} fontSize={font.size.xs} fill={color.ink2}>
                    {pct(v)}
                  </text>
                </g>
              );
            })}
          </g>
        ))}
      </svg>
      <p className="caption">
        A product is relevant when its composition qualifies it for an authorised claim on the need asked about. Adding
        LSA vectors changed nothing worth having; the gain comes from indexing what may lawfully be said.
      </p>
    </div>
  );
}
