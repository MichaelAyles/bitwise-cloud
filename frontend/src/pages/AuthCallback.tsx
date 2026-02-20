import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useShooAuth } from '@shoojs/react';
import { auth } from '../api';
import { useAuth } from '../auth';

export default function AuthCallback() {
  const { identity, loading, clearIdentity } = useShooAuth();
  const { login } = useAuth();
  const navigate = useNavigate();
  const handled = useRef(false);

  useEffect(() => {
    if (loading || !identity?.token || handled.current) return;
    handled.current = true;

    auth.oauthShoo(identity.token).then(async ({ access_token }) => {
      clearIdentity();
      await login(access_token);
      navigate('/documents');
    }).catch(() => {
      clearIdentity();
      navigate('/login');
    });
  }, [loading, identity, login, navigate, clearIdentity]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 px-4">
      <div className="text-zinc-400 text-sm">Signing in...</div>
    </div>
  );
}
