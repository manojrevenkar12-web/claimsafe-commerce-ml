import type { ModelEvent, Version } from "../../app/types";

export function VersionTable({ versions, events }: { versions: Version[]; events: ModelEvent[] }) {
  return (
    <div className="figure">
      <h3>Every version the registry holds</h3>
      <div className="scroll-x">
        <table>
          <thead>
            <tr>
              <th scope="col">Version</th>
              <th scope="col">Status</th>
              <th scope="col" className="num">
                Trained through day
              </th>
              <th scope="col">Why</th>
              <th scope="col">Data</th>
            </tr>
          </thead>
          <tbody>
            {versions.map((v) => (
              <tr key={v.version}>
                <td>v{v.version}</td>
                <td>{v.status.replace("_", " ")}</td>
                <td className="num">{v.trained_through_day}</td>
                <td>{v.reason}</td>
                <td className="mono-hash">{v.data_fingerprint}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="caption">{events.length} registry events, each with the day and the reason; the full log is in reports/replenishment.json.</p>
    </div>
  );
}
