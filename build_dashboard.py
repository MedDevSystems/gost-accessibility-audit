# FILE: build_dashboard.py
# VERSION: 1.0.0
# MODULE_CONTRACT:
# PURPOSE: [Генерация HTML-дашборда из batch-отчётов проверки ГОСТ-доступности.
#           Находит последнюю директорию reports/batch_*/ (или принимает путь аргументом),
#           читает summary.json + все {site_id}.json, генерирует dashboard/index.html
#           со вшитыми данными — самодостаточный HTML без внешних зависимостей.]
# SCOPE: [Dashboard, HTML, генерация отчёта, визуализация]
# KEYWORDS_MODULE: [dashboard, html, report, build, batch, summary]
# END_MODULE_CONTRACT

# MODULE_MAP:
# CONST [Маппинг категорий на русские названия] => CATEGORY_NAMES
# CONST [Порядок категорий] => CATEGORY_ORDER
# FUNC  [Поиск последней batch-директории] => find_latest_batch_dir
# FUNC  [Загрузка данных из batch-директории] => load_batch_data
# FUNC  [Генерация демо-данных] => generate_demo_data
# FUNC  [Генерация HTML-дашборда] => generate_html
# FUNC  [Точка входа] => main
# END_MODULE_MAP

# START_CHANGE_SUMMARY
# LAST_CHANGE: [Первоначальная реализация.]
# CHANGE_SUMMARY: [v1.0.0 — полная реализация с доступным HTML, категориями, деталями.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


CATEGORY_NAMES: Dict[str, str] = {
    "reference": "Эталон",
    "president": "Глава государства",
    "legislative": "Законодательная власть",
    "judicial": "Судебная власть",
    "government": "Правительство",
    "ministry": "Министерства",
    "service": "Госуслуги",
    "service_federal": "Федеральные службы",
    "agency": "Федеральные агентства",
    "corporation": "Государственные корпорации",
    "fund": "Внебюджетные фонды",
    "portal": "Порталы и информационные системы",
    "district": "Федеральные округа",
    "regional": "Региональные порталы",
    "specialized": "Специализированные",
}

CATEGORY_ORDER: List[str] = [
    "reference",
    "president",
    "legislative",
    "judicial",
    "government",
    "ministry",
    "service",
    "service_federal",
    "agency",
    "corporation",
    "fund",
    "portal",
    "district",
    "regional",
    "specialized",
]


# START_FUNCTION_find_latest_batch_dir
# CONTRACT:
# PURPOSE: [Находит последнюю по имени директорию reports/batch_*/.]
# INPUTS: base_dir: str — корневая директория проекта.
# OUTPUTS: Optional[str] — путь к директории или None.
# SIDE_EFFECTS: [Нет.]
# KEYWORDS: [find, batch, latest, directory]
def find_latest_batch_dir(base_dir: str) -> Optional[str]:
    """Находит последнюю batch-директорию в reports/."""
    pattern = os.path.join(base_dir, "reports", "batch_*")
    dirs = sorted(glob.glob(pattern))
    if dirs:
        return dirs[-1]
    return None
# END_FUNCTION_find_latest_batch_dir


