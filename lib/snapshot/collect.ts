// #region MODULE_CONTRACT [DOMAIN(9): Snapshot; CONCEPT(9): DOMCapture; TECH(8): EvalExpression]
// ## @modulecontract
// ## @purpose Snapshot collector — a single async IIFE as a string that runs
// ##          inside the inspected page (via inspectedWindow.eval in production
// ##          or page.evaluate in CLI/tests) and returns a Snapshot JSON.
// ## @scope DOM read-only; reads document.documentElement, querySelectorAll('img'),
// ##        and calls window.axe.run() for color-contrast violations.
// ## @input Implicit: the inspected page DOM. Expects window.axe to be already
// ##        injected by the caller before this expression is evaluated.
// ## @output Snapshot object (URL, language attributes, images[], axe contrast violations[]).
// ## @links USES_API(8): window.axe (caller injects axe-core); LINKS_TO: lib/types
// ## @invariants
// ## - Pure read of the DOM; never mutates the inspected page.
// ## - Returns valid Snapshot shape (see lib/types.ts) — caller can cast.
// ## - Safe to run multiple times on the same page (idempotent).
// ## - Every section is wrapped in its own try/catch; one failing section
// ##   contributes [] + a sectionErrors entry, never breaks the snapshot.
// ## - axe.run() failures collapse to empty axeViolations[].
// ## - The final return value is round-tripped through JSON to guarantee
// ##   inspectedWindow.eval can serialise it (catches DOM-node leaks, BigInt,
// ##   circular refs early — with a useful message instead of cryptic
// ##   "Cannot read properties of undefined (reading 'length')").
// ## @rationale
// ## Q: Why a string expression instead of an exported async function?
// ## A: inspectedWindow.eval accepts only an expression string. Keeping the
// ##    collector as a string at the source-of-truth level lets both production
// ##    (eval) and tests (page.evaluate accepts strings too) use the exact same
// ##    bytes. The expression is wrapped in an async IIFE so the eval result
// ##    is a Promise<Snapshot>.
// ## Q: Why does the caller inject axe, not the collector?
// ## A: axe.min.js is ~600 KB; injecting it inside this expression every call
// ##    would balloon the eval payload and slow each audit. Caller injects once
// ##    per page lifetime; collector just consumes window.axe.
// ## Q: Why per-section try/catch instead of one big wrapper?
// ## A: Real pages (dzen.ru, gosuslugi.ru) hit edge-cases in individual
// ##    sections — SVG elements with weird className types, MathML headings,
// ##    custom elements whose attributes throw on access. One-big-wrapper
// ##    surfaces zero data when any section fails; per-section keeps the
// ##    remaining 13 checks running and tells us EXACTLY which section to fix.
// ## @changes
// ## LAST_CHANGE: [v0.3.1] M-debug: per-section try/catch + sectionErrors[]
// ##              + JSON serialisation sanity check. Designed for "real-site
// ##              audit fails -> tell the developer which section died and
// ##              with what stack" support workflow.
// ## @modulemap
// ## CONST 9[The collector expression as a JS string] => COLLECT_EXPRESSION
// ## @usecases
// ## - [production]: panel -> inspectedWindow.eval(axeSource) ->
// ##                 inspectedWindow.eval(COLLECT_EXPRESSION) -> snapshot
// ## - [CLI]: tsx scripts/grab-snapshot.ts URL -> Playwright page.addScriptTag(axe)
// ##         -> page.evaluate(COLLECT_EXPRESSION) -> snapshot JSON
// ## - [tests]: vitest -> Playwright headless -> setContent(html) ->
// ##           addScriptTag(axe) -> evaluate(COLLECT_EXPRESSION) -> assertions
// #endregion MODULE_CONTRACT
// GREP_SUMMARY: snapshot, collector, inspectedWindow, eval, axe, lang, images, sectionErrors, M1
// STRUCTURE: ▶ async IIFE → ⚡ read documentElement lang/xml:lang/meta
//   → ○ ∋img: ⚡ compute visibility/rect/selector → ⊕ images[]
//   → ◇ window.axe present ? → ⚡ axe.run(all rules) → ⊕ axeViolations[]
//   → ⎋ JSON.parse(JSON.stringify(Snapshot))

