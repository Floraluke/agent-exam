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
export type JobSummary = {
  job_id: string; status: "AWAITING_OWNER_APPROVAL" | "QUEUED" | "REJECTED";
  evaluation_track: "closed_book"; result_scope: "official" | "internal_test";
  batch_preset: string; limit_profile_id: string; trial_count: number;
  run_ids: string[]; estimated_finish_at: null; created_at: string;
  owner_decided_by: string | null; owner_decided_at: string | null;
  owner_decision_reason: string | null;
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