# START_FUNCTION_load_batch_data
# CONTRACT:
# PURPOSE: [Загружает summary.json и все {site_id}.json из batch-директории.]
# INPUTS: batch_dir: str — путь к batch-директории.
# OUTPUTS: Tuple[dict, list[dict]] — (summary, site_reports).
# SIDE_EFFECTS: [Чтение файлов.]
# KEYWORDS: [load, batch, data, json]
def load_batch_data(batch_dir: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Загружает данные из batch-директории."""
    summary_path = os.path.join(batch_dir, "summary.json")
    if not os.path.exists(summary_path):
        raise FileNotFoundError(f"summary.json не найден в {batch_dir}")

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    site_reports = []
    for site_info in summary.get("sites", []):
        report_file = site_info.get("report_file", f"{site_info['id']}.json")
        report_path = os.path.join(batch_dir, report_file)
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                site_reports.append(json.load(f))
        else:
            # Формируем минимальный отчёт из summary
            site_reports.append({
                "id": site_info["id"],
                "name": site_info["name"],
                "url": site_info["url"],
                "category": site_info.get("category", "specialized"),
                "is_reference": site_info.get("is_reference", False),
                "summary": {
                    "total": site_info.get("pass", 0) + site_info.get("fail", 0) + site_info.get("uncertain", 0),
                    "pass": site_info.get("pass", 0),
                    "fail": site_info.get("fail", 0),
                    "uncertain": site_info.get("uncertain", 0),
                },
                "checks": [],
            })

    return summary, site_reports
# END_FUNCTION_load_batch_data


# START_FUNCTION_generate_demo_data
# CONTRACT:
# PURPOSE: [Генерирует демонстрационные данные когда реальных отчётов нет.]
# INPUTS: Нет.
# OUTPUTS: Tuple[dict, list[dict]] — (summary, site_reports).
# SIDE_EFFECTS: [Нет.]
# KEYWORDS: [demo, data, generate]
def generate_demo_data() -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Генерирует демо-данные для дашборда."""
    import random
    random.seed(42)

    demo_checks_meta = [
        ("GOST_R_52872_2019", "5.1", "SPECIAL", "Ссылка на версию для слабовидящих"),
        ("GOST_R_52872_2019", "WCAG 3.1.1", "3.1.1", "Язык страницы"),
        ("GOST_R_52872_2019", "WCAG 2.4.2", "2.4.2", "Заголовок страницы"),
        ("GOST_R_52872_2019", "WCAG 1.1.1", "1.1.1", "Alt-тексты изображений"),
        ("GOST_R_52872_2019", "WCAG 3.3.2", "3.3.2", "Подписи к полям форм"),
        ("GOST_R_52872_2019", "WCAG 2.4.1", "2.4.1", "Skip-link и landmarks"),
        ("GOST_R_52872_2019", "WCAG 1.4.4", "1.4.4", "Масштабирование viewport"),
        ("GOST_R_52872_2019", "П953 п.5", "CAPTCHA", "CAPTCHA с аудио"),
        ("GOST_R_52872_2019", "ГОСТ 52872", "SPECIAL", "Панель спецверсии"),
        ("GOST_R_52872_2019", "WCAG 1.4.3", "1.4.3", "Контрастность текста"),
        ("GOST_R_52872_2019", "WCAG 4.1.1", "4.1.1", "Валидный HTML"),
        ("GOST_R_52872_2019", "WCAG 4.1.2", "4.1.2", "ARIA-атрибуты"),
        ("GOST_R_52872_2019", "WCAG 2.4.7", "2.4.7", "Видимый фокус"),
        ("GOST_R_52872_2019", "WCAG 2.4.4", "2.4.4", "Текст ссылок"),
        ("GOST_R_52872_2019", "WCAG 1.4.2", "1.4.2", "Автовоспроизведение"),
        ("GOST_R_52872_2019", "WCAG 1.3.1", "1.3.1", "Структура заголовков"),
        ("GOST_R_52872_2019", "WCAG 2.1.1", "2.1.1", "Клавиатурный доступ"),
        ("GOST_R_52872_2019", "WCAG 2.1.2", "2.1.2", "Ловушки фокуса"),
        ("GOST_R_52872_2019", "WCAG 2.4.3", "2.4.3", "Порядок фокуса"),
        ("GOST_R_52872_2019", "WCAG 3.3.1", "3.3.1", "Ошибки форм"),
        ("GOST_R_52872_2019", "WCAG 1.4.5", "1.4.5", "Текст в изображениях"),
        ("GOST_R_52872_2019", "WCAG 1.4.1", "1.4.1", "Цвет как единственный канал"),
    ]

    demo_fail_reasons = {
        "5.1": "Кнопка спецверсии не найдена",
        "WCAG 3.1.1": "Атрибут lang отсутствует на <html>",
        "WCAG 2.4.2": "Шаблонный заголовок: 'Главная страница'",
        "WCAG 1.1.1": "3 изображения без alt-текста",
        "WCAG 3.3.2": "2 поля без label и aria-label",
        "WCAG 2.4.1": "Отсутствует landmark <main>",
        "WCAG 1.4.4": "user-scalable=no в meta viewport",
        "П953 п.5": "CAPTCHA без аудио-альтернативы",
        "ГОСТ 52872": "Панель спецверсии не обнаружена",
        "WCAG 1.4.3": "12 элементов с контрастом ниже 4.5:1",
        "WCAG 4.1.1": "5 дублированных id",
        "WCAG 4.1.2": "aria-labelledby ссылается на несуществующий id",
        "WCAG 2.4.7": "outline:none без замены на 8 элементах",
        "WCAG 2.4.4": "3 ссылки без текста",
        "WCAG 1.4.2": "Видео с autoplay без muted",
        "WCAG 1.3.1": "Пропуск уровня: h1 -> h3",
        "WCAG 2.1.1": "4 onclick без keyboard handler",
        "WCAG 2.1.2": "Модальное окно без кнопки закрытия",
        "WCAG 2.4.3": "tabindex=5 на 2 элементах",
        "WCAG 3.3.1": "required без aria-describedby",
        "WCAG 1.4.5": "Текст обнаружен в 2 изображениях",
        "WCAG 1.4.1": "Ссылки без подчёркивания в основном контенте",
    }

    demo_pass_reasons = {
        "5.1": "Кнопка найдена в header: 'Версия для слабовидящих'",
        "WCAG 3.1.1": 'lang="ru" установлен на <html>',
        "WCAG 2.4.2": "Заголовок уникален и описателен",
        "WCAG 1.1.1": "Все видимые изображения имеют alt",
        "WCAG 3.3.2": "Все поля имеют label или aria-label",
        "WCAG 2.4.1": "Skip-link + landmarks: main, nav, banner",
        "WCAG 1.4.4": "Viewport не блокирует масштабирование",
        "П953 п.5": "CAPTCHA не обнаружена",
        "ГОСТ 52872": "Панель спецверсии работает: шрифт, цвет, интервалы",
        "WCAG 1.4.3": "Контраст всех элементов >= 4.5:1",
        "WCAG 4.1.1": "HTML валиден, id уникальны",
        "WCAG 4.1.2": "ARIA-атрибуты корректны",
        "WCAG 2.4.7": "Все интерактивные элементы имеют видимый фокус",
        "WCAG 2.4.4": "Все ссылки имеют описательный текст",
        "WCAG 1.4.2": "Нет автовоспроизведения без muted",
        "WCAG 1.3.1": "Иерархия заголовков корректна",
        "WCAG 2.1.1": "Все интерактивные элементы доступны с клавиатуры",
        "WCAG 2.1.2": "Ловушки фокуса не обнаружены",
        "WCAG 2.4.3": "Порядок фокуса логичен",
        "WCAG 3.3.1": "Формы имеют механизмы обработки ошибок",
        "WCAG 1.4.5": "Текст в изображениях не обнаружен",
        "WCAG 1.4.1": "Ссылки имеют подчёркивание",
    }

    demo_sites_raw = [
        ("vos", "Всероссийское общество слепых", "https://www.vos.org.ru/", "reference", True),
        ("kremlin", "Президент России", "http://www.kremlin.ru/", "president", False),
        ("duma", "Государственная Дума", "http://www.duma.gov.ru/", "legislative", False),
        ("vsrf", "Верховный Суд", "http://www.vsrf.ru/", "judicial", False),
        ("government", "Правительство РФ", "http://government.ru/", "government", False),
        ("mvd", "МВД", "http://mvd.ru/", "ministry", False),
        ("minzdrav", "Минздрав", "http://www.rosminzdrav.ru/", "ministry", False),
        ("digital", "Минцифры", "https://digital.gov.ru/", "ministry", False),
        ("minfin", "Минфин", "http://minfin.ru/", "ministry", False),
        ("gosuslugi", "Госуслуги", "http://www.gosuslugi.ru/", "service", False),
        ("nalog", "ФНС (налоговая)", "http://www.nalog.ru/", "service_federal", False),
        ("rosreestr", "Росреестр", "http://www.rosreestr.ru/", "service_federal", False),
        ("fas", "ФАС (антимонопольная)", "http://fas.gov.ru/", "service_federal", False),
        ("rosatom", "Росатом", "http://www.rosatom.ru/", "corporation", False),
        ("roscosmos", "Роскосмос", "http://www.roscosmos.ru/", "corporation", False),
        ("sfr", "Социальный фонд России", "https://sfr.gov.ru/", "fund", False),
        ("cbr", "Центральный банк РФ", "https://www.cbr.ru/", "portal", False),
        ("zakupki", "Портал госзакупок", "http://zakupki.gov.ru/", "portal", False),
        ("mos", "Портал Москвы", "https://www.mos.ru/", "regional", False),
        ("sfri", "Федеральный реестр инвалидов", "https://sfri.ru/", "specialized", False),
    ]

    # Типичные паттерны: какие проверки обычно FAIL
    # Индексы проверок которые часто FAIL
    common_fail_indices = {9, 12, 5, 4}  # contrast, focus_visible, skip_link, form_labels
    rare_pass_indices = {0, 8}  # accessibility_link, special_version

    site_reports = []
    summary_sites = []

    for site_id, name, url, category, is_ref in demo_sites_raw:
        checks = []
        pass_count = 0
        fail_count = 0

        for idx, (gost_id, gost_section, wcag_ref, title) in enumerate(demo_checks_meta):
            # Determine verdict
            if is_ref:
                # Reference site: mostly PASS
                is_fail = idx in rare_pass_indices or random.random() < 0.15
            else:
                if idx in common_fail_indices:
                    is_fail = random.random() < 0.65
                elif idx in rare_pass_indices:
                    is_fail = random.random() < 0.55
                else:
                    is_fail = random.random() < 0.2

            verdict = "FAIL" if is_fail else "PASS"
            source = "llm" if idx >= 20 else "script"
            reason = demo_fail_reasons[gost_section] if is_fail else demo_pass_reasons[gost_section]

            if verdict == "PASS":
                pass_count += 1
            else:
                fail_count += 1

            checks.append({
                "gost_id": gost_id,
                "gost_section": gost_section,
                "wcag_ref": wcag_ref,
                "title": title,
                "verdict": verdict,
                "source": source,
                "reason": reason,
                "details": {},
            })

        report = {
            "id": site_id,
            "name": name,
            "url": url,
            "category": category,
            "is_reference": is_ref,
            "summary": {
                "total": len(checks),
                "pass": pass_count,
                "fail": fail_count,
                "uncertain": 0,
            },
            "checks": checks,
        }
        site_reports.append(report)

        summary_sites.append({
            "id": site_id,
            "name": name,
            "url": url,
            "category": category,
            "is_reference": is_ref,
            "pass": pass_count,
            "fail": fail_count,
            "uncertain": 0,
            "report_file": f"{site_id}.json",
        })

    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_sites": len(site_reports),
        "checks_per_site": len(demo_checks_meta),
        "sites": summary_sites,
        "is_demo": True,
    }

    return summary, site_reports
