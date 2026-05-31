// #region MODULE_CONTRACT [DOMAIN(7): Logging; CONCEPT(8): LDDLogging; TECH(6): console+stderr]
// ## @modulecontract
// ## @purpose Thin LDD-formatted logger with [IMP:N][fn][PHASE] msg [TAG] lines.
// ##          In a browser/extension context, routes through console.*. In Node
// ##          (CLI, tests), routes through process.stderr so stdout stays clean
// ##          for JSON output.
// ## @scope Phase/Tag string union types, importance threshold filtering via
// ##        localStorage flag, runtime sink selection.
// ## @input imp level, function name, phase, message, tag.
// ## @output process.stderr.write (Node) or console.{debug,info,warn,error} (browser).
// ## @links USES_API(7): console; USES_API(7): process.stderr; USES_API(5): localStorage
// ## @invariants
// ## - IMP >= 8 is always emitted regardless of the configured threshold
// ##   (important values must never be silenced by accident).
// ## - No external dependencies; bundle footprint stays under 1 KB.
// ## - Logger is side-effect free aside from one stderr/console call per line.
// ## - In Node, stdout is NEVER written by the logger — CLI tools pipe JSON
// ##   to stdout safely (e.g. `pnpm audit URL > report.json` puts only JSON
// ##   in the file).
// ## @rationale
// ## Q: Why not pino/winston/loglevel?
// ## A: Bundle size and DevTools context. console gives DevTools formatting
// ##    (collapsible groups, source maps) for free; a 3rd-party logger would
// ##    add weight without measurable benefit for an MVP this size.
// ## Q: Why positional arguments (imp, fn, phase, msg, tag) instead of a single object?
// ## A: The format is fixed for grep-ability; positional keeps call sites short
// ##    and matches the lesson_28 Python convention 1:1.
// ## Q: Why dual sink (stderr in Node, console in browser) and not just console?
// ## A: console.info in Node goes to stdout; that pollutes JSON output from
// ##    CLI tools. Forcing stderr in Node keeps `pnpm audit URL > file.json`
// ##    clean. Browser console layer is unchanged for the extension runtime.
// ## @changes
// ## LAST_CHANGE: [v0.3.0] Add in-memory ring buffer so the extension panel
// ##              can render the LDD trace inside the UI and let the user
// ##              download it (DevTools-of-DevTools console is too buried).
// ## @modulemap
// ## TYPE 5[Phase enum string union] => Phase
// ## TYPE 5[Tag enum string union] => Tag
// ## CONST 6[Capacity of in-memory log buffer] => LOG_BUFFER_MAX
// ## CONST 6[The buffer itself] => LOG_BUFFER
// ## FUNC 5[Read IMP threshold from localStorage] => _threshold
// ## FUNC 8[Format and emit a log line] => _emit
// ## FUNC 7[Push line into ring buffer with cap] => _pushBuffer
// ## FUNC 8[Read buffered lines (copy, not reference)] => getLogBuffer
// ## FUNC 7[Clear the buffer (e.g. at the start of a new audit)] => clearLogBuffer
// ## OBJ  9[Public logger surface] => log
// ## @usecases
// ## - [log.info]: AnyModule -> emit IMP:8-9 informational line -> DevTools console
// ## - [log.error]: AnyModule -> emit IMP:10 critical line -> DevTools console
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: logger, LDD, IMP, phase, tag, console, threshold, lesson_28

export type Phase =
  | "INIT"
  | "BUILD"
  | "SCAN"
  | "LOAD"
  | "DISPATCH"
  | "EXEC"
  | "RESULT"
  | "CONFIG"
  | "ERROR"
  | "FATAL"
  | "PARSE"
  | "SKIP";

export type Tag = "VALUE" | "INFO" | "WARN" | "FATAL" | "TRACE";

// #region BLOCK_CONSTANTS
const THRESHOLD_KEY = "gost_a11y_log_threshold";
const DEFAULT_THRESHOLD = 7;
const ALWAYS_EMIT_FROM = 8;
const LOG_BUFFER_MAX = 5000;
const LOG_BUFFER: string[] = [];
// #endregion BLOCK_CONSTANTS

