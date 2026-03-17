/* Кнопка сохранения HTML-отчёта */

interface Props {
  url: string;
}

export function ExportButton({ url }: Props) {
  const handleExport = () => {
    const html = document.documentElement.outerHTML;
    const blob = new Blob(
      [`<!DOCTYPE html>\n${html}`],
      { type: 'text/html;charset=utf-8' },
    );
    const a = document.createElement('a');
    const domain = new URL(url).hostname.replace(/\./g, '_');
    const date = new Date().toISOString().slice(0, 10);
    a.download = `audit_${domain}_${date}.html`;
    a.href = URL.createObjectURL(blob);
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <button className="btn-export" onClick={handleExport} type="button">
      Сохранить HTML
    </button>
  );
}
