import type { Verdict } from "../app/types";
import { color } from "../theme/tokens";

const LABEL: Record<Verdict, string> = { ok: "Allowed", rewrite: "Rewrite", block: "Remove" };
const ICON: Record<Verdict, string> = { ok: "✓", rewrite: "↻", block: "✕" };

/** A verdict is never colour alone: icon, word and colour together. */
export function VerdictChip({ verdict }: { verdict: Verdict }) {
  return (
    <span className="chip" style={{ color: color.verdict[verdict], background: color.verdictWash[verdict] }}>
      <span aria-hidden="true">{ICON[verdict]}</span>
      {LABEL[verdict]}
    </span>
  );
}

export const verdictLabel = (v: Verdict) => LABEL[v];
