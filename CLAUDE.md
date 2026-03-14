# GOST A11Y Automation

## Идея

Автоматизированное тестирование веб-сайтов на соответствие российским ГОСТам по доступности:
- **ГОСТ Р 52872-2019** (основной — базируется на WCAG 2.1 A/AA + российская специфика)
- **ГОСТ Р ИСО 40500-2014** (= WCAG 2.0)
- **ГОСТ Р 70176-2022** (доступность PDF-документов)
- **Приказ Минцифры № 953** (12 обязательных требований к госсайтам, с 01.09.2024, штрафы 20-30 тыс. руб.)

Целевая аудитория — государственные сайты РФ, которые **обязаны** соблюдать эти ГОСТы по закону.

## Принцип: Script-First, LLM as Fallback

Это **не** AI-first решение. AI — дорогой fallback, а не основной инструмент.

```
URL → Playwright (сбор данных) → Детерминированные скрипты → PASS/FAIL/UNCERTAIN
                                                                      │
                                                              только при UNCERTAIN
                                                                      ↓
                                                            Logger → LLM-агент
```

- **90% проверок** (20 из 22) закрываются скриптами без вызова модели
- **LLM** вызывается в 3 ролях:
  1. **Арбитр при UNCERTAIN** — скрипт нашёл элемент но не уверен в вердикте (зона unknown, неоднозначная позиция)
  2. **Vision-анализ** — скрипт делает скриншот img, LLM смотрит картинку ("есть ли текст?")
  3. **Семантический анализ** — скрипт находит подозрительные места, LLM интерпретирует контекст
- **Logger** — мост между скриптовым и AI-слоем: формирует `[FALLBACK_CONTEXT]` с точным слепком состояния

## Архитектура: 4-шаговый пайплайн

Каждая проверка наследуется от `GostCheck` (base_check.py) и реализует:

1. **collect(page)** — сбор данных через Playwright (JS в браузере)
2. **classify(data)** — классификация: зона, видимость, DOM-позиция и т.д.
3. **judge(classified)** — детерминированный вердикт: PASS / FAIL / UNCERTAIN
4. **fallback** (только при UNCERTAIN) — формирование контекста → LLM-агент

## Двойной прогон: основная + спецверсия

`runner.py` автоматически делает два прогона в изолированных контекстах браузера:

1. **Основная страница** — все 22 проверки
2. **Спецверсия** — если CheckAccessibilityLink нашла кнопку, скрипт кликает по ней в новом контексте и прогоняет 20 проверок (без CheckAccessibilityLink и CheckSpecialVersion)

Результат — сравнительная таблица: какие проверки прошли на основной и какие на спецверсии.

## Структура проекта

