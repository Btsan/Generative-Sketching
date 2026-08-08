# Design System — "Muted Academic"

Reference for the *Generative Sketching for Relational Joins* deck. Every token
lives as a CSS variable in `generative-sketching.html` (`:root`), so changing one
value re-themes the whole deck.

## Identity in one line
Slate-led scholarly palette; **clay is reserved for our method**; the recurring
**±1 sign vector** (dusty blue / dusty red) is the signature motif that threads
tug-of-war → QJL sign bits → random projections through the whole talk.

## Palette

| Token | Hex | Role |
|---|---|---|
| `--paper` | `#FAF8F4` | slide background |
| `--ink` | `#26292E` | body text |
| `--muted` | `#6B7078` | captions, secondary text |
| `--slate` | `#3E5C76` | **primary** — headings, rules, key terms |
| `--slate-soft` | `#E3E9EE` | slate tint fill (callouts) |
| `--clay` | `#B0654F` | **accent — our method only** |
| `--clay-soft` | `#F1E4DE` | clay tint fill |
| `--sage` | `#7A8B6F` | positive / pros |
| `--sage-soft` | `#E7EBE1` | sage tint fill |
| `--plus` | `#4E7A94` | tug-of-war **+1** (dusty blue) |
| `--minus` | `#C1666B` | tug-of-war **−1** (dusty red) |
| `--rule` | `#D8D2C6` | borders, table lines, dividers |

## Type

- **Headings & body:** Spectral (one disciplined serif; weights 400/500/600).
- **Labels / eyebrows / captions:** Inter (600 for eyebrows).
- **Formulas, data, code:** JetBrains Mono.

Type helpers: `.eyebrow` (uppercase Inter kicker), `.caption` (muted Inter),
`.mono` (JetBrains Mono), `.rule` (short slate underline under titles).

## Reusable components (classes already in the stylesheet)

- `.card` — white bordered container.
- `.ours` — clay-bordered block; **the only place clay is used**. Pair with an
  `.eyebrow` reading "Our method".
- `.callout` — slate-tinted key-insight block.
- `.proscons` grid with `.pros` (sage) and `.cons` (clay) cells.
- `.signvec` with `data-signvec="+-+--+"` → renders ±1 chips via
  `renderSignVectors()`. Inline `.tag-plus` / `.tag-minus` for ±1 in prose.
- Tables: `<th>` slate header, `td.k` for a key/label column.
- `.section-divider` — big mono numeral + clay kicker + slate title
  (use `data-auto-animate` to morph the number/title between divider slides).
- `.agenda` — auto-numbered outline list; add `.mine` to a line to mark it clay.

## Animation helpers

- **Morphs/moves:** put `data-auto-animate` on two consecutive `<section>`s and
  give matching elements the same `data-id`.
- **Draw-on arrow:** wrap an inline `<svg>` in `.fragment.draw`, set `--len` to the
  path length and `stroke-dasharray` to the same value; the stroke draws when the
  fragment becomes active. Example:

```html
<span class="fragment draw" style="--len:120;">
  <svg class="arrow-svg" width="140" height="24" viewBox="0 0 140 24"
       style="stroke-dasharray:120;">
    <line x1="4" y1="12" x2="124" y2="12"></line>
    <path class="head" d="M124 6 L136 12 L124 18 Z" style="stroke-dasharray:0;"></path>
  </svg>
</span>
```

- **Math:** MathJax is re-added when we build the first slide that needs it;
  `typesetSlide()` typesets each slide once, deferred off the navigation path.

## Palette swatch reference (hex, for quick copy)

paper `#FAF8F4` · ink `#26292E` · muted `#6B7078` · slate `#3E5C76` ·
slate-soft `#E3E9EE` · clay `#B0654F` · clay-soft `#F1E4DE` · sage `#7A8B6F` ·
sage-soft `#E7EBE1` · plus `#4E7A94` · minus `#C1666B` · rule `#D8D2C6`
