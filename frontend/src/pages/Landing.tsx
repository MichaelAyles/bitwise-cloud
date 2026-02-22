import { Link } from 'react-router-dom';

function BlueprintGrid() {
  return (
    <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern id="grid-sm" width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(148,163,184,0.06)" strokeWidth="0.5" />
        </pattern>
        <pattern id="grid-lg" width="100" height="100" patternUnits="userSpaceOnUse">
          <rect width="100" height="100" fill="url(#grid-sm)" />
          <path d="M 100 0 L 0 0 0 100" fill="none" stroke="rgba(148,163,184,0.12)" strokeWidth="0.5" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid-lg)" />
    </svg>
  );
}

function IsometricDiagram() {
  return (
    <svg viewBox="0 0 520 420" className="w-full max-w-lg" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* PDF layer (top) */}
      <g transform="translate(120, 10)">
        <path d="M0,50 L130,0 L310,60 L180,110 Z" fill="rgba(51,65,85,0.6)" stroke="rgba(148,163,184,0.4)" strokeWidth="1" />
        <path d="M0,50 L0,70 L180,130 L180,110 Z" fill="rgba(30,41,59,0.6)" stroke="rgba(148,163,184,0.4)" strokeWidth="1" />
        <path d="M180,110 L180,130 L310,80 L310,60 Z" fill="rgba(41,55,75,0.6)" stroke="rgba(148,163,184,0.4)" strokeWidth="1" />
        {/* Document lines */}
        <line x1="40" y1="55" x2="140" y2="30" stroke="rgba(148,163,184,0.3)" strokeWidth="0.5" />
        <line x1="40" y1="65" x2="140" y2="40" stroke="rgba(148,163,184,0.3)" strokeWidth="0.5" />
        <line x1="40" y1="75" x2="140" y2="50" stroke="rgba(148,163,184,0.3)" strokeWidth="0.5" />
        <text x="130" y="15" fill="rgba(148,163,184,0.8)" fontSize="11" fontFamily="monospace">PDF</text>
      </g>

      {/* Labels - right side */}
      <line x1="430" y1="65" x2="480" y2="45" stroke="rgba(148,163,184,0.4)" strokeWidth="0.5" />
      <text x="400" y="35" fill="rgba(203,213,225,0.8)" fontSize="9" fontFamily="sans-serif" textAnchor="middle">
        <tspan x="480" dy="0">Structured</tspan>
        <tspan x="480" dy="12">Data Layer</tspan>
      </text>

      {/* TEXT label - left */}
      <line x1="90" y1="120" x2="130" y2="120" stroke="rgba(148,163,184,0.4)" strokeWidth="0.5" />
      <text x="80" y="123" fill="rgba(203,213,225,0.8)" fontSize="9" fontFamily="monospace" textAnchor="end">TEXT</text>

      {/* Semantic search layer (middle) */}
      <g transform="translate(120, 120)">
        <path d="M0,50 L130,0 L310,60 L180,110 Z" fill="rgba(51,65,85,0.5)" stroke="rgba(148,163,184,0.35)" strokeWidth="1" />
        <path d="M0,50 L0,70 L180,130 L180,110 Z" fill="rgba(30,41,59,0.5)" stroke="rgba(148,163,184,0.35)" strokeWidth="1" />
        <path d="M180,110 L180,130 L310,80 L310,60 Z" fill="rgba(41,55,75,0.5)" stroke="rgba(148,163,184,0.35)" strokeWidth="1" />
        {/* Grid pattern inside */}
        <line x1="50" y1="55" x2="50" y2="95" stroke="rgba(148,163,184,0.15)" strokeWidth="0.5" />
        <line x1="90" y1="40" x2="90" y2="95" stroke="rgba(148,163,184,0.15)" strokeWidth="0.5" />
        <line x1="130" y1="30" x2="130" y2="90" stroke="rgba(148,163,184,0.15)" strokeWidth="0.5" />
        <line x1="170" y1="45" x2="170" y2="100" stroke="rgba(148,163,184,0.15)" strokeWidth="0.5" />
        <line x1="30" y1="65" x2="200" y2="65" stroke="rgba(148,163,184,0.15)" strokeWidth="0.5" />
        <line x1="35" y1="80" x2="195" y2="80" stroke="rgba(148,163,184,0.15)" strokeWidth="0.5" />
      </g>

      <line x1="435" y1="175" x2="490" y2="155" stroke="rgba(148,163,184,0.4)" strokeWidth="0.5" />
      <text x="490" y="150" fill="rgba(203,213,225,0.8)" fontSize="9" fontFamily="sans-serif">
        <tspan x="490" dy="0">Semantic</tspan>
        <tspan x="490" dy="12">Search Index</tspan>
      </text>

      {/* TABLES label - left */}
      <line x1="75" y1="230" x2="130" y2="230" stroke="rgba(148,163,184,0.4)" strokeWidth="0.5" />
      <text x="65" y="233" fill="rgba(203,213,225,0.8)" fontSize="9" fontFamily="monospace" textAnchor="end">TABLES</text>

      {/* STRUCTURED DATA LAYER label */}
      <text x="100" y="290" fill="rgba(203,213,225,0.7)" fontSize="8" fontFamily="sans-serif" textAnchor="end">
        <tspan x="110" dy="0">STRUCTURED</tspan>
        <tspan x="110" dy="11">DATA LAYER</tspan>
      </text>

      {/* Bottom layer */}
      <g transform="translate(120, 240)">
        <path d="M0,50 L130,0 L310,60 L180,110 Z" fill="rgba(51,65,85,0.4)" stroke="rgba(148,163,184,0.3)" strokeWidth="1" />
        <path d="M0,50 L0,70 L180,130 L180,110 Z" fill="rgba(30,41,59,0.4)" stroke="rgba(148,163,184,0.3)" strokeWidth="1" />
        <path d="M180,110 L180,130 L310,80 L310,60 Z" fill="rgba(41,55,75,0.4)" stroke="rgba(148,163,184,0.3)" strokeWidth="1" />
        {/* Table grid */}
        <rect x="50" y="40" width="80" height="50" rx="2" fill="none" stroke="rgba(148,163,184,0.2)" strokeWidth="0.5" />
        <line x1="50" y1="52" x2="130" y2="52" stroke="rgba(148,163,184,0.15)" strokeWidth="0.5" />
        <line x1="50" y1="64" x2="130" y2="64" stroke="rgba(148,163,184,0.15)" strokeWidth="0.5" />
        <line x1="50" y1="76" x2="130" y2="76" stroke="rgba(148,163,184,0.15)" strokeWidth="0.5" />
        <line x1="77" y1="40" x2="77" y2="90" stroke="rgba(148,163,184,0.15)" strokeWidth="0.5" />
        <line x1="104" y1="40" x2="104" y2="90" stroke="rgba(148,163,184,0.15)" strokeWidth="0.5" />
      </g>

      <text x="120" y="370" fill="rgba(203,213,225,0.7)" fontSize="8" fontFamily="sans-serif">
        <tspan x="130" dy="0">Structured</tspan>
        <tspan x="130" dy="11">Data Layer</tspan>
      </text>

      <line x1="435" y1="325" x2="480" y2="310" stroke="rgba(148,163,184,0.4)" strokeWidth="0.5" />
      <text x="480" y="305" fill="rgba(203,213,225,0.8)" fontSize="9" fontFamily="sans-serif">BITFIELDS</text>

      {/* Vertical connection lines */}
      <line x1="270" y1="85" x2="270" y2="125" stroke="rgba(148,163,184,0.2)" strokeWidth="0.5" strokeDasharray="3,3" />
      <line x1="270" y1="200" x2="270" y2="240" stroke="rgba(148,163,184,0.2)" strokeWidth="0.5" strokeDasharray="3,3" />
    </svg>
  );
}

