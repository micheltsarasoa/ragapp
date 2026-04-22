type StreamFrame =
  | { type: 'token'; content: string }
  | { type: 'done'; sources: string[]; scores: number[] }
  | { type: 'error'; content: string };

export async function* streamQuery(
  question: string,
  user_id: string,
): AsyncGenerator<{ token?: string; sources?: string[]; error?: string }> {
  const url = `/api/stream_query?question=${encodeURIComponent(question)}&user_id=${encodeURIComponent(user_id)}`;
  const res = await fetch(url);
  if (!res.ok) {
    yield { error: `Request failed: ${res.status}` };
    return;
  }
  if (!res.body) {
    yield { error: 'No response body' };
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    // Keep the last (possibly incomplete) fragment for the next iteration
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const frame: StreamFrame = JSON.parse(trimmed);
        if (frame.type === 'token') {
          yield { token: frame.content };
        } else if (frame.type === 'done') {
          yield { sources: frame.sources };
          return;
        } else if (frame.type === 'error') {
          yield { error: frame.content };
          return;
        }
      } catch {
        // malformed JSON line — skip
      }
    }
  }

  // Flush any remaining buffered data after the stream closes
  if (buffer.trim()) {
    try {
      const frame: StreamFrame = JSON.parse(buffer.trim());
      if (frame.type === 'done') {
        yield { sources: frame.sources };
      }
    } catch {
      // ignore
    }
  }
}