# END_FUNCTION_generate_demo_data


# START_FUNCTION_generate_html
# CONTRACT:
# PURPOSE: [Генерирует самодостаточный HTML-файл дашборда со вшитыми данными.]
# INPUTS: summary: dict, site_reports: list[dict].
# OUTPUTS: str — HTML-строка.
# SIDE_EFFECTS: [Нет.]
# KEYWORDS: [html, generate, dashboard, template]
def generate_html(summary: Dict[str, Any], site_reports: List[Dict[str, Any]]) -> str:
    """Генерирует HTML-дашборд."""

    # START_BLOCK_COMPUTE_STATS: [Вычисление общей статистики.]
    total_sites = summary.get("total_sites", len(site_reports))
    checks_per_site = summary.get("checks_per_site", 22)
    timestamp = summary.get("timestamp", datetime.now().isoformat())
    is_demo = summary.get("is_demo", False)

    try:
        dt = datetime.fromisoformat(timestamp)
        date_str = dt.strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError):
        date_str = str(timestamp)

    # Per-site stats
    all_pass_pcts = []
    best_site = None
    best_pct = -1
    worst_site = None
    worst_pct = 101

    for report in site_reports:
        s = report.get("summary", {})
        total = s.get("total", 0) or checks_per_site
        p = s.get("pass", 0)
        pct = round(p / total * 100, 1) if total > 0 else 0
        all_pass_pcts.append(pct)

        if pct > best_pct:
            best_pct = pct
            best_site = report
        if pct < worst_pct:
            worst_pct = pct
            worst_site = report

    avg_pct = round(sum(all_pass_pcts) / len(all_pass_pcts), 1) if all_pass_pcts else 0
    # END_BLOCK_COMPUTE_STATS

    # START_BLOCK_GROUP_BY_CATEGORY: [Группировка сайтов по категориям.]
    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for report in site_reports:
        cat = report.get("category", "specialized")
        by_category.setdefault(cat, []).append(report)
    # END_BLOCK_GROUP_BY_CATEGORY

    # START_BLOCK_BUILD_CATEGORY_SECTIONS: [Формирование HTML-секций для каждой категории.]
    categories_html_parts = []
    cat_index = 0
    for cat_key in CATEGORY_ORDER:
        sites_in_cat = by_category.get(cat_key, [])
        if not sites_in_cat:
            continue

        cat_index += 1
        cat_name = CATEGORY_NAMES.get(cat_key, cat_key)
        cat_pass = sum(r.get("summary", {}).get("pass", 0) for r in sites_in_cat)
        cat_fail = sum(r.get("summary", {}).get("fail", 0) for r in sites_in_cat)
        cat_total = cat_pass + cat_fail
        cat_pct = round(cat_pass / cat_total * 100, 1) if cat_total > 0 else 0

        # Build site rows
        site_rows = []
        for report in sites_in_cat:
            s = report.get("summary", {})
            total = s.get("total", 0) or checks_per_site
            p = s.get("pass", 0)
            f = s.get("fail", 0)
            pct = round(p / total * 100, 1) if total > 0 else 0
            ref_marker = ' <span class="ref-badge">эталон</span>' if report.get("is_reference") else ""
            site_name = _escape_html(report.get("name", report.get("id", "?")))
            site_url = _escape_html(report.get("url", ""))
            site_id = _escape_html(report.get("id", ""))

            # Build checks detail
            checks_rows = []
            for check in report.get("checks", []):
                v = check.get("verdict", "FAIL")
                v_class = "verdict-pass" if v == "PASS" else ("verdict-fail" if v == "FAIL" else "verdict-uncertain")
                v_label = v
                c_title = _escape_html(check.get("title", ""))
                c_gost = _escape_html(check.get("gost_section", ""))
                c_wcag = _escape_html(check.get("wcag_ref", ""))
                c_reason = _escape_html(check.get("reason", ""))
                c_source = _escape_html(check.get("source", "script"))

                checks_rows.append(
                    f'<tr>'
                    f'<td><span class="{v_class}">{v_label}</span></td>'
                    f'<td>{c_title}</td>'
                    f'<td>{c_gost}</td>'
                    f'<td>{c_wcag}</td>'
                    f'<td>{c_reason}</td>'
                    f'<td>{c_source}</td>'
                    f'</tr>'
                )

            checks_table = ""
            if checks_rows:
                checks_table = (
                    '<div class="checks-table-wrap">'
                    '<table class="checks-table">'
                    '<thead><tr>'
                    '<th scope="col">Вердикт</th>'
                    '<th scope="col">Проверка</th>'
                    '<th scope="col">ГОСТ</th>'
                    '<th scope="col">WCAG</th>'
                    '<th scope="col">Причина</th>'
                    '<th scope="col">Источник</th>'
                    '</tr></thead>'
                    '<tbody>' + "\n".join(checks_rows) + '</tbody>'
                    '</table></div>'
                )
            else:
                checks_table = '<p>Детали проверок отсутствуют (только сводные данные).</p>'

            pct_class = "pct-good" if pct >= 75 else ("pct-mid" if pct >= 50 else "pct-bad")

            site_rows.append(
                f'<tr>'
                f'<th scope="row">{site_name}{ref_marker}</th>'
                f'<td><a href="{site_url}" rel="noopener noreferrer">{site_url}</a></td>'
                f'<td class="num">{p}</td>'
                f'<td class="num">{f}</td>'
                f'<td class="num {pct_class}">{pct}%</td>'
                f'</tr>'
                f'<tr class="details-row"><td colspan="5">'
                f'<details id="site-{site_id}">'
                f'<summary>Подробности {checks_per_site} проверок</summary>'
                f'{checks_table}'
                f'</details>'
                f'</td></tr>'
            )

        sites_table = (
            '<div class="sites-table-wrap">'
            '<table class="sites-table">'
            '<thead><tr>'
            '<th scope="col">Сайт</th>'
            '<th scope="col">URL</th>'
            '<th scope="col">PASS</th>'
            '<th scope="col">FAIL</th>'
            '<th scope="col">%</th>'
            '</tr></thead>'
            '<tbody>' + "\n".join(site_rows) + '</tbody>'
            '</table></div>'
        )

        open_attr = ' open' if cat_key == "reference" else ''

        categories_html_parts.append(
            f'<details class="category-details"{open_attr}>'
            f'<summary>'
            f'<h3>{cat_name} '
            f'<span class="cat-stats">({len(sites_in_cat)} '
            f'{"сайт" if len(sites_in_cat) == 1 else ("сайта" if 2 <= len(sites_in_cat) <= 4 else "сайтов")}'
            f', {cat_pct}% соответствие)</span>'
            f'</h3>'
            f'</summary>'
            f'{sites_table}'
            f'</details>'
        )
    # END_BLOCK_BUILD_CATEGORY_SECTIONS

    categories_html = "\n".join(categories_html_parts)

    demo_banner = ""
    if is_demo:
        demo_banner = (
            '<div class="demo-banner" role="alert">'
            '<strong>Демонстрационные данные.</strong> '
            'Реальные отчёты не найдены. Запустите '
            '<code>python3 run_all_targets.py</code> для получения реальных результатов.'
            '</div>'
        )

    best_name = _escape_html(best_site.get("name", "?")) if best_site else "?"
    worst_name = _escape_html(worst_site.get("name", "?")) if worst_site else "?"

    # START_BLOCK_HTML_TEMPLATE: [Полный HTML-шаблон.]
    html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ГОСТ-доступность госсайтов РФ — результаты проверки</title>
