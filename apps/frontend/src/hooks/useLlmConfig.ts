import { useState, useEffect, useCallback } from 'react';
import { getLlmConfig, postLlmConfig, type LlmConfig } from '../api/llmConfig';

interface UseLlmConfigResult {
  config: LlmConfig | null;
  loading: boolean;
  error: string | null;
  save: (patch: { model?: string; base_url?: string; api_key?: string }) => Promise<void>;
}

export function useLlmConfig(): UseLlmConfigResult {
  const [config, setConfig] = useState<LlmConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getLlmConfig()
      .then((c) => {
        if (!cancelled) setConfig(c);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const save = useCallback(
    async (patch: { model?: string; base_url?: string; api_key?: string }) => {
      await postLlmConfig(patch);
      // Refetch from the server instead of optimistically merging locally.
      // The backend normalises values (e.g. strips whitespace, derives api_key_set)
      // and is the single source of truth for what was actually persisted.
      const fresh = await getLlmConfig();
      setConfig(fresh);
    },
    [],
  );

  return { config, loading, error, save };
}