// #region FUNC__pushBuffer [DOMAIN(6): Logging; CONCEPT(7): RingBuffer; TECH(5): Array]
// ## @purpose Append a formatted line to the in-memory buffer; drop oldest when full.
// ## @io string -> void
// ## @complexity 2
function _pushBuffer(line: string): void {
  LOG_BUFFER.push(line);
  if (LOG_BUFFER.length > LOG_BUFFER_MAX) LOG_BUFFER.shift();
}
// #endregion FUNC__pushBuffer

// #region FUNC_getLogBuffer [DOMAIN(7): Logging; CONCEPT(7): RingBuffer; TECH(5): Array]
// ## @purpose Return a COPY of the buffer so callers can render or download it
// ##          without seeing later in-place mutations.
// ## @io void -> string[]
// ## @complexity 1
export function getLogBuffer(): string[] {
  return LOG_BUFFER.slice();
}
// #endregion FUNC_getLogBuffer

// #region FUNC_clearLogBuffer [DOMAIN(7): Logging; CONCEPT(7): RingBuffer; TECH(5): Array]
// ## @purpose Clear the buffer (call at the start of a fresh audit so the
// ##          downloaded .log contains only that run, not history).
// ## @io void -> void
// ## @complexity 1
export function clearLogBuffer(): void {
  LOG_BUFFER.length = 0;
}
// #endregion FUNC_clearLogBuffer

// #region FUNC__threshold [DOMAIN(6): Logging; CONCEPT(7): Filtering; TECH(5): localStorage]
// ## @purpose Read the current IMP threshold from localStorage or fall back to default.
// ## @uses localStorage (guarded — works in browser, Node, and partial Node stubs alike)
// ## @io void -> number
// ## @complexity 3
function _threshold(): number {
  try {
    const ls = (globalThis as { localStorage?: Storage }).localStorage;
    const raw =
      ls && typeof ls.getItem === "function" ? ls.getItem(THRESHOLD_KEY) : null;
    const n = raw ? parseInt(raw, 10) : NaN;
    return Number.isFinite(n) ? n : DEFAULT_THRESHOLD;
  } catch {
    return DEFAULT_THRESHOLD;
  }
}
// #endregion FUNC__threshold

// #region FUNC__emit [DOMAIN(7): Logging; CONCEPT(8): LDDFormat; TECH(6): console+stderr]
// ## @purpose Format the LDD line and route via the appropriate sink for the runtime.
// ## @uses process.stderr (Node), console.{debug,info,warn,error} (browser)
// ## @io imp, fn, phase, msg, tag -> void
// ## @complexity 5
function _emit(
  imp: number,
  fn: string,
  phase: Phase,
  msg: string,
  tag: Tag,
): void {
  if (imp < _threshold() && imp < ALWAYS_EMIT_FROM) return;
  const line = `[IMP:${imp}][${fn}][${phase}] ${msg} [${tag}]`;

  // Push to in-memory buffer FIRST — both browser and Node benefit.
  _pushBuffer(line);

  // Node CLI / tests: route through stderr so stdout stays clean for JSON.
  const proc = (globalThis as { process?: { stderr?: { write?: (s: string) => unknown } } }).process;
  if (proc?.stderr && typeof proc.stderr.write === "function") {
    proc.stderr.write(line + "\n");
    return;
  }

  // Browser / extension: normal console levels for DevTools UX.
  if (imp >= 10) console.error(line);
  else if (imp >= 8) console.info(line);
  else if (imp >= 7) console.warn(line);
  else console.debug(line);
}
// #endregion FUNC__emit

export const log = {
  debug: (imp: number, fn: string, phase: Phase, msg: string, tag: Tag = "TRACE") =>
    _emit(imp, fn, phase, msg, tag),
  info: (imp: number, fn: string, phase: Phase, msg: string, tag: Tag = "INFO") =>
    _emit(imp, fn, phase, msg, tag),
  warn: (imp: number, fn: string, phase: Phase, msg: string, tag: Tag = "WARN") =>
    _emit(imp, fn, phase, msg, tag),
  error: (imp: number, fn: string, phase: Phase, msg: string, tag: Tag = "FATAL") =>
    _emit(imp, fn, phase, msg, tag),
};