```
gost_a11y/
├── __init__.py          # Пакет
├── models.py            # Verdict, CheckResult, CandidateInfo, FallbackContext, LLMVerdict
├── base_check.py        # GostCheck — абстрактный базовый класс, пайплайн
├── logger.py            # Структурированный ГОСТ-aware логгер, grep-friendly
├── browser.py           # Playwright lifecycle (контекстный менеджер, системный Chrome)
├── llm_fallback.py      # OpenRouter API → qwen/qwen3.5-35b-a3b (vision-language, thinking)
├── axe_helper.py        # Инжекция axe-core через Playwright, запуск по правилам
├── registry.py          # Реестр всех 22 проверок
├── runner.py            # CLI: двойной прогон (основная + спецверсия), JSON-отчёт
├── targets.py           # Реестр целевых госсайтов (20 + эталон ВОС)
└── checks/
    ├── __init__.py               # Реэкспорт всех 22 проверок
    │
    │  # Фаза 1: чистый скрипт (8 проверок)
    ├── check_accessibility_link.py  # ГОСТ 52872 п.5.1 — ссылка на спецверсию
    ├── check_page_lang.py           # WCAG 3.1.1 (A) — lang на <html>
    ├── check_page_title.py          # WCAG 2.4.2 (A) — <title> наличие и осмысленность
    ├── check_img_alt.py             # WCAG 1.1.1 (A) — alt-тексты на img
    ├── check_form_labels.py         # WCAG 3.3.2 (A) — label на input (П953 п.12)
    ├── check_skip_link.py           # WCAG 2.4.1 (A) — skip-link и landmark roles
    ├── check_viewport_zoom.py       # WCAG 1.4.4 (AA) — viewport не блокирует zoom (П953 п.2)
    ├── check_captcha.py             # П953 п.5 — CAPTCHA с аудио-альтернативой
    │
    │  # Фаза 2: axe-core (6 проверок)
    ├── check_contrast.py            # WCAG 1.4.3 (AA) — контраст 4.5:1 / 3:1 (П953 п.7)
    ├── check_valid_html.py          # WCAG 4.1.1 (A) — валидный HTML, уникальные id
    ├── check_aria.py                # WCAG 4.1.2 (A) — ARIA роли и атрибуты
    ├── check_focus_visible.py       # WCAG 2.4.7 (AA) — outline:none без замены (П953 п.1)
    ├── check_link_text.py           # WCAG 2.4.4 (A) — ссылки без текста (П953 п.6)
    ├── check_autoplay.py            # WCAG 1.4.2 (A) — autoplay без muted/controls (П953 п.10)
    │
    │  # Фаза 3: спецверсия (1 проверка, объединяет #15-#18)
    ├── check_special_version.py     # ГОСТ 52872 — клик → панель настроек (шрифт/цвет)
    │
    │  # Фаза 4: гибридные скрипт + LLM fallback (5 проверок)
    ├── check_heading_structure.py   # WCAG 1.3.1 (A) — h1-h6 иерархия, пропуски
    ├── check_keyboard_access.py     # WCAG 2.1.1 (A) — tabindex, onclick без keyboard (П953 п.1)
    ├── check_focus_trap.py          # WCAG 2.1.2 (A) — ловушки фокуса, модальные без close
    ├── check_focus_order.py         # WCAG 2.4.3 (A) — tabindex>0, DOM vs visual порядок
    ├── check_form_errors.py         # WCAG 3.3.1 (A) — aria-invalid, role=alert (П953 п.9, п.12)
    │
    │  # Фаза 5: AI-only / гибридные с LLM (2 проверки)
    ├── check_text_in_images.py      # WCAG 1.4.5 (AA) — скриншот img → LLM vision
    └── check_color_only.py          # WCAG 1.4.1 (A) — ссылки без underline → LLM (П953 п.8)
```

Вспомогательные файлы:
- `run_all_targets.py` — batch-прогон по 20 сайтам, изолированные отчёты
- `gost_checks_pseudocode.py` — псевдокод принципов компиляции ГОСТ → тест
- `mapping.md` — маппинг 38 критериев WCAG A/AA → тип проверки (AXE / AXE+AI / AI)
- `targets.md` — описание целевых сайтов
- `.env` — OPENROUTER_API_KEY

## Реализованные проверки (22 шт)

### Фаза 1: Чистый скрипт (8 проверок)

| # | Файл | ГОСТ / WCAG / П953 | Что делает |
|---|------|---------------------|------------|
| 1 | check_accessibility_link | ГОСТ 52872 п.5.1 | Поиск `<a>`, `<button>`, `[role]` по regex-паттернам (strong/weak). Зоны: header/nav/footer. Яндекс-валидация при FAIL. |
| 2 | check_page_lang | WCAG 3.1.1 (A) | `<html lang="ru">` — наличие, валидность BCP 47, fallback xml:lang |
| 3 | check_page_title | WCAG 2.4.2 (A), П953 п.6 | `<title>` — наличие, непустой, не шаблонный (regex BOILERPLATE_PATTERNS) |
| 4 | check_img_alt | WCAG 1.1.1 (A), П953 п.4 | Все видимые `<img>` имеют alt. Декоративные (role=presentation, aria-hidden) пропускаются |
| 5 | check_form_labels | WCAG 3.3.2 (A), П953 п.12 | `<input>` без `<label>`, aria-label, aria-labelledby или title |
| 6 | check_skip_link | WCAG 2.4.1 (A) | Skip-to-content ссылка + landmark roles (main, nav, banner, contentinfo) |
| 7 | check_viewport_zoom | WCAG 1.4.4 (AA), П953 п.2 | `<meta viewport>` не содержит user-scalable=no или maximum-scale<2 |
| 8 | check_captcha | П953 п.5 | Обнаружение reCAPTCHA/hCaptcha/custom/Turnstile, проверка аудио-альтернативы |

### Фаза 2: axe-core интеграция (6 проверок)

