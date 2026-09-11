// Public identity shapes mirror HTTP_API.md and FastAPI's ActorResponse schema.
export type Actor = {
  user_id: string;
  username: string;
  role: "owner" | "collaborator";
};

export type ApiErrorCode =
  | "AUTHENTICATION_REQUIRED" | "FORBIDDEN" | "VALIDATION_ERROR"
  | "DEPENDENCY_UNAVAILABLE" | "RATE_LIMITED" | "UNAVAILABLE"
  | "INVITATION_UNAVAILABLE" | "IDENTITY_CONFLICT" | "MEMBER_NOT_FOUND";

export type Invitation = {
  invitation_id: string;
  status: "pending" | "expired" | "revoked" | "redeemed";
  expires_at: string;
};

export type Member = { user_id: string; username: string; active: boolean };
export type Page<T> = { items: T[]; next_cursor: string | null };
