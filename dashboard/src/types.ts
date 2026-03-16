export interface CheckResult {
  gost_id: string
  gost_section: string
  wcag_ref: string
  title: string
  verdict: 'PASS' | 'FAIL' | 'UNCERTAIN'
  source: string
  reason: string
  details?: Record<string, unknown>
}

export interface SiteSummary {
  total: number
  pass: number
  fail: number
  uncertain: number
}

export interface SiteReport {
  id: string
  name: string
  url: string
  category: string
  is_reference: boolean
  summary: SiteSummary
  checks: CheckResult[]
}

export interface ReportData {
  timestamp: string
  total_sites: number
  checks_per_site: number
  is_demo: boolean
  avg_pct: number
  sites: SiteReport[]
}
