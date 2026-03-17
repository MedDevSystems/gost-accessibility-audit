/* API-клиент + EventSource для SSE-стриминга результатов аудита */

const BASE = '/api';

export async function startAudit(
  urls: string[],
  includeSpecial: boolean,
): Promise<string> {
  const res = await fetch(`${BASE}/audit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ urls, include_special: includeSpecial }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  const data = await res.json();
  return data.task_id;
}

export type SSEHandler = (eventType: string, data: Record<string, unknown>) => void;

export function subscribeToAudit(
  taskId: string,
  onEvent: SSEHandler,
  onError: (err: Event) => void,
): EventSource {
  const es = new EventSource(`${BASE}/audit/${taskId}/stream`);

  const eventTypes = [
    'status',
    'check_result',
    'page_start',
    'page_complete',
    'complete',
    'error',
    'heartbeat',
  ];

  for (const type of eventTypes) {
    es.addEventListener(type, (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        onEvent(type, data);
      } catch {
        onEvent(type, {});
      }
    });
  }

  es.onerror = onError;
  return es;
}
