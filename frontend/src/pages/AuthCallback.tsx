import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useShooAuth } from '@shoojs/react';
import { auth } from '../api';
import { useAuth } from '../auth';

export default function AuthCallback() {
  const { identity, loading } = useShooAuth();
  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (loading || !identity?.token) return;

    auth.oauthShoo(identity.token).then(async ({ access_token }) => {
      await login(access_token);
      navigate('/');
    }).catch(() => {
      navigate('/login');
    });
  }, [loading, identity, login, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 px-4">
      <div className="text-zinc-400 text-sm">Signing in...</div>
    </div>
  );
}
