// Access and refresh tokens live in sessionStorage for this first client.
// That is a temporary choice. The final browser storage design is still open.

const ACCESS_KEY = "swasthya.access";
const REFRESH_KEY = "swasthya.refresh";

export type ApiErrorBody = {
  code: string;
  message: string;
  details?: Record<string, string[]>;
};

export class ApiError extends Error {
  status: number;
  code: string;
  details: Record<string, string[]>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.status = status;
    this.code = body.code;
    this.details = body.details ?? {};
  }
}

export function accessToken() {
  return sessionStorage.getItem(ACCESS_KEY);
}

export function saveTokens(access: string, refresh: string) {
  sessionStorage.setItem(ACCESS_KEY, access);
  sessionStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
}

async function parseBody(response: Response) {
  const text = await response.text();
  if (!text) return null;
  return JSON.parse(text) as unknown;
}

export async function api<T>(path: string, options: RequestInit = {}, allowRefresh = true): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const access = accessToken();
  if (access) headers.set("Authorization", `Bearer ${access}`);

  const response = await fetch(path, { ...options, headers });
  if (response.status === 401 && allowRefresh && sessionStorage.getItem(REFRESH_KEY)) {
    const refreshed = await fetch("/api/auth/refresh/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: sessionStorage.getItem(REFRESH_KEY) }),
    });
    if (refreshed.ok) {
      const body = (await refreshed.json()) as { access: string; refresh?: string };
      sessionStorage.setItem(ACCESS_KEY, body.access);
      if (body.refresh) sessionStorage.setItem(REFRESH_KEY, body.refresh);
      return api<T>(path, options, false);
    }
    clearTokens();
  }

  const payload = await parseBody(response);
  if (!response.ok) {
    const error = (payload as { error?: ApiErrorBody } | null)?.error;
    throw new ApiError(
      response.status,
      error ?? { code: "error", message: `Request failed (${response.status}).` },
    );
  }
  return payload as T;
}
