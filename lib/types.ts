// #region MODULE_CONTRACT [DOMAIN(8): DomainModel; CONCEPT(9): ContractTypes; TECH(6): TypeScript]
// ## @modulecontract
// ## @purpose Core data contracts used across the extension: Snapshot (input to
// ##          checks), Defect (output of checks), Severity (enum).
// ## @scope Type declarations only; no runtime behaviour.
// ## @input n/a
// ## @output Types consumed by lib/checks/*, lib/report/*, tests/*.
// ## @links LINKS_TO: lib/checks (consumes types); lib/i18n/severity (maps Severity to Ru labels)
// ## @invariants
// ## - Severity enum string values are STABLE (used in JSON export schema).
// ## - Snapshot is extended only by adding new optional or default-empty fields;
// ##   never remove or rename existing fields without a schema version bump.
// ## - All check functions are pure: (snapshot: Snapshot) => Defect[].
// ## @rationale
// ## Q: Why string-literal union for Severity instead of enum?
// ## A: String literal unions serialize trivially to JSON, do not produce
// ##    runtime objects, and grep-search matches without follow-up.
// ## Q: Why "" empty-string sentinels in Snapshot instead of null?
// ## A: Matches the legacy collector convention (lesson_28 / Python ancestor)
// ##    and removes a class of null-checking noise in checks. We still treat
// ##    "" as "absent" semantically.
// ## Q: Why import axe types instead of depending on axe-core directly?
// ## A: We model only the fields we consume (id, impact, nodes, target,
// ##    failureSummary). Avoiding a direct axe-core import keeps the test
// ##    runtime trivial — fixtures are plain JSON, no DOM, no axe package.
// ##    The real collector (M1) injects axe.min.js into the inspected page
// ##    and pipes its output into snapshot.axeViolations.
// ## @changes
// ## LAST_CHANGE: [v0.1.0] M2 (partial): add AxeNode/AxeViolation + extend
// ##              Snapshot with axeViolations[] (all axe rules in one collection).
// ## @modulemap
// ## TYPE 9[Severity enum used in defects and reports] => Severity
// ## TYPE 8[Evidence payload attached to a defect] => DefectEvidence
// ## TYPE 9[Defect contract per TZ] => Defect
// ## TYPE 7[Skip-link candidate found by collector] => SkipLinkCandidate
// ## TYPE 7[Keyboard accessibility concern] => KeyboardConcern
// ## TYPE 7[Heading info captured by snapshot] => HeadingInfo
// ## TYPE 7[CAPTCHA widget detection] => CaptchaDetection
// ## TYPE 8[Per-image info captured by snapshot] => ImageInfo
// ## TYPE 7[Single offending element entry from axe-core] => AxeNode
// ## TYPE 8[Single rule violation entry from axe-core] => AxeViolation
// ## TYPE 9[Snapshot — input to every check] => Snapshot
// ## @usecases
// ## - [Defect]: pageLang() -> returns Defect[] -> rendered as cards in panel
// ## - [Snapshot]: snapshot collector (M1) -> input to every check -> serialized in test fixtures
// ## - [AxeViolation]: collector axe.run() result -> stored in snapshot -> consumed by contrast()
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: types, Snapshot, Defect, Severity, contract, schema, axe, M2

export type Severity = "Blocker" | "Critical" | "Normal" | "Minor";

export type DefectEvidence = {
  selector?: string;
  html?: string;
  value?: string;
};

export type Defect = {
  id: string;
  gostId: string;
  gostSection: string;
  // Verbatim Russian name of the ГОСТ "Критерий успешного применения"
  // (e.g. "Контрастность (минимальные требования)"), sourced from
  // docs/standards/gost-52872-2019.txt. Optional during migration; checks
  // populate it so reports cite criterion NUMBER and NAME per TZ principle 4.
  gostName?: string;
  // Conformance level of the criterion in ГОСТ Р 52872-2019 (mirrors WCAG):
  // "A" | "AA" | "AAA". Only 1.4.3 and 1.4.4 are AA among current checks.
  gostLevel?: "A" | "AA" | "AAA";
  wcagRef?: string;
  severity: Severity;
  title: string;
  shortDescription: string;
  longDescription: string;
  recommendation: string;
  evidence: DefectEvidence;
};

