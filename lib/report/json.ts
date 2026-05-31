// #region MODULE_CONTRACT [DOMAIN(8): Report; CONCEPT(9): Serialization; TECH(6): JSON]
// ## @modulecontract
// ## @purpose Serialize an AggregateReport into a versioned JSON document suitable
// ##          for downstream automation, archival, and regression comparison.
// ## @scope Schema versioning, ISO timestamp formatting, pretty-printed JSON
// ##        serialization. No I/O.
// ## @input AggregateReport
// ## @output JsonReport object and JSON string (pretty-printed, 2-space indent).
// ## @links USES_API(8): lib/report/aggregate
// ## @invariants
// ## - schemaVersion increments on any breaking change to the JSON layout.
// ## - generatedAt is an ISO 8601 UTC string derived from agg.timestamp (ms epoch).
// ## - severity values stay as English enum (machine-readable). UI/HTML layer
// ##   maps them to Russian labels — JSON stays stable.
// ## - Output JSON is sorted only by the explicit key order in toJsonReport.
// ## @rationale
// ## Q: Why a separate JsonReport type alongside AggregateReport?
// ## A: AggregateReport is the in-memory aggregate (fits in code); JsonReport
// ##    is the wire/file format (must stay backward-compatible). Keeping them
// ##    distinct lets us evolve internals freely while pinning the schema.
// ## Q: Why pretty-print with indent 2?
// ## A: Reports are human-read in editors and diffed in regression baselines.
// ##    The size penalty is negligible (text already small) and readability wins.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] M5: first JSON serializer for the aggregator output.
// ## @modulemap
// ## CONST 9[Schema version constant] => SCHEMA_VERSION
// ## TYPE  9[Serialized report shape] => JsonReport
// ## FUNC  9[Build JsonReport from AggregateReport] => toJsonReport
// ## FUNC  8[Serialize to pretty JSON string] => toJsonString
// ## @usecases
// ## - [toJsonString]: scripts/audit-url -> writeFileSync(reports/X.json, toJsonString(report))
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: report, JSON, serialize, schema version, JsonReport, M5

import type { AggregateReport, CheckRun, SeveritySummary } from "./aggregate";

export const SCHEMA_VERSION = "1.0";

export type JsonReport = {
  schemaVersion: string;
  generatedAt: string;
  url: string;
  totalDefects: number;
  severitySummary: SeveritySummary;
  byCheck: CheckRun[];
};

// #region FUNC_toJsonReport [DOMAIN(7): Report; CONCEPT(8): Serialization; TECH(5): Object]
// ## @purpose Wrap an AggregateReport in the versioned JSON envelope.
// ## @uses SCHEMA_VERSION, Date.prototype.toISOString
// ## @io AggregateReport -> JsonReport
// ## @complexity 1
export function toJsonReport(agg: AggregateReport): JsonReport {
  return {
    schemaVersion: SCHEMA_VERSION,
    generatedAt: new Date(agg.timestamp).toISOString(),
    url: agg.url,
    totalDefects: agg.totalDefects,
    severitySummary: agg.severitySummary,
    byCheck: agg.byCheck,
  };
}
// #endregion FUNC_toJsonReport

// #region FUNC_toJsonString [DOMAIN(7): Report; CONCEPT(8): Serialization; TECH(5): JSON]
// ## @purpose Convenience wrapper: pretty-printed JSON ready to write to disk or stdout.
// ## @uses toJsonReport, JSON.stringify
// ## @io AggregateReport -> string
// ## @complexity 1
export function toJsonString(agg: AggregateReport): string {
  return JSON.stringify(toJsonReport(agg), null, 2);
}
// #endregion FUNC_toJsonString
