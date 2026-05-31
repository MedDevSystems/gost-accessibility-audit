# План архитектуры: Chrome-расширение проверки страниц на ГОСТ Р 52872‑2019 / WCAG 2.1

> Документ — вход для Stage 4. Каждый модуль оформлен как скелет `MODULE_CONTRACT`. Тел функций нет; функции перечислены в `@modulemap`. Числовые веса помечены `(prov.)` где оценочны.
>
> **Статус документа:** главный архитектурный источник истины для целевого продукта.
> Если README, `CLAUDE.md` или миграционные заметки расходятся с этим планом,
> этот документ имеет больший вес. Документы статуса могут описывать текущий
> DevTools-прототип, но не переопределяют целевую архитектуру.

---

## 1. Резюме требований и допущений

**Задача.** Self-contained Chrome-расширение (Manifest V3) для веб-разработчика. По требованию проверяет текущую открытую страницу (живой отрендеренный DOM) на соответствие ГОСТ Р 52872‑2019 (гармонизирован с WCAG 2.1) и выдаёт: где расхождение, к какому пункту стандарта оно относится, как починить. Выход — структурированный JSON + PDF со скриншотами и аннотацией проблемных элементов. Лёгкая история прогонов.

**Стандарт.** ГОСТ Р 52872‑2019 (введён 01.04.2020, заменил редакцию 2012). Построен на четырёх принципах WCAG (воспринимаемость, управляемость, понятность, надёжность) и взял за основу WCAG 2.1 → критерии успеха WCAG 2.1 трассируются на пункты ГОСТ. Целевой уровень по умолчанию — **AA**.

**Допущения (всё домысленное — поправляемо):**
- Язык реализации — **TypeScript** (контракты между контекстами MV3 требуют типов).
- Каждый finding ссылается на пункт ГОСТ + критерий успеха WCAG (трассировка).
- Один прогон = одна текущая страница; многостраничный обход вне scope.
- Работает по тому, что открыто, включая страницы за авторизацией (исполнение в контексте страницы).
- Детерминированное ядро самодостаточно: без LLM-ключа система работает, LLM-проверки выключены.
- Скриншоты — видимый вьюпорт (`captureVisibleTab`) + аннотация элемента; полностраничная склейка — улучшение, не дефолт.
- PDF собирается на клиенте (`pdf-lib`).
- Язык вывода (отчёт, инструкции, UI) — русский.
- Ключ к LLM пользователь вводит в настройках; гейтвей — OpenAI-совместимый, модель мультимодальная.

**Граница MVP (первый вертикальный срез):** детерминированный движок без LLM + декларативный реестр правил + триггер из popup → JSON + PDF с вьюпорт-скриншотом и аннотациями + лёгкая история. **Отложено:** LLM-слой с тулзами, полностраничные склеенные скриншоты, режим формального аудита, многостраничный обход, сравнение «было/стало», шаринг.

---

## 2. Варианты архитектуры (две развилки с реальным трейд-оффом)

### Развилка A — движок детерминированных проверок

| | A1: обёртка над `axe-core` | A2: собственный реестр с нуля |
|---|---|---|
| Скорость разработки | Высокая — зрелый движок «из коробки» | Низкая — месяцы авторинга правил |
| Точность/покрытие | Проверено в проде, мало ложных срабатываний | Долго догонять по качеству |
| Контроль и маппинг на ГОСТ | Нужен слой-обёртка для маппинга на пункты | Полный контроль изначально |
| Зависимость | `axe-core` (MPL-2.0) | Нет внешней |

**Рекомендация: A1.** Берём `axe-core` как поставщик детерминированных проверок **за нашим фасадом `engine/catalog`**: фасад владеет маппингом «правило axe → пункт ГОСТ/WCAG», severity и шаблонами фиксов, а также держит слоты под LLM-проверки, которых у axe нет. «Чистый if/else MVP» при этом сохраняется — axe и есть детерминированный движок, мы лишь не переизобретаем его. Свои bespoke-правила добавляем точечно туда, где axe не покрывает ГОСТ.

### Развилка B — топология оркестрации в MV3

| | B1: service-worker-центричная | B2: content-script-центричная |
|---|---|---|
| Доступ к DOM | Через content script (RPC) | Прямой |
| Сеть/LLM (CORS, ключи) | Чисто (origin расширения) | Грязно (origin страницы) |
| `captureVisibleTab` | Доступно | Недоступно из page-контекста |
| Жизненный цикл | SW убивается по простою (~30с) | Живёт со страницей |
| Тяжёлая работа (canvas, PDF) | Через offscreen-документ | Конфликт с CSP страницы |

