"use client";

import React, { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type User = { id: string; name: string; email: string; organizations: { id: string; name: string; slug: string; role: string }[] };
type Project = { id: string; name: string; platform: string; organization_id: string; created_at: string };
type Issue = { id: string; title: string; exception_type: string; message: string; severity: string; status: string; priority: string; event_count: number; affected_users: number; first_seen: string; last_seen: string };
type Dashboard = { project: { id: string; name: string; platform: string }; metrics: { events: number; unresolved_issues: number; new_issues: number; affected_users: number }; trend: { label: string; events: number }[]; recent_issues: Issue[]; top_issues: Issue[] };
type IssueDetail = Issue & { fingerprint: string; project: { id: string; name: string; platform: string }; events: { id: string; event_id: string; message: string; exception_type: string; stacktrace: string; environment: string; user_id?: string; url?: string; context: Record<string, unknown>; tags: Record<string, unknown>; breadcrumbs: { category?: string; message?: string; timestamp?: string; level?: string; data?: Record<string, unknown> }[]; created_at: string }[]; activity: { id: string; action: string; detail: string; created_at: string }[] };
type Toast = { message: string; error?: boolean } | null;

const API = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data as T;
}

function Icon({ name, size = 17 }: { name: string; size?: number }) {
  const common = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, className: "nav-icon", "aria-hidden": true as const };
  const paths: Record<string, React.ReactNode> = {
    pulse: <><path d="M3 12h4l3-8 4 16 3-8h4" /></>,
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    alert: <><path d="M10.3 3.9 2.7 17a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4m0 4h.01"/></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/></>,
    code: <><path d="m8 17-5-5 5-5m8 0 5 5-5 5m-2-12-4 14"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.6a8 8 0 0 1-1.7 1l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.7-1l-1.7.6-1.4-2.4L7.3 15a8 8 0 0 1 0-2l-1.4-1.1 1.4-2.4 1.7.6a8 8 0 0 1 1.7-1l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.7 1l1.7-.6 1.4 2.4-1.4 1.1a8 8 0 0 1-.1 2Z"/></>,
    search: <><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9m-8 12a2 2 0 0 0 4 0"/></>,
    plus: <><path d="M12 5v14m-7-7h14"/></>,
    chevron: <><path d="m8 10 4 4 4-4"/></>,
    arrow: <><path d="M5 12h14m-6-6 6 6-6 6"/></>,
    close: <><path d="m18 6-12 12M6 6l12 12"/></>,
    copy: <><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/></>,
    check: <><path d="m5 12 4 4L19 6"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    users: <><path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2m6-10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm10 10v-2a4 4 0 0 0-3-3.9m-1-11a4 4 0 0 1 0 7.8"/></>,
    trend: <><path d="m3 17 6-6 4 4 8-9m-6 0h6v6"/></>,
    menu: <><path d="M4 6h16M4 12h16M4 18h16"/></>,
    logout: <><path d="M10 17l5-5-5-5m5 5H3m10-9h5a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3h-5"/></>,
    external: <><path d="M14 3h7v7m0-7-9 9"/><path d="M19 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h6"/></>,
  };
  return <svg {...common}>{paths[name] || paths.pulse}</svg>;
}

