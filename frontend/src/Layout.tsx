import { NavLink, Outlet, Navigate } from 'react-router-dom';
import { useAuth } from './auth';

const baseNavItems = [
  { to: '/setup', label: 'Setup' },
  { to: '/documents', label: 'Documents' },
  { to: '/search', label: 'Search' },
  { to: '/api-keys', label: 'API Keys' },
];

export default function Layout() {
  const { user, loading, logout } = useAuth();

  if (loading) {
    return <div className="min-h-screen bg-slate-900 flex items-center justify-center text-slate-400">Loading...</div>;
  }
  if (!user) return <Navigate to="/" />;

  const navItems = user.is_admin
    ? [...baseNavItems, { to: '/admin', label: 'Admin' }]
    : baseNavItems;

  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col relative overflow-hidden">
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
      <header className="relative z-10 border-b border-slate-700/50">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <span className="font-bold text-lg">Bitwise</span>
            <nav className="flex gap-1">
              {navItems.map(n => (
                <NavLink key={n.to} to={n.to} end={n.to === '/documents'}
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded text-sm transition-colors ${isActive ? 'bg-slate-700/50 text-white' : 'text-slate-400 hover:text-white'}`
                  }>
                  {n.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-400">{user.email}</span>
            <button onClick={logout} className="text-sm text-slate-500 hover:text-white transition-colors">Sign out</button>
          </div>
        </div>
      </header>
      <main className="relative z-10 max-w-6xl mx-auto px-4 py-8 flex-1 w-full">
        <Outlet />
      </main>
      <footer className="relative z-10 border-t border-slate-700/50 mt-auto">
        <div className="max-w-6xl mx-auto px-4 py-3 flex justify-between text-xs text-slate-500">
          <span>Bitwise</span>
          <span>{__GIT_SHA__ !== 'dev' ? __GIT_SHA__.slice(0, 7) : 'dev'}</span>
        </div>
      </footer>
    </div>
  );
}
