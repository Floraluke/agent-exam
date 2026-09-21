import { request } from "../api-client";
import type { JobDetail, RunReport } from "../contracts";
import { jobDetail, runReport } from "../job-client";
import { parseComparison, type ComparisonMatrix } from "./comparison-shape";

export type BoundedResult<T> = { values: Map<string, T>; failed: string[] };

export async function comparison(jobIds: string[]): Promise<ComparisonMatrix> {
  const query = new URLSearchParams({ job_ids: jobIds.join(",") });
  return parseComparison(await request("reports/comparisons?" + query));
}

async function bounded<T>(
  ids: string[], load: (id: string) => Promise<T>, limit = 3,
): Promise<BoundedResult<T>> {
  const unique = [...new Set(ids)];
  const values = new Map<string, T>(); const failed: string[] = [];
  let cursor = 0;
  async function worker() {
    while (cursor < unique.length) {
      const id = unique[cursor++];
      try { values.set(id, await load(id)); }
      catch { failed.push(id); }
    }
  }
  await Promise.all(Array.from(
    { length: Math.min(limit, unique.length) }, () => worker(),
  ));
  return { values, failed };
}

export function comparisonDetails(ids: string[]): Promise<BoundedResult<JobDetail>> {
  return bounded(ids, jobDetail);
}

export function comparisonReports(ids: string[]): Promise<BoundedResult<RunReport>> {
  return bounded(ids, runReport);
}
