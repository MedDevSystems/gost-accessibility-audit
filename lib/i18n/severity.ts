// #region MODULE_CONTRACT [DOMAIN(6): I18n; CONCEPT(7): SeverityLabels; TECH(5): Mapping]
// ## @modulecontract
// ## @purpose Map Severity enum values (English, stable in JSON schema) to
// ##          Russian labels used in UI panel and HTML report.
// ## @scope Lookup table only; no runtime behaviour beyond a record access.
// ## @input Severity
// ## @output Russian label string
// ## @links LINKS_TO: lib/types (Severity); CONSUMED_BY: panel UI (M2+), HTML report (M4)
// ## @invariants
// ## - Every Severity value MUST have a Russian label; enforced by the
// ##   Record<Severity, string> type (TypeScript will fail compile on omission).
// ## @rationale
// ## Q: Why English enum + i18n map instead of Russian-as-canonical?
// ## A: JSON export schema (M5) needs stable machine-readable values.
// ##    Russian labels live only on the presentation layer.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] M2 (partial): introduce 4-value map per TZ.
// ## @modulemap
// ## CONST 7[Russian severity labels] => RU_LABELS
// ## FUNC  8[Lookup Russian label for a Severity] => severityRu
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: i18n, severity, russian, label, mapping, Блокирующий, Критический

import type { Severity } from "../types";

// #region BLOCK_CONSTANTS
const RU_LABELS: Record<Severity, string> = {
  Blocker: "Блокирующий",
  Critical: "Критический",
  Normal: "Обычный",
  Minor: "Незначительный",
};
// #endregion BLOCK_CONSTANTS

// #region FUNC_severityRu [DOMAIN(6): I18n; CONCEPT(7): SeverityLabels; TECH(5): Lookup]
// ## @purpose Return the Russian label for a Severity value.
// ## @uses RU_LABELS
// ## @io Severity -> string
// ## @complexity 1
export function severityRu(s: Severity): string {
  return RU_LABELS[s];
}
// #endregion FUNC_severityRu
