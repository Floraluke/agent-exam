import SessionPanel from "../features/identity/session";

export default function Home() {
  return <main>
    <header>
      <span className="eyebrow">受邀团队 · 本机评测</span>
      <h1>AgentExam</h1>
      <p className="muted">从可信身份开始，让每次评测有明确的执行归属。</p>
    </header>
    <SessionPanel />
  </main>;
}
