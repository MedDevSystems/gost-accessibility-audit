import type { CheckResult } from '../types'

interface ChecksTableProps {
  checks: CheckResult[]
  checksPerSite: number
}

const VERDICT_CLASS: Record<string, string> = {
  PASS: 'verdict-pass',
  FAIL: 'verdict-fail',
  UNCERTAIN: 'verdict-uncertain',
}

export function ChecksTable({ checks, checksPerSite }: ChecksTableProps) {
  if (checks.length === 0) {
    return <p>Детали проверок отсутствуют (только сводные данные).</p>
  }

  return (
    <div className="checks-table-wrap">
      <table className="checks-table">
        <thead>
          <tr>
            <th scope="col">ГОСТ</th>
            <th scope="col">Вердикт</th>
            <th scope="col">Проверка</th>
            <th scope="col">Причина</th>
            <th scope="col">Источник</th>
          </tr>
        </thead>
        <tbody>
          {checks.map((check, i) => (
            <tr
              key={i}
              tabIndex={0}
              aria-label={`ГОСТ ${check.gost_section}, ${check.verdict}. Тест: ${check.title}. Результат: ${check.reason}`}
            >
              <td>
                <span className="mobile-label" aria-hidden="true">ГОСТ </span>
                {check.gost_section}
              </td>
              <td>
                <span className={VERDICT_CLASS[check.verdict] ?? ''}>
                  {check.verdict}
                </span>
              </td>
              <td>
                <span className="mobile-label" aria-hidden="true">тест: </span>
                {check.title}
              </td>
              <td>
                <span className="mobile-label" aria-hidden="true">результат: </span>
                {check.reason}
              </td>
              <td>{check.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {checks.length < checksPerSite && (
        <p>Показано {checks.length} из {checksPerSite} проверок.</p>
      )}
    </div>
  )
}
