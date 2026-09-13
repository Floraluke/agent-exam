import { ApiError } from "../api-client";
import {
  ARTIFACT_TYPES,
  CONTENT_STATUSES,
  PUBLIC_ARTIFACT_TYPES,
  REDACTION_STATUSES,
  RETENTION_CLASSES,
} from "../contracts";
import type { RunReport } from "../contracts";

const PUBLIC_TYPES = new Set<string>(PUBLIC_ARTIFACT_TYPES);

function record(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ApiError("UNAVAILABLE");
  }
  return value as Record<string, unknown>;
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

function texts(value: Record<string, unknown>, key: string): string[] {
  const item = value[key];
  if (!Array.isArray(item) || item.some((entry) => typeof entry !== "string")) {
    throw new ApiError("UNAVAILABLE");
  }
  return item;
}

export function parseArtifact(
  value: unknown,
): RunReport["artifact_links"][number] {
  const item = record(value);
  if (
    !/^[0-9a-f]{64}$/.test(String(item.sha256)) ||
    !ARTIFACT_TYPES.includes(
      String(item.artifact_type) as (typeof ARTIFACT_TYPES)[number],
    ) ||
    !REDACTION_STATUSES.includes(
      String(item.redaction_status) as (typeof REDACTION_STATUSES)[number],
    ) ||
    !RETENTION_CLASSES.includes(
      String(item.retention_class) as (typeof RETENTION_CLASSES)[number],
    ) ||
    !CONTENT_STATUSES.includes(
      String(item.content_status) as (typeof CONTENT_STATUSES)[number],
    )
  ) {
    throw new ApiError("UNAVAILABLE");
  }
  const size = natural(item, "size_bytes");
  const original = natural(item, "original_size_bytes");
  const truncated = item.truncated;
  const expires = nullableText(item, "expires_at");
  const deleted = nullableText(item, "deleted_at");
  const deletedBy = nullableText(item, "deleted_by");
  const reason = nullableText(item, "deletion_reason");
  const retention = item.retention_class as (typeof RETENTION_CLASSES)[number];
  const status = item.content_status as (typeof CONTENT_STATUSES)[number];
  const auditCount = [deleted, deletedBy, reason].filter(Boolean).length;
  const publicType = PUBLIC_TYPES.has(String(item.artifact_type));
  if (
    typeof truncated !== "boolean" ||
    original < size ||
    truncated !== (original > size) ||
    (retention === "long_term" && (expires !== null || truncated)) ||
    (retention === "raw_30d" && expires === null) ||
    (auditCount !== 0 && auditCount !== 3) ||
    (status === "deleted") !== (deleted !== null) ||
    (status === "available") !== (publicType && deleted === null)
  ) {
    throw new ApiError("UNAVAILABLE");
  }
  return {
    artifact_id: text(item, "artifact_id"),
    artifact_type: item.artifact_type as (typeof ARTIFACT_TYPES)[number],
    sha256: text(item, "sha256"),
    size_bytes: size,
    content_type: text(item, "content_type"),
    created_at: nullableText(item, "created_at"),
    redaction_status: item.redaction_status as (typeof REDACTION_STATUSES)[number],
    warnings: texts(item, "warnings"),
    retention_class: retention,
    original_size_bytes: original,
    truncated,
    expires_at: expires,
    deleted_at: deleted,
    deleted_by: deletedBy,
    deletion_reason: reason,
    content_status: status,
  };
}
