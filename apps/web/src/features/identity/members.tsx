"use client";

import { useEffect, useState } from "react";
import { ApiError } from "../../lib/api-client";
import * as api from "../../lib/membership-client";
import type { Invitation, Member, Page } from "../../lib/contracts";

const statusNames = { pending: "待使用", expired: "已过期", revoked: "已撤销", redeemed: "已兑换" };

export default function MembersPanel() {
  const [invitations, setInvitations] = useState<Page<Invitation>>({ items: [], next_cursor: null });
  const [members, setMembers] = useState<Page<Member>>({ items: [], next_cursor: null });
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");

  function explain(value: unknown) {
    setError(value instanceof ApiError ? value.message : "暂时无法加载成员管理，请稍后重试。");
  }

  async function refresh() {
    const [invitationPage, memberPage] = await Promise.all([api.invitations(), api.members()]);
    setInvitations(invitationPage);
    setMembers(memberPage);
  }

  useEffect(() => {
    let active = true;
    Promise.all([api.invitations(), api.members()]).then(([invitationPage, memberPage]) => {
      if (active) { setInvitations(invitationPage); setMembers(memberPage); }
    }).catch((value: unknown) => { if (active) explain(value); })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, []);

  async function run(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    try { await work(); }
    catch (value) { explain(value); }
    finally { setBusy(false); }
  }

  async function create() {
    setToken("");
    setToken(await api.invite());
    await refresh();
  }

  async function loadInvitations() {
    const next = await api.invitations(invitations.next_cursor);
    setInvitations({ ...next, items: [...invitations.items, ...next.items] });
  }

  async function loadMembers() {
    const next = await api.members(members.next_cursor);
    setMembers({ ...next, items: [...members.items, ...next.items] });
  }

  return <section aria-label="成员管理">
    <h2>成员管理</h2>
    {error && <p role="alert" className="error">{error}</p>}
    <button disabled={busy} onClick={() => run(refresh)}>刷新成员与邀请</button>
    <h3>邀请协作者</h3>
    <p>邀请码 24 小时内有效且只能使用一次，请自行安全交给受邀者。</p>
    <button disabled={busy} onClick={() => run(create)}>创建邀请码</button>
    {token && <div>
      <label htmlFor="created-invitation">仅此一次的邀请码</label>
      <input id="created-invitation" readOnly autoComplete="off" value={token} />
      <p>刷新、退出或关闭后无法再次查看，请勿放入公开记录。</p>
      <button onClick={() => setToken("")}>关闭邀请码</button>
    </div>}
    <ul>{invitations.items.map((invitation) => <li key={invitation.invitation_id}>
      邀请 {invitation.invitation_id} — {statusNames[invitation.status]}；
      到期 {new Date(invitation.expires_at).toLocaleString()}
      {invitation.status === "pending" && <button disabled={busy}
        onClick={() => run(async () => { await api.revoke(invitation.invitation_id); setToken(""); await refresh(); })}>
        撤销邀请 {invitation.invitation_id}
      </button>}
    </li>)}</ul>
    {invitations.next_cursor && <button disabled={busy} onClick={() => run(loadInvitations)}>更多邀请</button>}
    <h3>协作者</h3>
    {!members.items.length && <p>暂无协作者。</p>}
    <ul>{members.items.map((member) => <li key={member.user_id}>
      {member.username}（{member.active ? "已启用" : "已停用"}）
      {member.active && <button disabled={busy}
        onClick={() => run(async () => { await api.disable(member.user_id); await refresh(); })}>
        停用 {member.username}
      </button>}
    </li>)}</ul>
    {members.next_cursor && <button disabled={busy} onClick={() => run(loadMembers)}>更多成员</button>}
  </section>;
}
