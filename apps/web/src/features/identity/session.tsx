"use client";

import { useEffect, useState, type FormEvent } from "react";
import { ApiError, currentActor, login, logout } from "../../lib/api-client";
import type { Actor } from "../../lib/contracts";
import JoinPanel from "./join";
import MembersPanel from "./members";
import TasksPanel from "../catalog/tasks";
import AgentsPanel from "../catalog/agents";
import JobsPanel from "../jobs/submit";
import LeaderboardView from "../leaderboard/view";

export default function SessionPanel() {
  const [actor, setActor] = useState<Actor | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [joining, setJoining] = useState(false);
  const [joined, setJoined] = useState(false);

  function explain(value: unknown) {
    setError(value instanceof ApiError ? value.message : "暂时无法连接平台，请稍后重试。");
  }

  useEffect(() => {
    let active = true;
    currentActor().then((value) => { if (active) setActor(value); })
      .catch((value: unknown) => { if (active) explain(value); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try { setActor(await login(username, password)); }
    catch (value) { explain(value); }
    finally { setPassword(""); setBusy(false); }
  }

  async function signOut() {
    setBusy(true);
    setError("");
    try { await logout(); setActor(null); }
    catch (value) { explain(value); }
    finally { setBusy(false); }
  }

  if (loading) return <p role="status">正在检查登录状态…</p>;

  return <section className="session-card" aria-label="平台账号">
    {error && <p role="alert" className="error">{error}</p>}
    {actor ? <>
      <span className="eyebrow">应用身份已验证</span>
      <h2>已登录：{actor.username}</h2>
      <p>角色：{actor.role === "owner" ? "评测机所有者" : "协作者"}</p>
      <p className="muted">账号入口已接通；提交会先等待评测机所有者批准。</p>
      <button disabled={busy} onClick={signOut}>退出登录</button>
      {actor.role === "owner" && <MembersPanel />}
      <TasksPanel owner={actor.role === "owner"} />
      <AgentsPanel owner={actor.role === "owner"} />
      <JobsPanel owner={actor.role === "owner"} />
      <LeaderboardView />
    </> : <>
      {joined && <p role="status">加入成功，请使用新账号登录。</p>}
      {joining ? <>
        <JoinPanel onJoined={() => { setJoining(false); setJoined(true); }} />
        <button onClick={() => setJoining(false)}>返回登录</button>
      </> : <>
      <h2>登录平台</h2>
      <p className="muted">使用应用账号。这里不接收 Codex 或模型提供方的凭据。</p>
      <form onSubmit={submit}>
        <label htmlFor="username">账号</label>
        <input id="username" name="username" autoComplete="username" required
          minLength={3} maxLength={64} pattern="[a-z0-9][a-z0-9_.\-]{2,63}"
          value={username} onChange={(event) => setUsername(event.target.value)} />
        <label htmlFor="password">密码</label>
        <input id="password" name="password" type="password" autoComplete="current-password"
          required maxLength={128} value={password}
          onChange={(event) => setPassword(event.target.value)} />
        <button type="submit" disabled={busy}>{busy ? "正在登录…" : "登录"}</button>
      </form>
      <p className="muted small">不开放公共注册。所有者账号建立与恢复仅通过评测机本地维护命令完成。</p>
      <button onClick={() => { setJoining(true); setJoined(false); }}>使用邀请码加入</button>
      </>}
    </>}
  </section>;
}
