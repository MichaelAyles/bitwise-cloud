import { type FormEvent, useEffect, useState } from 'react';
import { apiKeys, documents, type ApiKey, type ApiKeyCreated, type Document, ApiError } from '../api';

export default function ApiKeys() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newKey, setNewKey] = useState<ApiKeyCreated | null>(null);
  const [error, setError] = useState('');

  // Create form
  const [name, setName] = useState('');
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);

  const load = async () => {
    const [k, d] = await Promise.all([apiKeys.list(), documents.list()]);
    setKeys(k);
    setDocs(d.filter(doc => doc.status === 'ready'));
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setCreating(true);
    try {
      const key = await apiKeys.create(name, selectedDocs);
      setNewKey(key);
      setShowCreate(false);
      setName('');
      setSelectedDocs([]);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to create key');
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (id: string) => {
    if (!confirm('Revoke this API key? This cannot be undone.')) return;
    try {
      await apiKeys.revoke(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to revoke key');
    }
  };

  const toggleDoc = (id: string) => {
    setSelectedDocs(prev => prev.includes(id) ? prev.filter(d => d !== id) : [...prev, id]);
  };

  const docTitle = (id: string) => docs.find(d => d.id === id)?.title || id.slice(0, 8);

  if (loading) return <p className="text-zinc-400 text-sm">Loading...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">API Keys</h1>
        <button onClick={() => { setShowCreate(!showCreate); setNewKey(null); }}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded px-4 py-2 transition-colors">
          Create Key
        </button>
      </div>

      {error && <div className="bg-red-900/40 border border-red-700 text-red-300 text-sm rounded px-3 py-2 mb-4">{error}</div>}

      {newKey && (
        <div className="bg-green-900/30 border border-green-700 rounded-lg p-4 mb-4">
          <p className="text-green-300 text-sm font-medium mb-2">API key created! Copy it now - it won't be shown again.</p>
          <code className="block bg-zinc-900 rounded px-3 py-2 text-sm text-green-300 font-mono break-all select-all">
            {newKey.key}
          </code>
          <p className="text-xs text-zinc-500 mt-2">
            Use this key as the <code className="text-zinc-400">api_key</code> parameter when calling MCP tools,
            or as the <code className="text-zinc-400">X-API-Key</code> header for REST API calls.
          </p>
        </div>
      )}

      {showCreate && (
        <form onSubmit={handleCreate} className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mb-6">
          <h2 className="text-sm font-medium mb-4">New API Key</h2>
          <div className="mb-4">
            <label className="block text-sm text-zinc-400 mb-1">Name</label>
            <input type="text" required value={name} onChange={e => setName(e.target.value)}
              placeholder="e.g., Claude Code, CI/CD"
              className="w-full max-w-sm bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
          </div>
          {docs.length > 0 && (
            <div className="mb-4">
              <label className="block text-sm text-zinc-400 mb-2">Document access</label>
              <div className="flex flex-wrap gap-2">
                {docs.map(doc => (
                  <button key={doc.id} type="button" onClick={() => toggleDoc(doc.id)}
                    className={`text-xs px-2 py-1 rounded border transition-colors ${
                      selectedDocs.includes(doc.id)
                        ? 'bg-blue-900/50 border-blue-700 text-blue-300'
                        : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-500'
                    }`}>
                    {doc.title.length > 50 ? doc.title.slice(0, 50) + '...' : doc.title}
                  </button>
                ))}
              </div>
              <p className="text-xs text-zinc-500 mt-1">
                {selectedDocs.length === 0 ? 'No documents selected — key will have access to all documents' : `${selectedDocs.length} document(s) selected`}
              </p>
            </div>
          )}
          <div className="flex gap-2">
            <button type="submit" disabled={creating}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded px-4 py-2 transition-colors">
              {creating ? 'Creating...' : 'Create'}
            </button>
            <button type="button" onClick={() => setShowCreate(false)}
              className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm rounded px-4 py-2 transition-colors">
              Cancel
            </button>
          </div>
        </form>
      )}

      {keys.length === 0 && !showCreate ? (
        <div className="border border-dashed border-zinc-700 rounded-lg p-12 text-center">
          <p className="text-zinc-400 mb-2">No API keys</p>
          <p className="text-zinc-500 text-sm">Create an API key to use with MCP tools or the REST API</p>
        </div>
      ) : (
        <div className="space-y-3">
          {keys.map(key => (
            <div key={key.id} className={`bg-zinc-900 border border-zinc-800 rounded-lg p-4 ${!key.is_active ? 'opacity-50' : ''}`}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium">{key.name}</span>
                    <code className="text-xs text-zinc-500 font-mono">{key.key_prefix}...</code>
                    {!key.is_active && (
                      <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-500 border border-zinc-700">revoked</span>
                    )}
                  </div>
                  <div className="flex gap-4 text-xs text-zinc-500">
                    <span>{key.request_count} requests</span>
                    {key.last_used_at && <span>Last used {new Date(key.last_used_at).toLocaleDateString()}</span>}
                    <span>Created {new Date(key.created_at).toLocaleDateString()}</span>
                  </div>
                  {key.document_ids.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {key.document_ids.map(id => (
                        <span key={id} className="text-xs px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-400">
                          {docTitle(id)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                {key.is_active && (
                  <button onClick={() => handleRevoke(key.id)}
                    className="text-zinc-600 hover:text-red-400 text-sm ml-4 transition-colors">
                    Revoke
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
