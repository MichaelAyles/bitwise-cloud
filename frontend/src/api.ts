const BASE = '/api';

let accessToken: string | null = null;

export function setToken(token: string | null) {
  accessToken = token;
  if (token) localStorage.setItem('token', token);
  else localStorage.removeItem('token');
}

export function getToken() {
  if (!accessToken) accessToken = localStorage.getItem('token');
  return accessToken;
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(opts.headers as Record<string, string> || {}),
  };
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!(opts.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${BASE}${path}`, { ...opts, headers });

  if (res.status === 401) {
    // Try refresh
    const refreshRes = await fetch(`${BASE}/auth/refresh`, { method: 'POST', credentials: 'include' });
    if (refreshRes.ok) {
      const data = await refreshRes.json();
      setToken(data.access_token);
      headers['Authorization'] = `Bearer ${data.access_token}`;
      const retry = await fetch(`${BASE}${path}`, { ...opts, headers });
      if (!retry.ok) throw new ApiError(retry.status, await retry.text());
      if (retry.status === 204) return undefined as T;
      return retry.json();
    }
    setToken(null);
    window.location.href = '/login';
    throw new ApiError(401, 'Session expired');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Auth
export const auth = {
  register: (email: string, password: string) =>
    request<{ access_token: string }>('/auth/register', {
      method: 'POST', body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string }>('/auth/login', {
      method: 'POST', body: JSON.stringify({ email, password }),
    }),
  refresh: () =>
    request<{ access_token: string }>('/auth/refresh', { method: 'POST', credentials: 'include' }),
};

// Users
export const users = {
  me: () => request<User>('/users/me'),
};

// Documents
export interface Document {
  id: string;
  title: string;
  filename: string;
  file_size_bytes: number;
  page_count: number | null;
  status: string;
  chunk_count: number;
  register_count: number;
  ingestion_error: string | null;
  created_at: string;
  updated_at: string;
}

export const documents = {
  list: () => request<Document[]>('/documents'),
  get: (id: string) => request<Document>(`/documents/${id}`),
  upload: (file: File, title?: string) => {
    const form = new FormData();
    form.append('file', file);
    if (title) form.append('title', title);
    return request<Document>('/documents/upload', { method: 'POST', body: form });
  },
  update: (id: string, title: string) =>
    request<Document>(`/documents/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) }),
  delete: (id: string) =>
    request<void>(`/documents/${id}`, { method: 'DELETE' }),
  progress: (id: string) =>
    request<{ status: string; progress_percent: number; progress_message: string | null }>(`/documents/${id}/progress`),
};

// Search
export interface SearchResult {
  score: number;
  text: string;
  document_id: string;
  document_title: string;
  page_number: number | null;
  section: string | null;
}

export const search = {
  query: (query: string, top_k = 10, doc_ids?: string[]) =>
    request<{ results: SearchResult[]; query: string; total: number }>('/search', {
      method: 'POST', body: JSON.stringify({ query, top_k, doc_ids: doc_ids || null }),
    }),
  register: (name: string, doc_ids?: string[]) =>
    request<any>('/search/register', {
      method: 'POST', body: JSON.stringify({ name, doc_ids: doc_ids || null }),
    }),
};

// API Keys
export interface ApiKey {
  id: string;
  key_prefix: string;
  name: string;
  is_active: boolean;
  last_used_at: string | null;
  request_count: number;
  created_at: string;
  expires_at: string | null;
  document_ids: string[];
}

export interface ApiKeyCreated extends ApiKey {
  key: string;
}

export const apiKeys = {
  list: () => request<ApiKey[]>('/api-keys'),
  create: (name: string, document_ids: string[]) =>
    request<ApiKeyCreated>('/api-keys', {
      method: 'POST', body: JSON.stringify({ name, document_ids }),
    }),
  update: (id: string, data: { name?: string }) =>
    request<ApiKey>(`/api-keys/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  updateDocuments: (id: string, document_ids: string[]) =>
    request<ApiKey>(`/api-keys/${id}/documents`, {
      method: 'PUT', body: JSON.stringify({ document_ids }),
    }),
  revoke: (id: string) =>
    request<void>(`/api-keys/${id}`, { method: 'DELETE' }),
};

// Types
export interface User {
  id: string;
  email: string;
  display_name: string | null;
  storage_used_bytes: number;
  storage_limit_bytes: number;
  created_at: string;
}
