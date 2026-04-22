export interface LlmConfig {
  model: string;
  base_url: string;
  api_key_set: boolean;
}

export async function getLlmConfig(): Promise<LlmConfig> {
  const res = await fetch('/api/llm_config');
  if (!res.ok) throw new Error(`Failed to fetch LLM config: ${res.status}`);
  return res.json();
}

export async function postLlmConfig(patch: {
  model?: string;
  base_url?: string;
  api_key?: string;
}): Promise<void> {
  const res = await fetch('/api/llm_config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error(`Failed to update LLM config: ${res.status}`);
}
