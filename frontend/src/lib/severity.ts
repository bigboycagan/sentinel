import type { Category, Severity } from "@/lib/types";

export const SEVERITIES: Severity[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];
export const CATEGORIES: Category[] = ["Security", "Code Quality", "Complexity", "Maintainability"];

export const SEVERITY_RANK: Record<Severity, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
  INFO: 4,
};

interface SeverityStyle {
  badge: string;
  dot: string;
  hex: string;
  text: string;
}

/** Functional severity ramp — red → orange → amber → blue → slate. */
export const SEVERITY_STYLES: Record<Severity, SeverityStyle> = {
  CRITICAL: {
    badge: "bg-[#450A0A] border-[#7F1D1D] text-[#FCA5A5]",
    dot: "bg-[#EF4444]",
    hex: "#EF4444",
    text: "text-[#FCA5A5]",
  },
  HIGH: {
    badge: "bg-[#431407] border-[#7C2D12] text-[#FDBA74]",
    dot: "bg-[#F97316]",
    hex: "#F97316",
    text: "text-[#FDBA74]",
  },
  MEDIUM: {
    badge: "bg-[#422006] border-[#78350F] text-[#FDE047]",
    dot: "bg-[#F59E0B]",
    hex: "#F59E0B",
    text: "text-[#FDE047]",
  },
  LOW: {
    badge: "bg-[#172554] border-[#1E3A8A] text-[#93C5FD]",
    dot: "bg-[#3B82F6]",
    hex: "#3B82F6",
    text: "text-[#93C5FD]",
  },
  INFO: {
    badge: "bg-[#1E293B] border-[#334155] text-[#CBD5E1]",
    dot: "bg-[#94A3B8]",
    hex: "#94A3B8",
    text: "text-[#CBD5E1]",
  },
};

/** Score bands, documented in backend/analyzers/scoring.py. */
export function scoreBand(score: number): { label: string; hex: string; text: string } {
  if (score >= 90) return { label: "Secure", hex: "#10B981", text: "text-emerald-400" };
  if (score >= 75) return { label: "Good", hex: "#34D399", text: "text-emerald-300" };
  if (score >= 50) return { label: "Needs Review", hex: "#F59E0B", text: "text-amber-400" };
  return { label: "Vulnerable", hex: "#EF4444", text: "text-red-400" };
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Human message for an ApiError body/status — never a raw stack trace. */
export function apiErrorMessage(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (status === 429) return "Too many analyses in a short time. Please wait a minute and try again.";
  if (status === 413) return "That file is too large to analyze. Lower it or raise the limit in Settings.";
  if (status >= 500) return "Something went wrong while analyzing the code.";
  return "Something went wrong while analyzing the code.";
}