**Рекомендация: B1 + offscreen.** SW — оркестратор и сеть; `content/snapshot` и `content/overlay` — зонд и подсветка в странице; **offscreen-документ** — canvas-кроп скриншотов и рендер PDF (у SW нет DOM). Риск «SW убивается на длинной LLM-цепочке» гасим: агентный цикл LLM держим в offscreen-документе + keepalive-порт; SW только маршрутизирует.

**Стек (каждая зависимость обоснована в модуле):** TypeScript · Vite + `@crxjs/vite-plugin` (boilerplate MV3) · `axe-core` (детерм. движок) · `pdf-lib` (PDF без DOM-зависимостей) · `idb` (тонкая обёртка IndexedDB) · `zod` (валидация настроек и JSON-ответов LLM) · нативный `fetch` для LLM (без SDK).

---

## 3. Декомпозиция на модули (скелеты `MODULE_CONTRACT`)

> Контракты приведены в docstring-конвенции Stage 4; в реализации лягут блок-комментарием над соответствующим `.ts`-модулем.

### shared/types — каркас контрактов
```text
"""
MODULE_CONTRACT [DOMAIN(3): a11y-аудит; CONCEPT(9): схемы-интерфейсы; TECH(4): TypeScript types]

@purpose   Единый источник типов, которыми обмениваются все контексты.
@scope     Только определения типов/схем; без логики и побочных эффектов.
@input     —
@output    Типы: PageSnapshot, ElementRef, Rule, Finding, Report, RunConfig.
@links     LINKS_TO: используется ВСЕМИ модулями как контракт интерфейсов.
@invariants
  - Чистый модуль типов: ноль рантайм-побочек.
  - Любое изменение схемы — это смена контракта между модулями (версионировать).
@rationale
  Q: Почему отдельный модуль типов?
  A: Интерфейсы между контекстами MV3 должны быть явными и едиными, иначе RPC рассинхронизируется.
@modulemap
  TYPE 9[модель страницы для проверок] => PageSnapshot
  TYPE 8[ссылка на элемент: селектор+bbox+роль] => ElementRef
  TYPE 9[правило каталога с маппингом на стандарт] => Rule
  TYPE 9[единичное нарушение] => Finding
  TYPE 8[агрегированный отчёт прогона] => Report
  TYPE 6[параметры прогона: уровень, наборы] => RunConfig
@usecases
  - [Finding]: Движок -> формирует нарушение -> отдаёт в report/model
"""
```

### shared/messaging — типизированная шина RPC
```text
"""
MODULE_CONTRACT [DOMAIN(2): a11y-аудит; CONCEPT(7): межконтекстный RPC; TECH(8): chrome.runtime ports]

@purpose   Типобезопасный обмен сообщениями popup ↔ SW ↔ content ↔ offscreen.
@scope     Транспорт и маршрутизация сообщений; не знает доменной логики.
@input     Типизированные запросы/ответы (по shared/types).
@output    Promise-ответы; стрим прогресса через долгоживущий порт.
@links     USES_API(8): chrome.runtime.sendMessage/connect; LINKS_TO: все контексты.
@invariants
  - Каждое сообщение имеет тег типа; неизвестные — отбрасываются.
  - Побочный эффект: открытие/закрытие портов; keepalive-ping для SW.
@rationale
  Q: Зачем своя шина, а не голый sendMessage?
  A: Голый API нетипизирован и теряет длинные цепочки; нужен прогресс-стрим и единый контракт.
@modulemap
  FUNC 7[вызвать удалённый хэндлер и дождаться ответа] => request   # @io: Msg -> Promise<Resp>
  FUNC 6[подписаться на стрим прогресса прогона] => openProgressPort # @io: runId -> Port
  FUNC 5[зарегистрировать хэндлер в контексте] => onRequest          # @io: (tag, fn) -> void
@usecases
  - [openProgressPort]: Popup -> подписка на runId -> живые апдейты статуса
"""
```

