import type { Demand } from "../types";
export const kwacha = (minor: number) => `K${new Intl.NumberFormat("en-ZM", { maximumFractionDigits: 2 }).format(minor / 100)}`;
export function snapshotLive(data: Demand, ageMilliseconds: number): boolean {
  const estimatedNow = data.serverNow + ageMilliseconds / 1000;
  return ageMilliseconds < 12000 && estimatedNow < data.accessExpiresAt && (data.nextExpiryAt === null || estimatedNow < data.nextExpiryAt);
}
