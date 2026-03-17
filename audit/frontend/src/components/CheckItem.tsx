/* Одна проверка: вердикт + описание + раскрывающийся блок деталей */

import type { CheckResultOut } from '../types';
import { ViolationNode } from './ViolationNode';

interface Props {
  result: CheckResultOut;
}

const VERDICT_ICONS: Record<string, string> = {
  PASS: '\u2713',
  FAIL: '\u2717',
  UNCERTAIN: '?',
};

const VERDICT_CLASSES: Record<string, string> = {
  PASS: 'verdict-pass',
  FAIL: 'verdict-fail',
  UNCERTAIN: 'verdict-uncertain',
};

interface ViolationNodeData {
  html?: string;
  target?: string | string[];
  impact?: string;
  failureSummary?: string;
  failure_summary?: string;
}

export function CheckItem({ result }: Props) {
  const violations = (result.details?.violations as Array<{
    nodes?: ViolationNodeData[];
    description?: string;
    impact?: string;
  }>) || [];
  const missingImages = (result.details?.missing_images as Array<{
    src?: string;
    selector?: string;
  }>) || [];
  const hasDetails = violations.length > 0 || missingImages.length > 0 ||
    (result.verdict !== 'PASS' && result.reason);

  return (
    <div className={`check-item ${VERDICT_CLASSES[result.verdict]}`}>
      <div className="check-header">
        <span className={`check-icon ${VERDICT_CLASSES[result.verdict]}`}>
          {VERDICT_ICONS[result.verdict]}
        </span>
        <div className="check-title-block">
          <span className="check-title">{result.title}</span>
          <span className="check-refs">
            ГОСТ {result.gost_section}
            {result.wcag_ref && result.wcag_ref !== 'SPECIAL' &&
              ` / WCAG ${result.wcag_ref}`}
          </span>
        </div>
        <span className="check-source">{result.source}</span>
      </div>

      {hasDetails && (
        <details className="check-details">
          <summary>Подробности</summary>
          <div className="check-details-content">
            {result.reason && (
              <p className="check-reason">{result.reason}</p>
            )}

            {result.description && (
              <p className="check-description">{result.description}</p>
            )}

            {violations.map((v, vi) => (
              <div key={vi} className="violation-group">
                {v.description && (
                  <p className="violation-description">{v.description}</p>
                )}
                {v.nodes?.map((node, ni) => (
                  <ViolationNode key={ni} node={node} />
                ))}
              </div>
            ))}

            {missingImages.map((img, i) => (
              <div key={i} className="violation-node">
                <code className="violation-html">
                  &lt;img src=&quot;{img.src}&quot;&gt;
                </code>
                {img.selector && (
                  <div className="violation-target">{img.selector}</div>
                )}
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
