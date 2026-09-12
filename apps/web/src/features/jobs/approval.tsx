"use client";

import { useState } from "react";

type Decision = "approve" | "reject";

export default function OwnerApprovalPanel({
  busy, decide,
}: {
  busy: boolean;
  decide: (kind: Decision, reason: string) => Promise<void>;
}) {
  const [reason, setReason] = useState("");

  return <section aria-label="所有者决定">
    <h3>所有者决定</h3>
    <p className="muted">请先核对上方冻结内容。不要填写凭据、Token 或宿主机路径。</p>
    <label htmlFor="owner-decision-reason">决定说明（可选）</label>
    <input id="owner-decision-reason" value={reason}
      onChange={(event) => {
        if ([...event.target.value].length <= 500) setReason(event.target.value);
      }} />
    <button disabled={busy} onClick={() => void decide("approve", reason)}>
      批准并排队
    </button>
    <button disabled={busy} onClick={() => void decide("reject", reason)}>
      拒绝批次
    </button>
  </section>;
}