| # | Файл | ГОСТ / WCAG / П953 | Что делает |
|---|------|---------------------|------------|
| 9 | check_contrast | WCAG 1.4.3 (AA), П953 п.7 | axe-core правила color-contrast, color-contrast-enhanced |
| 10 | check_valid_html | WCAG 4.1.1 (A) | axe-core: duplicate-id, списки, вложенность |
| 11 | check_aria | WCAG 4.1.2 (A) | axe-core: aria-allowed-attr, aria-roles, aria-valid-attr и др. |
| 12 | check_focus_visible | WCAG 2.4.7 (AA), П953 п.1 | CSS-анализ: `:focus { outline: none }` без box-shadow/border замены |
| 13 | check_link_text | WCAG 2.4.4 (A), П953 п.6 | axe-core: link-name, link-in-text-block |
| 14 | check_autoplay | WCAG 1.4.2 (A), П953 п.10 | `<video>/<audio>` с autoplay без muted и без controls |

### Фаза 3: Спецверсия (1 проверка, объединяет задачи #15-#18)

| # | Файл | ГОСТ / П953 | Что делает |
|---|------|-------------|------------|
| 15 | check_special_version | ГОСТ 52872, П953 п.2, п.7 | Находит кнопку/ссылку спецверсии → кликает → ищет панель настроек (font_size, color_scheme, spacing, images, reset) → замеряет computed style до/после |

### Фаза 4: Гибридные — скриптовая часть + LLM fallback при UNCERTAIN (5 проверок)

| # | Файл | ГОСТ / WCAG / П953 | Что делает скрипт | Когда LLM |
|---|------|---------------------|--------------------|-----------|
| 16 | check_heading_structure | WCAG 1.3.1 (A) | h1-h6 иерархия, пропуски уровней, пустые заголовки | Если структура неоднозначная |
| 17 | check_keyboard_access | WCAG 2.1.1 (A), П953 п.1 | tabindex<0 на интерактивных, onclick без keyboard handler | Если нужна оценка покрытия |
| 18 | check_focus_trap | WCAG 2.1.2 (A) | Модальные без close, tabindex>0, multiple autofocus | Если нужна runtime проверка |
| 19 | check_focus_order | WCAG 2.4.3 (A) | tabindex>0, DOM vs визуальный порядок (200px threshold) | Если нужна оценка логичности |
| 20 | check_form_errors | WCAG 3.3.1 (A), П953 п.9, п.12 | aria-invalid, aria-describedby, role=alert, .error containers | Если есть required но нет механизмов ошибок |

### Фаза 5: AI-only / гибридные с LLM (2 проверки)

| # | Файл | ГОСТ / WCAG / П953 | Как работает |
|---|------|---------------------|--------------|
| 21 | check_text_in_images | WCAG 1.4.5 (AA) | Скрипт находит видимые img >80px → element.screenshot() → LLM vision: "есть ли читаемый текст (не логотип)?" |
| 22 | check_color_only | WCAG 1.4.1 (A), П953 п.8 | Скрипт ищет: ссылки без underline, обязательные поля с цветной *, активные пункты меню только с цветом → если найдены → UNCERTAIN → LLM анализирует контекст |

## LLM интеграция

### Модель и API
- **Провайдер:** OpenRouter API (OpenAI-совместимый)
- **Модель:** `qwen/qwen3.5-35b-a3b` (vision-language, thinking-модель)
- **API-ключ:** `OPENROUTER_API_KEY` в `.env`
- **max_tokens:** 32000 (модель тратит ~1300 токенов на thinking, нужен запас)

### Особенности qwen3.5-35b-a3b
- **Thinking-модель:** ответ в двух полях — `reasoning` (цепочка рассуждений) и `content` (финальный ответ)
- При недостаточном max_tokens reasoning съедает весь бюджет, content остаётся null
- Логирование раздельное: `[RESPONSE]` для content, `[THINKING]` для reasoning, `[USAGE]` для токенов

### 3 роли LLM

**Роль 1: Арбитр при UNCERTAIN**
- Скрипт нашёл элемент, но не уверен в вердикте
- Получает: текст ГОСТа + структурированные данные от скрипта
- Возвращает: PASS/FAIL + reasoning + confidence
- Пример: zhit-vmeste.ru — ссылка в зоне `unknown`, top: 224px