### config/settings — настройки и доступ к LLM-гейтвею
```text
"""
MODULE_CONTRACT [DOMAIN(3): a11y-аудит; CONCEPT(6): конфигурация; TECH(7): chrome.storage + zod]

@purpose   Чтение/запись/валидация настроек: gateway URL, API-ключ, модель, уровень WCAG, включённые наборы.
@scope     Только конфиг; не делает сетевых вызовов.
@input     Пользовательский ввод из UI настроек.
@output    Валидированный RunConfig + креды LLM.
@links     USES_API(6): chrome.storage.local; USES_API(5): zod; LINKS_TO: popup, llm/client, engine/*.
@invariants
  - Ключ хранится в chrome.storage.local (НЕ sync) — не утекает между устройствами.
  - ВНИМАНИЕ-побочка: ключ в local не шифруется ОС → помечать риск в UI; опция «не хранить, вводить за сессию».
  - Невалидный конфиг не сохраняется (zod-схема).
@rationale
  Q: local vs sync для ключа?
  A: sync синхронизировал бы секрет в облако Google — недопустимо; local + явное предупреждение.
@modulemap
  FUNC 6[прочитать и провалидировать конфиг] => loadConfig       # @io: () -> RunConfig
  FUNC 6[сохранить конфиг после валидации] => saveConfig         # @io: Partial<RunConfig> -> Result
  FUNC 5[проверить доступность гейтвея/модели] => probeGateway   # @io: creds -> Health
@usecases
  - [probeGateway]: Разработчик -> вводит URL/ключ -> «модель доступна / ошибка»
"""
```

### popup — UI-контроллер и точка входа
```text
"""
MODULE_CONTRACT [DOMAIN(5): a11y-аудит; CONCEPT(6): презентация/намерение; TECH(7): React+MV3 popup]

@purpose   Запустить прогон, показать прогресс и список findings, дать экспорт и доступ к настройкам.
@scope     Только UI и захват намерения пользователя; доменной логики не содержит.
@input     Клики пользователя; стрим прогресса; готовый Report.
@output    Сообщения-намерения в оркестратор; рендер отчёта; триггеры экспорта.
@links     USES_API(6): shared/messaging; LINKS_TO: background/orchestrator, config/settings, export/*.
@invariants
  - Popup эфемерен (закрывается при потере фокуса) → состояние прогона живёт в SW, не в popup.
  - Никаких прямых сетевых/DOM-вызовов из popup.
@rationale
  Q: Почему состояние не в popup?
  A: Popup умирает при клике мимо; длинный прогон обязан переживать закрытие окна.
@modulemap
  FUNC 7[инициировать прогон по текущей вкладке] => startScan       # @io: RunConfig -> runId
  FUNC 6[отрисовать живой прогресс] => renderProgress               # @io: ProgressEvent -> UI
  FUNC 7[отрисовать список нарушений с фильтрами] => renderFindings # @io: Report -> UI
  FUNC 5[инициировать экспорт JSON/PDF] => triggerExport            # @io: (Report, fmt) -> download
@usecases
  - [startScan]: Разработчик -> жмёт «Проверить» -> запускается прогон текущей страницы
  - [renderFindings]: Разработчик -> видит нарушения, сгруппированные по пунктам ГОСТ
"""
```

### background/orchestrator — оркестратор прогона (service worker)
```text
"""
MODULE_CONTRACT [DOMAIN(6): a11y-аудит; CONCEPT(9): оркестрация/стейт-машина; TECH(9): MV3 service worker]

@purpose   Управлять жизненным циклом прогона: снимок → детерм. движок → (LLM) → агрегация → скриншоты → экспорт-модель → история.
@scope     Координация и состояние прогона; сами проверки делегирует.
@input     Намерение startScan(runId, RunConfig).
@output    ProgressEvent-стрим; финальный Report; запись в историю.
@links     LINKS_TO: content/snapshot, engine/deterministic, engine/llm, report/model, capture/screenshot, storage/history; USES_API(7): chrome.tabs, chrome.offscreen.
@invariants
  - Единственный владелец состояния прогона (источник истины).
  - Побочки: создаёт offscreen-документ; шлёт keepalive; пишет в историю.
  - Прогон идемпотентен по runId; параллельные прогоны одной вкладки сериализуются.
@rationale
  Q: Как пережить ~30с простоя SW на длинной LLM-цепочке?
  A: Долгую агентную работу выносим в offscreen; SW держит keepalive-порт и только маршрутизирует шаги.
@modulemap
  FUNC 9[провести прогон по шагам пайплайна] => runPipeline      # @io: (runId, RunConfig) -> Report
  FUNC 6[создать/переиспользовать offscreen] => ensureOffscreen  # @io: () -> void
  FUNC 6[эмитить событие прогресса] => emitProgress              # @io: ProgressEvent -> void
  FUNC 5[отменить прогон] => cancelRun                            # @io: runId -> void
@usecases
  - [runPipeline]: Система -> снимок→проверки→отчёт -> отдаёт Report и пишет историю
"""
```