<style>
/* === RESET & BASE === */
*, *::before, *::after {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  font-size: 1rem;
  line-height: 1.6;
  color: #1a1a1a;
  background: #ffffff;
}}

/* === SKIP-LINK === */
.skip-link {{
  position: absolute;
  left: -9999px;
  top: 0;
  z-index: 1000;
  padding: 0.5em 1em;
  background: #0000cc;
  color: #ffffff;
  text-decoration: underline;
  font-weight: bold;
}}
.skip-link:focus {{
  left: 0;
  outline: 3px solid #0000cc;
  outline-offset: 2px;
}}

/* === FOCUS === */
a:focus, button:focus, summary:focus, details:focus, [tabindex]:focus {{
  outline: 2px solid #0000cc;
  outline-offset: 2px;
}}

/* === LINKS === */
a {{
  color: #0000cc;
  text-decoration: underline;
}}
a:hover {{
  color: #000099;
}}
a:visited {{
  color: #551a8b;
}}

/* === LAYOUT === */
.container {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}}

/* === HEADER === */
header {{
  border-bottom: 3px solid #1a1a1a;
  padding: 1.5rem 0;
  margin-bottom: 1.5rem;
}}
header h1 {{
  margin: 0 0 0.25rem 0;
  font-size: 1.75rem;
  line-height: 1.3;
}}
header p {{
  margin: 0.25rem 0;
  color: #333;
}}

