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
  | "AGENT_CONFIGURATION_NOT_FOUND";

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
