/* Один проблемный HTML-элемент: код + селектор + impact */

interface ViolationData {
  html?: string;
  target?: string | string[];
  impact?: string;
  failureSummary?: string;
  failure_summary?: string;
}

interface Props {
  node: ViolationData;
}

const IMPACT_COLORS: Record<string, string> = {
  critical: '#ff4e42',
  serious: '#e65100',
  moderate: '#ffa400',
  minor: '#999',
};

export function ViolationNode({ node }: Props) {
  const target = Array.isArray(node.target)
    ? node.target.join(' > ')
    : node.target || '';
  const summary = node.failureSummary || node.failure_summary || '';
  const impact = node.impact || '';

  return (
    <div className="violation-node">
      {node.html && (
        <code className="violation-html">{node.html}</code>
      )}
      {target && <div className="violation-target">{target}</div>}
      <div className="violation-meta">
        {impact && (
          <span
            className="violation-impact"
            style={{ backgroundColor: IMPACT_COLORS[impact] || '#999' }}
          >
            {impact}
          </span>
        )}
        {summary && <span className="violation-summary">{summary}</span>}
      </div>
    </div>
  );
}
