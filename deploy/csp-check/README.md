# CSP check

Walks the paths in the CSP enforcement rule (`CLAUDE.md`) on the live site and counts violations:
the first screen, every example replay, one live question, one source link, the About page, the diagram
zoom and dark mode. It also feeds a hostile answer to the deployed bundle, faked in the browser, to check
that no image renders.

It ends with a deliberate violation as a control, because a zero means nothing unless the detector can
see one. It prints one `RESULT` line and exits non-zero if any path had a violation or the control didn't
fire.

**It spends one live question per browser** from the Groq quota the demo shares, and each counts toward
the daily cap and the per-IP limit. So it is run by hand and is not part of CI. `SKIP_LIVE=1` skips the
live question, and with it the only path that exercises `connect-src` through `/chat`.

## Running it

From this folder, with Node and Google Chrome installed:

    npm ci
    npx playwright install firefox webkit
    node csp-check.mjs chrome
    node csp-check.mjs firefox
    node csp-check.mjs webkit

The `playwright` version is pinned exactly, because it decides which Firefox and WebKit builds run.
These are Playwright's patched builds, and WebKit on Windows is not iOS Safari: it doesn't display the
PDF a source link opens, for one. That's why the checklist in `deploy/DEPLOY.md` adds a real iPhone.

## Why screenshots come last, in a separate pass

`page.screenshot()` itself fires a violation in WebKit: `style-src-elem`, blocked `inline`. Playwright's
`inPagePrepareForScreenshots` first creates a `<style>` element for its `syncAnimations` step, and in
WebKit the site's policy applies to it. The site itself creates no style element.

Measured on 2026-11-05 on WebKit 27.2: 0 violations while idle, exactly 1 after one screenshot, and 0 for
the same screenshot in Chrome. **`caret: "initial"` doesn't help**: it fired 1 as well, in both orders,
because that step runs whatever the caret setting is.

So the counting pass takes no screenshots. The screenshot pass runs after it, in a fresh context with no
detector, and uses no quota. A screenshot added to the counting pass would make WebKit report a violation
the site didn't cause.
