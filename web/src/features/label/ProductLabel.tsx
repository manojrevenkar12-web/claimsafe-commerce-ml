import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useMemo, useState } from "react";
import type { CatalogueRow } from "../../app/types";
import { EmptyState } from "../../shared/states";
import { VerdictChip } from "../../shared/VerdictChip";
import { motion as m } from "../../theme/tokens";

type View = "written" | "shown";

/** What a customer may see: allowed sentences as written, rewrites in the register's wording, removals dropped. */
export function customerLines(row: CatalogueRow): { text: string; law: boolean }[] {
  const byText = new Map(row.findings.map((f) => [f.sentence, f]));
  return row.sentences.flatMap((s): { text: string; law: boolean }[] => {
    if (s.verdict === "ok") return [{ text: s.text, law: false }];
    const f = byText.get(s.text);
    return s.verdict === "rewrite" && f?.suggestion ? [{ text: f.suggestion, law: true }] : [];
  });
}

export function ProductLabel({ rows, initial }: { rows: CatalogueRow[]; initial: string }) {
  const flagged = rows.filter((r) => r.findings.length > 0);
  const [id, setId] = useState(flagged.some((r) => r.product === initial) ? initial : (flagged[0]?.product ?? ""));
  const [view, setView] = useState<View>("written");
  const reduce = useReducedMotion();
  const row = flagged.find((r) => r.product === id);
  const shown = useMemo(() => (row ? customerLines(row) : []), [row]);

  if (!row) return <EmptyState title="No product description has a finding.">Every sentence in the catalogue is allowed as written.</EmptyState>;

  const findingFor = (text: string) => row.findings.find((f) => f.sentence === text);
  const enter = reduce ? { opacity: 1 } : { opacity: 0, y: 6 };
  return (
    <figure className="label" aria-label={`Product description check for ${row.name}`} >
      <header>
        <h3>Product description check</h3>
        <label className="picker">
          <span className="sr-only">Product </span>
          <select value={id} onChange={(e) => setId(e.target.value)} aria-label="Product to check">
            {flagged.map((r) => (
              <option key={r.product} value={r.product}>
                {r.name} ({r.product})
              </option>
            ))}
          </select>
        </label>
      </header>
      <div className="toggle" role="group" aria-label="Description view">
        <button aria-pressed={view === "written"} onClick={() => setView("written")}>
          As the shop wrote it
        </button>
        <button aria-pressed={view === "shown"} onClick={() => setView("shown")}>
          What a customer sees
        </button>
      </div>
      <AnimatePresence mode="wait" initial={false}>
        {view === "written" ? (
          <motion.div key={`w-${id}`} initial={enter} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: m.base, ease: m.ease }}>
            {row.sentences.map((s) => {
              const f = findingFor(s.text);
              return (
                <div className={`sentence ${s.verdict}`} key={s.text}>
                  <div>
                    <VerdictChip verdict={s.verdict} />
                  </div>
                  <span className="shop">{s.text}</span>
                  {f && <span className="why">{f.reason}</span>}
                </div>
              );
            })}
          </motion.div>
        ) : (
          <motion.div key={`s-${id}`} initial={enter} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: m.base, ease: m.ease }}>
            {shown.length === 0 ? (
              <EmptyState title="Nothing in this description may be shown.">
                Every sentence makes a claim the register does not allow. The description has to be rewritten by hand.
              </EmptyState>
            ) : (
              shown.map((l, i) =>
                l.law ? (
                  <p className="law line" key={i}>
                    {l.text}
                  </p>
                ) : (
                  <p className="line" key={i}>
                    {l.text}
                  </p>
                ),
              )
            )}
          </motion.div>
        )}
      </AnimatePresence>
      <figcaption className="caption">
        Serif text behind the green rule is the wording of Regulation (EU) No 432/2012. Rewrites only ever use it, and only
        for nutrients the product contains at 15% of the reference intake or more per daily dose.
      </figcaption>
    </figure>
  );
}
