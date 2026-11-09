import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import type { CatalogueRow, Verdict } from "../../app/types";
import { EmptyState } from "../../shared/states";
import { VerdictChip } from "../../shared/VerdictChip";
import { motion as m } from "../../theme/tokens";

type Filter = "all" | Verdict;
const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All products" },
  { id: "block", label: "Text to remove" },
  { id: "rewrite", label: "Text to rewrite" },
  { id: "ok", label: "Allowed as written" },
];

export function CatalogueAudit({ rows }: { rows: CatalogueRow[] }) {
  const [filter, setFilter] = useState<Filter>("all");
  const [open, setOpen] = useState<CatalogueRow | null>(null);
  const shown = filter === "all" ? rows : rows.filter((r) => r.verdict === filter);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="figure">
      <div className="filters" role="group" aria-label="Filter products">
        {FILTERS.map((f) => (
          <button key={f.id} aria-pressed={filter === f.id} onClick={() => setFilter(f.id)}>
            {f.label} ({f.id === "all" ? rows.length : rows.filter((r) => r.verdict === f.id).length})
          </button>
        ))}
      </div>
      {shown.length === 0 ? (
        <EmptyState title="No product in this group.">Choose another filter to see the rest of the catalogue.</EmptyState>
      ) : (
        <div className="scroll-x">
          <table>
            <thead>
              <tr>
                <th scope="col">Product</th>
                <th scope="col">Verdict</th>
                <th scope="col" className="num">
                  Sentences with a finding
                </th>
                <th scope="col" className="num">
                  Authorised claims it qualifies for
                </th>
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => (
                <tr
                  key={r.product}
                  className={r.findings.length ? "clickable" : undefined}
                  tabIndex={r.findings.length ? 0 : undefined}
                  onClick={() => r.findings.length && setOpen(r)}
                  onKeyDown={(e) => e.key === "Enter" && r.findings.length && setOpen(r)}
                >
                  <td>
                    {r.name} <span className="muted">{r.product}</span>
                  </td>
                  <td>
                    <VerdictChip verdict={r.verdict} />
                  </td>
                  <td className="num">{r.findings.length}</td>
                  <td className="num">{r.eligible_claims}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <AnimatePresence>
        {open && (
          <>
            <motion.div className="scrim" onClick={() => setOpen(null)} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
            <motion.aside
              className="drawer"
              role="dialog"
              aria-label={`Findings for ${open.name}`}
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ duration: m.base, ease: m.ease }}
            >
              <header>
                <div>
                  <h3>{open.name}</h3>
                  <span className="muted">
                    {open.product}, qualifies for {open.eligible_claims} authorised claims
                  </span>
                </div>
                <button className="btn" onClick={() => setOpen(null)} autoFocus>
                  Close
                </button>
              </header>
              {open.findings.map((f) => (
                <div className="finding" key={f.sentence}>
                  <VerdictChip verdict={f.verdict} />
                  <span>“{f.sentence}”</span>
                  <span className="ink2">{f.reason}</span>
                  {f.suggestion && <p className="law">{f.suggestion}</p>}
                </div>
              ))}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
