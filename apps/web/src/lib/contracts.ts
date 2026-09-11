// Public identity shapes mirror HTTP_API.md and FastAPI's ActorResponse schema.
export type Actor = {
  user_id: string;
  username: string;
  role: "owner" | "collaborator";
};

export type ApiErrorCode =
  | "AUTHENTICATION_REQUIRED" | "FORBIDDEN" | "VALIDATION_ERROR"
  | "DEPENDENCY_UNAVAILABLE" | "RATE_LIMITED" | "UNAVAILABLE";
