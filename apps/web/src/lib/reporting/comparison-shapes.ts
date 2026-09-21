import { ApiError } from "../api-client";

// §10.4 的五档独立于 §10.1 的 BatchOutcome 四档——不改动既有四档语义。
export const COMPARISON_OUTCOMES = [  "resolved", "unresolved", "infrastructure_error", "incomplete", "missing",
] as const;
export type ComparisonOutcome = typeof COMPARISON_OUTCOMES[number];

/** 与后端 MAX_COMPARISON_JOBS 一致；超过会被服务端拒绝为 COMPARISON_LIMIT_EXCEEDED。 */
export const COMPARISON_LIMIT = 20;

export const COMPARISON_OUTCOME_NAMES: Record<ComparisonOutcome, string> = {
  resolved: "已解决",
  unresolved: "未解决",
  infrastructure_error: "基础设施错误",
  incomplete: "未完成",
  missing: "缺失",
};

export type ComparisonColumn = {
  job_id: string;
  agent_configuration_id: string;
  agent_display_name: string;
};

export type ComparisonCell = {
  outcome: ComparisonOutcome;
  resolved: boolean | null;
  run_id: string | null;
  failure_code: string | null;
  report_path: string | null;
};

export type ComparisonRow = {
  task_instance_id: string;
  repo: string;
  cells: ComparisonCell[];
};

export type ComparisonTotals = {
  resolved: number;
  unresolved: number;
  infrastructure_error: number;
  incomplete: number;
  missing: number;
  decided: number;
  total: number;
};

export type ComparisonMatrix = {
  columns: ComparisonColumn[];
  rows: ComparisonRow[];
  totals: ComparisonTotals[];
};

function record(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ApiError("UNAVAILABLE");
  }
  return value as Record<string, unknown>;
}

function items(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new ApiError("UNAVAILABLE");
  return value;
}

function text(value: Record<string, unknown>, key: string): string {
  if (typeof value[key] !== "string") throw new ApiError("UNAVAILABLE");
  return value[key];
}

function nullableText(value: Record<string, unknown>, key: string): string | null {
  if (value[key] !== null && typeof value[key] !== "string") {
    throw new ApiError("UNAVAILABLE");
  }
  return value[key] as string | null;
}

function natural(value: Record<string, unknown>, key: string): number {
  const item = value[key];
  if (typeof item !== "number" || !Number.isInteger(item) || item < 0) {
    throw new ApiError("UNAVAILABLE");
  }
  return item;
}

function column(value: unknown): ComparisonColumn {
  const item = record(value);
  return {
    job_id: text(item, "job_id"),
    agent_configuration_id: text(item, "agent_configuration_id"),
    agent_display_name: text(item, "agent_display_name"),
  };
}

function cell(value: unknown): ComparisonCell {
  const item = record(value);
  const outcome = item.outcome;
  if (!COMPARISON_OUTCOMES.includes(outcome as ComparisonOutcome)) {
    throw new ApiError("UNAVAILABLE");
  }
  const resolved = item.resolved;
  if (resolved !== null && typeof resolved !== "boolean") {
    throw new ApiError("UNAVAILABLE");
  }
  const parsed: ComparisonCell = {
    outcome: outcome as ComparisonOutcome,
    resolved: resolved as boolean | null,
    run_id: nullableText(item, "run_id"),
    failure_code: nullableText(item, "failure_code"),
    report_path: nullableText(item, "report_path"),
  };
  // 硬规则：missing 不当作未解决或零，其 resolved 与 report_path 必须为 null。
  if (parsed.outcome === "missing" &&
      (parsed.resolved !== null || parsed.report_path !== null)) {
    throw new ApiError("UNAVAILABLE");
  }
  return parsed;
}

function row(value: unknown, width: number): ComparisonRow {
  const item = record(value);
  const cells = items(item.cells).map(cell);
  if (cells.length !== width) throw new ApiError("UNAVAILABLE");
  return {
    task_instance_id: text(item, "task_instance_id"),
    repo: text(item, "repo"),
    cells,
  };
}

function totals(value: unknown): ComparisonTotals {
  const item = record(value);
  const parsed: ComparisonTotals = {
    resolved: natural(item, "resolved"),
    unresolved: natural(item, "unresolved"),
    infrastructure_error: natural(item, "infrastructure_error"),
    incomplete: natural(item, "incomplete"),
    missing: natural(item, "missing"),
    decided: natural(item, "decided"),
    total: natural(item, "total"),
  };
  const decided = parsed.resolved + parsed.unresolved +
    parsed.infrastructure_error + parsed.incomplete;
  // v1 不返回字符串覆盖率；分母由 decided 与 total 两个整数表达。
  if (parsed.decided !== decided || parsed.total !== decided + parsed.missing) {
    throw new ApiError("UNAVAILABLE");
  }
  return parsed;
}

export function parseComparisonMatrix(value: unknown): ComparisonMatrix {
  const item = record(value);
  const columns = items(item.columns).map(column);
  const totalsList = items(item.totals).map(totals);
  if (totalsList.length !== columns.length) throw new ApiError("UNAVAILABLE");
  return {
    columns,
    rows: items(item.rows).map((entry) => row(entry, columns.length)),
    totals: totalsList,
  };
}