/* === DEMO BANNER === */
.demo-banner {{
  background: #fff3cd;
  border: 2px solid #856404;
  border-radius: 4px;
  padding: 0.75rem 1rem;
  margin-bottom: 1.5rem;
  color: #533f03;
}}
.demo-banner code {{
  background: #f5e6b8;
  padding: 0.1em 0.3em;
  border-radius: 2px;
}}

/* === STATS === */
.stats-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}}
.stat-card {{
  border: 2px solid #1a1a1a;
  border-radius: 4px;
  padding: 1rem;
}}
.stat-card .stat-value {{
  font-size: 2rem;
  font-weight: bold;
  display: block;
  margin-bottom: 0.25rem;
}}
.stat-card .stat-label {{
  font-size: 0.875rem;
  color: #333;
}}

/* === CATEGORIES (ACCORDION) === */
.category-details {{
  border: 2px solid #1a1a1a;
  border-radius: 4px;
  margin-bottom: 1rem;
}}
.category-details > summary {{
  padding: 0.75rem 1rem;
  cursor: pointer;
  list-style: none;
  background: #f5f5f5;
  border-radius: 2px;
}}
.category-details > summary::-webkit-details-marker {{
  display: none;
}}
.category-details > summary::before {{
  content: "\\25B6\\FE0E";
  display: inline-block;
  margin-right: 0.5rem;
  transition: transform 0.2s;
}}
.category-details[open] > summary::before {{
  transform: rotate(90deg);
}}
.category-details > summary h3 {{
  display: inline;
  font-size: 1.125rem;
  margin: 0;
}}
.cat-stats {{
  font-weight: normal;
  color: #555;
  font-size: 0.9375rem;
}}

