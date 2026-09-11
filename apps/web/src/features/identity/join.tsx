"use client";

import { useState, type FormEvent } from "react";
import { ApiError } from "../../lib/api-client";
import { redeem } from "../../lib/membership-client";

export default function JoinPanel({ onJoined }: { onJoined: () => void }) {
  const [token, setToken] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try { await redeem(token, username, password); onJoined(); }
    catch (value) { setError(value instanceof ApiError ? value.message : "暂时无法加入，请稍后重试。"); }
    finally { setPassword(""); setToken(""); setBusy(false); }
  }

  return <section aria-label="受邀加入">
    <h2>使用邀请码加入</h2>
    <p>由所有者提供邀请码；加入后获得协作者身份。请勿输入模型凭据。</p>
    {error && <p role="alert" className="error">{error}</p>}
    <form onSubmit={submit}>
      <label htmlFor="join-token">邀请码</label>
      <input id="join-token" type="password" autoComplete="off" required maxLength={128}
        value={token} onChange={(event) => setToken(event.target.value)} />
      <label htmlFor="join-username">新账号</label>
      <input id="join-username" autoComplete="username" required minLength={3} maxLength={64}
        pattern="[a-z0-9][a-z0-9_.\-]{2,63}" value={username}
        onChange={(event) => setUsername(event.target.value)} />
      <label htmlFor="join-password">新密码</label>
      <input id="join-password" type="password" autoComplete="new-password" required
        minLength={15} maxLength={128} value={password}
        onChange={(event) => setPassword(event.target.value)} />
      <button type="submit" disabled={busy}>{busy ? "正在加入…" : "加入平台"}</button>
    </form>
  </section>;
}
