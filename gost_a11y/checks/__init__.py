# FILE: gost_a11y/checks/__init__.py
# VERSION: 0.1.0
# MODULE_CONTRACT:
# PURPOSE: [Реэкспорт всех проверок из пакета checks.]
# SCOPE: [Пакет, реэкспорт]
# KEYWORDS_MODULE: [checks, init, export]
# END_MODULE_CONTRACT

from gost_a11y.checks.check_accessibility_link import CheckAccessibilityLink
from gost_a11y.checks.check_aria import CheckAria
from gost_a11y.checks.check_autoplay import CheckAutoplay
from gost_a11y.checks.check_captcha import CheckCaptcha
from gost_a11y.checks.check_color_only import CheckColorOnly
from gost_a11y.checks.check_contrast import CheckContrast
from gost_a11y.checks.check_focus_order import CheckFocusOrder
from gost_a11y.checks.check_focus_trap import CheckFocusTrap
from gost_a11y.checks.check_focus_visible import CheckFocusVisible
from gost_a11y.checks.check_form_errors import CheckFormErrors
from gost_a11y.checks.check_form_labels import CheckFormLabels
from gost_a11y.checks.check_heading_structure import CheckHeadingStructure
from gost_a11y.checks.check_img_alt import CheckImgAlt
from gost_a11y.checks.check_keyboard_access import CheckKeyboardAccess
from gost_a11y.checks.check_link_text import CheckLinkText
from gost_a11y.checks.check_page_lang import CheckPageLang
from gost_a11y.checks.check_page_title import CheckPageTitle
from gost_a11y.checks.check_skip_link import CheckSkipLink
from gost_a11y.checks.check_special_version import CheckSpecialVersion
from gost_a11y.checks.check_text_in_images import CheckTextInImages
from gost_a11y.checks.check_valid_html import CheckValidHTML
from gost_a11y.checks.check_viewport_zoom import CheckViewportZoom

__all__ = [
    "CheckAccessibilityLink",
    "CheckAria",
    "CheckAutoplay",
    "CheckCaptcha",
    "CheckColorOnly",
    "CheckContrast",
    "CheckFocusOrder",
    "CheckFocusTrap",
    "CheckFocusVisible",
    "CheckFormErrors",
    "CheckFormLabels",
    "CheckHeadingStructure",
    "CheckImgAlt",
    "CheckKeyboardAccess",
    "CheckLinkText",
    "CheckPageLang",
    "CheckPageTitle",
    "CheckSkipLink",
    "CheckSpecialVersion",
    "CheckTextInImages",
    "CheckValidHTML",
    "CheckViewportZoom",
]
