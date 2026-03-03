const BASE = '/api';

let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function setToken(token: string | null) {
  accessToken = token;
  if (token) localStorage.setItem('token', token);
  else localStorage.removeItem('token');
}

export function getToken() {
  if (!accessToken) accessToken = localStorage.getItem('token');
  return accessToken;
}

async function request<T>(
  path: string,
  opts: RequestInit = {},
  { skipAuthRetry = false }: { skipAuthRetry?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {
    ...(opts.headers as Record<string, string> || {}),
  };
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!(opts.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${BASE}${path}`, { ...opts, headers });

  if (res.status === 401 && !skipAuthRetry) {
    // Try refresh, sharing the promise across concurrent 401s
    if (!refreshPromise) {
      refreshPromise = (async () => {
        try {
          const refreshRes = await fetch(`${BASE}/auth/refresh`, { method: 'POST', credentials: 'include' });
          if (refreshRes.ok) {
            const data = await refreshRes.json();
            setToken(data.access_token);
            return data.access_token as string;
          }
          setToken(null);
          window.location.href = '/login';
          return null;
        } finally {
          refreshPromise = null;
        }
      })();
    }
    const newToken = await refreshPromise;
    if (newToken) {
      headers['Authorization'] = `Bearer ${newToken}`;
      const retry = await fetch(`${BASE}${path}`, { ...opts, headers });
      if (!retry.ok) throw new ApiError(retry.status, await retry.text());
      if (retry.status === 204) return undefined as T;
      return retry.json();
    }
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
  register: (email: string, password: string, invite_token?: string) =>
    request<{ access_token: string }>('/auth/register', {
      method: 'POST', body: JSON.stringify({ email, password, invite_token }),
    }, { skipAuthRetry: true }),
  login: (email: string, password: string) =>
    request<{ access_token: string }>('/auth/login', {
      method: 'POST', body: JSON.stringify({ email, password }),
    }, { skipAuthRetry: true }),
  oauthShoo: (id_token: string) =>
    request<{ access_token: string }>('/auth/oauth/shoo', {
      method: 'POST', body: JSON.stringify({ id_token }),
    }, { skipAuthRetry: true }),
  refresh: () =>
    request<{ access_token: string }>('/auth/refresh', { method: 'POST', credentials: 'include' }),
  settings: () =>
    request<{ registration_mode: string }>('/auth/settings'),
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
  key_value: string | null;
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

// Admin
export interface AdminStats {
  total_users: number;
  active_users: number;
  total_documents: number;
  total_storage_bytes: number;
  documents_by_status: Record<string, number>;
}

export interface AdminUser {
  id: string;
  email: string;
  display_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  storage_used_bytes: number;
  storage_limit_bytes: number;
  document_count: number;
  api_key_count: number;
}

export interface AdminDocument {
  id: string;
  title: string;
  filename: string;
  file_size_bytes: number;
  page_count: number | null;
  status: string;
  chunk_count: number;
  register_count: number;
  created_at: string;
  owner_email: string;
  owner_id: string;
}

export interface Invite {
  id: string;
  email: string;
  token: string;
  invited_by: string;
  accepted_at: string | null;
  created_at: string;
  expires_at: string;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded';
  checks: Record<string, string>;
}

export const health = {
  check: async (): Promise<HealthStatus> => {
    const res = await fetch(`${BASE}/health`);
    return res.json();
  },
};

export const admin = {
  stats: () => request<AdminStats>('/admin/stats'),
  users: () => request<AdminUser[]>('/admin/users'),
  getUser: (id: string) => request<AdminUser>(`/admin/users/${id}`),
  updateUser: (id: string, data: { is_active?: boolean; is_admin?: boolean; storage_limit_bytes?: number }) =>
    request<AdminUser>(`/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  documents: () => request<AdminDocument[]>('/admin/documents'),
  deleteDocument: (id: string) => request<void>(`/admin/documents/${id}`, { method: 'DELETE' }),
  invites: () => request<Invite[]>('/admin/invites'),
  createInvite: (email: string, expires_in_days = 7) =>
    request<Invite>('/admin/invites', { method: 'POST', body: JSON.stringify({ email, expires_in_days }) }),
  revokeInvite: (id: string) => request<void>(`/admin/invites/${id}`, { method: 'DELETE' }),
  settings: () => request<{ registration_mode: string }>('/admin/settings'),
  updateSettings: (data: { registration_mode?: string }) =>
    request<{ registration_mode: string }>('/admin/settings', { method: 'PATCH', body: JSON.stringify(data) }),
};

// Types
export interface User {
  id: string;
  email: string;
  display_name: string | null;
  is_admin: boolean;
  storage_used_bytes: number;
  storage_limit_bytes: number;
  created_at: string;
}