### content/snapshot — извлечение модели страницы (content script)
```text
"""
MODULE_CONTRACT [DOMAIN(7): a11y-аудит; CONCEPT(8): интроспекция DOM; TECH(8): content script / isolated world]

@purpose   Собрать сериализуемый снимок страницы: поддерево DOM, computed styles, ARIA/роли, лендмарки, язык, ссылки/формы.
@scope     Только чтение страницы; не мутирует DOM (мутации — у overlay).
@input     Запрос на снимок (опц. фильтр области).
@output    PageSnapshot (сериализуемый).
@links     USES_API(8): DOM/getComputedStyle/AccessibilityObject(part); LINKS_TO: orchestrator, engine/deterministic, llm/tools.
@invariants
  - Не изменяет страницу (read-only).
  - Cross-origin iframe недоступны → помечаются как непокрытые, а не молча пропускаются.
  - Снимок отражает состояние на момент триггера (без авто-обхода динамики).
@rationale
  Q: Почему отдельный снимок, а не гонять axe прямо по live DOM?
  A: Снимок — общий вход и для axe, и для LLM-тулзов; единый контракт + повторяемость.
@modulemap
  FUNC 8[собрать снимок страницы] => buildSnapshot            # @io: opts -> PageSnapshot
  FUNC 6[резолвить элемент по селектору] => resolveElement    # @io: selector -> ElementRef
  FUNC 5[пометить непокрытые зоны (iframe/shadow)] => markUncovered # @io: () -> Coverage
@usecases
  - [buildSnapshot]: Оркестратор -> просит снимок -> получает PageSnapshot для движков
"""
```

### content/overlay — подсветка элементов для скриншотов
```text
"""
MODULE_CONTRACT [DOMAIN(4): a11y-аудит; CONCEPT(5): визуальная разметка; TECH(7): DOM overlay]

@purpose   Подсветить проблемный элемент рамкой и проскроллить во вьюпорт перед захватом.
@scope     Только временные визуальные оверлеи; убирает за собой.
@input     ElementRef.
@output    Сигнал «готово к захвату»; bbox в координатах вьюпорта.
@links     LINKS_TO: capture/screenshot, orchestrator; USES_API(6): scrollIntoView, DOM.
@invariants
  - Побочка: добавляет/удаляет временный оверлей-узел; всегда чистит после захвата.
  - Оверлей не влияет на снимок (snapshot снимается ДО подсветки).
@rationale
  Q: Зачем отделять от snapshot?
  A: Чтение и мутация — разные ответственности; оверлей не должен попадать в проверяемую модель.
@modulemap
  FUNC 6[подсветить и проскроллить элемент] => highlight   # @io: ElementRef -> ViewportBox
  FUNC 5[снять подсветку] => clear                          # @io: () -> void
@usecases
  - [highlight]: capture/screenshot -> просит подсветить -> элемент в кадре, готов к снимку
"""
```

### engine/catalog — декларативный реестр правил
```text
"""
MODULE_CONTRACT [DOMAIN(9): соответствие ГОСТ; CONCEPT(9): реестр правил; TECH(4): данные + загрузчик]

@purpose   Источник истины «что проверяем»: каждый критерий — запись с пунктом ГОСТ, SC WCAG, уровнем, severity, типом (deterministic|llm), ссылкой на исполнителя, шаблоном фикса.
@scope     Метаданные и маппинг на стандарт; не исполняет проверки.
@input     RunConfig (уровень, включённые наборы).
@output    Отфильтрованный список Rule для исполнителей.
@links     LINKS_TO: engine/deterministic, engine/llm, report/model.
@invariants
  - Каждое правило ОБЯЗАНО иметь трассировку: пункт ГОСТ Р 52872‑2019 + критерий WCAG 2.1.
  - Маппинг ГОСТ↔WCAG — provisional, требует валидации экспертом (см. Открытые вопросы).
@rationale
  Q: Реестр-как-данные или код?
  A: Данные дают расширяемость и аудируемость, отделяют «что» от «как», и держат слоты под LLM-проверки.
@modulemap
  FUNC 7[отдать правила под уровень/наборы] => selectRules       # @io: RunConfig -> Rule[]
  FUNC 6[получить правило по id] => getRule                      # @io: ruleId -> Rule
  FUNC 5[разделить на детерм./LLM] => partitionByType            # @io: Rule[] -> {det, llm}
@usecases
  - [selectRules]: Оркестратор -> просит набор под AA -> получает правила для прогона
"""
```

