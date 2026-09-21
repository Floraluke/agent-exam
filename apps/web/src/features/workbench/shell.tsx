"use client";

import { useEffect, useState } from "react";
import type { Actor } from "../../lib/contracts";
import AgentsPanel from "../catalog/agents";
import TasksPanel from "../catalog/tasks";
import MembersPanel from "../identity/members";
import JobWorkspace from "../jobs/listing/workspace";
import ComparisonWorkspace from "../jobs/reporting/comparison";
import JobsPanel from "../jobs/submit";
import LeaderboardView from "../leaderboard/view";
import Dashboard from "./dashboard";

type View = "home" | "jobs" | "new" | "reports" | "tasks" | "agents" | "leaderboard" | "members";

const views = new Set<View>([
  "home", "jobs", "new", "reports", "tasks", "agents", "leaderboard", "members",
]);

function viewFromUrl(): View {
  if (typeof window === "undefined") return "home";
  const candidate = new URL(window.location.href).searchParams.get("view") as View;
  return views.has(candidate) ? candidate : "home";
}

function normalizedViewFromUrl(): View {
  const next = viewFromUrl();
  if (typeof window === "undefined" || next === "jobs") return next;
  const url = new URL(window.location.href);
  if (url.searchParams.has("job")) {
    url.searchParams.delete("job");
    window.history.replaceState(null, "", url);
  }
  return next;
}

export default function WorkbenchShell({
  actor,
  busy,
  signOut,
}: {
  actor: Actor;
  busy: boolean;
  signOut: () => Promise<void>;
}) {
  const [view, setView] = useState<View>(normalizedViewFromUrl);
  const [routeVersion, setRouteVersion] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  // 对比选择只存在于本机会话，不进 URL、刷新即空；列表与矩阵共用这一份。
  const [comparisonIds, setComparisonIds] = useState<string[]>([]);

  useEffect(() => {
    const restore = () => {
      setView(normalizedViewFromUrl()); setRouteVersion((value) => value + 1);
    };
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);

  function navigate(next: View, job?: string) {
    const url = new URL(window.location.href);
    url.searchParams.set("view", next);
    if (job) url.searchParams.set("job", job);
    else url.searchParams.delete("job");
    window.history.pushState(null, "", url);
    setView(next); setMenuOpen(false); setRouteVersion((value) => value + 1);
  }

  function toggleComparison(id: string) {
    setComparisonIds((items) => items.includes(id)
      ? items.filter((item) => item !== id)
      : [...items, id]);
  }

  const owner = actor.role === "owner";
  const activeView = !owner && view === "members" ? "home" : view;
  return <div className="workbench-shell">
    <header className="workbench-mobilebar">
      <div className="workbench-brand"><span>Agent</span>Exam</div>
      <button aria-controls="primary-sidebar" aria-expanded={menuOpen}
        onClick={() => setMenuOpen(!menuOpen)}>
        {menuOpen ? "关闭主导航" : "打开主导航"}
      </button>
    </header>
    <aside id="primary-sidebar"
      className={`workbench-sidebar${menuOpen ? " is-open" : ""}`}>
      <div className="workbench-brand"><span>Agent</span>Exam</div>
      <nav aria-label="主导航">
        <button aria-current={activeView === "home" ? "page" : undefined}
          onClick={() => navigate("home")}>工作台</button>
        <button aria-current={activeView === "jobs" ? "page" : undefined}
          onClick={() => navigate("jobs")}>评测</button>
        <button aria-current={activeView === "new" ? "page" : undefined}
          onClick={() => navigate("new")}>新建评测</button>
        <button aria-current={activeView === "reports" ? "page" : undefined}
          onClick={() => navigate("reports")}>对比报告</button>
        <button aria-current={activeView === "tasks" ? "page" : undefined}
          onClick={() => navigate("tasks")}>任务目录</button>
        <button aria-current={activeView === "agents" ? "page" : undefined}
          onClick={() => navigate("agents")}>配置目录</button>
        <button aria-current={activeView === "leaderboard" ? "page" : undefined}
          onClick={() => navigate("leaderboard")}>排行榜</button>
        {owner && <button aria-current={activeView === "members" ? "page" : undefined}
          onClick={() => navigate("members")}>成员管理</button>}
      </nav>
      <div className="workbench-actor">
        <strong>已登录：{actor.username}</strong>
        <span>{owner ? "评测机所有者" : "协作者"}</span>
        <button disabled={busy} onClick={() => void signOut()}>退出登录</button>
      </div>
    </aside>
    <div className="workbench-content">
      {activeView === "home" && <Dashboard owner={owner}
        newJob={() => navigate("new")} allJobs={() => navigate("jobs")}
        openJob={(id) => navigate("jobs", id)} />}
      {activeView === "new" && <section>
        <span className="eyebrow">三步提交</span>
        <h2>新建评测</h2>
        <JobsPanel owner={owner} onCancel={() => navigate("jobs")}
          onCreated={(job) => navigate("jobs", job.job_id)} />
      </section>}
      {activeView === "jobs" && <JobWorkspace key={routeVersion} actor={actor}
        newJob={() => navigate("new")} selected={comparisonIds}
        toggle={toggleComparison} compare={() => navigate("reports")} />}
      {activeView === "reports" && <ComparisonWorkspace ids={comparisonIds}
        toggle={toggleComparison} clearAll={() => setComparisonIds([])}
        openJob={(id) => navigate("jobs", id)} />}
      {activeView === "tasks" && <TasksPanel owner={owner} />}
      {activeView === "agents" && <AgentsPanel owner={owner} />}
      {activeView === "leaderboard" && <LeaderboardView />}
      {activeView === "members" && owner && <MembersPanel />}
    </div>
  </div>;
}
