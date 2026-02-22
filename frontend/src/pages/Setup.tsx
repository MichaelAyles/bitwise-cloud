import { useState } from 'react';
import { Link } from 'react-router-dom';

const snippetStyle = 'bg-slate-900/60 border border-slate-700/50 rounded p-3 font-mono text-xs text-slate-300 overflow-x-auto whitespace-pre';

type Tab = 'mcp' | 'rest' | 'plugin';

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 text-xs font-medium rounded-t transition-colors ${
        active
          ? 'bg-slate-900/60 text-white border border-slate-700/50 border-b-transparent'
          : 'text-slate-500 hover:text-slate-300'
      }`}
    >
      {children}
    </button>
  );
}

export default function Setup() {
  const [tab, setTab] = useState<Tab>('mcp');
  const origin = window.location.origin;

  const mcpSnippet = `{
  "mcpServers": {
    "bitwise": {
      "type": "streamable-http",
      "url": "${origin}/mcp",
      "headers": {
        "X-API-Key": "bw_your_api_key"
      }
    }
  }
}`;

  const restSnippet = `curl -H "X-API-Key: bw_your_api_key" \\
  "${origin}/api/v1/search?q=UART+baud+rate"`;

  const pluginSnippet = `# Clone the repo and run with the local plugin
claude --plugin-dir ./plugins/bitwise-embedded-docs`;

  return (
    <div>
      <h1 className="text-xl font-semibold mb-2">Getting Started</h1>
      <p className="text-slate-400 text-sm mb-8">Set up Bitwise in three steps.</p>

      <div className="space-y-6">
        {/* Step 1 */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-6">
          <div className="flex items-start gap-4">
            <span className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-sm font-bold text-blue-400">1</span>
            <div>
              <h2 className="font-semibold text-lg mb-1">Upload a Datasheet</h2>
              <p className="text-slate-400 text-sm leading-relaxed mb-3">
                Upload a PDF reference manual or datasheet. Bitwise extracts text, tables, register definitions, and builds a searchable index.
              </p>
              <Link to="/documents" className="text-blue-400 hover:text-blue-300 text-sm font-medium transition-colors">
                Go to Documents &rarr;
              </Link>
            </div>
          </div>
        </div>

        {/* Step 2 */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-6">
          <div className="flex items-start gap-4">
            <span className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-sm font-bold text-blue-400">2</span>
            <div>
              <h2 className="font-semibold text-lg mb-1">Create an API Key</h2>
              <p className="text-slate-400 text-sm leading-relaxed mb-3">
                Generate an API key to authenticate MCP and REST API requests. Keys can be scoped to specific documents.
              </p>
              <Link to="/api-keys" className="text-blue-400 hover:text-blue-300 text-sm font-medium transition-colors">
                Go to API Keys &rarr;
              </Link>
            </div>
          </div>
        </div>

        {/* Step 3 */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-6">
          <div className="flex items-start gap-4">
            <span className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-sm font-bold text-blue-400">3</span>
            <div className="w-full min-w-0">
              <h2 className="font-semibold text-lg mb-1">Connect Your Tools</h2>
              <p className="text-slate-400 text-sm leading-relaxed mb-4">
                Use one of the methods below to connect to Bitwise. Replace the API key placeholder with your real key.
              </p>

              <div className="flex gap-1 mb-0">
                <TabButton active={tab === 'mcp'} onClick={() => setTab('mcp')}>MCP</TabButton>
                <TabButton active={tab === 'rest'} onClick={() => setTab('rest')}>REST API</TabButton>
                <TabButton active={tab === 'plugin'} onClick={() => setTab('plugin')}>Claude Code Plugin</TabButton>
              </div>

              {tab === 'mcp' && (
                <div>
                  <p className="text-xs text-slate-500 mb-2 mt-3">Add to <code className="text-slate-400">.claude/settings.json</code>:</p>
                  <pre className={snippetStyle}>{mcpSnippet}</pre>
                </div>
              )}

              {tab === 'rest' && (
                <div>
                  <p className="text-xs text-slate-500 mb-2 mt-3">Search via the REST API:</p>
                  <pre className={snippetStyle}>{restSnippet}</pre>
                </div>
              )}

              {tab === 'plugin' && (
                <div>
                  <p className="text-xs text-slate-500 mb-2 mt-3">Run Claude Code with the local plugin (for standalone use without the hosted server):</p>
                  <pre className={snippetStyle}>{pluginSnippet}</pre>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
