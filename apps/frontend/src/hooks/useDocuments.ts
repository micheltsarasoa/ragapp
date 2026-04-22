import { useState, useEffect, useCallback } from 'react';
import {
  listDocuments,
  updateVisibility as apiUpdateVisibility,
  deleteDocument as apiDeleteDocument,
  type Document,
} from '../api/documents';

interface UseDocumentsResult {
  documents: Document[];
  loading: boolean;
  error: string | null;
  reload: () => void;
  updateVisibility: (source_id: string, visibility: 'public' | 'private') => Promise<void>;
  deleteDocument: (source_id: string) => Promise<void>;
}

export function useDocuments(user_id: string | null): UseDocumentsResult {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const reload = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    if (!user_id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    listDocuments(user_id)
      .then((docs) => {
        if (!cancelled) setDocuments(docs);
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
  }, [user_id, tick]);

  const updateVisibility = useCallback(
    async (source_id: string, visibility: 'public' | 'private') => {
      if (!user_id) return;
      await apiUpdateVisibility(source_id, visibility, user_id);
      setDocuments((prev) =>
        prev.map((d) => (d.source_id === source_id ? { ...d, visibility } : d)),
      );
    },
    [user_id],
  );

  const deleteDocument = useCallback(
    async (source_id: string) => {
      if (!user_id) return;
      await apiDeleteDocument(source_id, user_id);
      setDocuments((prev) => prev.filter((d) => d.source_id !== source_id));
    },
    [user_id],
  );

  return { documents, loading, error, reload, updateVisibility, deleteDocument };
}
