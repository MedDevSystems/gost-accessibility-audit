/* Полный отчёт по одной странице: gauge + статистика + категории + экспорт */

import type { PageReport } from '../types';
import { CATEGORY_ORDER } from '../types';
import { CategoryGroup } from './CategoryGroup';
import { ExportButton } from './ExportButton';
import { ScoreGauge } from './ScoreGauge';

interface Props {
  report: PageReport;
}

export function ReportView({ report }: Props) {
  const { summary, main_results, special_results, url, timestamp } = report;
  const date = new Date(timestamp).toLocaleString('ru-RU');

  const failResults = main_results.filter(r => r.verdict !== 'PASS');
  const passResults = main_results.filter(r => r.verdict === 'PASS');

  const groupByCategory = (results: typeof main_results) => {
    const grouped: Record<string, typeof main_results> = {};
    for (const r of results) {
      const cat = r.category || 'gost_specific';
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(r);
    }
    return grouped;
  };

  const failGroups = groupByCategory(failResults);
  const passGroups = groupByCategory(passResults);

  return (
    <div className="report-view">
      <div className="report-header">
        <ScoreGauge passed={summary.passed} total={summary.total} />
        <div className="report-meta">
          <h2 className="report-url">{url}</h2>
          <p className="report-date">{date}</p>
          <div className="report-stats">
            <span className="stat-pass">Пройдено: {summary.passed}</span>
            <span className="stat-fail">Не пройдено: {summary.failed}</span>
            {summary.uncertain > 0 && (
              <span className="stat-uncertain">Неопределённо: {summary.uncertain}</span>
            )}
          </div>
        </div>
      </div>

      <div className="report-section">
        <div className="stats-grid" role="group" aria-label="Статистика аудита">
          <div className="stat-card" aria-label={`Пройдено: ${summary.passed}`}>
            <span className="stat-value verdict-pass" aria-hidden="true">{summary.passed}</span>
            <span className="stat-label" aria-hidden="true">Пройдено</span>
          </div>
          <div className="stat-card" aria-label={`Не пройдено: ${summary.failed}`}>
            <span className="stat-value verdict-fail" aria-hidden="true">{summary.failed}</span>
            <span className="stat-label" aria-hidden="true">Не пройдено</span>
          </div>
          {summary.uncertain > 0 && (
            <div className="stat-card" aria-label={`Неопределённо: ${summary.uncertain}`}>
              <span className="stat-value verdict-uncertain" aria-hidden="true">{summary.uncertain}</span>
              <span className="stat-label" aria-hidden="true">Неопределённо</span>
            </div>
          )}
          <div className="stat-card" aria-label={`Оценка: ${summary.score_pct}%`}>
            <span className="stat-value" aria-hidden="true">{summary.score_pct}%</span>
            <span className="stat-label" aria-hidden="true">Оценка</span>
          </div>
        </div>

        <ExportButton url={url} />
      </div>

      {/* Не пройденные проверки — развёрнуты */}
      {failResults.length > 0 && (
        <div className="report-section">
          <h3 className="section-title section-fail">Не пройденные проверки</h3>
          {CATEGORY_ORDER.map(cat =>
            failGroups[cat] ? (
              <CategoryGroup
                key={cat}
                category={cat}
                results={failGroups[cat]}
                defaultOpen={true}
              />
            ) : null,
          )}
        </div>
      )}

      {/* Пройденные проверки — свёрнуты */}
      {passResults.length > 0 && (
        <div className="report-section">
          <details>
            <summary className="section-title section-pass">
              Пройденные проверки ({passResults.length})
            </summary>
            {CATEGORY_ORDER.map(cat =>
              passGroups[cat] ? (
                <CategoryGroup
                  key={cat}
                  category={cat}
                  results={passGroups[cat]}
                />
              ) : null,
            )}
          </details>
        </div>
      )}

      {/* Спецверсия */}
      {special_results && special_results.length > 0 && (
        <div className="report-section">
          <details>
            <summary className="section-title section-special">
              Спецверсия для слабовидящих
            </summary>
            {(() => {
              const specGroups = groupByCategory(special_results);
              return CATEGORY_ORDER.map(cat =>
                specGroups[cat] ? (
                  <CategoryGroup
                    key={`spec-${cat}`}
                    category={cat}
                    results={specGroups[cat]}
                  />
                ) : null,
              );
            })()}
          </details>
        </div>
      )}
    </div>
  );
}