### engine/deterministic — исполнитель машинных проверок
```text
"""
MODULE_CONTRACT [DOMAIN(8): соответствие ГОСТ; CONCEPT(8): rule engine; TECH(8): axe-core]

@purpose   Прогнать машинно-проверяемые правила по снимку и выдать сырые findings.
@scope     Только детерминированные проверки; нормализует результат axe к нашей модели.
@input     PageSnapshot + детерм. подмножество Rule[].
@output    Finding[] (с привязкой к ElementRef и пункту стандарта).
@links     USES_API(8): axe-core; LINKS_TO: engine/catalog, content/snapshot, report/model.
@invariants
  - Детерминирован: одинаковый снимок → одинаковые findings.
  - Не делает сети; работает офлайн.
  - Каждый axe-результат маппится на Rule из каталога или помечается «вне маппинга».
@rationale
  Q: Зачем axe-core, а не свои чеки?
  A: Зрелый, проверенный движок WCAG; писать заново — месяцы и хуже по точности. Обёртка даёт маппинг на ГОСТ.
@modulemap
  FUNC 8[прогнать детерм. правила] => runDeterministic        # @io: (PageSnapshot, Rule[]) -> Finding[]
  FUNC 6[нормализовать результат axe к Finding] => normalize  # @io: AxeResult -> Finding[]
@usecases
  - [runDeterministic]: Оркестратор -> снимок+правила -> список машинных нарушений
"""
```

### engine/llm — агент семантических проверок (post-MVP)
```text
"""
MODULE_CONTRACT [DOMAIN(7): соответствие ГОСТ; CONCEPT(8): LLM-агент/цепочка; TECH(7): function-calling]

@purpose   Оценить критерии, недоступные машине (осмысленность alt, порядок чтения, адекватность подписей) через цепочку function-calling с мультимодальной моделью.
@scope     Только LLM-проверки; деградирует в no-op, если LLM не настроен.
@input     PageSnapshot + LLM-подмножество Rule[] + клиент + тулзы.
@output    Finding[] с полем confidence и пометкой «проверить вручную».
@links     LINKS_TO: llm/client, llm/tools, engine/catalog, report/model.
@invariants
  - Побочки: сетевые вызовы к гейтвею; стоимость/латентность; шлёт скриншоты (токены).
  - LLM-finding всегда несёт confidence и НИКОГДА не выдаётся как юридически точный вердикт.
  - Выход модели валидируется zod-схемой; невалидный — отбрасывается, не падает прогон.
@rationale
  Q: Цепочка «любой сложности» в MVP?
  A: Нет — это вне MVP. Здесь фиксированный пайплайн вызовов на правило; произвольная агентность отложена.
@modulemap
  FUNC 8[прогнать LLM-проверки] => runLlmChecks           # @io: (PageSnapshot, Rule[]) -> Finding[]
  FUNC 6[собрать промпт под правило] => buildPrompt        # @io: (Rule, ctx) -> Messages
  FUNC 6[обработать tool-call и продолжить] => stepChain   # @io: ChainState -> ChainState
@usecases
  - [runLlmChecks]: Оркестратор -> снимок+LLM-правила -> findings с confidence
"""
```

### llm/client — транспорт к OpenAI-совместимому гейтвею
```text
"""
MODULE_CONTRACT [DOMAIN(2): a11y-аудит; CONCEPT(6): LLM-транспорт; TECH(8): fetch /chat/completions]

@purpose   Отправлять chat/completions с tools и мультимодальным контентом на пользовательский гейтвей.
@scope     Только транспорт: запрос, ретраи, таймаут, разбор ответа/tool_calls.
@input     Messages + tools + creds (из config/settings).
@output    Ответ модели: текст и/или tool_calls.
@links     USES_API(7): fetch; LINKS_TO: engine/llm, config/settings.
@invariants
  - Побочка: исходящая сеть на произвольный URL пользователя.
  - Ключ только в заголовке запроса; не логируется, не попадает в Report/историю.
  - Риск CORS: вызов из контекста расширения (origin расширения) — гейтвей должен это допускать.
@rationale
  Q: SDK или голый fetch?
  A: Голый fetch — без тяжёлой зависимости и совместим с любым OpenAI-подобным шлюзом.
@modulemap
  FUNC 7[выполнить chat/completions] => complete         # @io: (Messages, tools, creds) -> LlmResponse
  FUNC 5[ретрай с бэкоффом на 429/5xx] => withRetry       # @io: fn -> fn
@usecases
  - [complete]: engine/llm -> шлёт промпт+скрин -> получает вердикт/tool_calls
"""
```

