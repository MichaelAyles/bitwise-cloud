import { useEffect, useState, type FormEvent } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth';
import {
  admin,
  type AdminStats,
  type AdminUser,
  type AdminDocument,
  type Invite,
  ApiError,
} from '../api';

const tabs = ['Dashboard', 'Users', 'Documents', 'Invites'] as const;
type Tab = typeof tabs[number];

function formatBytes(bytes: number) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// --- Dashboard Tab ---

function DashboardTab() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [regMode, setRegMode] = useState('');
  const [toggling, setToggling] = useState(false);

  useEffect(() => {
    admin.stats().then(setStats);
    admin.settings().then(s => setRegMode(s.registration_mode));
  }, []);

  const toggleRegMode = async () => {
    setToggling(true);
    try {
      const newMode = regMode === 'invite_only' ? 'open' : 'invite_only';
      const res = await admin.updateSettings({ registration_mode: newMode });
      setRegMode(res.registration_mode);
    } finally {
      setToggling(false);
    }
  };

  if (!stats) return <div className="text-zinc-400">Loading stats...</div>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Users" value={stats.total_users} />
        <StatCard label="Active Users" value={stats.active_users} />
        <StatCard label="Total Documents" value={stats.total_documents} />
        <StatCard label="Storage Used" value={formatBytes(stats.total_storage_bytes)} />
      </div>

      {Object.keys(stats.documents_by_status).length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-zinc-400 mb-2">Documents by Status</h3>
          <div className="flex gap-3 flex-wrap">
            {Object.entries(stats.documents_by_status).map(([s, count]) => (
              <span key={s} className="bg-zinc-800 rounded px-3 py-1 text-sm">
                {s}: <span className="text-white font-medium">{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="border-t border-zinc-800 pt-4">
        <h3 className="text-sm font-medium text-zinc-400 mb-2">Registration Mode</h3>
        <div className="flex items-center gap-4">
          <span className={`text-sm font-medium ${regMode === 'invite_only' ? 'text-amber-400' : 'text-green-400'}`}>
            {regMode === 'invite_only' ? 'Invite Only' : 'Open'}
          </span>
          <button onClick={toggleRegMode} disabled={toggling}
            className="text-sm bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 px-3 py-1 rounded transition-colors">
            Switch to {regMode === 'invite_only' ? 'Open' : 'Invite Only'}
          </button>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <div className="text-sm text-zinc-400">{label}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  );
}

// --- Users Tab ---

function UsersTab() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    admin.users().then(setUsers).finally(() => setLoading(false));
  }, []);

  const toggleActive = async (u: AdminUser) => {
    const updated = await admin.updateUser(u.id, { is_active: !u.is_active });
    setUsers(prev => prev.map(p => p.id === updated.id ? updated : p));
  };

  const toggleAdmin = async (u: AdminUser) => {
    const updated = await admin.updateUser(u.id, { is_admin: !u.is_admin });
    setUsers(prev => prev.map(p => p.id === updated.id ? updated : p));
  };

  if (loading) return <div className="text-zinc-400">Loading users...</div>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-zinc-400 border-b border-zinc-800">
            <th className="pb-2 pr-4">Email</th>
            <th className="pb-2 pr-4">Active</th>
            <th className="pb-2 pr-4">Admin</th>
            <th className="pb-2 pr-4">Documents</th>
            <th className="pb-2 pr-4">Storage</th>
            <th className="pb-2 pr-4">Joined</th>
            <th className="pb-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map(u => (
            <tr key={u.id} className="border-b border-zinc-800/50">
              <td className="py-2 pr-4">{u.email}</td>
              <td className="py-2 pr-4">
                <span className={u.is_active ? 'text-green-400' : 'text-red-400'}>
                  {u.is_active ? 'Yes' : 'No'}
                </span>
              </td>
              <td className="py-2 pr-4">
                <span className={u.is_admin ? 'text-amber-400' : 'text-zinc-500'}>
                  {u.is_admin ? 'Yes' : 'No'}
                </span>
              </td>
              <td className="py-2 pr-4">{u.document_count}</td>
              <td className="py-2 pr-4">{formatBytes(u.storage_used_bytes)} / {formatBytes(u.storage_limit_bytes)}</td>
              <td className="py-2 pr-4 text-zinc-400">{formatDate(u.created_at)}</td>
              <td className="py-2 space-x-2">
                <button onClick={() => toggleActive(u)}
                  className={`text-xs px-2 py-1 rounded ${u.is_active ? 'bg-red-900/40 text-red-300 hover:bg-red-900/60' : 'bg-green-900/40 text-green-300 hover:bg-green-900/60'}`}>
                  {u.is_active ? 'Deactivate' : 'Activate'}
                </button>
                <button onClick={() => toggleAdmin(u)}
                  className="text-xs px-2 py-1 rounded bg-zinc-800 text-zinc-300 hover:bg-zinc-700">
                  {u.is_admin ? 'Remove Admin' : 'Make Admin'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- Documents Tab ---

function DocumentsTab() {
  const [docs, setDocs] = useState<AdminDocument[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    admin.documents().then(setDocs).finally(() => setLoading(false));
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this document? This cannot be undone.')) return;
    await admin.deleteDocument(id);
    setDocs(prev => prev.filter(d => d.id !== id));
  };

  if (loading) return <div className="text-zinc-400">Loading documents...</div>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-zinc-400 border-b border-zinc-800">
            <th className="pb-2 pr-4">Title</th>
            <th className="pb-2 pr-4">Owner</th>
            <th className="pb-2 pr-4">Status</th>
            <th className="pb-2 pr-4">Size</th>
            <th className="pb-2 pr-4">Chunks</th>
            <th className="pb-2 pr-4">Created</th>
            <th className="pb-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {docs.map(d => (
            <tr key={d.id} className="border-b border-zinc-800/50">
              <td className="py-2 pr-4 max-w-xs truncate">{d.title}</td>
              <td className="py-2 pr-4 text-zinc-400">{d.owner_email}</td>
              <td className="py-2 pr-4">
                <span className={`text-xs px-2 py-0.5 rounded ${
                  d.status === 'completed' ? 'bg-green-900/40 text-green-300' :
                  d.status === 'failed' ? 'bg-red-900/40 text-red-300' :
                  'bg-zinc-800 text-zinc-300'
                }`}>{d.status}</span>
              </td>
              <td className="py-2 pr-4">{formatBytes(d.file_size_bytes)}</td>
              <td className="py-2 pr-4">{d.chunk_count}</td>
              <td className="py-2 pr-4 text-zinc-400">{formatDate(d.created_at)}</td>
              <td className="py-2">
                <button onClick={() => handleDelete(d.id)}
                  className="text-xs px-2 py-1 rounded bg-red-900/40 text-red-300 hover:bg-red-900/60">
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {docs.length === 0 && <p className="text-zinc-500 text-sm mt-4">No documents yet.</p>}
    </div>
  );
}

// --- Invites Tab ---

function InvitesTab() {
  const [invites, setInvites] = useState<Invite[]>([]);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    admin.invites().then(setInvites).finally(() => setLoading(false));
  }, []);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setCreating(true);
    try {
      const inv = await admin.createInvite(email);
      setInvites(prev => [inv, ...prev]);
      setEmail('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to create invite');
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (id: string) => {
    if (!confirm('Revoke this invite?')) return;
    await admin.revokeInvite(id);
    setInvites(prev => prev.filter(i => i.id !== id));
  };

  const copyLink = (token: string, id: string) => {
    const link = `${window.location.origin}/register?token=${token}`;
    navigator.clipboard.writeText(link);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (loading) return <div className="text-zinc-400">Loading invites...</div>;

  const pending = invites.filter(i => !i.accepted_at);
  const accepted = invites.filter(i => i.accepted_at);

  return (
    <div className="space-y-6">
      <form onSubmit={handleCreate} className="flex gap-3 items-end">
        <div className="flex-1">
          <label className="block text-sm text-zinc-400 mb-1">Invite Email</label>
          <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
            placeholder="user@example.com"
            className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
        </div>
        <button type="submit" disabled={creating}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded px-4 py-2 transition-colors">
          {creating ? 'Sending...' : 'Send Invite'}
        </button>
      </form>
      {error && <div className="bg-red-900/40 border border-red-700 text-red-300 text-sm rounded px-3 py-2">{error}</div>}

      {pending.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-zinc-400 mb-2">Pending Invites</h3>
          <div className="space-y-2">
            {pending.map(inv => {
              const expired = new Date(inv.expires_at) < new Date();
              return (
                <div key={inv.id} className="flex items-center justify-between bg-zinc-900 border border-zinc-800 rounded px-4 py-3">
                  <div>
                    <span className="text-sm font-medium">{inv.email}</span>
                    <span className={`ml-3 text-xs ${expired ? 'text-red-400' : 'text-zinc-500'}`}>
                      {expired ? 'Expired' : `Expires ${formatDate(inv.expires_at)}`}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {!expired && (
                      <button onClick={() => copyLink(inv.token, inv.id)}
                        className="text-xs px-2 py-1 rounded bg-zinc-800 text-zinc-300 hover:bg-zinc-700">
                        {copiedId === inv.id ? 'Copied!' : 'Copy Link'}
                      </button>
                    )}
                    <button onClick={() => handleRevoke(inv.id)}
                      className="text-xs px-2 py-1 rounded bg-red-900/40 text-red-300 hover:bg-red-900/60">
                      Revoke
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {accepted.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-zinc-400 mb-2">Accepted Invites</h3>
          <div className="space-y-2">
            {accepted.map(inv => (
              <div key={inv.id} className="flex items-center justify-between bg-zinc-900/50 border border-zinc-800/50 rounded px-4 py-3">
                <div>
                  <span className="text-sm text-zinc-300">{inv.email}</span>
                  <span className="ml-3 text-xs text-green-400">Accepted {formatDate(inv.accepted_at!)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {invites.length === 0 && <p className="text-zinc-500 text-sm">No invites yet.</p>}
    </div>
  );
}

// --- Main Admin Page ---

export default function Admin() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>('Dashboard');

  if (!user?.is_admin) return <Navigate to="/" />;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Admin</h1>
      <div className="flex gap-1 mb-6 border-b border-zinc-800">
        {tabs.map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t ? 'border-blue-500 text-white' : 'border-transparent text-zinc-400 hover:text-white'
            }`}>
            {t}
          </button>
        ))}
      </div>
      {tab === 'Dashboard' && <DashboardTab />}
      {tab === 'Users' && <UsersTab />}
      {tab === 'Documents' && <DocumentsTab />}
      {tab === 'Invites' && <InvitesTab />}
    </div>
  );
}
