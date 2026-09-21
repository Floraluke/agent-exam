"use client";

import { useState } from "react";
import type { Actor } from "../../../lib/contracts";
import JobsPanel from "../submit";
import JobList from "./view";

function linkedJob() {
  return typeof window === "undefined" ? null :
    new URL(window.location.href).searchParams.get("job");
}

export default function JobWorkspace({
  actor,
  newJob,
}: {
  actor: Actor;
  newJob: () => void;
}) {
  const [job, setJob] = useState<string | null>(linkedJob);
  function openJob(id: string) {
    const url = new URL(window.location.href);
    url.searchParams.set("view", "jobs"); url.searchParams.set("job", id);
    window.history.pushState(null, "", url); setJob(id);
  }
  function back() {
    const url = new URL(window.location.href);
    url.searchParams.delete("job");
    window.history.pushState(null, "", url); setJob(null);
  }
  if (!job) return <JobList actor={actor} openJob={openJob} newJob={newJob} />;
  return <section>
    <div className="section-heading">
      <div><span className="eyebrow">服务器事实</span><h2>评测详情</h2></div>
      <button onClick={back}>返回评测列表</button>
    </div>
    <JobsPanel owner={actor.role === "owner"} showWizard={false} />
  </section>;
}
