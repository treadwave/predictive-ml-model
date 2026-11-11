import type { Status } from "./api";

export const STATUS_LABEL: Record<Status, string> = {
  normal: "Норма",
  warning: "Внимание",
  critical: "Критично",
};

export const SEVERITY_LABEL: Record<string, string> = {
  info: "Инфо",
  warning: "Внимание",
  critical: "Критично",
};

export const SENSORS: { code: string; name: string }[] = [
  { code: "s2", name: "T24 — темп. на выходе КНД, °R" },
  { code: "s3", name: "T30 — темп. на выходе КВД, °R" },
  { code: "s4", name: "T50 — темп. на выходе ТНД, °R" },
  { code: "s7", name: "P30 — давление на выходе КВД, psia" },
  { code: "s8", name: "Nf — скорость вентилятора, об/мин" },
  { code: "s9", name: "Nc — скорость ядра, об/мин" },
  { code: "s11", name: "Ps30 — стат. давление КВД, psia" },
  { code: "s12", name: "phi — расход топлива / Ps30" },
  { code: "s13", name: "NRf — привед. скорость вентилятора" },
  { code: "s14", name: "NRc — привед. скорость ядра" },
  { code: "s15", name: "BPR — степень двухконтурности" },
  { code: "s17", name: "htBleed — энтальпия отбора" },
  { code: "s20", name: "W31 — охлаждающий отбор ТВД, lbm/s" },
  { code: "s21", name: "W32 — охлаждающий отбор ТНД, lbm/s" },
];

export function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("ru-RU");
}

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("ru-RU");
}

export function formatRul(value: number): string {
  return Math.round(value).toString();
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatResidual(value: number): string {
  const points = Math.round(value * 100);
  return `${points > 0 ? "+" : ""}${points} п.п.`;
}
