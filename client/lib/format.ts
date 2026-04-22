import { format, formatDistanceToNowStrict, parseISO } from "date-fns";

type CurrencyOptions = {
  compact?: boolean;
  showSign?: boolean;
};

type PctOptions = {
  showSign?: boolean;
};

type NumberOptions = {
  decimals?: number;
};

export function formatCurrency(value: number, options: CurrencyOptions = {}) {
  const safeValue = Number.isFinite(value) ? value : 0;
  const absValue = Math.abs(safeValue);

  const formatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: options.compact ? "compact" : "standard",
    maximumFractionDigits: options.compact ? 1 : 2,
    minimumFractionDigits: options.compact ? 0 : 2,
  });

  const formatted = formatter.format(absValue);
  if (safeValue < 0) return `-${formatted}`;
  if (safeValue > 0 && options.showSign) return `+${formatted}`;
  return formatted;
}

export function formatPct(value: number, options: PctOptions = {}) {
  const safeValue = Number.isFinite(value) ? value : 0;
  const sign = safeValue > 0 && options.showSign !== false ? "+" : "";
  return `${sign}${safeValue.toFixed(2)}%`;
}

export function formatShares(value: number) {
  const safeValue = Number.isFinite(value) ? value : 0;
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 6,
  }).format(safeValue);
}

export function formatNumber(value: number, options: NumberOptions = {}) {
  const safeValue = Number.isFinite(value) ? value : 0;
  const decimals = options.decimals ?? 0;
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(safeValue);
}

export function formatDate(
  value: string | Date,
  mode?: "relative" | "long"
) {
  const date = value instanceof Date ? value : parseISO(value);
  if (Number.isNaN(date.getTime())) return "-";

  if (mode === "relative") {
    return `${formatDistanceToNowStrict(date, { addSuffix: true })}`;
  }

  if (mode === "long") {
    return format(date, "MMM d, yyyy h:mm a");
  }

  return format(date, "MMM d");
}
