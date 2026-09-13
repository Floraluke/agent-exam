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

export async function jobs(): Promise<Page<JobSummary>> {
  return parseJobPage(await request("jobs?limit=20"));
}

export async function runReport(id: string): Promise<RunReport> {
  return parseRunReport(await request("reports/runs/" + encodeURIComponent(id)));
}

export async function jobReport(id: string): Promise<JobReport> {
  return parseJobReport(await request("reports/jobs/" + encodeURIComponent(id)));
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
