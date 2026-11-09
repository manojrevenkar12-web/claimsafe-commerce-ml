import type { Answer, GuardRow } from "../../app/types";
import { int, pct } from "../../shared/format";
import { EmptyState } from "../../shared/states";

/** Split an advisor answer into the product line and the register sentences that follow it. */
export function splitAnswer(a: Answer): { head: string; claims: string } {
  const cut = a.text.indexOf(" EUR. ");
  return cut < 0 ? { head: a.text, claims: "" } : { head: a.text.slice(0, cut + 5), claims: a.text.slice(cut + 6) };
}

export function GuardTable({ guard }: { guard: GuardRow[] }) {
  return (
    <div className="figure">
      <h3>A drafter that embellishes, on purpose</h3>
      <table>
        <thead>
          <tr>
            <th scope="col" className="num">
              Embellish rate
            </th>
            <th scope="col" className="num">
              Made-up sentences
            </th>
            <th scope="col" className="num">
              Rewritten
            </th>
            <th scope="col" className="num">
              Removed
            </th>
            <th scope="col" className="num">
              Reached a customer
            </th>
          </tr>
        </thead>
        <tbody>
          {guard.map((g) => (
            <tr key={g.embellish_rate}>
              <td className="num">{pct(g.embellish_rate)}</td>
              <td className="num">{int(g.made_up_sentences)}</td>
              <td className="num">{int(g.rewritten)}</td>
              <td className="num">{int(g.blocked)}</td>
              <td className="num">
                <strong>{g.reached_customer}</strong>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="caption">
        The test drafter rewrites claims into marketing language and adds benefits nobody asked for, the way a language
        model writing shop copy does. Every answer passes the checker before it is shown.
      </p>
    </div>
  );
}

export function AdvisorExamples({ examples }: { examples: { q: string; answers: Answer[] }[] }) {
  if (examples.length === 0) return <EmptyState title="No advisor answers recorded.">Run scripts/run_benchmarks.py to record them.</EmptyState>;
  return (
    <div className="figure">
      <h3>What the advisor answered</h3>
      <div className="qa">
        {examples.map((e) => (
          <div key={e.q}>
            <p className="q">“{e.q}”</p>
            {e.answers.length === 0 ? (
              <p className="ink2">No product qualifies for an authorised claim on this need, so none is suggested.</p>
            ) : (
              (() => {
                const { head, claims } = splitAnswer(e.answers[0]!);
                return (
                  <>
                    <span>{head}</span>
                    {claims && <p className="law">{claims}</p>}
                    {e.answers.length > 1 && (
                      <p className="caption">
                        Also suggested: {e.answers.slice(1).map((a) => a.name).join(", ")}.
                      </p>
                    )}
                  </>
                );
              })()
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
