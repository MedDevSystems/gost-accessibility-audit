/* Группа проверок по категории ГОСТ с раскрытием */

import type { CheckResultOut } from '../types';
import { CATEGORY_LABELS } from '../types';
import { CheckItem } from './CheckItem';

interface Props {
  category: string;
  results: CheckResultOut[];
  defaultOpen?: boolean;
}

export function CategoryGroup({ category, results, defaultOpen = false }: Props) {
  const passed = results.filter(r => r.verdict === 'PASS').length;
  const failed = results.filter(r => r.verdict === 'FAIL').length;
  const label = CATEGORY_LABELS[category] || category;

  return (
    <details className="category-group" open={defaultOpen}>
      <summary className="category-summary">
        <span className="category-label">{label}</span>
        <span className="category-counters">
          {failed > 0 && <span className="counter-fail">{failed} не пройдено</span>}
          {passed > 0 && <span className="counter-pass">{passed} пройдено</span>}
        </span>
      </summary>
      <div className="category-checks">
        {results.map((r, i) => (
          <CheckItem key={`${r.gost_section}-${i}`} result={r} />
        ))}
      </div>
    </details>
  );
}
