// Public identity shapes mirror HTTP_API.md and FastAPI's ActorResponse schema.
export type Actor = {
  user_id: string;
  username: string;
  role: "owner" | "collaborator";
};

export type ApiErrorCode =
  | "AUTHENTICATION_REQUIRED" | "FORBIDDEN" | "VALIDATION_ERROR"
  | "DEPENDENCY_UNAVAILABLE" | "RATE_LIMITED" | "UNAVAILABLE"
  | "INVITATION_UNAVAILABLE" | "IDENTITY_CONFLICT" | "MEMBER_NOT_FOUND"
  | "INVALID_REQUEST" | "CATALOG_CONFLICT" | "TASK_NOT_FOUND"
  | "AGENT_CONFIGURATION_NOT_FOUND" | "AGENT_CONFIGURATION_DISABLED"
  | "IDEMPOTENCY_CONFLICT" | "IDEMPOTENCY_KEY_INVALID" | "JOB_NOT_FOUND"
  | "OWNER_APPROVAL_REQUIRED" | "JOB_STATE_CONFLICT"
  | "ARTIFACT_NOT_FOUND" | "ARTIFACT_NOT_READY"
  | "EMPTY_JOB_SELECTION" | "BATCH_PRESET_EXCEEDED"
  | "LIMIT_PROFILE_NOT_ALLOWED" | "EVALUATION_TRACK_NOT_ENABLED";

export type Invitation = {
  invitation_id: string;
  status: "pending" | "expired" | "revoked" | "redeemed";
  expires_at: string;
};

export type Member = { user_id: string; username: string; active: boolean };
export type Page<T> = { items: T[]; next_cursor: string | null };

export type CatalogTask = {
  task_id: string; instance_id: string; dataset_id: string; dataset_revision: string;
  split: string; repo: string; base_commit: string; problem_statement_preview: string;
  problem_statement?: string;
};

export type CatalogAgent = {
  agent_configuration_id: string; display_name: string; agent_type: "codex";
  agent_version: string; model_provider: "openai_chatgpt"; model: string;
  configuration_fingerprint: string; enabled: boolean;
  public_options?: { reasoning_effort: string }; limit_profile_id?: string | null;
};

export type BatchPreset = {
  batch_preset: string; minimum_tasks: number; maximum_tasks: number;
};
export type LimitProfile = {
  limit_profile_id: string; agent_wall_timeout_sec: number; agent_cpus: number;
  agent_memory_mb: number; agent_storage_mb: number;
  evaluator_wall_timeout_sec: number; evaluator_cpus: number;
  evaluator_memory_mb: number; pids_limit: number; patch_warning_bytes: number;
  patch_max_bytes: number; raw_artifact_max_bytes: number; raw_run_max_bytes: number;
  concurrency: number; max_retries: number;
};
export type JobOptions = {
  batch_presets: BatchPreset[]; evaluation_tracks: ["closed_book"];
  limit_profiles: LimitProfile[]; maximum_agent_configurations: number;
  maximum_runs: number;
};
export const JOB_STATUSES = [
  "AWAITING_OWNER_APPROVAL", "QUEUED", "PREPARING", "EXECUTING",
  "FINALIZING", "COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED", "REJECTED",
  "CANCEL_REQUESTED", "CANCELED",
] as const;
export type JobStatus = typeof JOB_STATUSES[number];
export const RUN_STATUSES = [
  "PENDING", "PREPARING", "RUNNING_AGENT", "VERIFYING",
  "COMPLETED", "FAILED", "CANCELED",
] as const;
export type RunStatus = typeof RUN_STATUSES[number];
export const ARTIFACT_TYPES = [
  "agent_patch", "public_test_summary", "public_trajectory",
] as const;
export type ArtifactType = typeof ARTIFACT_TYPES[number];
export const REDACTION_STATUSES = ["not_required", "redacted"] as const;
export type RedactionStatus = typeof REDACTION_STATUSES[number];
export type JobSummary = {
  job_id: string; status: JobStatus;
  evaluation_track: "closed_book"; result_scope: "official" | "internal_test";
  batch_preset: string; limit_profile_id: string; trial_count: number;
  run_ids: string[]; estimated_finish_at: null; created_at: string;
  owner_decided_by: string | null; owner_decided_at: string | null;
  owner_decision_reason: string | null;
  cancel_requested_by: string | null; cancel_requested_at: string | null;
  cancel_reason: string | null;
};
export type JobDetail = JobSummary & {
  task_snapshots: Array<{
    task_id: string; instance_id: string; problem_statement: string;
  }>;
  agent_snapshots: Array<{
    agent_configuration_id: string; display_name: string;
    agent_type: string; agent_version: string; model_provider: string; model: string;
    reasoning_effort: string; configuration_fingerprint: string;
  }>;
  limit_snapshot: Omit<LimitProfile, "limit_profile_id">;
  network_policy_id: string;
  network_policy_snapshot: {
    mode: string; web_search: string; arbitrary_hosts: boolean;
  };
  tool_profile_id: string;
  tool_profile_snapshot: {
    agent_type: string; web_search: string; arbitrary_commands: boolean;
  };
  harbor_revision: string; swe_gym_revision: string; swe_bench_fork_revision: string;
};

export type RunReport = {
  run: {
    run_id: string; job_id: string; status: RunStatus; stage: string | null;
    task_instance_id: string; agent_configuration_id: string;
    backend_job_ref: string | null; backend_trial_ref: string | null;
    failure_code: string | null; failure_summary: string | null;
    started_at: string | null; finished_at: string | null;
  };
  deterministic_result: null | {
    patch_exists: boolean; patch_successfully_applied: boolean; resolved: boolean;
    tests_status_summary: Record<string, unknown>; harness_revision: string;
    duration_ms: number | null;
  };
  process_metrics: {
    usage: {
      n_input_tokens: number | null; n_cache_tokens: number | null;
      n_output_tokens: number | null; cost_usd: number | null;
    };
    resources: {
      wall_time_sec: number | null; cpu_time_sec: number | null;
      peak_memory_bytes: number | null;
    };
  };
  judge_analyses: unknown[]; human_review: null; quality_tiebreak: null;
  review_status: "NOT_REQUIRED";
  artifact_links: Array<{
    artifact_id: string;
    artifact_type: ArtifactType;
    sha256: string; size_bytes: number; content_type: string;
    redaction_status: RedactionStatus; warnings: string[];
  }>;
};

export const BATCH_OUTCOMES = [
  "resolved", "unresolved", "infrastructure_error", "incomplete",
] as const;
export type BatchOutcome = typeof BATCH_OUTCOMES[number];
export type JobRunReport = {
  run_id: string; status: RunStatus; stage: string | null; stage_message: string;
  task_instance_id: string; agent_configuration_id: string;
  agent_display_name: string; outcome: BatchOutcome; resolved: boolean | null;
  failure_code: string | null; report_path: string;
};
export type JobReport = {
  job_id: string; status: JobStatus; stage_message: string;
  failure_code: string | null; trial_count: number; completed_runs: number;
  failed_runs: number; pending_runs: number; resolved_runs: number;
  unresolved_runs: number; runs: JobRunReport[];
};

export type ArtifactPage = Page<RunReport["artifact_links"][number]>;
export type TrajectoryEvent = {
  sequence: number; occurred_at: string; source: string; type: string;
  summary: string; payload: Record<string, never>;
};
export type TrajectoryPage = {
  items: TrajectoryEvent[]; next_after_sequence: number; complete: boolean;
};
