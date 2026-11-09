import { motion, useReducedMotion } from "framer-motion";
import { useState } from "react";
import type { Month } from "../../app/types";
import { linear, path, ticks } from "../../shared/scale";
import { chart, color, font, motion as m } from "../../theme/tokens";

const W = chart.width;

export type Marker = { month: number; kind: keyof typeof color.event; text: string };

/** One marker per month with an action, coloured by what happened. */
export function markers(months: Month[]): Marker[] {
  return months.flatMap((mo) =>
    mo.actions.map((a): Marker => {
      const kind = a.startsWith("rolled back") ? "rollback" : a.includes("without the gate") ? "bad" : "retrain";
      return { month: mo.month, kind, text: a };
    }),
  );
}

export function ReplayChart({ months }: { months: Month[] }) {
  const reduce = useReducedMotion();
  const [hover, setHover] = useState<Month | null>(null);
  const live = months.filter((mo) => mo.live.mae_days !== undefined);
  const hi = Math.max(...live.flatMap((mo) => [mo.live.mae_days ?? 0, mo.live.rule_mae_days ?? 0]));
  const yt = ticks(0, hi, chart.ticks);
  const { top, right, bottom, left } = chart.pad;
  const first = months[0]?.month ?? 0;
  const last = months[months.length - 1]?.month ?? 1;
  const x = linear([first, last], [left, W - right]);
  const y = linear([0, yt[yt.length - 1]!], [chart.height - bottom, top]);
  const line = (k: "mae_days" | "rule_mae_days") => path(live.map((mo) => [x(mo.month), y(mo.live[k] ?? 0)]));
  const marks = markers(months);
  const step = months.length > 1 ? x(first + 1) - x(first) : W;

  return (
    <div className="figure">
      <h3>Error on matured labels, month by month after release</h3>
      <div className="legend">
        <span>
          <i className="key" style={{ background: color.series.model }} />
          Model being served
        </span>
        <span>
          <i className="key dashed" style={{ color: color.series.rule }} />
          Pack-size rule
        </span>
        <span>
          <i className="swatch" style={{ background: color.event.retrain }} />
          Retrained and promoted
        </span>
        <span>
          <i className="swatch" style={{ background: color.event.bad }} />
          Release without the gate
        </span>
        <span>
          <i className="swatch" style={{ background: color.event.rollback }} />
          Rolled back
        </span>
      </div>
      <div className="chart-wrap">
        <svg viewBox={`0 0 ${W} ${chart.height}`} width="100%" role="img" aria-label="Mean absolute error of the served model and the rule per month">
          {yt.map((t) => (
            <g key={t}>
              <line x1={left} x2={W - right} y1={y(t)} y2={y(t)} stroke={color.grid} />
              <text x={left - chart.valueGap} y={y(t) + chart.baseline} textAnchor="end" fontSize={font.size.xs} fill={color.muted}>
                {t}
              </text>
            </g>
          ))}
          <text x={left} y={top - chart.valueGap} fontSize={font.size.xs} fill={color.muted}>
            days off
          </text>
          {months.map((mo) => (
            <text key={mo.month} x={x(mo.month)} y={chart.height - bottom + font.size.lg} textAnchor="middle" fontSize={font.size.xs} fill={color.muted}>
              {mo.month}
            </text>
          ))}
          {marks.map((mk, i) => (
            <line key={i} x1={x(mk.month) - (mk.kind === "rollback" ? chart.markerOffset : 0)} x2={x(mk.month) - (mk.kind === "rollback" ? chart.markerOffset : 0)} y1={top} y2={chart.height - bottom} stroke={color.event[mk.kind]} strokeWidth={chart.line} strokeDasharray={mk.kind === "retrain" ? undefined : "4 3"} />
          ))}
          <path d={line("rule_mae_days")} fill="none" stroke={color.series.rule} strokeWidth={chart.line} strokeDasharray="5 4" />
          <motion.path
            d={line("mae_days")}
            fill="none"
            stroke={color.series.model}
            strokeWidth={chart.line}
            initial={reduce ? false : { pathLength: 0 }}
            whileInView={{ pathLength: 1 }}
            viewport={{ once: true }}
            transition={{ duration: m.draw, ease: m.ease }}
          />
          {live.map((mo) => (
            <circle key={mo.month} cx={x(mo.month)} cy={y(mo.live.mae_days ?? 0)} r={chart.dot} fill={color.series.model} stroke={color.surface} strokeWidth={chart.line} />
          ))}
          {months.map((mo) => (
            <rect
              key={mo.month}
              x={x(mo.month) - step / 2}
              y={top}
              width={step}
              height={chart.height - top - bottom}
              fill="transparent"
              tabIndex={0}
              aria-label={`Month ${mo.month}`}
              onMouseEnter={() => setHover(mo)}
              onFocus={() => setHover(mo)}
              onMouseLeave={() => setHover(null)}
              onBlur={() => setHover(null)}
            />
          ))}
        </svg>
        {hover && (
          <div className="tooltip" role="tooltip" style={{ left: `${(x(hover.month) / W) * 100}%`, top: 0 }}>
            <strong>Month {hover.month}</strong>
            <div>
              Serving v{hover.champion}; {hover.live.n ?? 0} labels matured
            </div>
            <div>
              Model {hover.live.mae_days?.toFixed(1) ?? "n/a"} days, rule {hover.live.rule_mae_days?.toFixed(1) ?? "n/a"}
            </div>
            {hover.psi_alerts.length > 0 && <div>Drift: {hover.psi_alerts.join(", ")}</div>}
            {hover.actions.map((a) => (
              <div key={a}>{a}</div>
            ))}
          </div>
        )}
      </div>
      <p className="caption">
        Labels mature only once the customer reorders, so early months over-represent short run-outs and both lines rise
        with time. Decisions use the ratio of the two lines, which that bias cancels.
      </p>
    </div>
  );
}
