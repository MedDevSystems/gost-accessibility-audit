import type { SiteReport } from '../types'
import { ChecksTable } from './ChecksTable'

interface CategorySectionProps {
  name: string
  sites: SiteReport[]
  checksPerSite: number
  defaultOpen?: boolean
}

function pluralize(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod100 >= 11 && mod100 <= 19) return many
  if (mod10 === 1) return one
  if (mod10 >= 2 && mod10 <= 4) return few
  return many
}

function pctClass(pct: number): string {
  if (pct >= 75) return 'pct-good'
  if (pct >= 50) return 'pct-mid'
  return 'pct-bad'
}

export function CategorySection({ name, sites, checksPerSite, defaultOpen }: CategorySectionProps) {
  const catPass = sites.reduce((s, r) => s + r.summary.pass, 0)
  const catFail = sites.reduce((s, r) => s + r.summary.fail, 0)
  const catTotal = catPass + catFail
  const catPct = catTotal > 0 ? Math.round((catPass / catTotal) * 1000) / 10 : 0

  return (
    <details className="category-details" open={defaultOpen}>
      <summary>
        <h3>
          {name}{' '}
          <span className="cat-stats">
            ({sites.length} {pluralize(sites.length, 'сайт', 'сайта', 'сайтов')}, {catPct}%
            {' '}соответствие)
          </span>
        </h3>
      </summary>
      <div className="sites-table-wrap">
        <table className="sites-table">
          <thead>
            <tr>
              <th scope="col">Сайт</th>
              <th scope="col">URL</th>
              <th scope="col">PASS</th>
              <th scope="col">FAIL</th>
              <th scope="col">%</th>
            </tr>
          </thead>
          <tbody>
            {sites.map((site) => {
              const total = site.summary.total || checksPerSite
              const pct = total > 0 ? Math.round((site.summary.pass / total) * 1000) / 10 : 0
              return (
                <SiteRows
                  key={site.id}
                  site={site}
                  pct={pct}
                  checksPerSite={checksPerSite}
                />
              )
            })}
          </tbody>
        </table>
      </div>
    </details>
  )
}

interface SiteRowsProps {
  site: SiteReport
  pct: number
  checksPerSite: number
}

function SiteRows({ site, pct, checksPerSite }: SiteRowsProps) {
  return (
    <>
      <tr
        aria-label={`${site.name}. PASS: ${site.summary.pass}, FAIL: ${site.summary.fail}, соответствие: ${pct}%`}
      >
        <th scope="row">
          {site.name}
          {site.is_reference && <span className="ref-badge">эталон</span>}
        </th>
        <td>
          <a href={site.url} rel="noopener noreferrer">
            {site.url}
          </a>
        </td>
        <td className="num">
          <span className="mobile-label" aria-hidden="true">pass: </span>
          {site.summary.pass}
        </td>
        <td className="num">
          <span className="mobile-label" aria-hidden="true">fail: </span>
          {site.summary.fail}
        </td>
        <td className={`num ${pctClass(pct)}`}>{pct}%</td>
      </tr>
      <tr className="details-row">
        <td colSpan={5}>
          <details id={`site-${site.id}`}>
            <summary>Подробности {checksPerSite} проверок</summary>
            <ChecksTable checks={site.checks} checksPerSite={checksPerSite} />
          </details>
        </td>
      </tr>
    </>
  )
}
