/* Круговой SVG-индикатор оценки в стиле Lighthouse */

interface Props {
  passed: number;
  total: number;
}

export function ScoreGauge({ passed, total }: Props) {
  const pct = total > 0 ? passed / total : 0;
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - pct);

  let colorClass = 'gauge-red';
  if (pct >= 0.9) colorClass = 'gauge-green';
  else if (pct >= 0.5) colorClass = 'gauge-orange';

  return (
    <div className={`score-gauge ${colorClass}`}>
      <svg viewBox="0 0 120 120" width="120" height="120">
        <circle
          className="gauge-bg"
          cx="60" cy="60" r={radius}
          fill="none" strokeWidth="8"
        />
        <circle
          className="gauge-fill"
          cx="60" cy="60" r={radius}
          fill="none" strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 60 60)"
        />
      </svg>
      <div className="gauge-text">
        <span className="gauge-value">{passed}</span>
        <span className="gauge-slash">/</span>
        <span className="gauge-total">{total}</span>
      </div>
    </div>
  );
}
