import { defineConfig } from "wxt";

// See https://wxt.dev/api/config.html
export default defineConfig({
  // Override WXT's default ".output" with a visible folder name — the dot
  // prefix hides it in Finder by default and makes it awkward to find
  // the built .zip for "Load unpacked" / sharing.
  outDir: "output",
  manifest: {
    name: "GOST A11y",
    description:
      "Accessibility audit for ГОСТ Р 52872-2019 (Chrome DevTools panel).",
    version: "0.1.0",
    // DevTools-only extension: no host_permissions, no scripting permission.
    // Inspected page access is via chrome.devtools.inspectedWindow.eval,
    // which does not require host_permissions.
    permissions: [],
  },
});
