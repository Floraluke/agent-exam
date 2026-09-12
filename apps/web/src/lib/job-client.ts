import { request } from "./api-client";
import type { JobDetail, JobOptions, JobSummary, Page } from "./contracts";
import {
  parseJobDetail,
  parseJobOptions,
  parseJobPage,
  parseJobSummary,
} from "./job-shapes";

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
