// Hand-written mirrors of the Pydantic models in backend/models/*.py.
// Nothing infers across the HTTP boundary — change both sides in the same edit.

export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
export type Category = "Security" | "Code Quality" | "Complexity" | "Maintainability";

/** backend/models/analysis.py :: Finding */
export interface Finding {
  rule_id: string;
  severity: Severity;
  category: Category;
  title: string;
  message: string;
  file: string;
  line: number;
  column: number;
  recommendation: string;
  code_snippet: string | null;
}

/** backend/models/analysis.py :: ParseErrorInfo */
export interface ParseErrorInfo {
  message: string;
  line: number;
  column: number;
}

/** backend/models/analysis.py :: ScoreBreakdown */
export interface ScoreBreakdown {
  security: number;
  quality: number;
  complexity: number;
  maintainability: number;
}

/** backend/models/analysis.py :: SeverityCounts */
export interface SeverityCounts {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

/** backend/models/analysis.py :: FileMetrics */
export interface FileMetrics {
  total_lines: number;
  source_lines: number;
  comment_lines: number;
  blank_lines: number;
  function_count: number;
  class_count: number;
  max_nesting_depth: number | null;
  avg_function_length: number | null;
  avg_complexity: number | null;
  max_complexity: number | null;
  maintainability_index: number | null;
}

/** backend/models/analysis.py :: AnalysisReport */
export interface AnalysisReport {
  id: string;
  file_name: string;
  language: string;
  analyzed_at: string;
  scores: ScoreBreakdown | null;
  overall_score: number | null;
  counts: SeverityCounts;
  metrics: FileMetrics;
  findings: Finding[];
  parse_error: ParseErrorInfo | null;
}

/** backend/models/analysis.py :: AnalyzeRequest */
export interface AnalyzeRequest {
  code: string;
  file_name: string;
  language: string;
}

/** backend/models/analysis.py :: RuleMeta */
export interface RuleMeta {
  rule_id: string;
  title: string;
  category: Category;
  severity: Severity;
  description: string;
  recommendation: string;
  language: string;
}

/** backend/models/history.py :: HistorySummary */
export interface HistorySummary {
  id: string;
  created_at: string;
  file_name: string;
  language: string;
  overall_score: number | null;
  security_score: number | null;
  total_issues: number;
  critical_issues: number;
  high_issues: number;
  medium_issues: number;
  low_issues: number;
  info_issues: number;
}

/** backend/models/settings.py :: AppSettings */
export interface AppSettings {
  max_file_size_bytes: number;
  disabled_rules: string[];
}

/** backend/models/settings.py :: AppSettingsUpdate */
export interface AppSettingsUpdate {
  max_file_size_bytes?: number;
  disabled_rules?: string[];
}
