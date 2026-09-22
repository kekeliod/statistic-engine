export interface ProjectSummary {
  id: number;
  title: string;
  research_aim: string;
  created_at: string;
  updated_at: string;
  dataset_count: number;
}

export interface Project {
  id: number;
  title: string;
  research_aim: string;
  objectives: string[];
  research_questions: string[];
  hypotheses: string[];
  created_at: string;
  updated_at: string;
}

export interface ProjectCreatePayload {
  title: string;
  research_aim: string;
  objectives: string[];
  research_questions: string[];
  hypotheses: string[];
}

export interface Dataset {
  id: number;
  project_id: number;
  original_filename: string;
  file_type: string;
  sheet_name: string | null;
  n_rows: number;
  n_columns: number;
  columns: string[];
  version: number;
  is_active: boolean;
  uploaded_at: string;
}

export interface DatasetPreview {
  columns: string[];
  rows: Record<string, unknown>[];
  total_rows: number;
  offset: number;
  limit: number;
}

export interface ColumnProfile {
  name: string;
  dtype: string;
  non_null_count: number;
  missing_count: number;
  missing_pct: number;
  unique_count: number;
  mean: number | null;
  median: number | null;
  std: number | null;
  min: number | null;
  max: number | null;
  top_values: { value: string; count: number }[] | null;
}

export interface DuplicatesReport {
  duplicate_row_count: number;
  duplicate_row_pct: number;
  example_groups: number[][];
}

export interface OutlierColumnReport {
  column: string;
  method: string;
  count: number;
  pct: number;
  lower_bound: number | null;
  upper_bound: number | null;
  example_row_indices: number[];
  example_values: (number | null)[];
}

export interface InvalidValueColumnReport {
  column: string;
  reason: string;
  detail: string;
  count: number;
  examples: string[];
}

export interface QualityScoreBreakdown {
  overall: number;
  completeness: number;
  validity: number;
  consistency: number;
  duplicates: number;
  outliers: number;
  notes: string[];
  formula: string;
}

export interface DataQualityReport {
  n_rows: number;
  n_columns: number;
  columns: ColumnProfile[];
  duplicates: DuplicatesReport;
  outliers: OutlierColumnReport[];
  invalid_values: InvalidValueColumnReport[];
  score: QualityScoreBreakdown;
}

// ── Statistical analysis ────────────────────────────────────────────────────

export interface MethodRole {
  name: string;
  arity: "one" | "many";
  dtypes: string[];
  description: string;
}

export interface MethodSpec {
  key: string;
  label: string;
  category: string;
  description: string;
  when_to_use: string;
  roles: MethodRole[];
  param_defaults: Record<string, unknown>;
  bayesian_supported: boolean;
}

export interface StatEstimate {
  name: string;
  value: number | null;
  ci_low: number | null;
  ci_high: number | null;
  ci_level: number;
}

export interface StatEffectSize {
  name: string;
  value: number | null;
  magnitude: string | null;
}

export interface FrequentistBlock {
  statistic: { name: string; value: number | null };
  df: number | string | null;
  p_value: number | null;
  estimate: StatEstimate | null;
  effect_size: StatEffectSize | null;
  summary: string;
  coefficients?: { term: string; [k: string]: unknown }[];
}

export interface BayesianBlock {
  available: boolean;
  bayes_factor_10: number | null;
  interpretation: string | null;
  prior: string | null;
  summary: string;
  note: string | null;
}

export interface AssumptionCheck {
  key: string;
  label: string;
  passed: boolean | null;
  detail: string;
  p_value: number | null;
  recommendation: string | null;
}

export interface ResultTable {
  title: string;
  columns: string[];
  rows: (string | number | null)[][];
}

export interface StatResult {
  method: string;
  method_label: string;
  n_used: number;
  n_excluded: number;
  frequentist: FrequentistBlock;
  bayesian: BayesianBlock;
  assumptions: AssumptionCheck[];
  tables: ResultTable[];
  groups: Record<string, unknown>;
}

export interface Chart {
  id: number;
  project_id: number;
  analysis_id: number | null;
  kind: string;
  title: string;
  spec: { method?: string; available_kinds?: string[] };
  created_at: string;
}

export interface Analysis {
  id: number;
  project_id: number;
  dataset_id: number;
  objective_index: number | null;
  method: string;
  variables: Record<string, string | string[]>;
  params: Record<string, unknown>;
  status: "pending" | "complete" | "failed";
  result: StatResult | null;
  error: string | null;
  interpretation: string | null;
  charts: Chart[];
  created_at: string;
  updated_at: string;
}

export interface AnalysisCreatePayload {
  dataset_id: number;
  method: string;
  variables: Record<string, string | string[]>;
  params?: Record<string, unknown>;
  objective_index?: number | null;
}

export interface Recommendation {
  objective_index: number | null;
  objective_text: string;
  method_key: string;
  method_label: string;
  rationale: string;
  confidence: "high" | "medium" | "low";
  suggested_variables: Record<string, string | string[]>;
  chart_suggestion: string;
  alternative_method_key: string | null;
  source: "ai" | "rules";
}

export interface ChatMessage {
  id: number;
  project_id: number;
  role: "user" | "assistant";
  content: string;
  meta: { analysis_ids?: number[]; source?: string };
  created_at: string;
}

export interface ChatTurn {
  user: ChatMessage;
  assistant: ChatMessage;
  analysis_ids: number[];
  source: string;
}

export interface Health {
  status: string;
  ai_available: boolean;
}

export interface Report {
  id: number;
  project_id: number;
  title: string;
  format: "html" | "docx";
  created_at: string;
}
