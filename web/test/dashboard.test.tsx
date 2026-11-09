import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { App } from "../src/app/App";
import type { Dashboard } from "../src/app/types";
import { CatalogueAudit } from "../src/features/catalogue/CatalogueAudit";
import { customerLines, ProductLabel } from "../src/features/label/ProductLabel";
import { layers } from "../src/features/pipeline/Lineage";
import { markers } from "../src/features/replenish/ReplayChart";
import { splitAnswer } from "../src/features/search/AdvisorGuard";

const data = JSON.parse(readFileSync(resolve(__dirname, "../public/data/dashboard.json"), "utf8")) as Dashboard;
const rows = data.claims.catalogue_rows;
const row = (id: string) => rows.find((r) => r.product === id)!;

function serve(fail = { on: false }) {
  return vi.fn(async () => (fail.on ? new Response("nope", { status: 503 }) : new Response(JSON.stringify(data), { status: 200 })));
}

describe("dashboard", () => {
  it("shows a skeleton, then the report built from the benchmark data", async () => {
    vi.stubGlobal("fetch", serve());
    render(<App />);
    expect(screen.getByRole("status", { name: "Loading the report" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("only says what the law lets it say");
    for (const name of ["The claim checker", "The catalogue, audited", "Search and the advisor", "Reorder reminders, operated"]) {
      expect(screen.getByRole("region", { name })).toBeInTheDocument();
    }
    expect(screen.getAllByText(`${data.claims.heldout.false_passes} of ${data.claims.heldout.not_allowed}`).length).toBeGreaterThan(0);
    vi.unstubAllGlobals();
  });

  it("explains a failed load and loads again on retry", async () => {
    const fail = { on: true };
    vi.stubGlobal("fetch", serve(fail));
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The report could not be loaded");
    fail.on = false;
    fireEvent.click(screen.getByRole("button", { name: "Load again" }));
    expect(await screen.findByRole("heading", { level: 1 })).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("shows customers the register's wording in place of rewrites and drops removed sentences", async () => {
    const r = row("P27");
    const lines = customerLines(r);
    expect(lines.every((l) => !r.sentences.some((s) => s.verdict === "block" && s.text === l.text))).toBe(true);
    expect(lines.some((l) => l.law && l.text.includes("contributes to the maintenance of normal hair"))).toBe(true);
    render(<ProductLabel rows={rows} initial="P27" />);
    expect(screen.getByText("Anti-ageing from the inside.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "What a customer sees" }));
    await waitFor(() => expect(screen.queryByText("Anti-ageing from the inside.")).not.toBeInTheDocument());
    expect(await screen.findByText(lines[0]!.text)).toHaveClass("law");
  });

  it("says so when nothing in a description may be shown", async () => {
    render(<ProductLabel rows={rows} initial="P40" />);
    fireEvent.click(screen.getByRole("button", { name: "What a customer sees" }));
    expect(await screen.findByText("Nothing in this description may be shown.")).toBeInTheDocument();
  });

  it("filters the catalogue, shows an empty group, and opens a product's findings", () => {
    render(<CatalogueAudit rows={rows.filter((r) => r.verdict !== "ok")} />);
    fireEvent.click(screen.getByRole("button", { name: /Allowed as written/ }));
    expect(screen.getByText("No product in this group.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Text to rewrite/ }));
    fireEvent.click(screen.getByText("Vitamin D3 + K2 drops"));
    const drawer = screen.getByRole("dialog", { name: "Findings for Vitamin D3 + K2 drops" });
    expect(within(drawer).getByText("“The duo for strong bones.”")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
  });

  it("classifies registry actions for the replay chart", () => {
    const kinds = markers(data.replenishment.months).map((m) => `${m.month}:${m.kind}`);
    expect(kinds).toContain("17:bad");
    expect(kinds).toContain("18:rollback");
    expect(kinds).toContain("16:retrain");
  });

  it("lays out lineage so every edge points right, and splits advisor answers", () => {
    const { nodes, edges } = data.pipeline.lineage;
    const col = layers(nodes, edges);
    expect(edges.every(([a, b]) => (col.get(b) ?? 0) > (col.get(a) ?? 0))).toBe(true);
    const a = splitAnswer(data.claims.examples[1]!.answers[0]!);
    expect(a.head).toMatch(/EUR\.$/);
    expect(a.claims).toMatch(/^EPA and DHA contribute/);
  });
});
