import type { Dashboard } from "../../app/types";
import { days, int, pct } from "../../shared/format";

type Run = Dashboard["pipeline"]["prefect_run"];

export function GateRun({ run, spec, sql }: { run: Run; spec: string; sql: string }) {
  const { challenger: c, rule: r } = run.evaluate;
  const rows: [string, string, string][] = [
    ["Mean error", days(c.mae_days), days(r.mae_days)],
    ["Within 7 days", pct(c.within_7_days), pct(r.within_7_days)],
    ["Reminder after the customer ran out", pct(c.reminders_too_late, 1), pct(r.reminders_too_late, 1)],
  ];
  return (
    <div className="figure">
      <h3>The gate, as the Prefect flow ran it</h3>
      <table>
        <thead>
          <tr>
            <th scope="col">On {int(c.n)} held-back reorders</th>
            <th scope="col" className="num">
              Model
            </th>
            <th scope="col" className="num">
              Pack-size rule
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
        {run.passed_gate ? "Passed" : "Failed"}: a model is registered only if it beats the rule by the margin set in
        config/claimsafe.toml. Trained on {int(run.train.trained_on)} rows. Vertex AI spec: {spec}; BigQuery SQL: {sql}.
      </p>
    </div>
  );
}
