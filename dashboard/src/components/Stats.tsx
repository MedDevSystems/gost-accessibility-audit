interface StatsProps {
  avgPct: number
  totalSites: number
}

export function Stats({ avgPct, totalSites }: StatsProps) {
  return (
    <>
      <h2>Общая статистика</h2>
      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-value">{avgPct}%</span>
          <span className="stat-label">Среднее соответствие</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{totalSites}</span>
          <span className="stat-label">Проверено сайтов</span>
        </div>
      </div>
    </>
  )
}