**Роль 2: Vision-анализ (check_text_in_images)**
- Скрипт делает скриншот img через element.screenshot()
- LLM получает base64 картинку + метаданные (размер, alt)
- Отвечает: has_text, text_content, verdict

**Роль 3: Контекстный анализ (check_color_only)**
- Скрипт находит подозрительные места (ссылки без underline и т.д.)
- Формирует `suspects_formatted` — читаемый текст для LLM
- Кастомный system_prompt через `FallbackContext.extra["llm_system_prompt"]`
- LLM получает конкретные случаи и интерпретирует

### Контракт ответа LLM
```json
{"verdict": "PASS|FAIL", "reasoning": "2-3 предложения", "confidence": 0.85}
```
LLM **обязан** выбрать PASS или FAIL. UNCERTAIN недопустим. При сомнении — FAIL.

## axe-core интеграция

- **Пакет:** `axe-core-python` (содержит axe.min.js)
- **Инжекция:** `axe_helper.inject_axe(page)` — один раз на страницу, кешируется
- **Запуск:** `axe_helper.run_axe(page, rules=["color-contrast"])` — фильтр по правилам через `runOnly`
- **Результат:** violations с nodes (html, target, impact, failureSummary), passes_count

## Конвенции кода

### Контракты модулей

Каждый .py файл начинается с:
```python
# FILE: path/to/file.py
# VERSION: x.y.z
# MODULE_CONTRACT:
# PURPOSE: [Что делает модуль]
# SCOPE: [Область]
# KEYWORDS_MODULE: [ключевые слова]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CONST/FUNC/CLASS [описание] => ИмяСущности
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Последнее изменение]
# CHANGE_SUMMARY: [История]
# END_CHANGE_SUMMARY
```

### Контракты функций

```python
# START_FUNCTION_имя
# CONTRACT:
# PURPOSE: [Что делает]
# INPUTS: описание параметров с типами
# OUTPUTS: описание возвращаемого с типами
# SIDE_EFFECTS: [Побочные эффекты]
# KEYWORDS: [ключевые слова]
def имя(...):
    ...
# END_FUNCTION_имя
```

### Блочные маркеры

Логические блоки внутри функций оборачиваются:
```python
# START_BLOCK_NAME: [Описание что делает блок.]
...код...
# END_BLOCK_NAME
```

### Логирование

Формат: `[CATEGORY][GOST_REF][WCAG_REF][STEP][Status] Сообщение [RESULT]`

Категории:
- `[CHECK]` — шаги проверки (collect, classify, judge)
- `[FALLBACK_CONTEXT]` — контекст для LLM
- `[LLM]` — вызов LLM: `[CALL]`, `[RESPONSE]`, `[THINKING]`, `[USAGE]`, `[VERDICT]`
- `[VISION]` — vision-анализ: `[Call]`, `[Response]`, `[Verdict]`
- `[RESULT]` — итоговый результат проверки
- `[SUITE]` — уровень набора тестов, `[SUITE][SPECIAL]` — прогон на спецверсии
- `[BROWSER]` — Playwright навигация
- `[AXE]` — axe-core инжекция и запуск
- `[BATCH]` — batch-прогон по нескольким сайтам

Результаты: `ATTEMPT` / `SUCCESS` / `FAIL` / `INFO`

Лог grep-friendly:
```bash
grep "\[FAIL\]" reports/run.log              # все провалы
grep "\[UNCERTAIN\]" reports/run.log         # все неопределённости
grep "\[GOST_R_52872\]" reports/run.log      # проверки по конкретному ГОСТу
grep "\[FALLBACK_CONTEXT\]" reports/run.log  # контексты для LLM
grep "\[LLM\].*\[CALL\]" reports/run.log     # все вызовы LLM
grep "\[VISION\]" reports/run.log            # все vision-анализы
grep "\[SUITE\]\[SPECIAL\]" reports/run.log  # прогон спецверсии
```

## Целевые сайты

Эталон: **vos.org.ru** (Всероссийское общество слепых) — калибровка инструмента.

20 госсайтов по категориям: federal, service, judicial, specialized.
Полный список в `targets.py`.

### Результаты batch-прогона (20 сайтов)

