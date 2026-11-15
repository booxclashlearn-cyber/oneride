import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowUp, Check, Clock3, MessageCircle, Smartphone } from "lucide-react";
import { api } from "../lib/api";
import type { Transcript } from "../types";

export default function Simulator({ changed }: { changed: () => void }) {
  const [channel, setChannel] = useState("whatsapp"), [sender, setSender] = useState("+260970000101");
  const [text, setText] = useState(""), [data, setData] = useState<Transcript | null>(null);
  const [outgoing, setOutgoing] = useState<{text: string; at: number; beforeId: string}[]>([]), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const activeConversation = useRef("");
  activeConversation.current = `${sender}/${channel}`;
  const load = useCallback(async () => {
    const conversation = `${sender}/${channel}`;
    try { const result = await api<Transcript>(`/dev/messages?sender=${encodeURIComponent(sender)}&channel=${channel}`); if (activeConversation.current === conversation) setData(result); }
    catch (e) { setError(e instanceof Error ? e.message : "Simulator unavailable"); }
  }, [sender, channel]);
  useEffect(() => { setData(null); setOutgoing([]); void load(); const timer = setInterval(() => { if (!document.hidden) void load(); }, 3000); return () => clearInterval(timer); }, [load]);
  async function send(message = text) {
    if (!message.trim() || busy) return;
    setBusy(true); setError("");
    const conversation = activeConversation.current;
    try {
      const result = await api<Transcript>("/dev/messages", { channel, sender, text: message, eventId: crypto.randomUUID() });
      if (activeConversation.current === conversation) { setOutgoing(old => [...old, { text: message, at: result.serverNow, beforeId: result.messages.at(-1)?.id || "" }]); setText(""); setData(result); } changed();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not send simulation."); }
    finally { setBusy(false); }
  }
  async function advance(seconds: number) {
    setBusy(true); setError("");
    try { await api("/dev/clock", { seconds }); await load(); changed(); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not advance the test clock."); }
    finally { setBusy(false); }
  }
  const messages = (data?.messages || []).flatMap(m => [...outgoing.filter(o => o.beforeId === m.id).map((o, i) => ({...o, id: `out-${m.id}-${i}`, outgoing: true, context: null})), {...m, outgoing: false}]);
  return <aside className="simulator"><div className="sim-heading"><div><span className="eyebrow">DEVELOPMENT ONLY</span><h2>Passenger simulator</h2></div><span className="lab-tag">TEST LAB</span></div>
    <p className="sim-description">Send a simulated message. Watch the same demand engine update your dashboard.</p>
    <div className="channel-tabs" aria-label="Messaging channel"><button className={channel === "whatsapp" ? "selected" : ""} onClick={() => setChannel("whatsapp")}><MessageCircle size={16}/>WhatsApp</button><button className={channel === "sms" ? "selected" : ""} onClick={() => setChannel("sms")}><Smartphone size={16}/>SMS</button></div>
    <label className="field">Synthetic sender<select value={sender} onChange={e => setSender(e.target.value)}><option value="+260970000101">Passenger A · …0101</option><option value="+260970000102">Passenger B · …0102</option><option value="+260970000103">Passenger C · …0103</option></select></label>
    <div className="phone-chat"><div className="chat-title"><span className="chat-avatar"><MessageCircle size={20}/></span><div><strong>KaKoRide assistant</strong><span>Simulated conversation</span></div><span className="connection-dot"/></div>
      <div className="chat-history" aria-live="polite">{!messages.length && <div className="chat-intro"><MessageCircle size={28}/><strong>No app. Just a message.</strong><p>Send “Hi” to start, or try a ready-made request below.</p></div>}{messages.map(m => <div key={m.id} className={`bubble ${m.outgoing ? "outgoing" : "incoming"}`}><p>{m.text}</p>{m.context && !m.outgoing && <div className="reply-buttons">{["Yes, boarded", "Still waiting"].map((label, i) => <button key={label} disabled={busy} onClick={() => void send(channel === "whatsapp" ? `reply:${m.context!.request}:${m.context!.version}:${i + 1}` : `${i + 1} ${m.context!.request.slice(0, 6).toUpperCase()}${m.context!.version}`)}>{i === 0 && <Check size={13}/>} {label}</button>)}</div>}</div>)}</div>
      <form className="chat-compose" onSubmit={e => {e.preventDefault(); void send();}}><input aria-label="Passenger message" value={text} onChange={e => setText(e.target.value)} placeholder="Type a passenger message…" maxLength={500}/><button aria-label="Send simulated message" disabled={busy || !text.trim()}><ArrowUp size={20}/></button></form>
    </div>
    {error && <p className="error" role="alert">{error}</p>}
    <div className="quick-messages"><span className="small-label">QUICK MESSAGES</span><div>{["Hi", "RIDE KAMWALA TOWN 20", "RIDE CHILENJE TOWN 25 2", "STATUS", "CANCEL"].map(value => <button disabled={busy} key={value} onClick={() => void send(value)}>{value}</button>)}</div></div>
    <div className="clock-controls"><div><Clock3 size={16}/><strong>Test the waiting window</strong></div><p>Advances the shared local test clock, not your computer clock.</p><button disabled={busy} onClick={() => void advance(300)}>+5 min · send reminder</button><button disabled={busy} onClick={() => void advance(300)}>+5 min · test expiry</button></div>
    <p className="sim-footnote">No real WhatsApp or SMS is sent here. Provider webhooks use this same backend engine.</p>
  </aside>;
}
