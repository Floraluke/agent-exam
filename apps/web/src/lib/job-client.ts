import { request } from "./api-client";
import type { JobDetail, JobOptions, JobSummary, Page, RunReport } from "./contracts";
import {
  parseJobDetail,
  parseJobOptions,
  parseJobPage,
  parseJobSummary,
} from "./job-shapes";
import { parseRunReport } from "./report-shapes";

export async function jobOptions(): Promise<JobOptions> {
  return parseJobOptions(await request("job-options"));
}

export async function submitJob(body: object, key: string): Promise<JobSummary> {
  return parseJobSummary(await request("jobs", body, { "Idempotency-Key": key }));
}

export async function jobDetail(id: string): Promise<JobDetail> {
  return parseJobDetail(await request("jobs/" + encodeURIComponent(id)));
}

export async function decideJob(
  id: string,
  decision: "approve" | "reject",
  reason: string,
  key: string,
): Promise<JobSummary> {
  const body = reason === "" ? {} : { reason };
  return parseJobSummary(
    await request(`jobs/${encodeURIComponent(id)}/${decision}`, body, {
      "Idempotency-Key": key,
    }),
  );
}

export async function jobs(): Promise<Page<JobSummary>> {
  return parseJobPage(await request("jobs?limit=20"));
}

export async function runReport(id: string): Promise<RunReport> {
  return parseRunReport(await request("reports/runs/" + encodeURIComponent(id)));
}
