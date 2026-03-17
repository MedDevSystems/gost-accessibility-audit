/* Hook: стейт-машина аудита (idle -> running -> completed | error) */

import { useCallback, useRef, useState } from 'react';
import { startAudit, subscribeToAudit } from '../api';
import type { AuditState, CheckResultOut, PageReport } from '../types';

const INITIAL_STATE: AuditState = {
  phase: 'idle',
  taskId: null,
  currentUrl: null,
  currentCheck: null,
  checksDone: 0,
  checksTotal: 0,
  liveResults: [],
  pages: [],
  errorMessage: null,
};

export function useAudit() {
  const [state, setState] = useState<AuditState>(INITIAL_STATE);
  const esRef = useRef<EventSource | null>(null);

  const launch = useCallback(async (urls: string[], includeSpecial: boolean) => {
    // Закрываем предыдущее соединение
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    setState({
      ...INITIAL_STATE,
      phase: 'running',
    });

    try {
      const taskId = await startAudit(urls, includeSpecial);

      setState(prev => ({ ...prev, taskId }));

      const es = subscribeToAudit(
        taskId,
        (eventType, data) => {
          switch (eventType) {
            case 'page_start':
              setState(prev => ({
                ...prev,
                currentUrl: data.url as string,
                currentCheck: 'Загрузка страницы...',
              }));
              break;

            case 'check_result': {
              const result = data.result as CheckResultOut;
              const pass = data.pass as string;
              setState(prev => ({
                ...prev,
                currentCheck: pass === 'special' ? `[спец] ${result.title}` : result.title,
                checksDone: prev.checksDone + 1,
                checksTotal: data.checks_total as number,
                liveResults: [...prev.liveResults, result],
              }));
              break;
            }

            case 'page_complete': {
              const page = data as unknown as PageReport;
              setState(prev => ({
                ...prev,
                pages: [...prev.pages, page],
                liveResults: [],
              }));
              break;
            }

            case 'complete':
              setState(prev => ({
                ...prev,
                phase: 'completed',
                currentUrl: null,
                currentCheck: null,
              }));
              es.close();
              esRef.current = null;
              break;

            case 'error':
              setState(prev => ({
                ...prev,
                phase: 'error',
                errorMessage: data.error as string,
              }));
              es.close();
              esRef.current = null;
              break;

            case 'heartbeat':
              break;
          }
        },
        (err) => {
          // EventSource переподключается автоматически — onerror не значит фатальную ошибку.
          // Только если readyState === CLOSED (2) — соединение закрыто навсегда.
          const target = err.target as EventSource | null;
          if (target && target.readyState === EventSource.CLOSED) {
            setState(prev => {
              if (prev.phase === 'running') {
                return { ...prev, phase: 'error', errorMessage: 'SSE-соединение закрыто' };
              }
              return prev;
            });
          }
        },
      );

      esRef.current = es;
    } catch (err) {
      setState(prev => ({
        ...prev,
        phase: 'error',
        errorMessage: err instanceof Error ? err.message : String(err),
      }));
    }
  }, []);

  const reset = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    setState(INITIAL_STATE);
  }, []);

  return { state, launch, reset };
}
