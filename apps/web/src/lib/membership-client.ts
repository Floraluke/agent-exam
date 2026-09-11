import { ApiError, request } from "./api-client";
import type { Invitation, Member, Page } from "./contracts";

function record(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ApiError("UNAVAILABLE");
  }
  return Object.fromEntries(Object.entries(value));
}

function text(value: unknown): string {
  if (typeof value !== "string") throw new ApiError("UNAVAILABLE");
  return value;
}

function invitation(value: unknown): Invitation {
  const item = record(value);
  const status = item.status;
  if (status !== "pending" && status !== "expired" && status !== "revoked" && status !== "redeemed") {
    throw new ApiError("UNAVAILABLE");
  }
  return { invitation_id: text(item.invitation_id), expires_at: text(item.expires_at), status };
}

function member(value: unknown): Member {
  const item = record(value);
  if (typeof item.active !== "boolean") throw new ApiError("UNAVAILABLE");
  return { user_id: text(item.user_id), username: text(item.username), active: item.active };
}

async function page<T>(path: string, parse: (value: unknown) => T, cursor: string | null): Promise<Page<T>> {
  const value = record(await request(path + (cursor ? `?cursor=${encodeURIComponent(cursor)}` : "")));
  if (!Array.isArray(value.items)) throw new ApiError("UNAVAILABLE");
  return {
    items: value.items.map(parse),
    next_cursor: value.next_cursor === null ? null : text(value.next_cursor),
  };
}

export const invitations = (cursor: string | null = null) => page("invitations", invitation, cursor);
export const members = (cursor: string | null = null) => page("members", member, cursor);

export async function invite(): Promise<string> {
  return text(record(await request("invitations", {})).invitation_token);
}

export async function redeem(invitation_token: string, username: string, password: string): Promise<void> {
  await request("invitations/redeem", { invitation_token, username, password });
}

export async function revoke(id: string): Promise<void> {
  await request(`invitations/${encodeURIComponent(id)}/revoke`, {});
}

export async function disable(id: string): Promise<void> {
  await request(`members/${encodeURIComponent(id)}/disable`, {});
}
