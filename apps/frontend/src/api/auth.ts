export interface IdentityResponse {
  user_id: string;
  access_key: string;
  is_new: boolean;
}

export async function postIdentity(access_key?: string): Promise<IdentityResponse> {
  const res = await fetch('/api/auth/identity', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(access_key ? { access_key } : {}),
  });
  if (!res.ok) throw new Error(`Identity request failed: ${res.status}`);
  return res.json();
}
