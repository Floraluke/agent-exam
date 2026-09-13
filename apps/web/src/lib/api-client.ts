import type { Actor, ApiErrorCode } from "./contracts";

const messages: Record<ApiErrorCode, string> = {
  AUTHENTICATION_REQUIRED: "账号或密码不正确，或登录已失效。",
  FORBIDDEN: "请求未获允许，请从配置的同源入口访问。",
  VALIDATION_ERROR: "请检查输入格式。",
  DEPENDENCY_UNAVAILABLE: "平台存储暂不可用，请稍后重试。",
  RATE_LIMITED: "尝试过多，请稍等一分钟。",
  UNAVAILABLE: "暂时无法连接平台，请稍后重试。",
  INVITATION_UNAVAILABLE: "邀请码无效、已过期、已撤销或已使用。",
  IDENTITY_CONFLICT: "账号名称已被使用，或邀请已兑换，无法执行本操作。",
  MEMBER_NOT_FOUND: "未找到该成员，请刷新列表。",
  INVALID_REQUEST: "目录选择或筛选条件无效。",
  CATALOG_CONFLICT: "固定身份的内容发生冲突，未覆盖原记录。",
  TASK_NOT_FOUND: "未找到该任务，请刷新目录。",
  AGENT_CONFIGURATION_NOT_FOUND: "未找到该配置，请刷新目录。",
  AGENT_CONFIGURATION_DISABLED: "所选配置已禁用，请刷新后重新选择。",
  IDEMPOTENCY_CONFLICT: "本次提交标识已用于不同选择，请重新提交。",
  IDEMPOTENCY_KEY_INVALID: "提交标识无效，请重新提交。",
  JOB_NOT_FOUND: "未找到该评测批次，或当前账号无权查看。",
  OWNER_APPROVAL_REQUIRED: "只有评测机所有者可以批准或拒绝批次。",
  JOB_STATE_CONFLICT: "批次状态已经改变，请刷新后查看。",
  ARTIFACT_NOT_FOUND: "未找到该证据，或当前账号无权查看。",
  ARTIFACT_NOT_READY: "该证据尚不能安全公开。",
  ARTIFACT_DELETED: "该证据正文已按保留策略清理，审计元数据仍保留。",
  EMPTY_JOB_SELECTION: "请至少选择一道任务和一个配置。",
  BATCH_PRESET_EXCEEDED: "任务或配置数量不符合所选批次规模。",
  LIMIT_PROFILE_NOT_ALLOWED: "所选资源限制不可用，请刷新选项。",
  EVALUATION_TRACK_NOT_ENABLED: "所选评测赛道尚未开放。",
};

export class ApiError extends Error {
  constructor(readonly code: ApiErrorCode) { super(messages[code]); }
}

export async function request(
  path: string, body?: object, extraHeaders: Record<string, string> = {},
): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(`/api/v1/${path}`, {
      method: body === undefined ? "GET" : "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: body === undefined ? extraHeaders : {
        "Content-Type": "application/json", "X-AgentExam-Request": "1", ...extraHeaders,
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
