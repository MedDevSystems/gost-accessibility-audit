# FILE: gost_a11y/checks/__init__.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Реэкспорт всех проверок из пакета checks.]
# SCOPE: [Пакет, реэкспорт]
# KEYWORDS_MODULE: [checks, init, export]
# END_MODULE_CONTRACT

from gost_a11y.checks.check_accessibility_link import CheckAccessibilityLink

__all__ = ["CheckAccessibilityLink"]
