// The shape of public/data/dashboard.json, written by scripts/report.py.

export type Verdict = "ok" | "rewrite" | "block";

export interface Finding {
  sentence: string;
  verdict: Verdict;
  reason: string;
  suggestion: string | null;
}

export interface CatalogueRow {
  product: string;
  name: string;
  verdict: Verdict;
  eligible_claims: number;
  findings: Finding[];
  sentences: { text: string; verdict: Verdict }[];
  safe_text: string;
}

export interface EvalSplit {
  items: number;
  accuracy: number;
  accuracy_ci95: [number, number];
  false_passes: number;
  not_allowed: number;
  false_flags: number;
  allowed: number;
}

export interface SearchMethod {
  precision_at_k: number;
  recall_at_k: number;
  results_without_a_lawful_claim_for_the_need: number;
}

export interface GuardRow {
  embellish_rate: number;
  made_up_sentences: number;
  reached_customer: number;
  rewritten: number;
  blocked: number;
  sentences_checked: number;
  answers_shown: number;
}

export interface Answer {
  product: string;
  name: string;
  text: string;
  verdict: Verdict;
}

export interface Metrics {
  mae_days: number;
  n: number;
  reminders_on_time: number;
  reminders_too_late: number;
  within_7_days: number;
}

export interface Month {
  month: number;
  orders: number;
  champion: number;
  actions: string[];
  psi: Record<string, number>;
  psi_alerts: string[];
  live: { n?: number; mae_days?: number; rule_mae_days?: number; skill?: number };
}

export interface Version {
  version: number;
  status: string;
  reason: string;
  trained_through_day: number;
  training_customers: number;
  data_fingerprint: string;
  model_sha256: string;
}

export interface ModelEvent {
  day: number;
  event: string;
  version: number;
  detail: string;
}

export interface StoreCounts {
  identities: number;
  orders: number;
  features: number;
  personalisation_index: number;
  model_manifests?: number[];
}

export interface LineageNode {
  id: string;
  kind: "source" | "dataset" | "model" | "check" | "index";
  label: string;
  hash: string;
}

export interface Dashboard {
  tests: { python: number; web: number };
  claims: {
    register: { claims: number; nutrients: number; source: string };
    dev: EvalSplit;
    heldout: EvalSplit & { false_pass_rate_ci95: [number, number]; false_flag_rate_ci95: [number, number] };
    heldout_misses: { product: string; text: string }[];
    catalogue: { products: number; with_findings: number; blocked: number; rewrite_only: number; without_any_eligible_claim: number };
    catalogue_rows: CatalogueRow[];
    search: { k: number; queries: number; methods: Record<"marketing" | "claims" | "hybrid", SearchMethod> };
    guard: GuardRow[];
    examples: { q: string; answers: Answer[] }[];
  };
  replenishment: {
    world: { customers: number; orders: number; months: number; train_months: number };
    release: { v1_holdout: Metrics; rule_holdout: Metrics };
    months: Month[];
    served_mae_days: number;
    served_rule_mae_days: number;
    versions: Version[];
    events: ModelEvent[];
  };
  gdpr: {
    erased_customers: number;
    retrain_due_day: number;
    purged_versions: number[];
    deleted: StoreCounts[];
    after_delete: StoreCounts[];
    after_retrain: StoreCounts[];
  };
  pipeline: {
    vertex_spec: string;
    bigquery_sql: string;
    prefect_run: { passed_gate: boolean; evaluate: { challenger: Metrics; rule: Metrics }; train: { trained_on: number } };
    lineage: { nodes: LineageNode[]; edges: [string, string][] };
  };
}
