export const pct = (x: number, digits = 0) => `${(x * 100).toFixed(digits)}%`;
export const days = (x: number) => `${x.toFixed(1)} days`;
export const int = (x: number) => x.toLocaleString("en-GB");
