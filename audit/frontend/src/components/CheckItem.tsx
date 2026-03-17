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
  const missingImages = (d.missing_images || d.problem_images as ElementDetail[]) || [];
  const missingFields = (d.missing_fields as ElementDetail[]) || [];
  const negativeTabindex = (d.negative_tabindex as ElementDetail[]) || [];
  const issues = (d.issues as Array<{ type?: string; detail?: string }>) || [];

  /* Landmarks (2.4.1) */
  const landmarks = (d.landmarks as Array<{
    role?: string; tag?: string; aria_label?: string; visible?: boolean;
  }>) || [];
  const hasMain = d.has_main as boolean | undefined;
  const landmarkRoles = (d.visible_roles as string[]) || [];

  /* CSS suppressors (2.4.7) */
  const suppressors = (d.suppressors as Array<{
    selector?: string; has_replacement?: boolean; rule_text?: string;
  }>) || [];
  const dangerousSuppressors = d.dangerous_suppressors as number | undefined;

  const hasDetails = result.verdict !== 'PASS' && (
    result.reason ||
    violations.length > 0 ||
    missingImages.length > 0 ||
    missingFields.length > 0 ||
    negativeTabindex.length > 0 ||
    issues.length > 0 ||
    landmarks.length > 0 ||
    suppressors.length > 0
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

            {/* axe-core violations */}
            {violations.map((v, vi) => (
              <div key={vi} className="violation-group">
                {v.description && (
                  <p className="violation-description">{v.description}</p>
                )}
                <p className="violation-fix-placeholder">
                  Рекомендации по исправлению будут добавлены в следующей версии
                </p>
                {v.nodes?.map((node, ni) => (
                  <ViolationNode key={ni} node={node} />
                ))}
              </div>
            ))}

            {/* Изображения без alt / с проблемами */}
            {missingImages.length > 0 && (
              <div className="violation-group">
                <p className="violation-description">
                  Проблемные изображения ({missingImages.length})
                </p>
                {missingImages.map((img, i) => (
                  <div key={i} className="violation-node">
                    <code className="violation-html">
                      {img.html || `<img src="${img.src}">`}
                    </code>
                    {img.selector && (
                      <div className="violation-target">{img.selector}</div>
                    )}
                    {img.issue && (
                      <span className="violation-impact" style={{
                        backgroundColor: img.issue === 'no_alt' ? '#8b0000' : '#6b5000'
                      }}>
                        {img.issue === 'no_alt' ? 'нет alt' :
                         img.issue === 'meaningless_alt' ? 'бессмысленный alt' :
                         String(img.severity || img.issue)}
                      </span>
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

            {/* Landmarks (2.4.1) */}
            {landmarks.length > 0 && (
              <div className="violation-group">
                <p className="violation-description">Landmarks на странице</p>
                <div className="violation-node">
                  <div className="landmark-list">
                    {landmarkRoles.length > 0 && (
                      <p className="landmark-present">
                        Присутствуют: {landmarkRoles.join(', ')}
                      </p>
                    )}
                    {hasMain === false && (
                      <p className="landmark-missing">
                        Отсутствует: <strong>main</strong> (основное содержимое)
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* CSS-правила подавляющие фокус (2.4.7) */}
            {suppressors.length > 0 && (
              <div className="violation-group">
                <p className="violation-description">
                  CSS-правила подавляющие видимый фокус
                  {dangerousSuppressors !== undefined && ` (${dangerousSuppressors} опасных из ${suppressors.length})`}
                </p>
                {suppressors.filter(s => !s.has_replacement).slice(0, 10).map((s, i) => (
                  <div key={i} className="violation-node">
                    <code className="violation-html">
                      {s.selector} {'{ outline: none }'}
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
