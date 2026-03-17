/* TypeScript-интерфейсы для Audit API — зеркало Pydantic-моделей из schemas.py */

export interface CheckResultOut {
  gost_id: string;
  gost_section: string;
  wcag_ref: string;
  title: string;
  description: string;
  verdict: 'PASS' | 'FAIL' | 'UNCERTAIN';
  source: string;
  reason: string;
  details: Record<string, unknown>;
  category: string;
}

export interface AuditSummary {
  total: number;
  passed: number;
  failed: number;
  uncertain: number;
  score_pct: number;
}

export interface PageReport {
  url: string;
  timestamp: string;
  summary: AuditSummary;
  main_results: CheckResultOut[];
  special_results: CheckResultOut[] | null;
}

export type AuditPhase = 'idle' | 'running' | 'completed' | 'error';

export interface AuditState {
  phase: AuditPhase;
  taskId: string | null;
  currentUrl: string | null;
  currentCheck: string | null;
  checksDone: number;
  checksTotal: number;
  liveResults: CheckResultOut[];
  pages: PageReport[];
  errorMessage: string | null;
}

export const CATEGORY_LABELS: Record<string, string> = {
  perceivable: 'Воспринимаемость',
  operable: 'Управляемость',
  understandable: 'Понятность',
  robust: 'Надёжность',
  gost_specific: 'Требования ГОСТ и Приказа №953',
};

export const CATEGORY_ORDER = [
  'perceivable',
  'operable',
  'understandable',
  'robust',
  'gost_specific',
];