### llm/tools — поверхность инструментов модели
```text
"""
MODULE_CONTRACT [DOMAIN(4): a11y-аудит; CONCEPT(7): bridge tool-call↔страница; TECH(6): function schemas]

@purpose   Определить инструменты, которые модель может вызвать (query_dom, get_computed_style, get_accessibility_tree, capture_region, contrast_ratio, get_text), и диспетчеризовать их к зонду/захвату.
@scope     Описание схем тулзов + исполнение их вызовов; не решает, что проверять.
@input     tool_call от модели.
@output    tool_result (данные страницы / контраст / кроп).
@links     LINKS_TO: content/snapshot, capture/screenshot, engine/llm.
@invariants
  - Тулзы read-only по странице (кроме временной подсветки при capture_region).
  - Каждый тулз имеет JSON-schema; неизвестный вызов → структурированная ошибка модели.
@rationale
  Q: Зачем выделять тулзы в модуль?
  A: Это явный, тестируемый контракт «что LLM может узнать о странице»; ограничивает поверхность побочек.
@modulemap
  FUNC 6[вернуть JSON-схемы тулзов] => toolSchemas        # @io: () -> ToolSpec[]
  FUNC 7[исполнить вызов тулза] => dispatchTool           # @io: ToolCall -> ToolResult
@usecases
  - [dispatchTool]: engine/llm -> модель просит контраст узла -> возвращаем число
"""
```

### capture/screenshot — захват и аннотация скриншотов
```text
"""
MODULE_CONTRACT [DOMAIN(5): a11y-аудит; CONCEPT(6): аннотированный захват; TECH(8): captureVisibleTab + canvas/offscreen]

@purpose   Сделать снимок вьюпорта с подсвеченным элементом и кропнуть крупный план узла.
@scope     Захват + кроп/аннотация; координирует подсветку через overlay.
@input     ElementRef.
@output    PNG вьюпорта + PNG-кроп (data URL) для finding.
@links     USES_API(8): chrome.tabs.captureVisibleTab; LINKS_TO: content/overlay, offscreen, report/model.
@invariants
  - Побочки: захват вкладки (rate-limited Chrome); canvas-операции в offscreen.
  - Последовательность: overlay.highlight → capture → crop → overlay.clear (всегда чистим).
  - Off-screen элемент скроллится во вьюпорт перед захватом; cross-origin iframe не захватывается корректно — помечается.
@rationale
  Q: Почему кроп в offscreen, а не в content script?
  A: CSP страницы и изоляция; offscreen даёт чистый canvas без конфликтов со страницей.
@modulemap
  FUNC 7[снять аннотированный вьюпорт] => captureViewport   # @io: ElementRef -> PngRef
  FUNC 6[кропнуть область узла] => cropElement              # @io: (Png, box) -> PngRef
@usecases
  - [captureViewport]: report/model -> просит скрин нарушения -> получает PNG для PDF
"""
```

### report/model — модель отчёта, агрегация и JSON
```text
"""
MODULE_CONTRACT [DOMAIN(8): a11y-аудит; CONCEPT(8): модель отчёта; TECH(5): pure TS]

@purpose   Канонизировать findings: слить детерм.+LLM, дедуп, посчитать сводку (по severity/уровню, pass/fail по пунктам), стабильно отсортировать, отдать JSON.
@scope     Данные отчёта и их представление в JSON; не рендерит PDF и не ходит в сеть.
@input     Finding[] (из движков) + RunConfig + метаданные страницы.
@output    Report (объект) + JSON-строка.
@links     LINKS_TO: engine/*, export/pdf, storage/history; USES_API(4): JSON.
@invariants
  - Чистая трансформация: ноль сетевых/DOM-побочек.
  - Дедуп детерминирован; порядок findings стабилен (для diff «было/стало»).
  - JSON-схема версионирована (контракт машинного выхода).
@rationale
  Q: Почему JSON живёт здесь, а PDF — отдельно?
  A: JSON — это представление самой модели; PDF — отдельная тяжёлая технология рендера.
@modulemap
  FUNC 8[собрать отчёт из findings] => buildReport     # @io: (Finding[], meta) -> Report
  FUNC 6[слить и дедуплицировать] => mergeFindings      # @io: Finding[] -> Finding[]
  FUNC 6[посчитать сводку по пунктам] => summarize       # @io: Report -> Summary
  FUNC 5[сериализовать в JSON] => toJSON                 # @io: Report -> string
@usecases
  - [buildReport]: Оркестратор -> отдаёт findings -> получает готовый Report
"""
```

