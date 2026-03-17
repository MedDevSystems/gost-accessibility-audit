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

interface ElementDetail {
  tag?: string;
  type?: string;
  name?: string;
  src?: string;
  selector?: string;
  html?: string;
  text?: string;
  role?: string;
  tabindex?: number;
  [key: string]: unknown;
}

export function CheckItem({ result }: Props) {
  const d = result.details || {};

  /* axe-core violations */
  const violations = (d.violations as Array<{
    nodes?: ViolationNodeData[];
    description?: string;
    impact?: string;
    help?: string;
    helpUrl?: string;
  }>) || [];

  /* Phase 1: проблемные элементы из разных проверок */
  const missingImages = (d.missing_images as ElementDetail[]) || [];
  const missingFields = (d.missing_fields as ElementDetail[]) || [];
  const suppressors = (d.dangerous_suppressors || d.suppressors as Array<{
    selector?: string;
    property?: string;
    replacement?: string;
  }>) || [];
  const negativeTabindex = (d.negative_tabindex as ElementDetail[]) || [];
  const issues = (d.issues as Array<{ type?: string; detail?: string }>) || [];

  const hasDetails = result.verdict !== 'PASS' && (
    result.reason ||
    violations.length > 0 ||
    missingImages.length > 0 ||
    missingFields.length > 0 ||
    (suppressors as unknown[]).length > 0 ||
    negativeTabindex.length > 0 ||
    issues.length > 0
  );

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
              result.wcag_ref !== 'SPECIAL_FUNC' &&
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

            {/* axe-core violations с полными деталями */}
            {violations.map((v, vi) => (
              <div key={vi} className="violation-group">
                {v.description && (
                  <p className="violation-description">{v.description}</p>
                )}
                {v.helpUrl && (
                  <a className="violation-learn-more" href={v.helpUrl as string}
                     target="_blank" rel="noopener noreferrer">
                    Как исправить
                  </a>
                )}
                {v.nodes?.map((node, ni) => (
                  <ViolationNode key={ni} node={node} />
                ))}
              </div>
            ))}

            {/* Изображения без alt */}
            {missingImages.length > 0 && (
              <div className="violation-group">
                <p className="violation-description">
                  Изображения без alt-текста ({missingImages.length})
                </p>
                {missingImages.map((img, i) => (
                  <div key={i} className="violation-node">
                    <code className="violation-html">
                      {img.html || `<img src="${img.src}">`}
                    </code>
                    {img.selector && (
                      <div className="violation-target">{img.selector}</div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Поля формы без меток */}
            {missingFields.length > 0 && (
              <div className="violation-group">
                <p className="violation-description">
                  Поля формы без меток ({missingFields.length})
                </p>
                {missingFields.map((f, i) => (
                  <div key={i} className="violation-node">
                    <code className="violation-html">
                      {f.html || `<${f.tag || 'input'} type="${f.type}" name="${f.name}">`}
                    </code>
                    {f.selector && (
                      <div className="violation-target">{f.selector}</div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* CSS-правила подавляющие outline */}
            {(suppressors as Array<{ selector?: string }>).length > 0 && (
              <div className="violation-group">
                <p className="violation-description">
                  CSS-правила подавляющие видимый фокус ({(suppressors as unknown[]).length})
                </p>
                {(suppressors as Array<{ selector?: string; property?: string }>).map((s, i) => (
                  <div key={i} className="violation-node">
                    <code className="violation-html">
                      {s.selector} {'{'} {s.property || 'outline: none'} {'}'}
                    </code>
                  </div>
                ))}
              </div>
            )}

            {/* Элементы с отрицательным tabindex */}
            {negativeTabindex.length > 0 && (
              <div className="violation-group">
                <p className="violation-description">
                  Элементы с tabindex&lt;0 ({negativeTabindex.length})
                </p>
                {negativeTabindex.map((el, i) => (
                  <div key={i} className="violation-node">
                    <code className="violation-html">
                      {el.html || `<${el.tag}${el.role ? ` role="${el.role}"` : ''} tabindex="${el.tabindex}">`}
                    </code>
                    {el.text && <div className="violation-target">text: {el.text}</div>}
                  </div>
                ))}
              </div>
            )}

            {/* Общие issues */}
            {issues.map((iss, i) => (
              <div key={i} className="violation-node">
                <div className="violation-summary">
                  {iss.detail || iss.type || JSON.stringify(iss)}
                </div>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
