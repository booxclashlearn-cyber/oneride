import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRight, Bus, ChevronRight, FlaskConical, LayoutDashboard, LogOut, MapPin, Radio, RefreshCw, ShieldCheck, WifiOff } from "lucide-react";
import { api, ApiError, hasToken, setToken } from "./lib/api";
import { restoreSignIn, signIn, signOut } from "./lib/auth";
import { snapshotLive } from "./lib/demand";
import DemandCards from "./components/DemandCards";
import Simulator from "./components/Simulator";
import type { Access, Config, Demand, Profile } from "./types";

function Login({ config, done }: { config: Config; done: () => Promise<void> }) {
  const [email, setEmail] = useState(""), [password, setPassword] = useState(""), [busy, setBusy] = useState(false), [error, setError] = useState("");
  async function login(profile?: string) {
    setBusy(true); setError("");
    try {
      if (profile) { const result = await api<{token: string}>("/dev/login", { profile }); setToken(result.token); }
      else await signIn(email, password);
      await done();
    } catch (e) { setError(e instanceof ApiError ? e.message : "Could not sign in. Check your account and connection."); }
    finally { setBusy(false); }
  }
  return <div className="login-layout"><section className="login-story"><Brand/><span className="eyebrow">A CLEARER ROAD AHEAD</span><h1>Know where<br/>people are<br/><em>waiting.</em></h1><p>Your passengers send a message.<br/>You see the demand ahead.</p><div className="login-route"><span/><div>One route. A connected community.</div><span/></div></section><section className="login-form"><span className="eyebrow">DRIVER CONTROL CENTRE</span><h2>Welcome back.</h2><p>Sign in to see passenger demand on your routes.</p>{config.development ? <><div className="development-banner"><FlaskConical size={19}/><div><strong>Local development</strong><span>Persistent local data. No paid services required.</span></div></div><button className="primary-button" disabled={busy} onClick={() => void login("driver")}>Open demo dashboard <ArrowRight size={18}/></button><button className="text-button" disabled={busy} onClick={() => void login("locked")}>Test an account without a subscription</button><button className="text-button" disabled={busy} onClick={() => void login("admin")}>Open local admin tools</button></> : <form onSubmit={e => {e.preventDefault(); void login();}}><label className="field">Email<input required type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)}/></label><label className="field">Password<input required type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)}/></label><button disabled={busy} className="primary-button">{busy ? "Signing in…" : "Sign in"}<ArrowRight size={18}/></button><p className="subtle">Accounts and route access are provisioned by your administrator.</p></form>}{error && <p className="error" role="alert">{error}</p>}<div className="privacy-note"><ShieldCheck size={18}/><span>Passenger contact details stay private. Drivers see demand totals only.</span></div></section></div>;
}

function Brand() { return <div className="brand"><span><Bus size={25}/></span><strong>KaKo<span>Ride</span></strong></div>; }

function Admin() {
  const [health, setHealth] = useState<{outbox: Record<string, number>; pendingJobs: number} | null>(null), [notice, setNotice] = useState("");
  const [uid, setUid] = useState("demo-locked"), [route, setRoute] = useState("woodlands-town"), [active, setActive] = useState(true);
  useEffect(() => { api<typeof health>("/api/admin/health").then(setHealth).catch(e => setNotice(e.message)); }, []);
  async function grant(e: React.FormEvent) { e.preventDefault(); try { await api("/api/admin/entitlements", {uid, routeId: route, days: 30, active}); setNotice("Route access saved. The driver must refresh their dashboard."); } catch (e) { setNotice(e instanceof Error ? e.message : "Could not save access."); } }
  return <section className="admin-panel"><div className="section-heading"><div><h2>Access & messaging health</h2><p>Manual route grants. No payment processing.</p></div></div><form className="admin-grant" onSubmit={grant}><label className="field">Firebase driver UID<input value={uid} onChange={e => setUid(e.target.value)} required/></label><label className="field">Route<select value={route} onChange={e => setRoute(e.target.value)}><option value="woodlands-town">Woodlands → Town Centre</option><option value="town-woodlands">Town Centre → Woodlands</option></select></label><label className="field">Access<select value={String(active)} onChange={e => setActive(e.target.value === "true")}><option value="true">Active for 30 days</option><option value="false">Revoke access</option></select></label><button className="primary-button">Save route access</button></form>{notice && <p role="status" className="info-banner">{notice}</p>}{health && <div className="health-grid">{Object.entries(health.outbox).map(([label, count]) => <div key={label}><strong>{count}</strong><span>{label}</span></div>)}<div><strong>{health.pendingJobs}</strong><span>pending reminders</span></div></div>}</section>;
}

