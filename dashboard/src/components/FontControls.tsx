import { useFontSize } from '../hooks/useFontSize'

export function FontControls() {
  const { increase, decrease, reset } = useFontSize()

  return (
    <div className="font-controls" role="group" aria-label="Размер шрифта">
      <button type="button" aria-label="Увеличить шрифт" onClick={increase}>
        A+
      </button>
      <button type="button" aria-label="Уменьшить шрифт" onClick={decrease}>
        A&minus;
      </button>
      <button type="button" aria-label="Сбросить размер шрифта" onClick={reset}>
        Сброс шрифта
      </button>
    </div>
  )
}
