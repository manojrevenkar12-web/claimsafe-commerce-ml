import type { LineageNode } from "../../app/types";
import { chart, color, font, radius } from "../../theme/tokens";

/** Column of each node: the length of the longest path into it, so every edge points right. */
export function layers(nodes: LineageNode[], edges: [string, string][]): Map<string, number> {
  const col = new Map(nodes.map((n) => [n.id, 0]));
  for (let pass = 0; pass < nodes.length; pass++) {
    for (const [a, b] of edges) col.set(b, Math.max(col.get(b) ?? 0, (col.get(a) ?? 0) + 1));
  }
  return col;
}

export function Lineage({ nodes, edges }: { nodes: LineageNode[]; edges: [string, string][] }) {
  const col = layers(nodes, edges);
  const { w, h, colGap, rowGap } = chart.node;
  const rows = new Map<number, number>();
  const pos = new Map<string, { x: number; y: number }>();
  for (const n of nodes) {
    const c = col.get(n.id) ?? 0;
    const r = rows.get(c) ?? 0;
    rows.set(c, r + 1);
    pos.set(n.id, { x: c * (w + colGap), y: r * (h + rowGap) });
  }
  const width = (Math.max(...col.values()) + 1) * (w + colGap) - colGap;
  const height = Math.max(...rows.values()) * (h + rowGap) - rowGap;
  return (
    <div className="figure">
      <h3>Lineage of the run, with content hashes</h3>
      <div className="scroll-x">
        <svg viewBox={`0 0 ${width} ${height}`} width="100%" style={{ maxWidth: width }} role="img" aria-label="Pipeline lineage graph">
          {edges.map(([a, b]) => {
            const p = pos.get(a)!;
            const q = pos.get(b)!;
            const x1 = p.x + w;
            const y1 = p.y + h / 2;
            const x2 = q.x;
            const y2 = q.y + h / 2;
            const mid = (x1 + x2) / 2;
            return <path key={`${a}-${b}`} d={`M${x1} ${y1} C${mid} ${y1} ${mid} ${y2} ${x2} ${y2}`} fill="none" stroke={color.axis} strokeWidth={chart.line} />;
          })}
          {nodes.map((n) => {
            const p = pos.get(n.id)!;
            return (
              <g key={n.id} transform={`translate(${p.x} ${p.y})`}>
                <rect width={w} height={h} rx={radius.sm} fill={color.surface} stroke={n.kind === "check" ? color.accent : color.axis} />
                <text x={chart.valueGap * 2} y={h / 2 - chart.baseline} fontSize={font.size.xs} fill={color.ink}>
                  {n.label}
                </text>
                <text x={chart.valueGap * 2} y={h / 2 + font.size.xs} fontSize={font.size.xs} fill={color.muted}>
                  {n.kind}
                  {n.hash ? ` ${n.hash.slice(0, 8)}` : ""}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <p className="caption">
        The same steps compile to a Vertex AI pipeline spec and run as a Prefect flow; the feature SQL runs in DuckDB here
        and is transpiled to BigQuery SQL.
      </p>
    </div>
  );
}
