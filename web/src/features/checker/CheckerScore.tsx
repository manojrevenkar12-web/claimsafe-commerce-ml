import type { Dashboard } from "../../app/types";
import { pct } from "../../shared/format";

type Claims = Dashboard["claims"];

export function CheckerScore({ claims }: { claims: Claims }) {
  const { dev, heldout: h } = claims;
  const rows: [string, string, string][] = [
    ["Sentences", String(dev.items), String(h.items)],
    ["Accuracy", pct(dev.accuracy, 1), `${pct(h.accuracy, 1)} (95% CI ${pct(h.accuracy_ci95[0], 0)}–${pct(h.accuracy_ci95[1], 0)})`],
    ["Not-allowed text let through", `${dev.false_passes} of ${dev.not_allowed}`, `${h.false_passes} of ${h.not_allowed}`],
    ["Allowed text flagged", `${dev.false_flags} of ${dev.allowed}`, `${h.false_flags} of ${h.allowed}`],
  ];
  return (
    <div className="split">
      <div className="figure">
        <h3>Two sets of labelled shop sentences</h3>
        <table>
          <thead>
            <tr>
              <th scope="col">Measure</th>
              <th scope="col" className="num">
                Dev, built against
              </th>
              <th scope="col" className="num">
                Held-out, run once
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([k, a, b]) => (
              <tr key={k}>
                <th scope="row">{k}</th>
                <td className="num">{a}</td>
                <td className="num">{b}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="caption">
          The held-out sentences were written and their hashes pinned before the checker first ran; its result is
          published as it came out. Dev is perfect because the vocabulary was tuned on it.
        </p>
      </div>
      <div className="figure">
        <h3>What the held-out run let through</h3>
        {claims.heldout_misses.length === 0 ? (
          <p className="ink2">Nothing: every not-allowed sentence was caught.</p>
        ) : (
          <ul className="misses" aria-label="Held-out false passes">
            {claims.heldout_misses.map((m) => (
              <li key={`${m.product}-${m.text}`}>
                <span className="muted">{m.product}</span>
                <span>“{m.text}”</span>
              </li>
            ))}
          </ul>
        )}
        <p className="caption">
          All are implied claims with no nutrient or function word the vocabulary knows (“glow”, “cleanses”, “nerves”).
          The next round needs a broader implied-claim detector and a fresh held-out set; this one is spent.
        </p>
      </div>
    </div>
  );
}
