import type { Actor, ApiErrorCode } from "./contracts";

const messages: Record<ApiErrorCode, string> = {
  AUTHENTICATION_REQUIRED: "账号或密码不正确，或登录已失效。",
  FORBIDDEN: "请求未获允许，请从配置的同源入口访问。",
  VALIDATION_ERROR: "请检查输入格式。",
  DEPENDENCY_UNAVAILABLE: "身份存储暂不可用，请稍后重试。",
  RATE_LIMITED: "尝试过多，请稍等一分钟。",
  UNAVAILABLE: "暂时无法连接平台，请稍后重试。",
  INVITATION_UNAVAILABLE: "邀请码无效、已过期、已撤销或已使用。",
  IDENTITY_CONFLICT: "账号名称已被使用，或邀请已兑换，无法执行本操作。",
  MEMBER_NOT_FOUND: "未找到该成员，请刷新列表。",
};

export class ApiError extends Error {
  constructor(readonly code: ApiErrorCode) { super(messages[code]); }
}

export async function request(path: string, body?: object): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(`/api/v1/${path}`, {
      method: body === undefined ? "GET" : "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: body === undefined ? {} : {
        "Content-Type": "application/json", "X-AgentExam-Request": "1",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch { throw new ApiError("UNAVAILABLE"); }
  if (!response.ok) {
    let payload: unknown;
    try { payload = await response.json(); }
    catch { throw new ApiError("UNAVAILABLE"); }
    if (typeof payload === "object" && payload !== null && "error" in payload &&
        typeof payload.error === "object" && payload.error !== null &&
        "code" in payload.error && knownError(payload.error.code)) {
      throw new ApiError(payload.error.code);
    }
    throw new ApiError("UNAVAILABLE");
  }
  if (response.status === 204) return null;
  try { return await response.json(); }
  catch { throw new ApiError("UNAVAILABLE"); }
}

function knownError(value: unknown): value is ApiErrorCode {
  return typeof value === "string" && Object.prototype.hasOwnProperty.call(messages, value);
}

function actor(value: unknown): Actor {
  if (typeof value !== "object" || value === null ||
      !("user_id" in value) || typeof value.user_id !== "string" ||
      !("username" in value) || typeof value.username !== "string" ||
      !("role" in value) || !["owner", "collaborator"].includes(String(value.role))) {
    throw new ApiError("UNAVAILABLE");
  }
  return {
    user_id: value.user_id, username: value.username,
    role: value.role === "owner" ? "owner" : "collaborator",
  };
}

export async function currentActor(): Promise<Actor | null> {
  try { return actor(await request("auth/me")); }
  catch (error) {
    if (error instanceof ApiError && error.code === "AUTHENTICATION_REQUIRED") return null;
    throw error;
  }
}

export async function login(username: string, password: string): Promise<Actor> {
  return actor(await request("auth/login", { username, password }));
}

export async function logout(): Promise<void> { await request("auth/logout", {}); }