function PipelineStrip() {
  const steps = ['UPLOAD', 'EXTRACT', 'INDEX', 'SEARCH', 'INTEGRATE'];
  return (
    <div className="flex items-center justify-center gap-2 sm:gap-4 flex-wrap">
      {steps.map((step, i) => (
        <div key={step} className="flex items-center gap-2 sm:gap-4">
          <span className="px-3 sm:px-5 py-2 border border-slate-500/30 rounded text-xs sm:text-sm font-mono text-slate-300 tracking-wider">
            {step}
          </span>
          {i < steps.length - 1 && (
            <svg className="w-5 h-5 text-slate-500/50 shrink-0" viewBox="0 0 20 20" fill="none">
              <path d="M5 10h10M12 6l4 4-4 4" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          )}
        </div>
      ))}
    </div>
  );
}

export default function Landing() {
  return (
    <div className="min-h-screen bg-slate-900 text-white relative overflow-hidden">
      <BlueprintGrid />

      {/* Header */}
      <header className="relative z-10 border-b border-slate-700/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="10" />
              <path d="M8 12l2 2 4-4" />
            </svg>
            <span className="font-bold text-lg">Bitwise</span>
          </div>
          <nav className="flex items-center gap-4 sm:gap-6 text-sm">
            <a href="#features" className="text-slate-400 hover:text-white transition-colors hidden sm:inline">Docs</a>
            <a href="#pipeline" className="text-slate-400 hover:text-white transition-colors hidden sm:inline">Pricing</a>
            <Link to="/login" className="text-slate-400 hover:text-white transition-colors">Sign In</Link>
            <Link to="/register" className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded px-4 py-1.5 transition-colors">
              Get Started
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <main className="relative z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight tracking-tight">
                Engineered<br />for engineers.
              </h1>
              <p className="mt-6 text-slate-400 text-lg max-w-md leading-relaxed">
                Structured search made easy, designed and engineered for engineers.
              </p>
              <div className="mt-8 flex gap-3">
                <Link to="/register"
                  className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded px-5 py-2.5 transition-colors">
                  Explore Features
                </Link>
                <a href="#pipeline"
                  className="bg-transparent border border-slate-500/40 hover:border-slate-400 text-white text-sm font-medium rounded px-5 py-2.5 transition-colors">
                  Documentation
                </a>
              </div>
            </div>
            <div className="hidden lg:flex justify-center">
              <IsometricDiagram />
            </div>
          </div>
        </div>

        {/* Pipeline strip */}
        <div id="pipeline" className="relative z-10 border-t border-b border-slate-700/50 bg-slate-800/30 backdrop-blur-sm">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
            <PipelineStrip />
          </div>
        </div>

        {/* Features section */}
        <div id="features" className="max-w-6xl mx-auto px-4 sm:px-6 py-20">
          <div className="grid sm:grid-cols-3 gap-8">
            <div className="border border-slate-700/50 rounded-lg p-6 bg-slate-800/20">
              <div className="text-blue-400 text-2xl mb-3 font-mono">&gt;_</div>
              <h3 className="font-semibold text-lg mb-2">MCP Integration</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                Connect directly to Claude Code and other AI tools via the Model Context Protocol.
              </p>
              <pre className="mt-3 bg-slate-900/60 border border-slate-700/50 rounded p-3 font-mono text-xs text-slate-400 overflow-x-auto whitespace-pre">{`"url": "https://your-host/mcp"
"api_key": "bw_..."`}</pre>
            </div>
            <div className="border border-slate-700/50 rounded-lg p-6 bg-slate-800/20">
              <div className="text-blue-400 text-2xl mb-3 font-mono">#[]</div>
              <h3 className="font-semibold text-lg mb-2">Hybrid Search</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                Semantic + keyword search with automatic table extraction from datasheets and PDFs.
              </p>
              <pre className="mt-3 bg-slate-900/60 border border-slate-700/50 rounded p-3 font-mono text-xs text-slate-400 overflow-x-auto whitespace-pre">{`search_docs("UART baud rate register")`}</pre>
            </div>
            <div className="border border-slate-700/50 rounded-lg p-6 bg-slate-800/20">
              <div className="text-blue-400 text-2xl mb-3 font-mono">{ }</div>
              <h3 className="font-semibold text-lg mb-2">REST API</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                API keys with per-document scoping. Integrate search into your own tools and workflows.
              </p>
              <pre className="mt-3 bg-slate-900/60 border border-slate-700/50 rounded p-3 font-mono text-xs text-slate-400 overflow-x-auto whitespace-pre">{`curl -H "X-API-Key: bw_..." \\
  /api/v1/search?q=SPI+clock`}</pre>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-700/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex justify-between text-xs text-slate-600">
          <span>Bitwise</span>
          <span>&copy; 2026</span>
        </div>
      </footer>
    </div>
  );
}
