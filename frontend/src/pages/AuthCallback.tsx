import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useShooAuth } from '@shoojs/react';

export default function AuthCallback() {
  // SDK auto-handles the callback: exchanges code, persists identity, then
  // redirects back to the page that initiated sign-in. The originating page's
  // GoogleSignInButton picks up the stored identity and calls the backend.
  const { error } = useShooAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (error) {
      navigate(`/login?error=${encodeURIComponent(error)}`);
    }
  }, [error, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
      <div className="text-slate-400 text-sm">Signing in...</div>
    </div>
  );
}
