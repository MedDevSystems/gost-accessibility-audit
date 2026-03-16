import reportData from './data/report.json'
import type { ReportData, SiteReport } from './types'
import { FontControls } from './components/FontControls'
import { Stats } from './components/Stats'
import { CategorySection } from './components/CategorySection'
import { Reference } from './components/Reference'

const CATEGORY_ORDER = [
  'reference',
  'president',
  'legislative',
  'judicial',
  'government',
  'ministry',
  'service',
  'service_federal',
  'agency',
  'corporation',
  'fund',
  'portal',
  'district',
  'regional',
  'specialized',
] as const

const CATEGORY_NAMES: Record<string, string> = {
  reference: 'Эталон',
  president: 'Глава государства',
  legislative: 'Законодательная власть',
  judicial: 'Судебная власть',
  government: 'Правительство',
  ministry: 'Министерства',
  service: 'Госуслуги',
  service_federal: 'Федеральные службы',
  agency: 'Федеральные агентства',
  corporation: 'Государственные корпорации',
  fund: 'Внебюджетные фонды',
  portal: 'Порталы и информационные системы',
  district: 'Федеральные округа',
  regional: 'Региональные порталы',
  specialized: 'Специализированные',
}

const data = reportData as ReportData

function groupByCategory(sites: SiteReport[]): Map<string, SiteReport[]> {
  const groups = new Map<string, SiteReport[]>()
  for (const site of sites) {
    const cat = site.category || 'specialized'
    const list = groups.get(cat)
    if (list) {
      list.push(site)
    } else {
      groups.set(cat, [site])
    }
  }
  return groups
}

export default function App() {
  const grouped = groupByCategory(data.sites)

  return (
    <>
      <a href="#main" className="skip-link">
        Перейти к содержимому
      </a>

      <header role="banner">
        <div className="container">
          <h1>ГОСТ-доступность госсайтов РФ</h1>
        </div>
      </header>

      <main id="main" role="main">
        <div className="container">
          {data.is_demo && (
            <div className="demo-banner" role="alert">
              <strong>Демонстрационные данные.</strong> Реальные отчёты не
              найдены. Запустите <code>python3 run_all_targets.py</code> для
              получения реальных результатов.
            </div>
          )}

          <FontControls />

          <Stats avgPct={data.avg_pct} totalSites={data.total_sites} />

          <h2>Результаты по категориям</h2>
          {CATEGORY_ORDER.map((catKey) => {
            const sites = grouped.get(catKey)
            if (!sites || sites.length === 0) return null
            return (
              <CategorySection
                key={catKey}
                name={CATEGORY_NAMES[catKey] ?? catKey}
                sites={sites}
                checksPerSite={data.checks_per_site}
                defaultOpen={catKey === 'reference'}
              />
            )
          })}

          <Reference />
        </div>
      </main>
    </>
  )
}
