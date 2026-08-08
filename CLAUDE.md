# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the presentation

```bash
python3 -m http.server
# then open http://localhost:8000/
```

Opening `generative-sketching.html` via `file://` also works but CDN resources (fonts, MathJax) may be flaky.

Keyboard shortcuts during presentation: arrow keys navigate, `F` fullscreen, `S` speaker notes, `ESC` overview, `.` pause.

## Architecture

Two files total:

- **`generative-sketching.html`** — the entire deck: embedded CSS, all slide `<section>` elements, and inline JS.
- **`design-system.md`** — design token reference (palette, typography, components).

All dependencies are CDN-loaded (Reveal.js 5.1.0, MathJax 3, Google Fonts — requires network). To go offline, vendor those libraries locally and update the `<link>`/`<script>` URLs.

### Design system

All tokens live as CSS variables in the `:root` block (`:root` → `<style>` in `<head>`). Changing one variable re-themes the whole deck. Full token table is in `design-system.md`.

**Color discipline:** `--clay` (`#B0654F`) is reserved exclusively for "our method" content. Use `--slate` for all other primary accents.

### Slide structure

Slides are `<section>` elements inside `.slides`. Nest `<section>` elements for vertical (down) stacks. The deck currently has stub slides for each agenda item — content goes under the matching `<section>`.

### Reusable components (CSS classes already defined)

| Class | Purpose |
|---|---|
| `.ours` | Clay-bordered block — **only place clay is used**; pair with `.eyebrow` reading "Our method" |
| `.callout` | Slate-tinted key-insight block |
| `.card` | White bordered container |
| `.proscons` / `.pros` / `.cons` | Side-by-side pros/cons grid |
| `.section-divider` | Big mono numeral + clay kicker + slate title |
| `.agenda` | Auto-numbered outline list; add `.mine` to a line to mark it clay |
| `.eyebrow` | Uppercase Inter kicker label |
| `.signvec` | ±1 sign vector chips via `data-signvec="+-+--+"` attribute |

### JS helpers

- **`renderSignVectors(root)`** — converts `data-signvec` attributes to colored ±1 chip HTML. Called on page load and on each `slidechanged` event.
- **`typesetSlide(slide)`** — runs MathJax on a slide once, deferred off the navigation path so a MathJax error never breaks navigation.

### Math

Use `\( ... \)` or `$ ... $` for inline math, `\[ ... \]` for display math. MathJax is configured with `startup: { typeset: false }` — typesetting is driven by `typesetSlide()` per slide, not on page load.

### Auto-animate (morphing between slides)

Add `data-auto-animate` to two consecutive `<section>` elements; give matching elements the same `data-id` to morph them. Used for section-divider number/title transitions.

### Draw-on arrows

Wrap an inline `<svg>` in `.fragment.draw`, set `--len` CSS var and `stroke-dasharray` both to the path length. The stroke animates when the fragment activates.
