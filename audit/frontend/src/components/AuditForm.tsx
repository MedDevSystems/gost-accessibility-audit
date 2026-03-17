/* Форма ввода URL(ов) + кнопка запуска аудита */

import { useState } from 'react';

interface Props {
  onStart: (urls: string[], includeSpecial: boolean) => void;
  disabled: boolean;
}

export function AuditForm({ onStart, disabled }: Props) {
  const [urlInput, setUrlInput] = useState('');
  const [includeSpecial, setIncludeSpecial] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const urls = urlInput
      .split('\n')
      .map(u => u.trim())
      .filter(u => u.length > 0);
    if (urls.length === 0) return;
    onStart(urls, includeSpecial);
  };

  return (
    <form className="audit-form" onSubmit={handleSubmit}>
      <label htmlFor="url-input" className="form-label">
        URL для проверки
      </label>
      <textarea
        id="url-input"
        className="url-input"
        value={urlInput}
        onChange={e => setUrlInput(e.target.value)}
        placeholder="https://example.gov.ru/&#10;Один URL на строку"
        rows={3}
        disabled={disabled}
        required
      />
      <div className="form-controls">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={includeSpecial}
            onChange={e => setIncludeSpecial(e.target.checked)}
            disabled={disabled}
          />
          Проверять спецверсию
        </label>
        <button type="submit" className="btn-start" disabled={disabled}>
          {disabled ? 'Проверка...' : 'Начать аудит'}
        </button>
      </div>
    </form>
  );
}