/* === TABLES === */
.sites-table-wrap, .checks-table-wrap {{
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  margin: 0.5rem 0;
}}
table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9375rem;
}}
th, td {{
  text-align: left;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #ddd;
  vertical-align: top;
}}
thead th {{
  background: #f5f5f5;
  font-weight: 600;
  border-bottom: 2px solid #1a1a1a;
  white-space: nowrap;
}}
.num {{
  text-align: right;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}}

/* === DETAILS ROW === */
.details-row > td {{
  padding: 0;
  border-bottom: 2px solid #ccc;
}}
.details-row details {{
  padding: 0 0.75rem;
}}
.details-row details summary {{
  padding: 0.4rem 0;
  cursor: pointer;
  font-size: 0.875rem;
  color: #555;
}}

/* === CHECKS TABLE === */
.checks-table {{
  font-size: 0.8125rem;
}}
.checks-table th, .checks-table td {{
  padding: 0.35rem 0.5rem;
}}

/* === VERDICTS === */
.verdict-pass {{
  color: #006400;
  font-weight: 600;
}}
.verdict-fail {{
  color: #8b0000;
  font-weight: 600;
}}
.verdict-uncertain {{
  color: #856404;
  font-weight: 600;
}}
.pct-good {{ color: #006400; font-weight: 600; }}
.pct-mid {{ color: #856404; font-weight: 600; }}
.pct-bad {{ color: #8b0000; font-weight: 600; }}

/* === REF BADGE === */
.ref-badge {{
  display: inline-block;
  background: #006400;
  color: #fff;
  font-size: 0.6875rem;
  padding: 0.1em 0.4em;
  border-radius: 3px;
  vertical-align: middle;
  margin-left: 0.25rem;
  font-weight: normal;
}}

/* === FOOTER === */
footer {{
  border-top: 3px solid #1a1a1a;
  padding: 1.5rem 0;
  margin-top: 2rem;
  font-size: 0.875rem;
  color: #555;
}}
footer p {{
  margin: 0.25rem 0;
}}

/* === RESPONSIVE === */
@media (max-width: 640px) {{
  header h1 {{ font-size: 1.375rem; }}
  .stats-grid {{ grid-template-columns: 1fr 1fr; }}
  .stat-card .stat-value {{ font-size: 1.5rem; }}
  table {{ font-size: 0.8125rem; }}
  th, td {{ padding: 0.35rem 0.5rem; }}
}}
@media (max-width: 400px) {{
  .stats-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<a href="#main" class="skip-link">Перейти к содержимому</a>

<header role="banner">
<div class="container">
<h1>ГОСТ-доступность госсайтов РФ</h1>
<p>Автоматическая проверка на соответствие ГОСТ Р 52872-2019, WCAG 2.1 A/AA и Приказу Минцифры №953</p>
<p>Проверено сайтов: <strong>{total_sites}</strong> | Проверок на сайт: <strong>{checks_per_site}</strong> | Дата: <strong>{date_str}</strong></p>
</div>
</header>

<main id="main" role="main">
<div class="container">

{demo_banner}

<h2>Общая статистика</h2>
<div class="stats-grid">
<div class="stat-card">
<span class="stat-value">{avg_pct}%</span>
<span class="stat-label">Среднее соответствие</span>
</div>
<div class="stat-card">
<span class="stat-value">{total_sites}</span>
<span class="stat-label">Проверено сайтов</span>
</div>
<div class="stat-card">
<span class="stat-value pct-good">{best_name}</span>
<span class="stat-label">Лучший результат ({best_pct}%)</span>
</div>
<div class="stat-card">
<span class="stat-value pct-bad">{worst_name}</span>
<span class="stat-label">Худший результат ({worst_pct}%)</span>
</div>
</div>

<h2>Результаты по категориям</h2>
{categories_html}

</div>
</main>

<footer role="contentinfo">
<div class="container">
<p>ГОСТ Р 52872-2019 | ГОСТ Р ИСО 40500-2014 (WCAG 2.0) | Приказ Минцифры №953</p>
<p>Инструмент: <strong>gost-a11y-automation</strong> — автоматическая проверка доступности госсайтов</p>
<p>Этот документ сам является образцом доступности: skip-link, landmarks, семантическая разметка, контраст >= 4.5:1</p>
</div>
</footer>

</body>
</html>'''
    # END_BLOCK_HTML_TEMPLATE

    return html
# END_FUNCTION_generate_html


# START_FUNCTION_escape_html
# CONTRACT:
# PURPOSE: [Экранирование HTML-спецсимволов.]
# INPUTS: s: str.
# OUTPUTS: str.
# KEYWORDS: [escape, html, security]
def _escape_html(s: str) -> str:
    """Экранирует HTML-спецсимволы."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
# END_FUNCTION_escape_html


# START_FUNCTION_main
# CONTRACT:
# PURPOSE: [Точка входа. Парсит аргументы, загружает данные, генерирует HTML.]
# INPUTS: sys.argv.
# OUTPUTS: Создаёт dashboard/index.html.
# SIDE_EFFECTS: [Чтение файлов, запись файла.]
# KEYWORDS: [main, entry, cli]
def main() -> None:
    """Точка входа для генерации дашборда."""
    parser = argparse.ArgumentParser(
        description="Генерация HTML-дашборда из batch-отчётов ГОСТ-доступности"
    )
    parser.add_argument(
        "batch_dir",
        nargs="?",
        default=None,
        help="Путь к директории batch-отчёта (по умолчанию — последняя reports/batch_*/)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Путь для сохранения HTML (по умолчанию — dashboard/index.html)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Сгенерировать дашборд с демо-данными",
    )
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Determine data source
    if args.demo:
        print("Генерация демо-данных...")
        summary, site_reports = generate_demo_data()
    elif args.batch_dir:
        batch_dir = args.batch_dir
        if not os.path.isabs(batch_dir):
            batch_dir = os.path.join(base_dir, batch_dir)
        print(f"Загрузка данных из {batch_dir}...")
        summary, site_reports = load_batch_data(batch_dir)
    else:
        batch_dir = find_latest_batch_dir(base_dir)
        if batch_dir:
            print(f"Найдена последняя batch-директория: {batch_dir}")
            summary, site_reports = load_batch_data(batch_dir)
        else:
            print("Batch-отчёты не найдены. Генерация демо-данных...")
            summary, site_reports = generate_demo_data()

    # Generate HTML
    html = generate_html(summary, site_reports)

    # Write output
    if args.output:
        output_path = args.output
        if not os.path.isabs(output_path):
            output_path = os.path.join(base_dir, output_path)
    else:
        output_path = os.path.join(base_dir, "dashboard", "index.html")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = round(os.path.getsize(output_path) / 1024, 1)
    print(f"Дашборд создан: {output_path} ({size_kb} КБ)")
    print(f"Сайтов: {len(site_reports)}, категорий: {len(set(r.get('category', '') for r in site_reports))}")


if __name__ == "__main__":
    main()
# END_FUNCTION_main
