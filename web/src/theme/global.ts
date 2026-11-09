import { breakpoint, color, font, layout, radius, rule, space } from "./tokens";

// The stylesheet is generated from the tokens, so no value in it is typed twice.
export const globalCss = `
:root { color-scheme: light; }
* { box-sizing: border-box; }
html, body { margin: 0; background: ${color.page}; color: ${color.ink}; }
body { font-family: ${font.sans}; font-size: ${font.size.md}px; line-height: ${font.leading.body}; -webkit-font-smoothing: antialiased; }
h1, h2, h3 { margin: 0; line-height: ${font.leading.snug}; font-weight: ${font.weight.semibold}; }
h2 { font-size: ${font.size.xl}px; letter-spacing: -0.005em; }
h3 { font-size: ${font.size.md}px; }
p { margin: 0; max-width: ${layout.measure}ch; }
a { color: ${color.accent}; text-underline-offset: 3px; }
:focus-visible { outline: 2px solid ${color.accent}; outline-offset: 2px; border-radius: ${radius.sm}px; }
button, select { font: inherit; color: inherit; }
.page { max-width: ${layout.maxWidth}px; margin: 0 auto; padding: ${space[8]}px ${layout.gutter}px ${space[20]}px; }
.top { display: flex; justify-content: space-between; gap: ${space[4]}px; flex-wrap: wrap; font-size: ${font.size.sm}px;
  color: ${color.ink2}; padding-bottom: ${space[10]}px; }
.top nav { display: flex; gap: ${space[5]}px; flex-wrap: wrap; }
.hero { display: grid; grid-template-columns: minmax(0, 6fr) minmax(${layout.labelMin}px, 6fr); gap: ${space[12]}px; align-items: start; }
.hero h1 { font-size: ${font.size.display}px; line-height: ${font.leading.tight}; font-weight: ${font.weight.bold}; letter-spacing: -0.02em; }
.lead { color: ${color.ink2}; font-size: ${font.size.lg}px; margin-top: ${space[5]}px; }
.facts { margin: ${space[8]}px 0 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: ${space[6]}px ${space[8]}px; }
.facts div { border-top: ${rule.hair}px solid ${color.axis}; padding-top: ${space[3]}px; }
.facts dt { font-size: ${font.size.xxl}px; font-weight: ${font.weight.semibold}; line-height: ${font.leading.snug}; font-variant-numeric: tabular-nums; }
.facts dd { margin: ${space[1]}px 0 0; color: ${color.ink2}; font-size: ${font.size.sm}px; }
.law { font-family: ${font.serif}; line-height: ${font.leading.serif}; border-left: ${rule.law}px solid ${color.law};
  background: ${color.lawWash}; padding: ${space[2]}px ${space[4]}px; border-radius: 0 ${radius.sm}px ${radius.sm}px 0; }
.label { background: ${color.surface}; border: 1px solid ${color.border}; border-radius: ${radius.md}px; padding: ${space[6]}px; }
.label header { display: flex; justify-content: space-between; gap: ${space[3]}px; align-items: baseline; flex-wrap: wrap; margin-bottom: ${space[4]}px; }
.label select { border: 1px solid ${color.axis}; background: ${color.surface}; border-radius: ${radius.sm}px; padding: ${space[1]}px ${space[2]}px; max-width: 100%; }
.toggle { display: inline-flex; border: 1px solid ${color.axis}; border-radius: ${radius.sm}px; overflow: hidden; margin: ${space[4]}px 0; }
.toggle button { border: 0; background: transparent; padding: ${space[2]}px ${space[4]}px; cursor: pointer; font-size: ${font.size.sm}px; }
.toggle button[aria-pressed="true"] { background: ${color.accent}; color: ${color.surface}; }
.sentence { display: grid; gap: ${space[1]}px; padding: ${space[2]}px 0; border-bottom: 1px solid ${color.grid}; }
.sentence:last-child { border-bottom: 0; }
.sentence .shop { font-size: ${font.size.md}px; }
.sentence.block .shop { text-decoration: line-through; text-decoration-color: ${color.verdict.block}; color: ${color.ink2}; }
.sentence .why { font-size: ${font.size.xs}px; color: ${color.ink2}; }
.chip { display: inline-flex; align-items: center; gap: ${space[1]}px; font-size: ${font.size.xs}px; font-weight: ${font.weight.medium};
  white-space: nowrap; padding: 0 ${space[2]}px; border-radius: ${radius.sm}px; line-height: 1.7; }
.section { margin-top: ${space[20]}px; }
.section > header { margin-bottom: ${space[6]}px; display: grid; gap: ${space[2]}px; }
.section > header p { color: ${color.ink2}; }
.split { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: ${space[8]}px; align-items: start; }
.figure { background: ${color.surface}; border: 1px solid ${color.border}; border-radius: ${radius.md}px; padding: ${space[5]}px; }
.figure h3 { margin-bottom: ${space[2]}px; }
.caption { color: ${color.ink2}; font-size: ${font.size.sm}px; margin-top: ${space[3]}px; }
.legend { display: flex; gap: ${space[5]}px; flex-wrap: wrap; font-size: ${font.size.sm}px; color: ${color.ink2}; margin: ${space[1]}px 0 ${space[3]}px; }
.legend span { display: inline-flex; align-items: center; gap: ${space[2]}px; }
.swatch { width: ${space[3]}px; height: ${space[3]}px; border-radius: 2px; display: inline-block; }
.key { width: ${space[4]}px; height: 2px; display: inline-block; }
.key.dashed { background: repeating-linear-gradient(90deg, currentColor 0 4px, transparent 4px 7px) !important; }
table { border-collapse: collapse; width: 100%; font-size: ${font.size.sm}px; }
th { text-align: left; font-weight: ${font.weight.medium}; color: ${color.ink2}; padding: ${space[2]}px ${space[3]}px; border-bottom: 1px solid ${color.axis}; }
td { padding: ${space[2]}px ${space[3]}px; border-bottom: 1px solid ${color.grid}; vertical-align: top; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
tbody tr.clickable { cursor: pointer; }
tbody tr.clickable:hover td, tbody tr.clickable:focus-visible td { background: ${color.wash}; }
.filters { display: flex; gap: ${space[2]}px; flex-wrap: wrap; margin-bottom: ${space[3]}px; }
.filters button { border: 1px solid ${color.axis}; background: transparent; border-radius: ${radius.sm}px; padding: ${space[1]}px ${space[3]}px;
  cursor: pointer; font-size: ${font.size.sm}px; }
.filters button[aria-pressed="true"] { border-color: ${color.accent}; background: ${color.wash}; color: ${color.accent}; }
.misses { margin: 0; padding: 0; list-style: none; display: grid; gap: ${space[2]}px; font-size: ${font.size.sm}px; }
.misses li { display: grid; grid-template-columns: ${space[10]}px 1fr; gap: ${space[2]}px; }
.qa { display: grid; gap: ${space[4]}px; }
.qa > div { border-top: 1px solid ${color.grid}; padding-top: ${space[3]}px; }
.qa .q { font-weight: ${font.weight.medium}; margin-bottom: ${space[2]}px; }
.qa .law { font-size: ${font.size.sm}px; margin-top: ${space[2]}px; }
.muted { color: ${color.muted}; }
.ink2 { color: ${color.ink2}; }
.mono-hash { font-variant-numeric: tabular-nums; letter-spacing: 0.02em; color: ${color.ink2}; }
.tooltip { position: absolute; pointer-events: none; background: ${color.surface}; border: 1px solid ${color.border};
  border-radius: ${radius.sm}px; padding: ${space[2]}px ${space[3]}px; font-size: ${font.size.xs}px; box-shadow: 0 2px 8px ${color.border};
  z-index: 2; max-width: 280px; }
.tooltip strong { font-size: ${font.size.sm}px; }
.chart-wrap { position: relative; }
.state { padding: ${space[8]}px; border: 1px dashed ${color.axis}; border-radius: ${radius.md}px; display: grid; gap: ${space[3]}px; justify-items: start; }
.btn { border: 1px solid ${color.accent}; color: ${color.accent}; background: transparent; border-radius: ${radius.sm}px;
  padding: ${space[2]}px ${space[4]}px; cursor: pointer; }
.btn:hover { background: ${color.wash}; }
.skeleton { background: linear-gradient(90deg, ${color.grid}, ${color.surface}, ${color.grid}); background-size: 200% 100%;
  border-radius: ${radius.sm}px; animation: shimmer 1.4s ease-in-out infinite; }
@keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }
@media (prefers-reduced-motion: reduce) { .skeleton { animation: none; } }
.drawer { position: fixed; top: 0; right: 0; bottom: 0; width: min(${layout.drawer}px, 100vw); background: ${color.surface};
  border-left: 1px solid ${color.border}; padding: ${space[6]}px; overflow-y: auto; z-index: 5; box-shadow: -8px 0 24px ${color.border}; }
.drawer header { display: flex; justify-content: space-between; gap: ${space[3]}px; align-items: start; margin-bottom: ${space[4]}px; }
.drawer .finding { display: grid; gap: ${space[2]}px; padding: ${space[3]}px 0; border-bottom: 1px solid ${color.grid}; }
.scrim { position: fixed; inset: 0; background: rgba(21,33,27,0.18); z-index: 4; }
.limits { margin-top: ${space[20]}px; border-top: 1px solid ${color.axis}; padding-top: ${space[6]}px; color: ${color.ink2};
  font-size: ${font.size.sm}px; display: grid; gap: ${space[3]}px; }
.limits ul { margin: 0; padding-left: ${space[5]}px; display: grid; gap: ${space[2]}px; max-width: 90ch; }
.scroll-x { overflow-x: auto; }
.picker { color: ${color.ink2}; font-size: ${font.size.sm}px; }
.line { margin: ${space[2]}px 0; }
figure { margin: 0; }
.gap-top { margin-top: ${space[8]}px; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
@media (max-width: ${breakpoint.narrow}px) {
  .hero, .split, .facts { grid-template-columns: 1fr; }
  .hero h1 { font-size: ${font.size.xxl}px; }
  .page { padding-top: ${space[5]}px; }
}
`;
