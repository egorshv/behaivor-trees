import type {
  ExecutionSession,
  SessionStateResponse,
  TreeDocument,
  TreeSummary,
  TreeUpsertRequest,
  ValidationResult,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed with ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  healthcheck: () => request<{ status: string }>("/health"),
  listTrees: () => request<TreeSummary[]>("/trees"),
  getTree: (treeId: string) => request<TreeDocument>(`/trees/${treeId}`),
  createTree: (payload: TreeUpsertRequest) =>
    request<TreeDocument>("/trees", { method: "POST", body: JSON.stringify(payload) }),
  updateTree: (treeId: string, payload: TreeUpsertRequest) =>
    request<TreeDocument>(`/trees/${treeId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteTree: (treeId: string) => request<void>(`/trees/${treeId}`, { method: "DELETE" }),
  validateTree: (treeId: string) =>
    request<ValidationResult>(`/trees/${treeId}/validate`, { method: "POST" }),
  runTree: (treeId: string) =>
    request<ExecutionSession>(`/trees/${treeId}/run`, { method: "POST" }),
  getSession: (sessionId: string) => request<ExecutionSession>(`/sessions/${sessionId}`),
  getSessionState: (sessionId: string) =>
    request<SessionStateResponse>(`/sessions/${sessionId}/state`),
  tickSession: (sessionId: string) =>
    request<ExecutionSession>(`/sessions/${sessionId}/tick`, { method: "POST" }),
  resetSession: (sessionId: string) =>
    request<ExecutionSession>(`/sessions/${sessionId}/reset`, { method: "POST" }),
};