// Skip-link candidate found by the collector — an anchor whose href is
// a fragment ("#main", "#content", ...) AND whose text looks like a
// skip-link phrase. targetExists tells the check whether the fragment
// actually points to an element on the page (broken target = useless link).
export type SkipLinkCandidate = {
  href: string;
  text: string;
  selector: string;
  targetExists: boolean;
};

// Keyboard accessibility concern collected from the page. reason
// discriminates the two patterns this collector currently detects:
//   onclick-no-keyboard: non-interactive element (div/span/li/td/tr/p)
//     has an HTML onclick handler but no role / tabindex / keyboard handler
//   negative-tabindex-interactive: an interactive element (a/button/input)
//     has tabindex < 0 AND is not disabled — removed from tab order
export type KeyboardConcern = {
  reason: "onclick-no-keyboard" | "negative-tabindex-interactive";
  tag: string;
  text: string;
  selector: string;
};

// Heading info captured by the collector for HeadingStructure check.
// level is 1-6 (h1 -> 1, h6 -> 6); visible reflects display/visibility/opacity
// up the ancestor chain.
export type HeadingInfo = {
  level: number;
  text: string;
  selector: string;
  visible: boolean;
};

// CAPTCHA detection — collector recognises common widgets by script src,
// iframe src, or class name. type is a short label ("recaptcha", "hcaptcha",
// "smartcaptcha", "turnstile", "generic"); source is the matched URL or
// class string for evidence.
export type CaptchaDetection = {
  type: string;
  source: string;
  selector: string;
};

// Per-image info captured by the snapshot collector for ImgAlt and
// related checks. alt === null means "no alt attribute at all" (a
// violation); alt === "" means "explicitly decorative" (compliant per
// HTML spec). visible/width/height drive filters that skip icons and
// hidden images.
export type ImageInfo = {
  src: string;
  alt: string | null;
  ariaLabel: string;
  ariaHidden: boolean;
  role: string;
  width: number;
  height: number;
  visible: boolean;
  selector: string;
};

// Subset of axe-core's NodeResult that contrast() actually consumes.
// target may contain multiple selectors when the element lives inside
// an iframe (cross-frame addressing). impact on the node overrides the
// parent violation's impact when present.
export type AxeNode = {
  html: string;
  target: string[];
  impact: "minor" | "moderate" | "serious" | "critical" | null;
  failureSummary: string;
};

// Subset of axe-core's Violation that any axe-driven check consumes.
// id discriminates between rules: "color-contrast", "link-name", "valid-lang",
// "html-has-lang", "duplicate-id", … See https://dequeuniversity.com/rules/axe/
export type AxeViolation = {
  id: string;
  impact: "minor" | "moderate" | "serious" | "critical" | null;
  description: string;
  help: string;
  helpUrl: string;
  tags: string[];
  nodes: AxeNode[];
};

// Snapshot grows incrementally as new checks need new data.
// Current coverage: PageLang (language), PageTitle (title), ViewportZoom
// (viewport meta), SkipLink (skip-link candidates), CaptchaPresence
// (captcha widgets), ImgAlt (images), Contrast (axe). Planned extensions:
// forms, headings.
export type Snapshot = {
  url: string;
  timestamp: number;
  documentLang: string;
  documentXmlLang: string;
  metaContentLanguage: string;
  documentTitle: string;
  viewportMeta: string;
  skipLinks: SkipLinkCandidate[];
  captchas: CaptchaDetection[];
  headings: HeadingInfo[];
  keyboardConcerns: KeyboardConcern[];
  images: ImageInfo[];
  // All axe-core violations collected in one batch. Each check filters by
  // axeViolation.id (e.g. "color-contrast", "link-name") to find its own.
  axeViolations: AxeViolation[];
  // Diagnostic field: per-section failures captured by the collector.
  // Populated only when at least one section's try/catch fired on a real
  // page (e.g. captchas section blew up on dzen.ru). Absent / empty when
  // the collector ran cleanly. Surfaced verbatim in the panel log so we
  // can pinpoint and fix the offending section without bisecting blindly.
  sectionErrors?: Array<{ section: string; message: string; stack?: string }>;
};
