# Vendored dependencies

The deck loads everything from here, so it renders with **no network at all**. Verified by
running headless Chrome with `--proxy-server="127.0.0.1:1"` (a dead proxy, so every network
request fails while `file://` still resolves) and confirming fonts, MathJax typesetting,
the JS-driven figures, and the video all still worked.

Keep this folder next to `generative-sketching.html`. 2.6 MB total.

| Folder | Size | What | Source |
|---|---|---|---|
| `reveal/` | 228 KB | `reset.min.css`, `reveal.min.css`, `reveal.min.js`, `plugin/notes/notes.min.js` | cdnjs, reveal.js **5.1.0** |
| `mathjax/` | 1.5 MB | `tex-mml-chtml.js` + `output/chtml/fonts/woff-v2/*.woff` (23 files) | jsdelivr, mathjax **3.2.2** |
| `fonts/` | 808 KB | `fonts.css` + `files/*.woff2` (43 files) | Google Fonts — Spectral, Inter, JetBrains Mono |

## Things that will bite you if you move files around

- **The MathJax font path is derived, not configured.** MathJax resolves `[mathjax]` to the
  directory of its own `<script src>` and then looks for
  `output/chtml/fonts/woff-v2/` *underneath* it. Renaming `vendor/mathjax/` is fine;
  flattening it is not — the math will render with fallback glyphs and wrong metrics.
- **`fonts.css` uses relative `url(files/…)`.** It only works while it sits beside `files/`.
  The original Google CSS was fetched with a desktop-Chrome User-Agent so it serves woff2;
  fetching it with a different UA yields a different (older) format set.
- All 7 Google subsets were kept (latin, latin-ext, cyrillic, cyrillic-ext, greek,
  greek-ext, vietnamese), so rendering is byte-identical to the CDN version. The deck only
  needs latin, but dropping the rest saves ~500 KB and buys nothing.
- Inter is a variable font: 20 of its 63 `@font-face` rules point at the same woff2 files,
  which is why there are 43 files rather than 63. Checked for basename collisions — none.

## Refreshing

Re-download the same version numbers, or bump them deliberately — the deck is pinned to
reveal.js 5.1.0, whose auto-animate and fragment behaviour the slides depend on in detail.

```bash
R=https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.1.0
curl -sS -o vendor/reveal/reset.min.css              "$R/reset.min.css"
curl -sS -o vendor/reveal/reveal.min.css             "$R/reveal.min.css"
curl -sS -o vendor/reveal/reveal.min.js              "$R/reveal.min.js"
curl -sS -o vendor/reveal/plugin/notes/notes.min.js  "$R/plugin/notes/notes.min.js"
curl -sS -o vendor/mathjax/tex-mml-chtml.js \
  "https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-mml-chtml.js"
# fonts: re-fetch the css2 URL with a desktop UA, then pull each url() and rewrite to files/
```

## Still needs the network

Only the two citation links — `github.com/facebookresearch/ijepa` and
`github.com/galilai-group/lejepa` — which open in a new tab and do not affect the deck.
