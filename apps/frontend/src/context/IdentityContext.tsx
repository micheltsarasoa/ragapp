import { createContext, useContext, useEffect, useState } from 'react';
import { postIdentity, type IdentityResponse } from '../api/auth';

const STORAGE_KEY = 'ragapp_access_key';

interface IdentityContextValue {
  identity: IdentityResponse | null;
  loading: boolean;
  // Exposed so consumers can render an error banner + retry button when the backend
  // is unreachable on startup instead of silently leaving the UI in a broken state.
  error: string | null;
  setAccessKey: (key: string) => void;
  retry: () => void;
}

const IdentityContext = createContext<IdentityContextValue | null>(null);

export function IdentityProvider({ children }: { children: React.ReactNode }) {
  const [identity, setIdentity] = useState<IdentityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function resolve(key?: string) {
    setLoading(true);
    setError(null);
    try {
      const result = await postIdentity(key);
      // Persist the canonical key returned by the server — it normalises casing and
      // generates a new random key when none is supplied.
      localStorage.setItem(STORAGE_KEY, result.access_key);
      setIdentity(result);
    } catch (err) {
      // Don't swallow the error: the UI would be stuck with identity=null and loading=false
      // and no way to tell the user what went wrong or offer a retry.
      setError(err instanceof Error ? err.message : 'Failed to authenticate');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) ?? undefined;
    resolve(stored);
  }, []);

  function setAccessKey(key: string) {
    resolve(key);
  }

  function retry() {
    const stored = localStorage.getItem(STORAGE_KEY) ?? undefined;
    resolve(stored);
  }

  return (
    <IdentityContext.Provider value={{ identity, loading, error, setAccessKey, retry }}>
      {children}
    </IdentityContext.Provider>
  );
}

export function useIdentityContext() {
  const ctx = useContext(IdentityContext);
  if (!ctx) throw new Error('useIdentityContext must be used inside IdentityProvider');
  return ctx;
}
