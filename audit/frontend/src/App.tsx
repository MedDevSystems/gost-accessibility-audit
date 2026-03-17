/* Корневой компонент: форма + прогресс + отчёт */

import { useAudit } from './hooks/useAudit';
import { AuditForm } from './components/AuditForm';
import { ProgressBar } from './components/ProgressBar';
import { ReportView } from './components/ReportView';

export function App() {
  const { state, launch, reset } = useAudit();

  return (
    <div className="app">
      <header className="app-header">
        <h1>Аудит доступности</h1>
        <p className="app-subtitle">
          ГОСТ Р 52872-2019 &middot; ГОСТ Р ИСО 40500-2014 &middot; Приказ Минцифры №953
        </p>
      </header>

      <main className="app-main">
        <AuditForm
          onStart={launch}
          disabled={state.phase === 'running'}
        />

        {state.phase === 'running' && (
          <ProgressBar
            currentUrl={state.currentUrl}
            currentCheck={state.currentCheck}
            checksDone={state.checksDone}
            checksTotal={state.checksTotal}
          />
        )}

        {state.phase === 'error' && (
          <div className="error-block">
            <p className="error-message">{state.errorMessage}</p>
            <button className="btn-reset" onClick={reset} type="button">
              Попробовать снова
            </button>
          </div>
        )}

        {(state.phase === 'completed' || state.pages.length > 0) &&
          state.pages.map((page, i) => (
            <ReportView key={`${page.url}-${i}`} report={page} />
          ))
        }

        {state.phase === 'completed' && (
          <button className="btn-reset" onClick={reset} type="button">
            Новый аудит
          </button>
        )}
      </main>

      <footer className="app-footer">
        <p>Автоматизированное тестирование доступности госсайтов</p>
      </footer>
    </div>
  );
}
