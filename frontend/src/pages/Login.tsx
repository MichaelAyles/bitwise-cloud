import { type FormEvent, useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { auth, ApiError } from '../api';
import { useAuth } from '../auth';
import GoogleSignInButton from '../components/GoogleSignInButton';

export default function Login() {
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(searchParams.get('error') || '');
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState(false);
  const [inviteOnly, setInviteOnly] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    auth.settings().then(s => setInviteOnly(s.registration_mode === 'invite_only'));
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
      const { access_token } = await auth.login(email, password);
      await login(access_token);
      navigate('/documents');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-white mb-1">BitWise Cloud</h1>
        <p className="text-zinc-400 mb-8 text-sm">Sign in to your account</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="bg-red-900/40 border border-red-700 text-red-300 text-sm rounded px-3 py-2">{error}</div>}
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Email</label>
            <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Password</label>
            <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
          </div>
          <button type="submit" disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded px-3 py-2 transition-colors">
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
        <GoogleSignInButton onToken={handleOAuthToken} disabled={oauthLoading} />
        {!inviteOnly && (
          <p className="text-zinc-500 text-sm mt-6 text-center">
            No account? <Link to="/register" className="text-blue-400 hover:underline">Register</Link>
          </p>
        )}
      </div>
    </div>
  );
}
