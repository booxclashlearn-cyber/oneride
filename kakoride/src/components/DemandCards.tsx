import { ArrowDown, ArrowUpRight, MapPin, Users } from "lucide-react";
import type { Demand } from "../types";
import { kwacha } from "../lib/demand";

export default function DemandCards({ data, live }: { data: Demand | null; live: boolean }) {
  const shown = live ? data : null;
  return <>
    <div className="metrics" aria-live="polite" aria-label="Demand totals">
      <article><div className="metric-label">Passengers waiting <Users size={18}/></div><strong>{shown ? shown.passengers : "—"}</strong><span>At stops ahead of you</span></article>
      <article><div className="metric-label">Waiting stops <MapPin size={18}/></div><strong>{shown ? shown.waitingStops : "—"}</strong><span>Along your selected route</span></article>
      <article><div className="metric-label">Fares offered <ArrowUpRight size={18}/></div><strong>{shown ? kwacha(shown.offeredMinor) : "—"}</strong><span>Passenger budgets · not earnings</span></article>
    </div>
    <div className="section-heading"><div><h2>Demand along your route</h2><p>Only stations ahead of your current stop.</p></div><span className="small-label">BY BOARDING STOP</span></div>
    {!shown ? <div className="empty-state"><span className="empty-icon"><MapPin/></span><h3>Waiting for a fresh snapshot</h3><p>We hide totals when they expire or the connection is stale.</p></div>
      : !shown.groups.length ? <div className="empty-state"><span className="empty-icon"><Users/></span><h3>No passengers waiting ahead</h3><p>New requests will appear here automatically. Try the messaging simulator in local development.</p></div>
      : <div className="stop-list">{shown.groups.map((group, i) => <article className="stop-card" key={group.stopId}>
        <div className="stop-header"><div className="stop-index">{String(i + 1).padStart(2, "0")}</div><div><h3>{group.name}</h3><p>Boarding station</p></div><div className="stop-count"><strong>{group.passengers}</strong><span>waiting</span></div></div>
        <div className="destination-list">{group.destinations.map(dest => <div className="destination" key={dest.stopId}><ArrowDown size={16}/><div><strong>{dest.name}</strong><span>{dest.passengers} passenger{dest.passengers === 1 ? "" : "s"} · {kwacha(dest.minFareMinor)}{dest.maxFareMinor !== dest.minFareMinor ? `–${kwacha(dest.maxFareMinor)}` : ""} each</span></div><b>{kwacha(dest.offeredMinor)}</b></div>)}</div>
        <footer><span>Total offered at this stop</span><strong>{kwacha(group.offeredMinor)}</strong></footer>
      </article>)}</div>}
  </>;
}