### export/pdf — рендер PDF-отчёта
```text
"""
MODULE_CONTRACT [DOMAIN(5): a11y-аудит; CONCEPT(6): рендер отчёта; TECH(7): pdf-lib / offscreen]

@purpose   Собрать человекочитаемый PDF: сводка, по каждому нарушению — пункт ГОСТ/WCAG, скриншот+кроп, пояснение, как починить.
@scope     Только рендер PDF из Report; не считает и не агрегирует.
@input     Report (со ссылками на PNG).
@output    PDF-файл (Blob/bytes) для скачивания.
@links     USES_API(7): pdf-lib; LINKS_TO: report/model, capture/screenshot, popup.
@invariants
  - Побочка: сборка бинарного PDF (в offscreen, т.к. встраивание изображений ресурсоёмко).
  - Раскладка детерминирована для одинакового Report.
@rationale
  Q: pdf-lib или jsPDF?
  A: pdf-lib — чистый JS без обязательного DOM, удобно встраивать PNG и контролировать раскладку.
@modulemap
  FUNC 7[сгенерировать PDF из отчёта] => renderPdf       # @io: Report -> PdfBytes
  FUNC 5[сверстать страницу нарушения] => layoutFinding  # @io: Finding -> PdfPage
@usecases
  - [renderPdf]: Разработчик -> «Экспорт PDF» -> файл со скринами и инструкциями
"""
```

### storage/history — история прогонов
```text
"""
MODULE_CONTRACT [DOMAIN(4): a11y-аудит; CONCEPT(6): персистентность; TECH(7): IndexedDB / idb]

@purpose   Хранить результаты прогонов, листать историю, грузить прошлый отчёт, поддержать diff «было/стало».
@scope     Только персистентность; не строит и не рендерит отчёты.
@input     Report + ключ (URL+время).
@output    Сохранённые записи; списки; пары для сравнения.
@links     USES_API(7): IndexedDB(idb); LINKS_TO: orchestrator, report/model, popup.
@invariants
  - Побочка: запись/чтение IndexedDB; квоты браузера → политика ротации старых прогонов.
  - PNG-скриншоты могут раздувать базу → опция «хранить без изображений».
@rationale
  Q: IndexedDB, а не chrome.storage?
  A: Отчёты со скринами крупные и структурированные; storage.local не для таких объёмов.
@modulemap
  FUNC 6[сохранить прогон] => saveRun           # @io: Report -> runId
  FUNC 6[список прогонов по URL] => listRuns      # @io: url -> RunMeta[]
  FUNC 5[загрузить прогон] => loadRun             # @io: runId -> Report
  FUNC 5[сравнить два прогона] => diffRuns         # @io: (a,b) -> Diff
@usecases
  - [diffRuns]: Разработчик -> сравнивает до/после правок -> что починено/появилось
"""
```

---

## 4. Поток данных (глифы `STRUCTURE`)

Легенда: `▶` старт · `→` поток · `⊕` параллельные проверки · `⚡` сеть/LLM · `◇` захват/аннотация · `∑` агрегация · `⎋` возврат в UI · `○∋` хранилище.

```
▶ popup.startScan
   → orchestrator.runPipeline
      → content/snapshot.buildSnapshot  ──►  PageSnapshot
         ⊕ engine/deterministic.runDeterministic (axe-core)         ──► Finding[]det
         ⊕ engine/llm.runLlmChecks  →  llm/tools.dispatchTool ⇄ snapshot/capture
                                     →  llm/client.complete ⚡ gateway ──► Finding[]llm
      ∑ report/model.buildReport (merge · dedup · summarize)         ──► Report
      ◇ capture/screenshot (overlay.highlight → captureVisibleTab → crop → clear) ──► PNG→Report
      → report/model.toJSON ──► JSON
      → export/pdf.renderPdf ──► PDF
      → storage/history.saveRun ○∋ IndexedDB
   ⎋ popup.renderFindings / triggerExport
```

---

## 5. Структура каталогов

