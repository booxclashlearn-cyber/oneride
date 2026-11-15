import { describe, expect, it } from "vitest";
import { kwacha, snapshotLive } from "./lib/demand";
import type { Demand } from "./types";
const data = {serverNow: 1000, nextExpiryAt: 1005, accessExpiresAt: 2000} as Demand;
describe("server-time demand freshness", () => {
  it("formats integer minor units as kwacha", () => { expect(kwacha(6500)).toBe("K65"); expect(kwacha(2550)).toBe("K25.5"); });
  it("hides demand exactly at expiry between refreshes", () => {expect(snapshotLive(data, 4999)).toBe(true); expect(snapshotLive(data, 5000)).toBe(false);});
  it("hides stale data even without an expiry", () => expect(snapshotLive({...data, nextExpiryAt: null}, 12000)).toBe(false));
  it("hides demand when the subscription expires", () => expect(snapshotLive({...data, accessExpiresAt: 1001}, 1000)).toBe(false));
});