Ни один госсайт не прошёл все проверки. Типичный результат: 13 PASS / 7 FAIL.
- **Лучший:** МВД (16 PASS / 4 FAIL)
- **Эталон ВОС:** 15 PASS / 5 FAIL
- **Худший:** ФРИИ sfri.ru (0/20 — сайт не загрузился, SSL)
- **Типичные FAIL:** контрастность, outline:none, отсутствие `<main>`, поля без label

## Стек

- **Python 3.12** — основной язык
- **Playwright** — браузерная автоматизация, системный Chrome (/usr/bin/google-chrome)
- **axe-core** — инжектируется через Playwright для детерминированных a11y-правил
- **OpenRouter API** — LLM (qwen/qwen3.5-35b-a3b, vision-language, thinking)
- **openai SDK** — клиент для OpenRouter (совместимый API)

## Запуск

```bash
cd /home/koskokos/gost-a11y-automation

# Один сайт (основная + спецверсия)
python3 -m gost_a11y.runner https://www.vos.org.ru/

# Один сайт, без проверки спецверсии
python3 -m gost_a11y.runner https://kremlin.ru/ --no-special

# Один сайт, с окном браузера
python3 -m gost_a11y.runner https://kremlin.ru/ --no-headless

# Все 20 сайтов (batch)
python3 run_all_targets.py

# Отчёты
reports/report_YYYYMMDD_HHMMSS.json   # одиночный прогон
reports/batch_YYYYMMDD_HHMMSS/        # batch: summary.json + {site_id}.json + {site_id}.log
```

## Покрытие Приказа Минцифры № 953

| П953 | Требование | Наша проверка | Статус |
|------|-----------|---------------|--------|
| п.1 | Клавиатурный доступ без ограничений по времени | #17, #18, #12 | ✅ |
| п.2 | Текст масштабируется на 200% | #7, #15 | ✅ |
| п.3 | PDF совместимы с AT | #28 | ❌ |
| п.4 | Нетекстовый контент имеет alt | #4, #21 | ✅ |
| п.5 | CAPTCHA доступна | #8 | ✅ |
| п.6 | Заголовки и ссылки описательны | #3, #13 | ✅ |
| п.7 | Контрастность по ГОСТ | #9, #15 | ✅ |
| п.8 | Не только сенсорные характеристики | #22 | ✅ |
| п.9 | Обратная связь текстом | #20 | ✅ |
| п.10 | Автообновления контролируются | #14 | ✅ |
| п.11 | Фокус не меняет контекст | #27 | ❌ |
| п.12 | Поля форм с описаниями | #5, #20 | ✅ |

**10 из 12 пунктов П953 покрыты.**

## Не реализовано (TODO)

### Высокий приоритет (3 проверки из плана)
- [ ] **#19 Осмысленность alt** (WCAG 1.1.1) — скрипт уже проверяет наличие alt (#4), нужен LLM vision для проверки *соответствует ли alt содержимому картинки*
- [ ] **#27 Контекст не меняется при фокусе** (WCAG 3.2.1, П953 п.11) — при фокусе нет неожиданных изменений. Сложно проверить скриптом, нужен runtime Tab-обход
- [ ] **#28 PDF доступность** (ГОСТ Р 70176-2022, П953 п.3) — найти PDF-ссылки, скачать, проверить tagged PDF

### Средний приоритет (WCAG критерии не в плане)
- [ ] Субтитры для видео (WCAG 1.2.1-1.2.5) — нет видео-анализа
- [ ] Язык частей страницы (WCAG 3.1.2) — AXE+AI
- [ ] Множественные способы навигации (WCAG 2.4.5) — AI
- [ ] Единообразная навигация (WCAG 3.2.3-3.2.4) — AI, нужен multi-page анализ

### Низкий приоритет
- [ ] Тайминг (WCAG 2.2.1-2.2.2) — обнаружение таймеров
- [ ] Вспышки (WCAG 2.3.1) — видео-анализ
- [ ] Сенсорные характеристики (WCAG 1.3.3) — чисто AI
- [ ] Предложение исправления ошибок (WCAG 3.3.3-3.3.4) — AI

### Инфраструктура
- [ ] Интеграция двойного прогона (основная + спецверсия) в `run_all_targets.py`
- [ ] Сравнительный отчёт между сайтами (рейтинг)
- [ ] Retry для нестабильных сайтов (таймауты)
- [ ] Кеширование axe-core результатов
- [ ] Параллельный прогон сайтов
