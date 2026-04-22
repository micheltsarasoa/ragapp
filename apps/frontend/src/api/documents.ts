export interface Document {
  source_id: string;
  filename: string;
  visibility: 'public' | 'private';
  uploaded_at: string;
}

export async function listDocuments(user_id: string): Promise<Document[]> {
  const res = await fetch(`/api/documents?user_id=${encodeURIComponent(user_id)}`);
  if (!res.ok) throw new Error(`Failed to list documents: ${res.status}`);
  return res.json();
}

export async function uploadDocument(
  file: File,
  visibility: 'public' | 'private',
  user_id: string,
): Promise<{ source_id: string; status: string }> {
  const form = new FormData();
  form.append('file', file);
  form.append('visibility', visibility);
  form.append('user_id', user_id);
  const res = await fetch('/api/documents/upload', { method: 'POST', body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function updateVisibility(
  source_id: string,
  visibility: 'public' | 'private',
  user_id: string,
): Promise<void> {
  const res = await fetch(`/api/documents/${encodeURIComponent(source_id)}/visibility`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ visibility, user_id }),
  });
  if (!res.ok) throw new Error(`Visibility update failed: ${res.status}`);
}

export async function deleteDocument(source_id: string, user_id: string): Promise<void> {
  const res = await fetch(
    `/api/documents/${encodeURIComponent(source_id)}?user_id=${encodeURIComponent(user_id)}`,
    { method: 'DELETE' },
  );
  if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
}
