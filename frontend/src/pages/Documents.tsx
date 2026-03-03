import { useCallback, useEffect, useRef, useState } from 'react';
import { documents, type Document, ApiError } from '../api';

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    ready: 'bg-green-900/50 text-green-400 border-green-700',
    pending: 'bg-yellow-900/50 text-yellow-400 border-yellow-700',
    ingesting: 'bg-blue-900/50 text-blue-400 border-blue-700',
    failed: 'bg-red-900/50 text-red-400 border-red-700',
    removing: 'bg-slate-700/50 text-slate-400 border-slate-500/50',
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded border ${colors[status] || 'bg-slate-700/50 text-slate-400 border-slate-500/50'}`}>
      {status}
    </span>
  );
}

function ProgressBar({ docId }: { docId: string }) {
  const [pct, setPct] = useState(0);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const p = await documents.progress(docId);
        if (!active) return;
        setPct(p.progress_percent);
        setMsg(p.progress_message || '');
        if (p.status === 'ingesting' || p.status === 'pending') {
          setTimeout(poll, 2000);
        }
      } catch { /* ignore */ }
    };
    poll();
    return () => { active = false; };
  }, [docId]);

  return (
    <div className="mt-2">
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>{msg || 'Processing...'}</span>
        <span>{pct}%</span>
      </div>
      <div className="h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
        <div className="h-full bg-blue-500 transition-all duration-500 rounded-full" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function Documents() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  const load = useCallback(async () => {
    try {
      const d = await documents.list();
      setDocs(d);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  // Auto-refresh while any doc is processing
  useEffect(() => {
    if (docs.some(d => d.status === 'pending' || d.status === 'ingesting')) {
      const id = setInterval(load, 5000);
      return () => clearInterval(id);
    }
  }, [docs, load]);

  const [uploadProgress, setUploadProgress] = useState('');

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setError('');

    // Validate all files first
    const toUpload: File[] = [];
    for (const file of Array.from(files)) {
      if (file.size > 100 * 1024 * 1024) {
        setError(`${file.name} exceeds 100 MB limit`);
        if (fileRef.current) fileRef.current.value = '';
        return;
      }
      toUpload.push(file);
    }

    setUploading(true);
    let failed = 0;
    for (let i = 0; i < toUpload.length; i++) {
      setUploadProgress(`Uploading ${i + 1} of ${toUpload.length}: ${toUpload[i].name}`);
      try {
        await documents.upload(toUpload[i]);
      } catch (err) {
        failed++;
        setError(err instanceof ApiError ? err.message : `Failed to upload ${toUpload[i].name}`);
      }
    }
    setUploadProgress('');
    setUploading(false);
    if (fileRef.current) fileRef.current.value = '';
    await load();
    if (failed > 0 && toUpload.length > 1) {
      setError(`${failed} of ${toUpload.length} uploads failed`);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this document and its indices?')) return;
    try {
      await documents.delete(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Delete failed');
    }
  };

  const startRename = (doc: Document) => {
    setRenamingId(doc.id);
    setRenameValue(doc.title);
  };

  const cancelRename = () => {
    setRenamingId(null);
    setRenameValue('');
  };

  const handleRename = async (id: string) => {
    const trimmed = renameValue.trim();
    if (!trimmed) return;
    try {
      await documents.update(id, trimmed);
      setRenamingId(null);
      setRenameValue('');
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Rename failed');
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Documents</h1>
        <label className={`cursor-pointer bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded px-4 py-2 transition-colors ${uploading ? 'opacity-50 pointer-events-none' : ''}`}>
          {uploading ? 'Uploading...' : 'Upload PDFs'}
          <input ref={fileRef} type="file" accept=".pdf" multiple className="hidden" onChange={handleUpload} disabled={uploading} />
        </label>
      </div>

      {uploadProgress && <div className="bg-blue-900/40 border border-blue-700 text-blue-300 text-sm rounded px-3 py-2 mb-4">{uploadProgress}</div>}
      {error && <div className="bg-red-900/40 border border-red-700 text-red-300 text-sm rounded px-3 py-2 mb-4">{error}</div>}

      {loading ? (
        <p className="text-slate-400 text-sm">Loading...</p>
      ) : docs.length === 0 ? (
        <div className="border border-dashed border-slate-600/50 rounded-lg p-12 text-center">
          <p className="text-slate-400 mb-2">No documents yet</p>
          <p className="text-slate-500 text-sm">Upload a PDF reference manual to get started</p>
        </div>
      ) : (
        <div className="space-y-3">
          {docs.map(doc => (
            <div key={doc.id} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {renamingId === doc.id ? (
                      <input
                        type="text"
                        value={renameValue}
                        onChange={e => setRenameValue(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === 'Enter') handleRename(doc.id);
                          if (e.key === 'Escape') cancelRename();
                        }}
                        onBlur={() => handleRename(doc.id)}
                        autoFocus
                        className="flex-1 min-w-0 bg-slate-700/50 border border-slate-600/50 rounded px-2 py-0.5 text-sm text-white focus:outline-none focus:border-blue-500"
                      />
                    ) : (
                      <h3
                        className="text-sm font-medium truncate cursor-pointer hover:text-blue-400 transition-colors"
                        onClick={() => startRename(doc)}
                      >
                        {doc.title}
                      </h3>
                    )}
                    <StatusBadge status={doc.status} />
                  </div>
                  <div className="flex gap-4 text-xs text-slate-500">
                    <span>{formatBytes(doc.file_size_bytes)}</span>
                    {doc.page_count && <span>{doc.page_count} pages</span>}
                    {doc.chunk_count > 0 && <span>{doc.chunk_count} chunks</span>}
                    {doc.register_count > 0 && <span>{doc.register_count} registers</span>}
                  </div>
                  {doc.ingestion_error && (
                    <p className="text-xs text-red-400 mt-1">{doc.ingestion_error}</p>
                  )}
                  {(doc.status === 'pending' || doc.status === 'ingesting') && (
                    <ProgressBar docId={doc.id} />
                  )}
                </div>
                <button onClick={() => handleDelete(doc.id)}
                  className="text-slate-500 hover:text-red-400 text-sm ml-4 transition-colors">
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
