export interface Config { development: boolean; simulatorEnabled: boolean; storage: string; demoRoutes: boolean }
export interface Profile { uid: string; name: string; role: "driver" | "admin"; approved: boolean }
export interface Stop { id: string; name: string }
export interface Route { id: string; name: string; stopIds: string[]; demo: boolean }
export interface Access { profile: Profile; routes: Route[]; stops: Stop[]; entitlements: {routeId: string; expiresAt: number; source: string}[]; serverNow: number }
export interface DestinationGroup { stopId: string; name: string; passengers: number; offeredMinor: number; minFareMinor: number; maxFareMinor: number }
export interface StopGroup { stopId: string; name: string; passengers: number; offeredMinor: number; destinations: DestinationGroup[] }
export interface Demand { route: Route; groups: StopGroup[]; passengers: number; waitingStops: number; offeredMinor: number; serverNow: number; generatedAt: number; nextExpiryAt: number | null; accessExpiresAt: number }
export interface ChatMessage { id: string; text: string; at: number; status: string; context: {request: string; version: number} | null }
export interface Transcript { messages: ChatMessage[]; active: boolean; serverNow: number }
