import type { Dashboard, StoreCounts } from "../../app/types";

type Gdpr = Dashboard["gdpr"];
const STORES: { id: keyof Omit<StoreCounts, "model_manifests">; label: string }[] = [
  { id: "identities", label: "Identity table" },
  { id: "orders", label: "Orders" },
  { id: "features", label: "Feature rows" },
  { id: "personalisation_index", label: "Personalisation index" },
];

const sum = (xs: StoreCounts[], k: keyof Omit<StoreCounts, "model_manifests">) => xs.reduce((a, x) => a + (x[k] ?? 0), 0);
const models = (xs: StoreCounts[]) => new Set(xs.flatMap((x) => x.model_manifests ?? [])).size;

export function Erasure({ gdpr }: { gdpr: Gdpr }) {
  return (
    <div className="figure">
      <h3>{gdpr.erased_customers} erasure requests, store by store</h3>
      <table>
        <thead>
          <tr>
            <th scope="col">Store</th>
            <th scope="col" className="num">
              Deleted
            </th>
            <th scope="col" className="num">
              Left after deletion
            </th>
            <th scope="col" className="num">
              Left after retraining
            </th>
          </tr>
        </thead>
        <tbody>
          {STORES.map((s) => (
            <tr key={s.id}>
              <th scope="row">{s.label}</th>
              <td className="num">{sum(gdpr.deleted, s.id)}</td>
              <td className="num">{sum(gdpr.after_delete, s.id)}</td>
              <td className="num">{sum(gdpr.after_retrain, s.id)}</td>
            </tr>
          ))}
          <tr>
            <th scope="row">Model versions that learned from them, marked for retraining</th>
            <td className="num">{models(gdpr.after_delete)}</td>
            <td className="num">{models(gdpr.after_delete)}</td>
            <td className="num">{models(gdpr.after_retrain)}</td>
          </tr>
        </tbody>
      </table>
      <p className="caption">
        Customers are known to the warehouse only by a keyed pseudonym; the identity table is separate. A model whose
        training manifest names an erased customer is marked for retraining by day {gdpr.retrain_due_day}; after the
        retrain the old version ({gdpr.purged_versions.map((v) => `v${v}`).join(", ")}) is purged.
      </p>
    </div>
  );
}