// The expression is a single string so it can be passed verbatim to
// chrome.devtools.inspectedWindow.eval (production) or page.evaluate (CLI/tests).
// Both runtimes execute it in the page's JS context with full DOM access.
export const COLLECT_EXPRESSION = `
(async () => {
 var __sectionErrors = [];
 function __section(name, fn, fallback) {
   try {
     return fn();
   } catch (e) {
     __sectionErrors.push({
       section: name,
       message: (e && e.message) ? String(e.message) : String(e),
       stack: (e && e.stack) ? String(e.stack).split('\\n').slice(0, 6).join('\\n') : ''
     });
     return fallback;
   }
 }
 async function __sectionAsync(name, fn, fallback) {
   try {
     return await fn();
   } catch (e) {
     __sectionErrors.push({
       section: name,
       message: (e && e.message) ? String(e.message) : String(e),
       stack: (e && e.stack) ? String(e.stack).split('\\n').slice(0, 6).join('\\n') : ''
     });
     return fallback;
   }
 }

 try {
  // ---- Document-level metadata (cheap, unlikely to throw) -----------------
  var doc = __section('document-meta', function () {
    var html = document.documentElement;
    var metaTag = document.querySelector('meta[http-equiv="content-language" i]');
    var viewportMetaTag = document.querySelector('meta[name="viewport" i]');
    return {
      documentLang: (html && html.getAttribute('lang')) || '',
      documentXmlLang: (html && html.getAttribute('xml:lang')) || '',
      metaContentLanguage: metaTag ? (metaTag.getAttribute('content') || '') : '',
      documentTitle: document.title || '',
      viewportMeta: viewportMetaTag ? (viewportMetaTag.getAttribute('content') || '') : ''
    };
  }, {
    documentLang: '', documentXmlLang: '', metaContentLanguage: '',
    documentTitle: '', viewportMeta: ''
  });

  // ---- Keyboard concerns --------------------------------------------------
  var keyboardConcerns = __section('keyboard-concerns', function () {
    var out = [];
    // Pattern 1: div/span/li/td/tr/p with onclick but no role / tabindex / keyboard handler
    var clickyCandidates = document.querySelectorAll(
      'div[onclick], span[onclick], li[onclick], td[onclick], tr[onclick], p[onclick]'
    );
    for (var i = 0; i < clickyCandidates.length; i++) {
      var el = clickyCandidates[i];
      try {
        var hasKb = el.hasAttribute('onkeydown') || el.hasAttribute('onkeyup') || el.hasAttribute('onkeypress');
        if (hasKb || el.hasAttribute('role') || el.hasAttribute('tabindex')) continue;
        var rect = el.getBoundingClientRect();
        if (!(rect.width > 0 && rect.height > 0)) continue;
        out.push({
          reason: 'onclick-no-keyboard',
          tag: el.tagName.toLowerCase(),
          text: ((el.textContent || '') + '').trim().substring(0, 60),
          selector: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '')
        });
      } catch (eInner) { /* skip this element */ }
    }
    // Pattern 2: interactive element with tabindex<0 and not disabled
    var negTabindexed = document.querySelectorAll('[tabindex]');
    var interactiveSelector = 'a[href], button, input, select, textarea, [role="button"], [role="link"], [role="tab"]';
    for (var j = 0; j < negTabindexed.length; j++) {
      var el2 = negTabindexed[j];
      try {
        var ti = parseInt(el2.getAttribute('tabindex') || '0', 10);
        if (!(ti < 0)) continue;
        if (!el2.matches(interactiveSelector)) continue;
        var clsName = (typeof el2.className === 'string') ? el2.className : '';
        var disabled = el2.hasAttribute('disabled') ||
          el2.getAttribute('aria-disabled') === 'true' ||
          /\\bdisabled\\b/.test(clsName);
        if (disabled) continue;
        out.push({
          reason: 'negative-tabindex-interactive',
          tag: el2.tagName.toLowerCase(),
          text: ((el2.textContent || '') + '').trim().substring(0, 60),
          selector: el2.tagName.toLowerCase() + (el2.id ? '#' + el2.id : '') + '[tabindex="' + ti + '"]'
        });
      } catch (eInner2) { /* skip */ }
    }
    return out;
  }, []);

  // ---- Headings -----------------------------------------------------------
  var headings = __section('headings', function () {
    var out = [];
    var nodes = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
    for (var i = 0; i < nodes.length; i++) {
      var h = nodes[i];
      try {
        var lvl = parseInt(h.tagName.slice(1), 10);
        if (!(lvl >= 1 && lvl <= 6)) continue;
        var vis = true;
        var cur = h;
        while (cur && cur !== document.body) {
          var s = getComputedStyle(cur);
          if (!s) break;
          if (s.display === 'none' || s.visibility === 'hidden' || parseFloat(s.opacity) === 0) {
            vis = false; break;
          }
          cur = cur.parentElement;
        }
        out.push({
          level: lvl,
          text: ((h.textContent || '') + '').trim().substring(0, 120),
          selector: h.id ? '#' + h.id : h.tagName.toLowerCase(),
          visible: vis
        });
      } catch (eInner) { /* skip this heading */ }
    }
    return out;
  }, []);

  // ---- CAPTCHA widgets ----------------------------------------------------
  var captchas = __section('captchas', function () {
    var out = [];
    var captchaTypes = [
      { type: 'recaptcha', re: /google\\.com\\/recaptcha|gstatic\\.com\\/recaptcha|g-recaptcha/i },
      { type: 'hcaptcha', re: /hcaptcha\\.com|h-captcha/i },
      { type: 'smartcaptcha', re: /captcha-api\\.yandex|smartcaptcha|smart-captcha/i },
      { type: 'turnstile', re: /challenges\\.cloudflare\\.com\\/turnstile|cf-turnstile/i }
    ];
    var probes = [
      { sel: 'script', attr: 'src', kind: 'tag' },
      { sel: 'iframe', attr: 'src', kind: 'tag' },
      { sel: '[class*="captcha" i],[class*="g-recaptcha"],[class*="h-captcha"],[class*="cf-turnstile"]', attr: 'class', kind: 'class' }
    ];
    for (var p = 0; p < probes.length; p++) {
      var probe = probes[p];
      var nodes = document.querySelectorAll(probe.sel);
      for (var i = 0; i < nodes.length; i++) {
        var el = nodes[i];
        try {
          var value = el.getAttribute(probe.attr) || '';
          if (!value) continue;
          for (var ct = 0; ct < captchaTypes.length; ct++) {
            if (captchaTypes[ct].re.test(value)) {
              var clsRaw = (typeof el.className === 'string') ? el.className : (el.getAttribute('class') || '');
              var selector;
              if (probe.kind === 'class') {
                var clsList = clsRaw.toString().trim().split(/\\s+/).slice(0, 2).join('.');
                selector = el.tagName.toLowerCase() + (clsList ? '.' + clsList : '');
              } else {
                selector = probe.sel + '[' + probe.attr + '="' + value.substring(0, 80) + '"]';
              }
              out.push({ type: captchaTypes[ct].type, source: value.substring(0, 200), selector: selector });
              break;
            }
          }
        } catch (eInner) { /* skip */ }
      }
    }
    return out;
  }, []);

  // ---- Skip-links ---------------------------------------------------------
  var skipLinks = __section('skip-links', function () {
    var out = [];
    var skipPattern = /пропустить|перейти к (содерж|основн|main)|skip( to)? (main|content|navigation)|jump to/i;
    var anchors = document.querySelectorAll('a[href]');
    var scanned = 0;
    for (var i = 0; i < anchors.length && scanned < 20; i++) {
      scanned++;
      var a = anchors[i];
      try {
        var href = a.getAttribute('href') || '';
        if (!href.startsWith('#') || href.length < 2) continue;
        var text = ((a.textContent || '') + '').trim();
        if (!text || !skipPattern.test(text)) continue;
        var targetId = href.slice(1);
        var targetExists = false;
        try { targetExists = !!document.getElementById(decodeURIComponent(targetId)); }
        catch (e1) { targetExists = !!document.getElementById(targetId); }
        out.push({
          href: href,
          text: text.substring(0, 80),
          selector: 'a[href="' + href + '"]',
          targetExists: targetExists
        });
      } catch (eInner) { /* skip */ }
    }
    return out;
  }, []);

  // ---- Images -------------------------------------------------------------
  var images = __section('images', function () {
    var out = [];
    var nodes = document.querySelectorAll('img');
    for (var i = 0; i < nodes.length; i++) {
      var img = nodes[i];
      try {
        var rect = img.getBoundingClientRect();
        var visible = true;
        var cur = img;
        while (cur && cur !== document.body) {
          var s = getComputedStyle(cur);
          if (!s) break;
          if (s.display === 'none' || s.visibility === 'hidden' || parseFloat(s.opacity) === 0) {
            visible = false; break;
          }
          cur = cur.parentElement;
        }
        var parts = [];
        var node = img; var hops = 0;
        while (node && node !== document.body && hops < 5) {
          var part = node.tagName.toLowerCase();
          if (node.id) { parts.unshift('#' + node.id); break; }
          if (typeof node.className === 'string' && node.className.trim()) {
            var cls = node.className.trim().split(/\\s+/).slice(0, 2).join('.');
            if (cls) part += '.' + cls;
          }
          parts.unshift(part);
          node = node.parentElement; hops++;
        }
        out.push({
          src: img.src || '',
          alt: img.hasAttribute('alt') ? img.getAttribute('alt') : null,
          ariaLabel: img.getAttribute('aria-label') || '',
          ariaHidden: img.getAttribute('aria-hidden') === 'true',
          role: img.getAttribute('role') || '',
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          visible: visible,
          selector: parts.join(' > ')
        });
      } catch (eInner) { /* skip this image */ }
    }
    return out;
  }, []);

  // ---- Axe-core: all rules we currently care about ------------------------
  var axeViolations = await __sectionAsync('axe', async function () {
    if (typeof window.axe === 'undefined') return [];
    var axeResult = await window.axe.run(document, {
      runOnly: {
        type: 'rule',
        values: [
          'color-contrast',
          'link-name',
          'duplicate-id-aria',
          'duplicate-id-active',
          'aria-roles',
          'aria-valid-attr',
          'aria-valid-attr-value',
          'aria-required-attr',
          'button-name',
          'no-autoplay-audio',
          'label',
          'select-name'
        ]
      }
    });
    return (axeResult.violations || []).map(function (v) {
      return {
        id: v.id,
        impact: v.impact || null,
        description: v.description || '',
        help: v.help || '',
        helpUrl: v.helpUrl || '',
        tags: v.tags || [],
        nodes: (v.nodes || []).map(function (n) {
          return {
            html: n.html || '',
            target: Array.isArray(n.target)
              ? n.target.map(function (t) { return String(t); })
              : [String(n.target)],
            impact: n.impact || null,
            failureSummary: n.failureSummary || ''
          };
        })
      };
    });
  }, []);

  var result = {
    url: location.href,
    timestamp: Date.now(),
    documentLang: doc.documentLang,
    documentXmlLang: doc.documentXmlLang,
    metaContentLanguage: doc.metaContentLanguage,
    documentTitle: doc.documentTitle,
    viewportMeta: doc.viewportMeta,
    skipLinks: skipLinks,
    captchas: captchas,
    headings: headings,
    keyboardConcerns: keyboardConcerns,
    images: images,
    axeViolations: axeViolations,
    sectionErrors: __sectionErrors
  };

  // Serialisation sanity check — guarantee inspectedWindow.eval can return
  // this object. If something snuck in (e.g. an undefined.length deep in
  // a section we forgot to guard), we trap it here with a clear message
  // instead of getting cryptic "Cannot read properties of undefined" from
  // Chrome's serialiser.
  try {
    return JSON.parse(JSON.stringify(result));
  } catch (eSer) {
    return {
      __collectError: 'Serialisation failed: ' + ((eSer && eSer.message) ? eSer.message : String(eSer)),
      __collectStack: (eSer && eSer.stack) ? String(eSer.stack) : '',
      __collectUrl: location.href,
      __sectionErrors: __sectionErrors
    };
  }
 } catch (e) {
   // Top-level safety net. Should never fire now that every section has its
   // own try/catch, but kept as a last line of defence so the panel always
   // gets back a JSON object instead of a raw exception.
   return {
     __collectError: (e && e.message) ? String(e.message) : String(e),
     __collectStack: (e && e.stack) ? String(e.stack) : '',
     __collectUrl: location.href,
     __sectionErrors: __sectionErrors
   };
 }
})()
`;
