export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}
let token = sessionStorage.getItem("kakoride.driver") || "";
let refreshToken: (() => Promise<string>) | undefined;
export function setToken(value: string, refresh?: () => Promise<string>) {
  token = value;
  refreshToken = refresh;
  if (value) sessionStorage.setItem("kakoride.driver", value);
  else sessionStorage.removeItem("kakoride.driver");
}
export function hasToken() { return !!token; }
export async function api<T>(path: string, body?: unknown): Promise<T> {
  if (refreshToken) token = await refreshToken();
  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ""}${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(15000), cache: "no-store",
  });
  const data = await response.json();
  if (!response.ok) throw new ApiError(data.error || data.detail || "Could not complete the request.", response.status);
  return data;
}
