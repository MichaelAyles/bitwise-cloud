import { type FormEvent, useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { auth, ApiError } from '../api';
import { useAuth } from '../auth';
import GoogleSignInButton from '../components/GoogleSignInButton';

export default function Register() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState(false);
  const [checkingMode, setCheckingMode] = useState(true);
  const [inviteOnly, setInviteOnly] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    auth.settings().then(s => {
      setInviteOnly(s.registration_mode === 'invite_only');
    }).finally(() => setCheckingMode(false));
  }, []);

  const handleOAuthToken = useCallback(async (idToken: string) => {
    setOauthLoading(true);
    setError('');
    try {
      const { access_token } = await auth.oauthShoo(idToken);
      await login(access_token);
      navigate('/documents');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Google sign-in failed');
    } finally {
      setOauthLoading(false);
    }
  }, [login, navigate]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { access_token } = await auth.register(email, password, token || undefined);
      await login(access_token);
      navigate('/documents');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  if (checkingMode) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
        <div className="text-slate-400 text-sm">Loading...</div>
      </div>
    );
  }

  // No token and invite-only mode — show blocked message but still allow Google sign-in
  if (inviteOnly && !token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
        <div className="w-full max-w-sm text-center">
          <h1 className="text-2xl font-bold text-white mb-1">Bitwise</h1>
          <p className="text-slate-400 mb-6 text-sm">Registration is invite-only</p>
          <p className="text-slate-500 text-sm mb-6">You need an invitation link to create an account, or sign in with Google.</p>
          {error && <div className="bg-red-900/40 border border-red-700 text-red-300 text-sm rounded px-3 py-2 mb-4">{error}</div>}
          <GoogleSignInButton onToken={handleOAuthToken} disabled={oauthLoading} />
          <p className="text-slate-500 text-sm mt-6">
            <Link to="/login" className="text-blue-400 hover:underline">Back to sign in</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-white mb-1">Bitwise</h1>
        <p className="text-slate-400 mb-8 text-sm">
          {token ? 'You\'ve been invited! Create your account.' : 'Create your account'}
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="bg-red-900/40 border border-red-700 text-red-300 text-sm rounded px-3 py-2">{error}</div>}
          <div>
            <label className="block text-sm text-slate-400 mb-1">Email</label>
            <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
              className="w-full bg-slate-800/50 border border-slate-600/50 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Password</label>
            <input type="password" required minLength={8} value={password} onChange={e => setPassword(e.target.value)}
              className="w-full bg-slate-800/50 border border-slate-600/50 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
          </div>
          <button type="submit" disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded px-3 py-2 transition-colors">
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>
        <GoogleSignInButton onToken={handleOAuthToken} disabled={oauthLoading} />
        <p className="text-slate-500 text-sm mt-6 text-center">
          Have an account? <Link to="/login" className="text-blue-400 hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
