import { CatalogueAudit } from "../features/catalogue/CatalogueAudit";
import { CheckerScore } from "../features/checker/CheckerScore";
import { ProductLabel } from "../features/label/ProductLabel";
import { GateRun } from "../features/pipeline/GateRun";
import { Lineage } from "../features/pipeline/Lineage";
import { Erasure } from "../features/privacy/Erasure";
import { ReplayChart } from "../features/replenish/ReplayChart";
import { VersionTable } from "../features/replenish/VersionTable";
import { AdvisorExamples, GuardTable } from "../features/search/AdvisorGuard";
import { SearchCompare } from "../features/search/SearchCompare";
import { days, int, pct } from "../shared/format";
import { Section } from "../shared/Section";
import { ErrorState, Skeleton } from "../shared/states";
import { space } from "../theme/tokens";
import type { Dashboard } from "./types";
import { useJson } from "./useData";

const REPO = "https://github.com/manojrevenkar12-web/claimsafe-commerce-ml";
const HERO_PRODUCT = "P27";

function Hero({ d }: { d: Dashboard }) {
  const c = d.claims;
  const made = c.guard.reduce((a, g) => a + g.made_up_sentences, 0);
  const leaked = c.guard.reduce((a, g) => a + g.reached_customer, 0);
  const r = d.replenishment;
  return (
    <div className="hero">
      <div>
        <h1>A supplement shop that only says what the law lets it say.</h1>
        <p className="lead">
          Product copy, search and an AI advisor checked sentence by sentence against the {c.register.claims} health claims
          the EU has authorised for vitamins and minerals. Next to it, a reorder-reminder model run the way a data platform
          runs one: point-in-time features, a gate, drift checks, rollback, and erasure that reaches the model.
        </p>
        <dl className="facts">
          <div>
            <dt>
              {leaked} of {int(made)}
            </dt>
            <dd>made-up health claims from a deliberately embellishing drafter reached a customer.</dd>
          </div>
          <div>
            <dt>
              {c.heldout.false_passes} of {c.heldout.not_allowed}
            </dt>
            <dd>not-allowed sentences got past the checker on the held-out set, run once and published as it came out.</dd>
          </div>
          <div>
            <dt>{pct(c.search.methods.marketing.results_without_a_lawful_claim_for_the_need)} → {pct(c.search.methods.claims.results_without_a_lawful_claim_for_the_need)}</dt>
            <dd>of search results with nothing lawful to say for the need, when the index holds authorised claims instead of shop copy.</dd>
          </div>
          <div>
            <dt>{days(r.served_mae_days)}</dt>
            <dd>
              mean error of the reorder date served over {r.months.length} months, against {days(r.served_rule_mae_days)} for
              the pack-size rule, through a demand shift and a bad release.
            </dd>
          </div>
        </dl>
      </div>
      <ProductLabel rows={c.catalogue_rows} initial={HERO_PRODUCT} />
    </div>
  );
}

function Report({ d }: { d: Dashboard }) {
  const c = d.claims;
  const r = d.replenishment;
  return (
    <>
      <Hero d={d} />
      <Section
        id="checker"
        title="The claim checker"
        lead={`Each sentence is matched to the register for the nutrients the product actually contains at a qualifying dose. Allowed wording passes, near-misses are rewritten into the register's own words, and medicinal or unauthorised claims are removed.`}
      >
        <CheckerScore claims={c} />
      </Section>
      <Section
        id="catalogue"
        title="The catalogue, audited"
        lead={`${c.catalogue.with_findings} of ${c.catalogue.products} product descriptions have a sentence that must change; ${c.catalogue.blocked} contain text that has to go. Open a product to see each finding and its lawful rewrite.`}
      >
        <CatalogueAudit rows={c.catalogue_rows} />
      </Section>
      <Section
        id="search"
        title="Search and the advisor"
        lead="Customers ask about needs, not nutrients. Searching what may lawfully be said about each product finds the right products and keeps the advisor's answers inside the register."
      >
        <SearchCompare methods={c.search.methods} k={c.search.k} queries={c.search.queries} />
        <div className="split gap-top">
          <GuardTable guard={c.guard} />
          <AdvisorExamples examples={c.examples} />
        </div>
      </Section>
      <Section
        id="replenishment"
        title="Reorder reminders, operated"
        lead={`${int(r.world.customers)} simulated customers and ${int(r.world.orders)} orders over ${r.world.months} months. The model learns when each customer runs out; in month 15 a new acquisition channel and a price rise change how long packs last.`}
      >
        <ReplayChart months={r.months} />
        <div className="gap-top">
          <VersionTable versions={r.versions} events={r.events} />
        </div>
      </Section>
      <Section
        id="platform"
        title="Privacy and the pipeline"
        lead="Erasure has to reach every copy of a customer, including what a model learned from them. The training run is one set of steps that compiles for Vertex AI and runs under Prefect."
      >
        <Lineage nodes={d.pipeline.lineage.nodes} edges={d.pipeline.lineage.edges} />
        <div className="split gap-top">
          <Erasure gdpr={d.gdpr} />
          <GateRun run={d.pipeline.prefect_run} spec={d.pipeline.vertex_spec} sql={d.pipeline.bigquery_sql} />
        </div>
      </Section>
      <section className="limits" aria-label="Limits">
        <h3>Limits</h3>
        <ul>
          <li>Products, customers and orders are invented. The claim register is real, transcribed from the annex of Regulation (EU) No 432/2012 for 14 nutrients; botanicals, whose claims are still on hold in the EU, are treated as having none.</li>
          <li>The held-out checker set is spent. Its {c.heldout.false_passes} misses are implied claims; fixing them needs a new detector and a new held-out set.</li>
          <li>The Vertex AI spec is compiled and checked, not submitted; there is no live Google Cloud project behind this page. The BigQuery SQL is transpiled, not run against BigQuery.</li>
          <li>This is not legal advice. A regulatory reviewer still signs off on copy; the checker decides what reaches that reviewer and what never reaches a customer.</li>
        </ul>
        <p>
          {d.tests.python} Python and {d.tests.web} web tests. Source: <a href={REPO}>{REPO.replace("https://", "")}</a>
        </p>
      </section>
    </>
  );
}

export function App() {
  const load = useJson<Dashboard>("dashboard.json");
  return (
    <main className="page">
      <div className="top">
        <span>claimsafe-commerce-ml</span>
        <nav aria-label="Sections">
          <a href="#checker">Checker</a>
          <a href="#catalogue">Catalogue</a>
          <a href="#search">Search</a>
          <a href="#replenishment">Reminders</a>
          <a href="#platform">Privacy and pipeline</a>
        </nav>
      </div>
      {load.state === "loading" && <Skeleton height={space[20] * 4} lines={4} label="Loading the report" />}
      {load.state === "error" && <ErrorState what="The report" message={load.message} onRetry={load.retry} />}
      {load.state === "ready" && <Report d={load.data} />}
    </main>
  );
}
