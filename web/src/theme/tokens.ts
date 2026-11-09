// Every colour, size and duration the dashboard uses.
// Two voices: the shop's own copy is set in Public Sans; wording quoted from Regulation (EU) No 432/2012 is set in
// Source Serif 4 behind a rule, so a reader can tell at a glance which words are the law's.
// Chart series use slots 1 and 2 of the validated dataviz palette; verdicts always carry a label as well as a colour.

export const color = {
  page: "#f1f4f0",
  surface: "#fbfcfa",
  ink: "#15211b",
  ink2: "#4b5a52",
  muted: "#7f8b84",
  grid: "#dfe5df",
  axis: "#bfc9c1",
  border: "rgba(21,33,27,0.12)",
  wash: "rgba(30,91,69,0.07)",
  accent: "#1e5b45",
  law: "#1e5b45",
  lawWash: "rgba(30,91,69,0.06)",
  series: { model: "#2a78d6", rule: "#898781", marketing: "#eb6834", claims: "#2a78d6", hybrid: "#184f95" },
  verdict: { ok: "#1b7f3b", rewrite: "#a86400", block: "#c0362c" },
  verdictWash: { ok: "rgba(27,127,59,0.10)", rewrite: "rgba(168,100,0,0.12)", block: "rgba(192,54,44,0.10)" },
  event: { retrain: "#1e5b45", bad: "#c0362c", rollback: "#a86400" },
} as const;

export const font = {
  sans: "'Public Sans Variable', system-ui, -apple-system, 'Segoe UI', sans-serif",
  serif: "'Source Serif 4 Variable', Georgia, 'Times New Roman', serif",
  // A modular scale (ratio 1.25) from a 16px body.
  size: { xs: 13, sm: 14, md: 16, lg: 20, xl: 25, xxl: 31, display: 46 },
  weight: { regular: 400, medium: 520, semibold: 640, bold: 760 },
  leading: { tight: 1.1, snug: 1.3, body: 1.55, serif: 1.62 },
} as const;

export const space = { 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32, 10: 40, 12: 48, 16: 64, 20: 80 } as const;

export const radius = { sm: 3, md: 6 } as const;

export const rule = { law: 3, hair: 1 } as const;

export const layout = { maxWidth: 1160, measure: 68, gutter: 24, drawer: 480, labelMin: 420 } as const;

export const motion = {
  fast: 0.16,
  base: 0.32,
  draw: 1.0,
  stagger: 0.06,
  ease: [0.22, 1, 0.36, 1] as [number, number, number, number],
} as const;

export const chart = {
  height: 280,
  pad: { top: 20, right: 20, bottom: 36, left: 48 },
  ticks: 5,
  line: 2,
  dot: 4,
  hit: 26,
  bar: 14,
  barGap: 4,
  groupGap: 18,
  labelWidth: 230,
  barArea: 520,
  valueRoom: 56,
  valueGap: 6,
  barRadius: 2,
  baseline: 3,
  node: { w: 178, h: 46, colGap: 22, rowGap: 14 },
  markerOffset: 5,
  width: 1060,
} as const;

export const breakpoint = { narrow: 780 } as const;