function timeAgo(value?: string) {
  if (!value) return "—";
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (!Number.isFinite(seconds)) return "—";
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
function dateTime(value?: string) { return value ? new Date(value).toLocaleString() : "—"; }
function shortNum(value: number) { return new Intl.NumberFormat("en", { notation: value > 9999 ? "compact" : "standard", maximumFractionDigits: 1 }).format(value || 0); }
function severityClass(value: string) { return ["fatal", "error"].includes(value) ? "error" : value === "warning" ? "warning" : "info"; }

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [authMode, setAuthMode] = useState<"login" | "register">("register");
  const [authLoading, setAuthLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const [authError, setAuthError] = useState("");
  const [toast, setToast] = useState<Toast>(null);
  const [page, setPage] = useState("overview");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [windowRange, setWindowRange] = useState("24h");
  const [issues, setIssues] = useState<Issue[]>([]);
  const [issueTotal, setIssueTotal] = useState(0);
  const [issueStatus, setIssueStatus] = useState("unresolved");
  const [issueSeverity, setIssueSeverity] = useState("all");
  const [issueEnvironment, setIssueEnvironment] = useState("all");
  const [issueTime, setIssueTime] = useState("all");
  const [issueSort, setIssueSort] = useState("last_seen");
  const [issueOffset, setIssueOffset] = useState(0);
  const [issueQuery, setIssueQuery] = useState("");
  const [selectedIssue, setSelectedIssue] = useState<IssueDetail | null>(null);
  const [loadingData, setLoadingData] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [platform, setPlatform] = useState("react");
  const [creatingProject, setCreatingProject] = useState(false);
  const [newProjectCredential, setNewProjectCredential] = useState<{ public_key: string; dsn: string } | null>(null);
  const [credentialVisible, setCredentialVisible] = useState(false);

  const notify = useCallback((message: string, error = false) => {
    setToast({ message, error });
    window.setTimeout(() => setToast(null), 3200);
  }, []);

  const loadProjects = useCallback(async () => {
    const data = await api<{ items: Project[] }>("/api/v1/projects");
    setProjects(data.items);
    const saved = typeof window !== "undefined" ? localStorage.getItem("pw_project_id") : null;
    const nextId = data.items.some((p) => p.id === saved) ? saved! : (data.items[0]?.id || "");
    setProjectId(nextId);
    if (nextId) localStorage.setItem("pw_project_id", nextId);
  }, []);

  const loadDashboard = useCallback(async (id = projectId, range = windowRange) => {
    if (!id) return;
    const data = await api<Dashboard>(`/api/v1/dashboard?project_id=${encodeURIComponent(id)}&window=${range}`);
    setDashboard(data);
  }, [projectId, windowRange]);

  const loadIssues = useCallback(async (id = projectId) => {
    if (!id) return;
    const params = new URLSearchParams({ project_id: id, status: issueStatus, severity: issueSeverity, environment: issueEnvironment, limit: "25", sort: issueSort, offset: String(issueOffset) });
    if (issueTime !== "all") {
      const millis = issueTime === "24h" ? 24 * 60 * 60 * 1000 : issueTime === "7d" ? 7 * 24 * 60 * 60 * 1000 : 30 * 24 * 60 * 60 * 1000;
      params.set("since", new Date(Date.now() - millis).toISOString());
    }
    if (issueQuery.trim()) params.set("q", issueQuery.trim());
    const data = await api<{ items: Issue[]; total: number }>(`/api/v1/issues?${params.toString()}`);
    setIssues(data.items); setIssueTotal(data.total);
  }, [projectId, issueStatus, issueSeverity, issueEnvironment, issueTime, issueSort, issueOffset, issueQuery]);

  const loadIssueDetail = useCallback(async (id: string) => {
    try { setSelectedIssue(await api<IssueDetail>(`/api/v1/issues/${id}`)); }
    catch (error) { notify(error instanceof Error ? error.message : "Could not load issue", true); }
  }, [notify]);

  useEffect(() => {
    api<{ user: User }>("/api/v1/me").then(async (data) => {
      setUser(data.user);
      await loadProjects();
    }).catch(() => setUser(null)).finally(() => setChecking(false));
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => undefined);
  }, [loadProjects]);

  useEffect(() => {
    if (!user || !projectId) { setDashboard(null); return; }
    setLoadingData(true);
    loadDashboard(projectId, windowRange).catch((error) => notify(error instanceof Error ? error.message : "Dashboard failed to load", true)).finally(() => setLoadingData(false));
  }, [user, projectId, windowRange, loadDashboard, notify]);

  useEffect(() => {
    if (!user || !projectId || page !== "issues") return;
    const timer = window.setTimeout(() => loadIssues().catch((error) => notify(error instanceof Error ? error.message : "Issues failed to load", true)), 180);
    return () => window.clearTimeout(timer);
  }, [user, projectId, page, issueStatus, issueSeverity, issueEnvironment, issueTime, issueSort, issueOffset, issueQuery, loadIssues, notify]);

  useEffect(() => {
    if (!user || !projectId || !dashboard) return;
    const source = new EventSource(`${API}/api/v1/stream?project_id=${encodeURIComponent(projectId)}`, { withCredentials: true });
    source.addEventListener("refresh", () => {
      loadDashboard(projectId, windowRange).catch(() => undefined);
      if (page === "issues") loadIssues(projectId).catch(() => undefined);
    });
    return () => source.close();
  }, [user, projectId, dashboard?.project.id, windowRange, page, loadDashboard, loadIssues]);

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setAuthError(""); setAuthLoading(true);
    const form = new FormData(event.currentTarget);
    const body: Record<string, string> = { email: String(form.get("email") || ""), password: String(form.get("password") || "") };
    if (authMode === "register") { body.name = String(form.get("name") || ""); body.organization_name = String(form.get("organization") || "My workspace"); }
    try {
      const data = await api<{ user: User }>(`/api/v1/auth/${authMode}`, { method: "POST", body: JSON.stringify(body) });
      setUser(data.user); await loadProjects();
      notify(authMode === "register" ? "Workspace created" : "Signed in");
    } catch (error) { setAuthError(error instanceof Error ? error.message : "Authentication failed"); }
    finally { setAuthLoading(false); }
  }

  async function signOut() {
    try { await api("/api/v1/auth/logout", { method: "POST" }); } catch { /* local UI can still sign out */ }
    setUser(null); setProjects([]); setProjectId(""); setDashboard(null); setSelectedIssue(null); setPage("overview");
  }

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setCreatingProject(true);
    try {
      const data = await api<{ project: Project; public_key: string; dsn: string }>("/api/v1/projects", {
        method: "POST", body: JSON.stringify({ name: projectName, platform, organization_id: user?.organizations[0]?.id }),
      });
      setProjects((old) => [...old, data.project]); setProjectId(data.project.id); localStorage.setItem("pw_project_id", data.project.id);
      setNewProjectCredential({ public_key: data.public_key, dsn: data.dsn }); setCredentialVisible(true); setProjectName(""); setPage("setup");
      notify("Project created. Copy its ingestion key now.");
    } catch (error) { notify(error instanceof Error ? error.message : "Project creation failed", true); }
    finally { setCreatingProject(false); }
  }

  async function copyText(text: string) {
    try { await navigator.clipboard.writeText(text); notify("Copied to clipboard"); }
    catch { notify("Clipboard access was blocked by the browser", true); }
  }

  async function sendTestEvent() {
    if (!newProjectCredential) { notify("Rotate the project key to obtain a new DSN", true); return; }
    try {
      const response = await fetch(newProjectCredential.dsn, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event_id: crypto.randomUUID(), message: "PulseWatch test event — connection verified", exception_type: "PulseWatchTestError", stacktrace: "Error: PulseWatch test event\n    at testConnection (pulsewatch://onboarding)", severity: "warning", environment: "development", context: { source: "onboarding" }, tags: { test: "true" } }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || `Test event failed (${response.status})`);
      notify("Test event accepted"); await loadDashboard(projectId).catch(() => undefined);
    } catch (error) { notify(error instanceof Error ? error.message : "Could not send test event", true); }
  }

  async function issueAction(action: string, value?: string) {
    if (!selectedIssue) return;
    try {
      await api(`/api/v1/issues/${selectedIssue.id}/actions`, { method: "POST", body: JSON.stringify({ action, value }) });
      await loadIssueDetail(selectedIssue.id);
      await loadDashboard(projectId).catch(() => undefined);
      if (page === "issues") await loadIssues(projectId).catch(() => undefined);
      notify(action === "resolve" ? "Issue resolved" : action === "reopen" ? "Issue reopened" : action === "ignore" ? "Issue ignored" : "Issue updated");
    } catch (error) { notify(error instanceof Error ? error.message : "Action failed", true); }
  }

  async function rotateKey() {
    if (!projectId) return;
    try {
      const data = await api<{ public_key: string; dsn: string }>(`/api/v1/projects/${projectId}/rotate-key`, { method: "POST" });
      setNewProjectCredential(data); setCredentialVisible(true); setPage("setup"); notify("Ingestion key rotated. Update your SDK configuration.");
    } catch (error) { notify(error instanceof Error ? error.message : "Key rotation failed", true); }
  }

  const currentProject = projects.find((project) => project.id === projectId);
  const greetingName = user?.name?.split(" ")[0] || "there";

  if (checking) return <div className="auth-page"><div className="auth-form-wrap"><div className="brand"><div className="brand-mark"><Icon name="pulse" size={19}/></div><div><div className="brand-name">PulseWatch</div><div className="brand-sub">Application observability</div></div></div><p className="muted" style={{ fontSize: 12 }}>Loading your workspace…</p></div></div>;

  if (!user) return <main className="auth-page">
    <section className="auth-visual">
      <div className="brand"><div className="brand-mark"><Icon name="pulse" size={19}/></div><div><div className="brand-name">PulseWatch</div><div className="brand-sub">Application observability</div></div></div>
      <div className="auth-copy"><div className="eyebrow">Visibility when it matters</div><h1>Know what broke.<br/><span>Fix what matters.</span></h1><p>Application errors, grouped issues and actionable context in one focused workspace. Find the root of a failure before your users have to tell you.</p></div>
      <div className="auth-visual-foot">ENGINEERED FOR DEVELOPERS · BUILT FOR CLARITY</div>
    </section>
    <section className="auth-form-wrap"><form className="auth-form" onSubmit={submitAuth}>
      <div className="eyebrow">{authMode === "register" ? "Create your workspace" : "Welcome back"}</div>
      <h2>{authMode === "register" ? "Start monitoring" : "Sign in to PulseWatch"}</h2>
      <p className="auth-subtitle">{authMode === "register" ? "Set up your workspace and connect the first application." : "Continue to your application observability workspace."}</p>
      {authError && <div className="error-banner">{authError}</div>}
      {authMode === "register" && <><div className="field"><label>Your name</label><input name="name" placeholder="Alex Morgan" minLength={2} required autoComplete="name"/></div><div className="field"><label>Workspace name</label><input name="organization" placeholder="Acme Engineering" minLength={2} required/></div></>}
      <div className="field"><label>Work email</label><input name="email" type="email" placeholder="you@company.com" required autoComplete="email"/></div>
      <div className="field"><label>Password</label><input name="password" type="password" placeholder="At least 8 characters" minLength={authMode === "register" ? 8 : 1} required autoComplete={authMode === "register" ? "new-password" : "current-password"}/></div>
      <button className="primary-button full-button" type="submit" disabled={authLoading}>{authLoading ? "Please wait…" : authMode === "register" ? "Create workspace" : "Sign in"} <Icon name="arrow" size={14}/></button>
      <div className="auth-switch">{authMode === "register" ? "Already have an account?" : "New to PulseWatch?"}<button className="link-button" type="button" onClick={() => { setAuthMode(authMode === "register" ? "login" : "register"); setAuthError(""); }}>{authMode === "register" ? "Sign in" : "Create an account"}</button></div>
    </form></section>
  </main>;

  const navItems = [{ id: "overview", label: "Overview", icon: "grid" }, { id: "issues", label: "Issues", icon: "alert" }, { id: "setup", label: "SDK Setup", icon: "code" }, { id: "settings", label: "Project settings", icon: "settings" }];

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? "open" : ""}`}>
      <div className="brand"><div className="brand-mark"><Icon name="pulse" size={19}/></div><div><div className="brand-name">PulseWatch</div><div className="brand-sub">Application observability</div></div></div>
      <div className="workspace-label">Workspace</div>
      <div className="nav-group">
        {navItems.map((item) => <button key={item.id} className={`nav-btn ${page === item.id ? "active" : ""}`} onClick={() => { setPage(item.id); setMobileNav(false); }}><Icon name={item.icon} size={16}/>{item.label}{item.id === "issues" && dashboard?.metrics.unresolved_issues ? <span style={{ marginLeft: "auto", fontSize: 9, color: "#9d8adf" }}>{shortNum(dashboard.metrics.unresolved_issues)}</span> : null}</button>)}
      </div>
      <div className="nav-spacer"/>
      <button className="nav-btn" onClick={() => { setPage("setup"); setMobileNav(false); }}><Icon name="plus" size={16}/>Connect an application</button>
      <div className="sidebar-bottom"><div className="user-row"><div className="avatar">{user.name.slice(0, 1).toUpperCase()}</div><div style={{ minWidth: 0, flex: 1 }}><div className="user-name">{user.name}</div><div className="user-email">{user.email}</div></div><button className="top-icon" title="Sign out" onClick={signOut}><Icon name="logout" size={14}/></button></div></div>
    </aside>
    <main className="main-area">
      <header className="topbar">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}><button className="top-icon mobile-menu" onClick={() => setMobileNav(!mobileNav)} aria-label="Toggle navigation"><Icon name="menu" size={17}/></button><div className="crumb">Workspace <span style={{ color: "#444c5b", margin: "0 7px" }}>/</span> <strong>{navItems.find((item) => item.id === page)?.label || "Overview"}</strong></div></div>
        <div className="topbar-right">
          {projects.length > 0 && <select className="select-dark" value={projectId} onChange={(event) => { setProjectId(event.target.value); localStorage.setItem("pw_project_id", event.target.value); setPage("overview"); }} aria-label="Select project">{projects.map((project) => <option value={project.id} key={project.id}>{project.name}</option>)}</select>}
          
        </div>
      </header>

      {!projects.length ? <div className="onboarding-wrap"><div className="eyebrow">Get started · 01 / 03</div><div className="onboarding-card"><div className="step-row"><div className="step-dot done"/><div className="step-dot"/><div className="step-dot"/></div><div className="brand-mark" style={{ marginBottom: 18 }}><Icon name="layers" size={18}/></div><h1 className="page-title">Create your first project</h1><p className="page-desc" style={{ marginBottom: 24 }}>Projects represent the applications you monitor. Start with one application, then connect the PulseWatch SDK.</p><form onSubmit={createProject}><div className="field"><label>Project name</label><input value={projectName} onChange={(e) => setProjectName(e.target.value)} placeholder="e.g. Customer Dashboard" minLength={2} required/></div><div className="field"><label>Application platform</label><select value={platform} onChange={(e) => setPlatform(e.target.value)}><option value="react">React</option><option value="nextjs">Next.js</option><option value="javascript">Browser JavaScript</option><option value="python">Python</option><option value="fastapi">FastAPI</option></select></div><button className="primary-button" disabled={creatingProject}>{creatingProject ? "Creating…" : "Create project"} <Icon name="arrow" size={14}/></button></form></div></div> : <div className="content">
        {page === "overview" && <>
          <div className="page-heading"><div><div className="eyebrow">System overview</div><h1 className="page-title">Good to see you, {greetingName}.</h1><p className="page-desc">Here’s what is happening in <strong style={{ color: "#d6d9e3" }}>{currentProject?.name || "your project"}</strong>.</p></div><div className="actions"><select className="filter-select" value={windowRange} onChange={(e) => setWindowRange(e.target.value)}><option value="24h">Last 24 hours</option><option value="7d">Last 7 days</option><option value="30d">Last 30 days</option></select><button className="secondary-button" onClick={() => { loadDashboard().catch((e) => notify(e.message, true)); }}><Icon name="clock" size={13}/> Refresh</button></div></div>
          {loadingData && !dashboard ? <div className="panel empty-state">Loading project metrics…</div> : dashboard && <>
            <div className="grid-metrics">
              <Metric label="Events received" value={shortNum(dashboard.metrics.events)} note={`In the last ${windowRange === "24h" ? "24 hours" : windowRange === "7d" ? "7 days" : "30 days"}`} icon="pulse"/>
              <Metric label="Unresolved issues" value={shortNum(dashboard.metrics.unresolved_issues)} note="Across this project" icon="alert"/>
              <Metric label="New issues" value={shortNum(dashboard.metrics.new_issues)} note="First seen in selected period" icon="trend"/>
              <Metric label="Affected users" value={shortNum(dashboard.metrics.affected_users)} note="Distinct user identifiers" icon="users"/>
            </div>
            <div className="dashboard-grid">
              <section className="panel"><div className="panel-head"><div><div className="panel-title">Event volume</div><div className="panel-sub">Incoming error and message events</div></div><div className="status-note"><span className="legend-dot"/>Events</div></div>
                {dashboard.trend.every((point) => point.events === 0) ? <div className="empty-state"><div className="empty-icon"><Icon name="trend" size={18}/></div><div className="empty-title">No events in this period</div><div className="empty-desc">Connect an SDK or send a test event to start building your event history.</div><button className="secondary-button" onClick={() => setPage("setup")}>Set up an SDK</button></div> : <div className="chart-wrap">{dashboard.trend.map((point, index) => <div className="chart-column" key={`${point.label}-${index}`} title={`${point.label}: ${point.events} events`}><div className="chart-bar" style={{ height: `${Math.max(2, point.events / Math.max(1, ...dashboard.trend.map((p) => p.events)) * 100)}%` }}/></div>)}<div className="chart-ticks"><span>{dashboard.trend[0]?.label}</span><span>{dashboard.trend[Math.floor(dashboard.trend.length / 2)]?.label}</span><span>{dashboard.trend[dashboard.trend.length - 1]?.label}</span></div></div>}
              </section>
              <section className="panel"><div className="panel-head"><div><div className="panel-title">Most frequent issues</div><div className="panel-sub">Ranked by occurrence count</div></div><button className="ghost-button" onClick={() => setPage("issues")}>View all <Icon name="arrow" size={12}/></button></div>
                {dashboard.top_issues.length ? <div className="issue-mini-list">{dashboard.top_issues.map((issue) => <button className="issue-mini" key={issue.id} style={{ width: "100%", background: "none", border: 0, textAlign: "left", color: "inherit" }} onClick={() => loadIssueDetail(issue.id)}><span className={`sev-dot ${severityClass(issue.severity)}`}/><div className="issue-mini-main"><div className="issue-mini-title">{issue.title}</div><div className="issue-mini-meta">{timeAgo(issue.last_seen)} · {issue.status}</div></div><span className="issue-count">{issue.event_count}×</span></button>)}</div> : <div className="empty-state" style={{ padding: "24px 8px" }}><div className="empty-title">No issues yet</div><div className="empty-desc">Your first captured error will appear here.</div></div>}
              </section>
            </div>
            <section className="panel"><div className="panel-head"><div><div className="panel-title">Recently active issues</div><div className="panel-sub">Latest issues by last occurrence</div></div><button className="ghost-button" onClick={() => setPage("issues")}>Open issue feed <Icon name="arrow" size={12}/></button></div>
              {dashboard.recent_issues.length ? <div className="issue-mini-list">{dashboard.recent_issues.map((issue) => <button className="issue-mini" key={issue.id} style={{ width: "100%", background: "none", border: 0, textAlign: "left", color: "inherit" }} onClick={() => loadIssueDetail(issue.id)}><span className={`sev-dot ${severityClass(issue.severity)}`}/><div className="issue-mini-main"><div className="issue-mini-title">{issue.title}</div><div className="issue-mini-meta">{issue.exception_type} · Last seen {timeAgo(issue.last_seen)}</div></div><span className={`status-pill ${issue.status}`}>{issue.status}</span><span className="issue-count">{issue.event_count} events</span></button>)}</div> : <div className="empty-state"><div className="empty-title">Your issue feed is clear</div><div className="empty-desc">No issues have been recorded for this project yet.</div><button className="secondary-button" onClick={() => setPage("setup")}>Connect your application</button></div>}
            </section>
          </>}
        </>}

        {page === "issues" && <>
          <div className="page-heading"><div><div className="eyebrow">Error monitoring</div><h1 className="page-title">Issues</h1><p className="page-desc">Investigate grouped errors and track their resolution.</p></div><div className="actions"><span className="status-note">{issueTotal} issues</span></div></div>
          <section className="panel table-panel"><div className="table-toolbar"><div className="toolbar-left"><input className="search-input" placeholder="Search issues…" value={issueQuery} onChange={(e) => { setIssueQuery(e.target.value); setIssueOffset(0); }}/><select className="filter-select" value={issueStatus} onChange={(e) => { setIssueStatus(e.target.value); setIssueOffset(0); }}><option value="unresolved">Unresolved</option><option value="resolved">Resolved</option><option value="ignored">Ignored</option><option value="all">All statuses</option></select><select className="filter-select" value={issueSeverity} onChange={(e) => { setIssueSeverity(e.target.value); setIssueOffset(0); }}><option value="all">All levels</option><option value="fatal">Fatal</option><option value="error">Error</option><option value="warning">Warning</option><option value="info">Info</option></select><select className="filter-select" value={issueEnvironment} onChange={(e) => { setIssueEnvironment(e.target.value); setIssueOffset(0); }}><option value="all">All environments</option><option value="production">Production</option><option value="development">Development</option><option value="staging">Staging</option></select><select className="filter-select" value={issueTime} onChange={(e) => { setIssueTime(e.target.value); setIssueOffset(0); }}><option value="all">Any time</option><option value="24h">Last 24 hours</option><option value="7d">Last 7 days</option><option value="30d">Last 30 days</option></select><select className="filter-select" value={issueSort} onChange={(e) => setIssueSort(e.target.value)}><option value="last_seen">Recently active</option><option value="frequency">Most events</option></select></div><div className="toolbar-right"><button className="secondary-button" onClick={() => loadIssues().catch((e) => notify(e.message, true))}>Refresh</button></div></div>
            {issues.length ? <><div className="table-scroll"><table className="issue-table"><thead><tr><th>Issue</th><th>Level</th><th>Status</th><th>Events</th><th>Users</th><th>Last seen</th></tr></thead><tbody>{issues.map((issue) => <tr key={issue.id} onClick={() => loadIssueDetail(issue.id)}><td><div className="issue-main"><span className={`sev-dot ${severityClass(issue.severity)}`}/><div><div className="issue-main-title">{issue.title}</div><div className="issue-main-sub mono">{issue.id.slice(0, 8)} · {issue.exception_type}</div></div></div></td><td><span className={`severity-pill ${severityClass(issue.severity)}`}>{issue.severity}</span></td><td><span className={`status-pill ${issue.status}`}>{issue.status}</span></td><td className="mono">{shortNum(issue.event_count)}</td><td className="mono">{shortNum(issue.affected_users)}</td><td>{timeAgo(issue.last_seen)}</td></tr>)}</tbody></table></div><div className="table-toolbar"><span className="status-note">Showing {issueTotal === 0 ? 0 : issueOffset + 1}–{Math.min(issueOffset + issues.length, issueTotal)} of {issueTotal}</span><div className="toolbar-right"><button className="secondary-button" disabled={issueOffset === 0} onClick={() => setIssueOffset(Math.max(0, issueOffset - 25))}>Previous</button><button className="secondary-button" disabled={issueOffset + 25 >= issueTotal} onClick={() => setIssueOffset(issueOffset + 25)}>Next</button></div></div></> : <div className="empty-state"><div className="empty-icon"><Icon name="check" size={18}/></div><div className="empty-title">No matching issues</div><div className="empty-desc">Try changing the status or severity filters. New events will be grouped into issues automatically.</div><button className="secondary-button" onClick={() => { setIssueStatus("all"); setIssueSeverity("all"); setIssueEnvironment("all"); setIssueTime("all"); setIssueQuery(""); setIssueOffset(0); }}>Clear filters</button></div>}
          </section>
        </>}

        {page === "setup" && <>
          <div className="page-heading"><div><div className="eyebrow">Instrumentation</div><h1 className="page-title">Connect your application</h1><p className="page-desc">Install the PulseWatch SDK to start collecting real application errors.</p></div></div>
          <div className="dashboard-grid"><section className="panel"><div className="panel-head"><div><div className="panel-title">JavaScript / React / Next.js</div><div className="panel-sub">Browser-side instrumentation</div></div><span className="status-pill">Browser SDK</span></div>
            <div className="section-label">1. Install the local SDK</div><div className="code-block">npm install /path/to/PulseWatch-MVP/sdk/javascript</div>
            <div className="section-label">2. Initialize PulseWatch</div><div className="code-block">{`import { init } from "@pulsewatch/browser-sdk";\n\ninit({\n  dsn: process.env.NEXT_PUBLIC_PULSEWATCH_DSN,\n  environment: process.env.NODE_ENV,\n});`}</div>
            <div className="section-label">3. Capture an exception</div><div className="code-block">{`import { captureException } from "@pulsewatch/browser-sdk";\n\ntry {\n  throw new Error("Checkout failed");\n} catch (error) {\n  captureException(error, { feature: "checkout" });\n}`}</div>
          </section><section className="panel"><div className="panel-head"><div><div className="panel-title">Python / FastAPI</div><div className="panel-sub">Server-side instrumentation</div></div><span className="status-pill">Python SDK</span></div>
            <div className="section-label">1. Install from the project source</div><div className="code-block">pip install -e ./sdk/python</div>
            <div className="section-label">2. Initialize the SDK</div><div className="code-block">{`from pulsewatch_sdk import init, capture_exception\n\ninit("YOUR_PROJECT_DSN", environment="production")\n\ntry:\n    risky_operation()\nexcept Exception as exc:\n    capture_exception(exc, {"route": "/checkout"})`}</div>
            <div className="section-label">3. FastAPI example</div><div className="code-block">sdk/python/examples/fastapi_example.py</div>
          </section></div>
          <section className="panel" style={{ marginTop: 14 }}><div className="panel-head"><div><div className="panel-title">Project ingestion credential</div><div className="panel-sub">Write-only key for submitting events. It cannot access private project APIs.</div></div><button className="secondary-button" onClick={rotateKey}>Rotate key</button></div>
            {newProjectCredential && credentialVisible ? <><div className="notice" style={{ marginBottom: 13 }}>Copy this key now. The full value is only returned during project creation or key rotation. Rotating invalidates previously issued keys.</div><div className="code-head"><span>Project DSN</span><button className="ghost-button" onClick={() => copyText(newProjectCredential.dsn)}>Copy DSN <Icon name="copy" size={12}/></button></div><div className="code-block">{newProjectCredential.dsn}</div><div className="code-head" style={{ marginTop: 14 }}><span>Public ingestion key</span><button className="ghost-button" onClick={() => copyText(newProjectCredential.public_key)}>Copy key <Icon name="copy" size={12}/></button></div><div className="code-block">{newProjectCredential.public_key}</div><button className="primary-button" style={{ marginTop: 14 }} onClick={sendTestEvent}>Send a test event <Icon name="arrow" size={13}/></button></> : <div className="empty-state" style={{ padding: "20px 10px" }}><div className="empty-title">Credential is stored securely</div><div className="empty-desc">The full key is never displayed again after you leave the creation flow. Rotate the key to issue a new one.</div><button className="secondary-button" onClick={rotateKey}>Generate new ingestion key</button></div>}
          </section>
        </>}

        {page === "settings" && <>
          <div className="page-heading"><div><div className="eyebrow">Configuration</div><h1 className="page-title">Project settings</h1><p className="page-desc">Manage project identity and ingestion credentials.</p></div></div>
          <section className="panel"><div className="panel-head"><div><div className="panel-title">General</div><div className="panel-sub">Project information</div></div></div>
            <div className="setting-row"><div><div className="setting-title">Project name</div><div className="setting-desc">The project shown in your workspace.</div></div><strong style={{ fontSize: 12 }}>{currentProject?.name || "—"}</strong></div>
            <div className="setting-row"><div><div className="setting-title">Platform</div><div className="setting-desc">Primary application runtime.</div></div><span className="status-pill">{currentProject?.platform || "—"}</span></div>
            <div className="setting-row"><div><div className="setting-title">Project ID</div><div className="setting-desc mono">{projectId}</div></div><button className="ghost-button" onClick={() => copyText(projectId)}>Copy ID <Icon name="copy" size={12}/></button></div>
            <div className="setting-row"><div><div className="setting-title">Ingestion key</div><div className="setting-desc">Rotate immediately if you believe a key has been exposed.</div></div><button className="danger-button" onClick={rotateKey}>Rotate key</button></div>
          </section>
          <section className="panel" style={{ marginTop: 14 }}><div className="panel-head"><div><div className="panel-title">Workspace account</div><div className="panel-sub">Signed-in user and current organization</div></div></div><div className="setting-row"><div><div className="setting-title">{user.name}</div><div className="setting-desc">{user.email}</div></div><button className="secondary-button" onClick={signOut}>Sign out</button></div></section>
        </>}
      </div>}
    </main>
    {selectedIssue && <div className="detail-overlay" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedIssue(null); }}><section className="detail-drawer"><div className="drawer-head"><div><div className="eyebrow" style={{ marginBottom: 3 }}>Issue investigation</div><div className="mono" style={{ color: "#858fa3", fontSize: 9 }}>{selectedIssue.id}</div></div><button className="top-icon" onClick={() => setSelectedIssue(null)} aria-label="Close issue"><Icon name="close" size={16}/></button></div><div className="drawer-body">
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}><span className={`severity-pill ${severityClass(selectedIssue.severity)}`}>{selectedIssue.severity}</span><span className={`status-pill ${selectedIssue.status}`}>{selectedIssue.status}</span><span className="status-note">{selectedIssue.exception_type}</span></div>
        <h2 className="detail-title">{selectedIssue.title}</h2><div className="detail-actions">{selectedIssue.status !== "resolved" ? <button className="primary-button" onClick={() => issueAction("resolve")}> <Icon name="check" size={13}/> Resolve</button> : <button className="secondary-button" onClick={() => issueAction("reopen")}>Reopen issue</button>}<button className="secondary-button" onClick={() => issueAction("ignore")}>Ignore</button><button className="secondary-button" onClick={() => issueAction("assign_to_me")}>Assign to me</button><select className="filter-select" value={selectedIssue.priority} onChange={(e) => issueAction("priority", e.target.value)} aria-label="Issue priority"><option value="low">Low priority</option><option value="normal">Normal priority</option><option value="high">High priority</option><option value="urgent">Urgent priority</option></select></div>
        <div className="detail-meta-grid"><div className="detail-meta"><span>Events</span><strong>{shortNum(selectedIssue.event_count)}</strong></div><div className="detail-meta"><span>Affected users</span><strong>{shortNum(selectedIssue.affected_users)}</strong></div><div className="detail-meta"><span>First seen</span><strong>{timeAgo(selectedIssue.first_seen)}</strong></div><div className="detail-meta"><span>Last seen</span><strong>{timeAgo(selectedIssue.last_seen)}</strong></div></div>
        <div className="section-label">Stack trace · latest event</div>{selectedIssue.events[0]?.stacktrace ? <pre className="stack-block">{selectedIssue.events[0].stacktrace}</pre> : <div className="stack-block">No stack trace was supplied by the SDK for this event.</div>}
        <div className="section-label">Latest event context</div>{selectedIssue.events[0] ? <div className="event-context"><div className="context-item"><small>Environment</small><strong>{selectedIssue.events[0].environment}</strong></div><div className="context-item"><small>URL</small><strong>{selectedIssue.events[0].url || "Not provided"}</strong></div><div className="context-item"><small>User ID</small><strong>{selectedIssue.events[0].user_id || "Anonymous"}</strong></div><div className="context-item"><small>Event ID</small><strong className="mono">{selectedIssue.events[0].event_id}</strong></div>{Object.entries(selectedIssue.events[0].tags || {}).map(([key, value]) => <div className="context-item" key={`tag-${key}`}><small>Tag · {key}</small><strong>{String(value)}</strong></div>)}{Object.entries(selectedIssue.events[0].context || {}).map(([key, value]) => <div className="context-item" key={`context-${key}`}><small>Context · {key}</small><strong>{typeof value === "object" ? JSON.stringify(value) : String(value)}</strong></div>)}</div> : null}
        <div className="section-label">Breadcrumbs · latest event</div>{selectedIssue.events[0]?.breadcrumbs?.length ? selectedIssue.events[0].breadcrumbs.map((crumb, index) => <div className="event-row" key={`${crumb.timestamp || "crumb"}-${index}`}><div><strong style={{ color: "#cbd2e0" }}>{crumb.message || crumb.category || "Activity"}</strong><div className="muted mono" style={{ marginTop: 4 }}>{crumb.category || "event"}{crumb.data && Object.keys(crumb.data).length ? ` · ${JSON.stringify(crumb.data)}` : ""}</div></div><span className="muted" style={{ whiteSpace: "nowrap" }}>{crumb.timestamp ? timeAgo(crumb.timestamp) : "—"}</span></div>) : <div className="status-note">No breadcrumbs were supplied for this event.</div>}
        <div className="section-label">Event history · most recent 50</div>{selectedIssue.events.length ? selectedIssue.events.map((event) => <div className="event-row" key={event.id}><div><strong style={{ color: "#d8deea" }}>{event.message}</strong><div className="muted mono" style={{ marginTop: 4 }}>{event.environment} · {event.event_id.slice(0, 18)}</div></div><span className="muted" style={{ whiteSpace: "nowrap" }}>{timeAgo(event.created_at)}</span></div>) : <div className="status-note">No event payloads available.</div>}
        <div className="section-label">Activity</div>{selectedIssue.activity.length ? selectedIssue.activity.map((activity) => <div className="event-row" key={activity.id}><div><strong style={{ color: "#cbd2e0", textTransform: "capitalize" }}>{activity.action.replaceAll("_", " ")}</strong><div className="muted" style={{ marginTop: 4 }}>{activity.detail}</div></div><span className="muted" style={{ whiteSpace: "nowrap" }}>{timeAgo(activity.created_at)}</span></div>) : <div className="status-note">No activity recorded.</div>}
      </div></section></div>}
    {toast && <div role="status" className={`toast ${toast.error ? "error" : ""}`}>{toast.message}</div>}
  </div>;
}

function Metric({ label, value, note, icon }: { label: string; value: string; note: string; icon: string }) {
  return <div className="metric-card"><div className="metric-label"><span>{label}</span><span className="metric-icon"><Icon name={icon} size={15}/></span></div><div className="metric-value">{value}</div><div className="metric-note">{note}</div></div>;
}
