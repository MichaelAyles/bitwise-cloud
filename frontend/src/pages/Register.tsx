import { type FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useShooAuth } from '@shoojs/react';
import { auth, ApiError } from '../api';
import { useAuth } from '../auth';

function GoogleSignInButton({ onToken, disabled }: { onToken: (token: string) => void; disabled: boolean }) {
  const { identity, loading: shooLoading, signIn } = useShooAuth();
  const fired = useRef(false);

  useEffect(() => {
    if (!shooLoading && identity?.token && !fired.current) {
      fired.current = true;
      onToken(identity.token);
    }
  }, [shooLoading, identity, onToken]);

  return (
    <>
      <div className="relative my-6">
        <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-zinc-800" /></div>
        <div className="relative flex justify-center text-xs"><span className="bg-zinc-950 px-2 text-zinc-500">or</span></div>
      </div>
      <button
        type="button"
        onClick={() => signIn()}
        disabled={disabled || shooLoading}
        className="w-full flex items-center justify-center gap-2 bg-zinc-900 border border-zinc-700 hover:border-zinc-500 disabled:opacity-50 text-white text-sm font-medium rounded px-3 py-2 transition-colors"
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
        {disabled ? 'Signing in...' : 'Sign in with Google'}
      </button>
    </>
  );
}

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
      navigate('/');
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
      navigate('/');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  if (checkingMode) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950 px-4">
        <div className="text-zinc-400 text-sm">Loading...</div>
      </div>
    );
  }

  // No token and invite-only mode — show blocked message but still allow Google sign-in
  if (inviteOnly && !token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950 px-4">
        <div className="w-full max-w-sm text-center">
          <h1 className="text-2xl font-bold text-white mb-1">BitWise Cloud</h1>
          <p className="text-zinc-400 mb-6 text-sm">Registration is invite-only</p>
          <p className="text-zinc-500 text-sm mb-6">You need an invitation link to create an account, or sign in with Google.</p>
          {error && <div className="bg-red-900/40 border border-red-700 text-red-300 text-sm rounded px-3 py-2 mb-4">{error}</div>}
          <GoogleSignInButton onToken={handleOAuthToken} disabled={oauthLoading} />
          <p className="text-zinc-500 text-sm mt-6">
            <Link to="/login" className="text-blue-400 hover:underline">Back to sign in</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-white mb-1">BitWise Cloud</h1>
        <p className="text-zinc-400 mb-8 text-sm">
          {token ? 'You\'ve been invited! Create your account.' : 'Create your account'}
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="bg-red-900/40 border border-red-700 text-red-300 text-sm rounded px-3 py-2">{error}</div>}
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Email</label>
            <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Password</label>
            <input type="password" required minLength={8} value={password} onChange={e => setPassword(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
          </div>
          <button type="submit" disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded px-3 py-2 transition-colors">
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>
        <GoogleSignInButton onToken={handleOAuthToken} disabled={oauthLoading} />
        <p className="text-zinc-500 text-sm mt-6 text-center">
          Have an account? <Link to="/login" className="text-blue-400 hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
