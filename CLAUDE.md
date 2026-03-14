# GOST A11Y Automation

## Идея

Автоматизированное тестирование веб-сайтов на соответствие российским ГОСТам по доступности для слепых и слабовидящих:
- **ГОСТ Р ИСО 40500-2014** (= WCAG 2.0)
- **ГОСТ Р 52872-2019** (расширенные требования РФ)

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

- **80% проверок** закрываются скриптами без вызова модели
- **LLM** вызывается только когда скрипт не может вынести вердикт (UNCERTAIN)
- **Logger** — мост между скриптовым и AI-слоем: формирует `[FALLBACK_CONTEXT]` с точным слепком состояния

## Архитектура: 4-шаговый пайплайн

Каждая проверка наследуется от `GostCheck` (base_check.py) и реализует:

1. **collect(page)** — сбор данных через Playwright (JS в браузере)
2. **classify(data)** — классификация: зона, видимость, DOM-позиция и т.д.
3. **judge(classified)** — детерминированный вердикт: PASS / FAIL / UNCERTAIN
4. **fallback** (только при UNCERTAIN) — формирование контекста → LLM-агент

## Структура проекта

```
gost_a11y/
├── __init__.py          # Пакет
├── models.py            # Verdict, CheckResult, CandidateInfo, FallbackContext, LLMVerdict
├── base_check.py        # GostCheck — абстрактный базовый класс, пайплайн
├── logger.py            # Структурированный ГОСТ-aware логгер, grep-friendly
├── browser.py           # Playwright lifecycle (контекстный менеджер)
├── llm_fallback.py      # Claude API интеграция (заглушка в MVP)
├── registry.py          # Реестр всех проверок
├── runner.py            # CLI точка входа, оркестрация, JSON-отчёт
├── targets.py           # Реестр целевых госсайтов (20 + эталон ВОС)
└── checks/
    ├── __init__.py
    └── check_accessibility_link.py  # Первая проверка: ссылка на версию для слабовидящих
```

Вспомогательные файлы:
- `gost_checks_pseudocode.py` — псевдокод принципов компиляции ГОСТ → тест
- `mapping.md` — маппинг 38 критериев WCAG A/AA → тип проверки (AXE / AXE+AI / AI)
- `targets.md` — описание целевых сайтов

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
- `[CHECK]` — шаги проверки
- `[FALLBACK_CONTEXT]` — контекст для LLM
- `[LLM]` — вердикт LLM
- `[RESULT]` — итоговый результат
- `[SUITE]` — уровень набора тестов
- `[BROWSER]` — Playwright

Результаты: `ATTEMPT` / `SUCCESS` / `FAIL` / `INFO`

Лог grep-friendly:
```bash
grep "\[FAIL\]" reports/run.log           # все провалы
grep "\[UNCERTAIN\]" reports/run.log      # все неопределённости
grep "\[GOST_R_52872\]" reports/run.log   # проверки по конкретному ГОСТу
grep "\[FALLBACK_CONTEXT\]" reports/run.log  # контексты для LLM
```

## Целевые сайты

Эталон: **vos.org.ru** (Всероссийское общество слепых) — калибровка инструмента.
Если эталон не проходит проверку — проблема в тесте, не в сайте.

20 госсайтов по категориям: federal, service, judicial, specialized.
Полный список в `targets.py`.

## Маппинг ГОСТ → проверки

Подробности в `mapping.md`. Сводка:
- **~6** чисто детерминированных (AXE) — lang, contrast, валидный HTML
- **~18** гибридных (AXE+AI) — базовая проверка скриптом, глубокая — LLM
- **~14** преимущественно AI — семантика, визуал, поведение

## Стек

- **Python** — основной язык
- **Playwright** — браузерная автоматизация, a11y tree, скриншоты
- **axe-core** — инжектируется через Playwright для детерминированных правил
- **Claude API** — LLM fallback (средние модели, без оркестратора в MVP)

## Запуск

```bash
cd /home/koskokos/gost-a11y-automation
python -m gost_a11y.runner https://kremlin.ru/
python -m gost_a11y.runner https://kremlin.ru/ --no-headless  # с окном браузера
```

## Текущий статус

Реализовано:
- [x] Каркас проекта: models, base_check, logger, browser, runner, registry
- [x] Первая проверка: check_accessibility_link (ГОСТ Р 52872-2019 п.5.1)
  - collect: JS поиск ссылок по ключевым словам и href-паттернам
  - classify: зона (header/nav/footer/sidebar), видимость, DOM-позиция
  - judge: многоветвистая логика PASS/FAIL/UNCERTAIN
  - Яндекс-валидация при FAIL: проверка существования спецверсии через поиск
- [x] Реестр 20 целевых госсайтов + эталон ВОС
- [x] Маппинг 38 критериев WCAG → тип проверки

Не реализовано:
- [ ] LLM fallback (заглушка)
- [ ] axe-core интеграция
- [ ] Остальные 27+ проверок из mapping.md
- [ ] Batch-запуск по всем целевым сайтам
- [ ] Сравнительный отчёт (сайт vs эталон)
