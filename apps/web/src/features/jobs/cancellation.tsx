"use client";

import { useState } from "react";

export default function CancellationPanel({
  busy, cancel,
}: {
  busy: boolean;
  cancel: (reason: string) => Promise<void>;
}) {
  const [reason, setReason] = useState("");
  return <section aria-label="取消评测">
    <h3>取消评测</h3>
    <p className="muted">执行中取消只停止后续 Trial，不会强制终止当前 Trial。</p>
    <label htmlFor="job-cancel-reason">取消说明（可选）</label>
    <input id="job-cancel-reason" value={reason}
      onChange={(event) => {
        if ([...event.target.value].length <= 500) setReason(event.target.value);
      }} />
    <button disabled={busy} onClick={() => void cancel(reason)}>取消批次</button>
  </section>;
}
