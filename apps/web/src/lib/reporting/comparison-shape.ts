import { ApiError } from "../api-client";
import { nullableText, number, object, text } from "../jobs/shapes";

export const COMPARISON_OUTCOMES = [
  "resolved", "unresolved", "infrastructure_error", "incomplete", "missing",
] as const;
export type ComparisonOutcome = typeof COMPARISON_OUTCOMES[number];

export type ComparisonCell = {
  outcome: ComparisonOutcome; resolved: boolean | null; run_id: string | null;
  failure_code: string | null; report_path: string | null;
};
export type ComparisonColumn = {
  job_id: string; agent_configuration_id: string; agent_display_name: string;
};
export type ComparisonTotals = {
  resolved: number; unresolved: number; infrastructure_error: number;
  incomplete: number; missing: number; decided: number; total: number;
};
export type ComparisonMatrix = {
  columns: ComparisonColumn[];
  rows: Array<{ task_instance_id: string; repo: string; cells: ComparisonCell[] }>;
  totals: ComparisonTotals[];
};

function nullableFlag(item: Record<string, unknown>, key: string) {
  if (item[key] !== null && typeof item[key] !== "boolean") {
    throw new ApiError("UNAVAILABLE");
  }
  return item[key] as boolean | null;
}

function cell(value: unknown): ComparisonCell {
  const item = object(value);
  if (!COMPARISON_OUTCOMES.includes(String(item.outcome) as ComparisonOutcome)) {
    throw new ApiError("UNAVAILABLE");
  }
  const outcome = item.outcome as ComparisonOutcome;
  const parsed = {
    outcome, resolved: nullableFlag(item, "resolved"),
    run_id: nullableText(item, "run_id"),
    failure_code: nullableText(item, "failure_code"),
    report_path: nullableText(item, "report_path"),
  };
  const expected = outcome === "resolved" ? true : outcome === "unresolved" ? false : null;
  if (parsed.resolved !== expected ||
      (outcome === "missing" && parsed.report_path !== null) ||
      (outcome !== "missing" && (parsed.run_id === null || parsed.report_path === null))) {
    throw new ApiError("UNAVAILABLE");
  }
  return parsed;
}

function totals(value: unknown): ComparisonTotals {
  const item = object(value);
  const result = {
    resolved: number(item, "resolved"), unresolved: number(item, "unresolved"),
    infrastructure_error: number(item, "infrastructure_error"),
    incomplete: number(item, "incomplete"), missing: number(item, "missing"),
    decided: number(item, "decided"), total: number(item, "total"),
  };
  if (result.decided !== result.resolved + result.unresolved +
      result.infrastructure_error + result.incomplete ||
      result.total !== result.decided + result.missing) throw new ApiError("UNAVAILABLE");
  return result;
}

export function parseComparison(value: unknown): ComparisonMatrix {
  const item = object(value);
  if (!Array.isArray(item.columns) || !Array.isArray(item.rows) ||
      !Array.isArray(item.totals)) throw new ApiError("UNAVAILABLE");
  const columns = item.columns.map((value) => {
    const column = object(value);
    return {
      job_id: text(column, "job_id"),
      agent_configuration_id: text(column, "agent_configuration_id"),
      agent_display_name: text(column, "agent_display_name"),
    };
  });
  const rows = item.rows.map((value) => {
    const row = object(value);
    if (!Array.isArray(row.cells)) throw new ApiError("UNAVAILABLE");
    return {
      task_instance_id: text(row, "task_instance_id"), repo: text(row, "repo"),
      cells: row.cells.map(cell),
    };
  });
  const parsedTotals = item.totals.map(totals);
  if (parsedTotals.length !== columns.length ||
      rows.some((row) => row.cells.length !== columns.length) ||
      parsedTotals.some((total) => total.total !== rows.length)) {
    throw new ApiError("UNAVAILABLE");
  }
  return { columns, rows, totals: parsedTotals };
}
