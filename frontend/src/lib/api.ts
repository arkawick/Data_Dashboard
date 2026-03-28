import { getAccessToken, getRefreshToken, storeTokens, clearTokens } from "./auth";
import type {
  LoginRequest,
  LoginResponse,
  HealthResponse,
  GraphStatsResponse,
  StatsResponse,
  PaginatedResponse,
  Bug,
  TestCase,
  Project,
  Requirement,
  Employee,
  QueryRequest,
  QueryResponse,
  PipelineRebuildResponse,
  PipelineStatusResponse,
} from "@/types/api";

const DJANGO_URL = import.meta.env.VITE_DJANGO_URL ?? "http://localhost:8000";
const FASTAPI_URL = import.meta.env.VITE_FASTAPI_URL ?? "http://localhost:8001";

// ---- Refresh token logic ----
let isRefreshing = false;
let refreshQueue: Array<(token: string | null) => void> = [];

async function refreshAccessToken(): Promise<string | null> {
  if (isRefreshing) {
    return new Promise((resolve) => {
      refreshQueue.push(resolve);
    });
  }
  isRefreshing = true;
  try {
    const refreshToken = getRefreshToken();
    if (!refreshToken) throw new Error("No refresh token");
    const res = await fetch(`${DJANGO_URL}/api/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) throw new Error("Refresh failed");
    const data = await res.json() as { access_token: string };
    const newToken = data.access_token;
    const stored = JSON.parse(localStorage.getItem("username") ?? '""') as string;
    const role = localStorage.getItem("role") ?? "user";
    storeTokens(newToken, refreshToken, stored, role);
    refreshQueue.forEach((cb) => cb(newToken));
    return newToken;
  } catch {
    clearTokens();
    refreshQueue.forEach((cb) => cb(null));
    window.location.href = "/login";
    return null;
  } finally {
    isRefreshing = false;
    refreshQueue = [];
  }
}

// ---- Django authenticated fetch ----
async function djangoFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> ?? {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res = await fetch(`${DJANGO_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`;
      res = await fetch(`${DJANGO_URL}${path}`, { ...options, headers });
    }
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ---- FastAPI fetch (no auth) ----
async function fastapiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> ?? {}),
  };
  const res = await fetch(`${FASTAPI_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`FastAPI error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ====== AUTH ======
export async function login(data: LoginRequest): Promise<LoginResponse> {
  const res = await fetch(`${DJANGO_URL}/api/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error("Invalid credentials");
  }
  return res.json() as Promise<LoginResponse>;
}

// ====== FASTAPI ======
export async function fetchHealth(): Promise<HealthResponse> {
  return fastapiFetch<HealthResponse>("/health");
}

export async function fetchGraphStats(): Promise<GraphStatsResponse> {
  return fastapiFetch<GraphStatsResponse>("/graph/stats");
}

export async function queryGraphRAG(data: QueryRequest): Promise<QueryResponse> {
  return fastapiFetch<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function queryHybrid(data: QueryRequest): Promise<QueryResponse> {
  return fastapiFetch<QueryResponse>("/query/hybrid", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ====== DJANGO ======
export async function fetchStats(): Promise<StatsResponse> {
  return djangoFetch<StatsResponse>("/api/stats/");
}

export async function fetchBugs(params: Record<string, string>): Promise<PaginatedResponse<Bug>> {
  const qs = new URLSearchParams(params).toString();
  return djangoFetch<PaginatedResponse<Bug>>(`/api/bugs/?${qs}`);
}

export async function fetchTestCases(params: Record<string, string>): Promise<PaginatedResponse<TestCase>> {
  const qs = new URLSearchParams(params).toString();
  return djangoFetch<PaginatedResponse<TestCase>>(`/api/test-cases/?${qs}`);
}

export async function fetchProjects(params: Record<string, string>): Promise<PaginatedResponse<Project>> {
  const qs = new URLSearchParams(params).toString();
  return djangoFetch<PaginatedResponse<Project>>(`/api/projects/?${qs}`);
}

export async function fetchRequirements(params: Record<string, string>): Promise<PaginatedResponse<Requirement>> {
  const qs = new URLSearchParams(params).toString();
  return djangoFetch<PaginatedResponse<Requirement>>(`/api/requirements/?${qs}`);
}

export async function fetchEmployees(params: Record<string, string>): Promise<PaginatedResponse<Employee>> {
  const qs = new URLSearchParams(params).toString();
  return djangoFetch<PaginatedResponse<Employee>>(`/api/employees/?${qs}`);
}

export async function rebuildPipeline(): Promise<PipelineRebuildResponse> {
  return djangoFetch<PipelineRebuildResponse>("/api/rebuild/", { method: "POST" });
}

export async function fetchPipelineStatus(taskId: string): Promise<PipelineStatusResponse> {
  return fastapiFetch<PipelineStatusResponse>(`/pipeline/status/${taskId}`);
}