export default function App() {
  const [config, setConfig] = useState<Config | null>(null), [access, setAccess] = useState<Access | null>(null);
  const [route, setRoute] = useState(""), [station, setStation] = useState("");
  const [data, setData] = useState<Demand | null>(null), [received, setReceived] = useState(0), [tick, setTick] = useState(0);
  const [error, setError] = useState(""), [initialError, setInitialError] = useState(""), [busy, setBusy] = useState(false), [showSimulator, setShowSimulator] = useState(false);
  const epoch = useRef(0), mounted = useRef(true);
  const loadAccess = useCallback(async () => {
    const result = await api<Access>("/api/driver/routes"); setAccess(result); setError("");
    const selected = result.routes.find(r => r.id === "woodlands-town") || result.routes[0];
    setRoute(selected?.id || ""); setStation(selected?.stopIds[0] || "");
  }, []);
  useEffect(() => {
    mounted.current = true;
    void (async () => { try { const cfg = await api<Config>("/api/config"); if (!mounted.current) return; setConfig(cfg); if (!cfg.development) await restoreSignIn(); if (hasToken()) try { await loadAccess(); } catch { setToken(""); } } catch { if (mounted.current) setInitialError("Could not reach the KaKoRide API. Start the backend and refresh this page."); } })();
    return () => { mounted.current = false; epoch.current++; };
  }, [loadAccess]);
  const refresh = useCallback(async () => {
    if (!route || !station || !access) return;
    const currentEpoch = epoch.current;
    setBusy(true);
    try { const fresh = await api<Demand>(`/api/driver/demand?routeId=${encodeURIComponent(route)}&currentStopId=${encodeURIComponent(station)}`); if (currentEpoch === epoch.current && mounted.current) { setData(fresh); setReceived(performance.now()); setError(""); } }
    catch (e) { if (currentEpoch === epoch.current && mounted.current) { setData(null); setError(e instanceof Error ? e.message : "Connection interrupted"); if (e instanceof ApiError && e.status === 401) {setToken(""); setAccess(null);} } }
    finally { if (currentEpoch === epoch.current && mounted.current) setBusy(false); }
  }, [route, station, access]);
  useEffect(() => { epoch.current++; setData(null); if (!access) return; void refresh(); let stopped = false; let timer: ReturnType<typeof setTimeout>; const loop = async () => { if (!document.hidden) await refresh(); if (!stopped) timer = setTimeout(loop, 3000); }; timer = setTimeout(loop, 3000); const visible = () => { if (!document.hidden) void refresh(); }; document.addEventListener("visibilitychange", visible); return () => {stopped = true; clearTimeout(timer); epoch.current++; document.removeEventListener("visibilitychange", visible);}; }, [refresh, access]);
  useEffect(() => { const timer = setInterval(() => setTick(performance.now()), 1000); return () => clearInterval(timer); }, []);
  async function logout() { if (config) await signOut(config.development); epoch.current++; setAccess(null); setData(null); }
  if (initialError) return <div className="startup"><Brand/><h1>Backend connection needed</h1><p role="alert">{initialError}</p><button className="primary-button" onClick={() => location.reload()}>Try again</button></div>;
  if (!config) return <div className="startup"><Brand/><p role="status">Connecting to KaKoRide…</p></div>;
  if (!access) return <Login config={config} done={loadAccess}/>;
  const selected = access.routes.find(r => r.id === route);
  const live = !!data && !error && snapshotLive(data, Math.max(0, tick - received));
  const currentIndex = selected?.stopIds.indexOf(station) ?? 0;
  const currentName = access.stops.find(s => s.id === station)?.name || "Select station";
  const profile: Profile = access.profile;
  return <div className="app-shell"><aside className="sidebar"><Brand/><span className="sidebar-label">WORKSPACE</span><button className="nav-item active"><LayoutDashboard size={18}/>Demand dashboard</button>{config.simulatorEnabled && <button className={`nav-item ${showSimulator ? "highlight" : ""}`} onClick={() => setShowSimulator(!showSimulator)}><FlaskConical size={18}/>Messaging simulator<span className="nav-dot"/></button>}<div className="sidebar-note"><span className="sidebar-note-icon"><Radio size={21}/></span><strong>A little insight.<br/>A better journey.</strong><p>Passenger messages become a clearer picture of the road ahead.</p></div><div className="sidebar-profile"><div className="avatar">{profile.name.split(" ").map(n => n[0]).slice(0, 2).join("")}</div><div><strong>{profile.name}</strong><span>{profile.role === "admin" ? "Administrator" : "Driver workspace"}</span></div><button aria-label="Sign out" onClick={() => void logout()}><LogOut size={18}/></button></div></aside>
    <div className="workspace"><header className="topbar"><div className="breadcrumb">Workspace <ChevronRight size={14}/><strong>Demand dashboard</strong></div><div className="topbar-right">{config.development && <span className="demo-chip">LOCAL DEMO</span>}<button className="mobile-logout" aria-label="Sign out" onClick={() => void logout()}><LogOut size={18}/></button><span className="privacy-chip"><ShieldCheck size={15}/>Private by design</span></div></header>
      <main className="dashboard"><div className="page-title"><div><span className="eyebrow">YOUR ROUTE, AT A GLANCE</span><h1>See the demand ahead.</h1><p>Less guessing. More connected journeys.</p></div><div className={`live-status ${live ? "connected" : ""}`}><span/>{live ? "Live demand" : busy ? "Connecting…" : "Awaiting data"}</div></div>
        <div className="route-controls"><label className="field">YOUR ROUTE<select value={route} onChange={e => {const r = access.routes.find(r => r.id === e.target.value)!; setRoute(r.id); setStation(r.stopIds[0]);}} disabled={!access.routes.length}>{!access.routes.length && <option>No subscribed routes</option>}{access.routes.map(r => <option value={r.id} key={r.id}>{r.name}</option>)}</select></label><label className="field">CURRENT STATION<select value={station} onChange={e => setStation(e.target.value)} disabled={!selected}>{selected?.stopIds.map(id => <option key={id} value={id}>{access.stops.find(s => s.id === id)?.name}</option>)}</select></label><button className="refresh-button" aria-label="Refresh demand" onClick={() => void refresh()} disabled={busy || !selected}><RefreshCw size={18} className={busy ? "spinning" : ""}/></button></div>
        <div className="route-position"><MapPin size={15}/><span>You're at <strong>{currentName}</strong></span><span className="position-divider"/><span>{Math.max(0, (selected?.stopIds.length || 1) - currentIndex - 1)} stops ahead</span><span className="last-updated">{data && live ? `Updated ${new Date(data.generatedAt * 1000).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"})}` : "Fresh connection required"}</span></div>
        {config.demoRoutes && <p className="illustrative-note">Illustrative routes for testing · not verified live transport coverage.</p>}
        {error && <div className="error connection-error" role="alert"><WifiOff size={18}/>{error}</div>}
        {!access.routes.length && profile.role !== "admin" ? <div className="access-gate"><ShieldCheck size={36}/><h2>Your route access starts here.</h2><p>An active route subscription is required to view passenger demand. Contact your administrator to activate access.</p><span>Passengers use KaKoRide free. Driver payments are not processed in this demo.</span><button className="primary-button" onClick={() => void loadAccess().catch(e => setError(e.message))}>Check my access</button></div> : null}
        {profile.role === "admin" ? <Admin/> : <div className={`dashboard-columns ${showSimulator && config.simulatorEnabled ? "with-simulator" : ""}`}><section className="demand-content"><DemandCards data={data} live={live}/><div className="dashboard-footer"><ShieldCheck size={15}/><span>Aggregated demand only. No passenger names or phone numbers.</span></div></section>{showSimulator && config.simulatorEnabled && <Simulator changed={() => void refresh()}/>}</div>}
        {config.simulatorEnabled && !showSimulator && profile.role !== "admin" && <button className="open-lab" onClick={() => setShowSimulator(true)}><FlaskConical size={19}/><div><strong>Try the messaging flow</strong><span>Send a simulated WhatsApp or SMS and see demand appear.</span></div><ArrowRight size={19}/></button>}
      </main>
    </div></div>;
}
