import { NavLink, Outlet, Navigate } from 'react-router-dom';
import { useAuth } from './auth';

const navItems = [
  { to: '/', label: 'Documents' },
  { to: '/search', label: 'Search' },
  { to: '/api-keys', label: 'API Keys' },
];

export default function Layout() {
  const { user, loading, logout } = useAuth();

  if (loading) {
    return <div className="min-h-screen bg-zinc-950 flex items-center justify-center text-zinc-400">Loading...</div>;
  }
  if (!user) return <Navigate to="/login" />;

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <header className="border-b border-zinc-800">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <span className="font-bold text-lg">BitWise</span>
            <nav className="flex gap-1">
              {navItems.map(n => (
                <NavLink key={n.to} to={n.to} end={n.to === '/'}
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded text-sm transition-colors ${isActive ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-white'}`
                  }>
                  {n.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-zinc-400">{user.email}</span>
            <button onClick={logout} className="text-sm text-zinc-500 hover:text-white transition-colors">Sign out</button>
          </div>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
