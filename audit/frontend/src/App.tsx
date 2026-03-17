/* Корневой компонент: форма + прогресс + отчёт */

import { useAudit } from './hooks/useAudit';
import { AuditForm } from './components/AuditForm';
import { ProgressBar } from './components/ProgressBar';
import { ReportView } from './components/ReportView';

export function App() {
  const { state, launch, reset } = useAudit();

  return (
    <>
      <a className="skip-link" href="#main">
        Перейти к содержимому
      </a>
      <div className="container">
        <header>
          <h1>Аудит доступности</h1>
        </header>

        <main id="main">
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

        <footer>
          <p>Автоматизированное тестирование доступности госсайтов</p>
        </footer>
      </div>
    </>
  );
}
