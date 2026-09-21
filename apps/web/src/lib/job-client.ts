import { request } from "./api-client";
import type {
  ArtifactPage, JobDetail, JobOptions, JobReport, JobSummary, Page, RunReport,
  TrajectoryPage,
} from "./contracts";
import { parseJobReport } from "./batch-report-shapes";
import {
  parseJobDetail,
  parseJobOptions,
  parseJobPage,
  parseJobSummary,
} from "./job-shapes";
import { parseArtifactPage, parseRunReport, parseTrajectoryPage } from "./report-shapes";
import { parseComparisonMatrix } from "./reporting/comparison-shapes";
import type { ComparisonMatrix } from "./reporting/comparison-shapes";

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

export async function cancelJob(
  id: string, reason: string, key: string,
): Promise<JobSummary> {
  const body = reason === "" ? {} : { reason };
  return parseJobSummary(
    await request(`jobs/${encodeURIComponent(id)}/cancel`, body, {
      "Idempotency-Key": key,
    }),
  );
}

export async function recoverJob(id: string): Promise<JobSummary> {
  return parseJobSummary(await request(`jobs/${encodeURIComponent(id)}/recover`, {}));
}

export async function retryJob(id: string, key: string): Promise<JobSummary> {
  return parseJobSummary(
    await request(`jobs/${encodeURIComponent(id)}/retry`, {}, {
      "Idempotency-Key": key,
    }),
  );
}

export async function jobs(query = new URLSearchParams({ limit: "20" })):
Promise<Page<JobSummary>> {
  return parseJobPage(await request("jobs?" + query));
}

export async function runReport(id: string): Promise<RunReport> {
  return parseRunReport(await request("reports/runs/" + encodeURIComponent(id)));
}

export async function jobReport(id: string): Promise<JobReport> {
  return parseJobReport(await request("reports/jobs/" + encodeURIComponent(id)));
}

export async function comparisons(ids: string[]): Promise<ComparisonMatrix> {
  const query = new URLSearchParams({ job_ids: ids.join(",") });
  return parseComparisonMatrix(await request("reports/comparisons?" + query));
}

export async function runArtifacts(id: string): Promise<ArtifactPage> {
  return parseArtifactPage(
    await request(`runs/${encodeURIComponent(id)}/artifacts?limit=100`),
  );
}

export async function runTrajectory(id: string, after = 0): Promise<TrajectoryPage> {
  return parseTrajectoryPage(
    await request(
      `runs/${encodeURIComponent(id)}/trajectory?after_sequence=${after}&limit=100`,
    ),
  );
}
