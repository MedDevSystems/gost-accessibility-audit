/* Прогресс проверки в реальном времени */

interface Props {
  currentUrl: string | null;
  currentCheck: string | null;
  checksDone: number;
  checksTotal: number;
}

export function ProgressBar({ currentUrl, currentCheck, checksDone, checksTotal }: Props) {
  const pct = checksTotal > 0 ? Math.round((checksDone / checksTotal) * 100) : 0;

  return (
    <div className="progress-container">
      <div className="progress-header">
        <span className="progress-label">Проверка: {checksDone} / {checksTotal}</span>
        <span className="progress-pct">{pct}%</span>
      </div>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
      {currentUrl && (
        <div className="progress-detail">
          <span className="progress-url">{currentUrl}</span>
          {currentCheck && <span className="progress-check">{currentCheck}</span>}
        </div>
      )}
    </div>
  );
}
