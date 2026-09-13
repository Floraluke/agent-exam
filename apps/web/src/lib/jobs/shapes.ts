import { ApiError } from "../api-client";
import { JOB_STATUSES } from "../contracts";
import type { JobSummary } from "../contracts";

export function object(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ApiError("UNAVAILABLE");
  }
  return value as Record<string, unknown>;
}

export function text(value: Record<string, unknown>, key: string): string {
  if (typeof value[key] !== "string") throw new ApiError("UNAVAILABLE");
  return value[key];
}

export function number(value: Record<string, unknown>, key: string): number {
  if (!Number.isInteger(value[key]) || Number(value[key]) < 0) {
    throw new ApiError("UNAVAILABLE");
  }
  return Number(value[key]);
}

export function bool(value: Record<string, unknown>, key: string): boolean {
  if (typeof value[key] !== "boolean") throw new ApiError("UNAVAILABLE");
  return value[key];
}

export function nullableText(
  value: Record<string, unknown>, key: string,
): string | null {
  if (value[key] !== null && typeof value[key] !== "string") {
    throw new ApiError("UNAVAILABLE");
  }
  return value[key] as string | null;
}

function normalizedReason(value: Record<string, unknown>, key: string): string | null {
  const reason = nullableText(value, key);
  if (reason !== null &&
      (reason !== reason.trim() || [...reason].length < 1 || [...reason].length > 500 ||
       /[\u0000-\u001f\u007f-\u009f]/u.test(reason))) {
    throw new ApiError("UNAVAILABLE");
  }
  return reason;
}

export function parseJobSummary(value: unknown): JobSummary {
  const item = object(value);
  if (
    !JOB_STATUSES.includes(String(item.status) as typeof JOB_STATUSES[number]) ||
    item.evaluation_track !== "closed_book" ||
    !["official", "internal_test"].includes(String(item.result_scope)) ||
    !Array.isArray(item.run_ids) ||
    item.run_ids.some((id) => typeof id !== "string") ||
    item.estimated_finish_at !== null
  ) throw new ApiError("UNAVAILABLE");
  const decidedBy = nullableText(item, "owner_decided_by");
  const decidedAt = nullableText(item, "owner_decided_at");
  const reason = normalizedReason(item, "owner_decision_reason");
  const cancelBy = nullableText(item, "cancel_requested_by");
  const cancelAt = nullableText(item, "cancel_requested_at");
  const cancelReason = normalizedReason(item, "cancel_reason");
  const failureCode = nullableText(item, "failure_code");
  const failureSummary = nullableText(item, "failure_summary");
  const rerunOf = nullableText(item, "rerun_of_job_id");
  const awaiting = item.status === "AWAITING_OWNER_APPROVAL";
  const canceled = item.status === "CANCELED";
  const hasDecision = decidedBy !== null && decidedAt !== null;
  const hasCancellation = cancelBy !== null && cancelAt !== null;
  const cancelState = ["CANCEL_REQUESTED", "CANCELED"].includes(String(item.status));
  const failed = ["FAILED", "COMPLETED_WITH_ERRORS"].includes(String(item.status));
  if (
    (decidedBy === null) !== (decidedAt === null) ||
    (!hasDecision && reason !== null) || (awaiting && hasDecision) ||
    (!awaiting && !canceled && !hasDecision) ||
    ((cancelBy === null) !== (cancelAt === null)) ||
    (!hasCancellation && cancelReason !== null) || cancelState !== hasCancellation ||
    ((failureCode === null) !== (failureSummary === null)) ||
    failed !== (failureCode !== null) || rerunOf === item.job_id
  ) throw new ApiError("UNAVAILABLE");
  return {
    job_id: text(item, "job_id"),
    status: item.status as JobSummary["status"],
    evaluation_track: "closed_book",
    result_scope: item.result_scope === "official" ? "official" : "internal_test",
    batch_preset: text(item, "batch_preset"),
    limit_profile_id: text(item, "limit_profile_id"),
    trial_count: number(item, "trial_count"),
    run_ids: item.run_ids,
    estimated_finish_at: null,
    created_at: text(item, "created_at"),
    owner_decided_by: decidedBy,
    owner_decided_at: decidedAt,
    owner_decision_reason: reason,
    cancel_requested_by: cancelBy,
    cancel_requested_at: cancelAt,
    cancel_reason: cancelReason,
    failure_code: failureCode,
    failure_summary: failureSummary,
    rerun_of_job_id: rerunOf,
  };
}