```
gost-a11y-extension/
├─ manifest.config.ts            # MV3-манифест (permissions: activeTab, scripting, offscreen, storage; host_permissions)
├─ package.json
├─ vite.config.ts                # Vite + @crxjs/vite-plugin
├─ tsconfig.json
├─ src/
│  ├─ popup/
│  │  ├─ index.html
│  │  └─ Popup.tsx               # UI-контроллер
│  ├─ background/
│  │  └─ orchestrator.ts         # service worker — стейт-машина прогона
│  ├─ content/
│  │  ├─ snapshot.ts             # извлечение PageSnapshot (read-only)
│  │  └─ overlay.ts              # подсветка/скролл для захвата
│  ├─ offscreen/
│  │  ├─ offscreen.html
│  │  └─ offscreen.ts            # хост canvas-кропа и рендера PDF + LLM-цикл
│  ├─ engine/
│  │  ├─ catalog.ts              # реестр правил (логика выборки)
│  │  ├─ catalog.data.ts         # определения правил + маппинг ГОСТ↔WCAG
│  │  ├─ deterministic.ts        # обёртка axe-core + нормализация
│  │  └─ llm.ts                  # агент LLM-проверок (post-MVP)
│  ├─ llm/
│  │  ├─ client.ts               # OpenAI-совместимый транспорт
│  │  └─ tools.ts                # схемы тулзов + диспетчер
│  ├─ capture/
│  │  └─ screenshot.ts           # captureVisibleTab + кроп
│  ├─ report/
│  │  └─ model.ts                # схема + агрегация + toJSON
│  ├─ export/
│  │  └─ pdf.ts                  # Report → PDF (pdf-lib)
│  ├─ storage/
│  │  └─ history.ts              # IndexedDB
│  ├─ config/
│  │  └─ settings.ts             # настройки + креды LLM
│  └─ shared/
│     ├─ types.ts                # PageSnapshot, Finding, Report, Rule…
│     └─ messaging.ts            # типизированный RPC между контекстами
└─ tests/
   ├─ deterministic.spec.ts      # фикстуры HTML → ожидаемые findings
   ├─ catalog.spec.ts            # целостность маппинга ГОСТ↔WCAG
   └─ report-model.spec.ts       # дедуп/сводка/стабильность порядка
```

---

## 6. Риски, граничные случаи, открытые вопросы

**Риски**
- **Жизненный цикл SW (~30с простоя):** длинные LLM-цепочки убьются. Митигация — агентный цикл в offscreen + keepalive-порт.
- **CORS на пользовательском гейтвее:** вызов из origin расширения может отклоняться шлюзом. Документировать требования; тест `probeGateway`.
- **Секрет в `chrome.storage.local`:** не шифруется ОС. Митигация — предупреждение в UI + опция «не хранить ключ».
- **LLM-галлюцинации/стоимость/латентность:** семантические findings ненадёжны как вердикт. Митигация — confidence + «проверить вручную», мультимодальные токены контролировать.
- **Маппинг ГОСТ↔WCAG:** ядро ценности; ошибка маппинга = неверная трассировка. Требует валидации экспертом.

**Граничные случаи**
- `captureVisibleTab` снимает только вьюпорт и rate-limited; off-screen узлы скроллим, sticky-шапки могут перекрывать.
- Cross-origin iframe и (частично) shadow DOM недоступны/ограничены → помечать как непокрытое, не выдавать «пройдено».
- SPA/динамика: снимок только на момент триггера; модалки/меню вручную; авто-обход состояний — вне scope.
- Большие страницы: производительность axe и размер снимка/истории.

**Открытые вопросы**
1. Авторитетный источник маппинга пунктов ГОСТ Р 52872‑2019 ↔ критериев WCAG 2.1 — таблица/эксперт? (сейчас provisional)
2. Нужен ли режим «ручной чек-лист» для критериев, не покрываемых ни скриптом, ни LLM? (вне MVP)
3. Политика ключа: хранить в local с предупреждением, или только за сессию без сохранения?
4. Покрытие iframe / shadow DOM в v1 — обязательное или отложить?
5. Уровень AA достаточен, или таргетим часть AAA?

---

## 7. Порядок сборки (тонкий вертикальный срез → MVP)

1. **Каркас контрактов:** `shared/types` + `shared/messaging` + `config/settings`. Без них рассинхронятся контексты.
2. **Спинной мозг прогона:** `content/snapshot` + минимальный `background/orchestrator` + `popup`. Цель — round-trip: клик → снимок → заглушка-finding → список в popup.
3. **Реальные машинные проверки:** `engine/catalog` (+`catalog.data`) + `engine/deterministic` (axe-core). ⟵ **детерм. ядро работает: настоящие findings в popup.**
4. **Машинный выход:** `report/model` (+`toJSON`). Структурированный JSON.
5. **Скриншоты:** `content/overlay` + `capture/screenshot` + offscreen. Аннотированные PNG.
6. **PDF:** `export/pdf`. ⟵ **MVP «готов»: JSON + PDF со скринами и инструкциями.**
7. **История:** `storage/history` (+`diffRuns`). Сравнение «было/стало».
8. **LLM-слой (post-MVP):** `llm/client` + `llm/tools` + `engine/llm`. Подключаемые семантические проверки.

Шаги 1–6 дают рабочий детерминированный инструмент **до единой строчки LLM-кода**.
