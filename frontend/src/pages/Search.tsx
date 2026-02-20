import { type FormEvent, useEffect, useState } from 'react';
import { search, documents, type SearchResult, type Document } from '../api';

export default function Search() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [docs, setDocs] = useState<Document[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);

  useEffect(() => {
    documents.list().then(d => setDocs(d.filter(doc => doc.status === 'ready')));
  }, []);

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setSearched(true);
    try {
      const res = await search.query(query, 10, selectedDocs.length > 0 ? selectedDocs : undefined);
      setResults(res.results);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const toggleDoc = (id: string) => {
    setSelectedDocs(prev => prev.includes(id) ? prev.filter(d => d !== id) : [...prev, id]);
  };

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6">Search Documents</h1>

      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-2">
          <input type="text" value={query} onChange={e => setQuery(e.target.value)}
            placeholder="Search for registers, peripherals, configuration..."
            className="flex-1 bg-slate-800/50 border border-slate-600/50 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
          <button type="submit" disabled={searching}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded px-4 py-2 transition-colors whitespace-nowrap">
            {searching ? 'Searching...' : 'Search'}
          </button>
        </div>

        {docs.length > 1 && (
          <div className="flex flex-wrap gap-2 mt-3">
            <span className="text-xs text-slate-500 py-1">Filter:</span>
            {docs.map(doc => (
              <button key={doc.id} type="button" onClick={() => toggleDoc(doc.id)}
                className={`text-xs px-2 py-1 rounded border transition-colors ${
                  selectedDocs.includes(doc.id)
                    ? 'bg-blue-900/50 border-blue-700 text-blue-300'
                    : 'bg-slate-800/50 border-slate-600/50 text-slate-400 hover:border-slate-400'
                }`}>
                {doc.title.length > 40 ? doc.title.slice(0, 40) + '...' : doc.title}
              </button>
            ))}
          </div>
        )}
      </form>

      {searching && <p className="text-slate-400 text-sm">Searching...</p>}

      {!searching && searched && results.length === 0 && (
        <p className="text-slate-400 text-sm">No results found for "{query}"</p>
      )}

      {results.length > 0 && (
        <div className="space-y-4">
          {results.map((r, i) => (
            <div key={i} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <span className="text-xs text-slate-500">#{i + 1}</span>
                  <span className="text-xs text-blue-400 ml-2">{r.document_title}</span>
                  {r.section && <span className="text-xs text-slate-500 ml-2">&gt; {r.section}</span>}
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  {r.page_number && <span>p. {r.page_number}</span>}
                  <span>score: {r.score.toFixed(2)}</span>
                </div>
              </div>
              <pre className="text-sm text-slate-300 whitespace-pre-wrap font-mono leading-relaxed max-h-64 overflow-y-auto">
                {r.text.replace(/^\[.*?\]\n?/, '')}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
