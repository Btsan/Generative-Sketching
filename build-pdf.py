#!/usr/bin/env python3
"""Build a print-ready copy of the deck and export it to PDF.

Two stages, because neither one alone works:

  1. Chrome's --print-to-pdf fires at the load event, but Reveal builds its print
     layout asynchronously (two awaited requestAnimationFrame hops inside the print
     plugin), so printing the deck directly yields a blank two-page PDF. So stage 1
     loads the print copy with --dump-dom and a virtual-time budget, giving Reveal
     time to build the .pdf-page wrappers, MathJax time to typeset every slide, and
     the deck's own layout*() measurers time to draw their SVG connectors.

  2. The dumped DOM is stripped of every <script> and printed. It is fully static by
     then -- all positions are baked into style attributes -- so --print-to-pdf's
     print-at-load behaviour is exactly what we want.

Requires only Google Chrome; no Node.
"""

import base64, os, re, shutil, subprocess, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "generative-sketching.html")
PRINT_SRC = os.path.join(HERE, "generative-sketching-print.html")
FLAT = os.path.join(HERE, "_print-flat.html")
PDF_WIN = r"C:\Users\btsan\OneDrive\Desktop\LLNL Seminar\generative-sketching.pdf"
PDF = os.path.join(HERE, "generative-sketching.pdf")
CHROME = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
URL_BASE = "file:///C:/Users/btsan/OneDrive/Desktop/LLNL%20Seminar/"

CHROME_FLAGS = [
    "--headless=new", "--disable-gpu", "--allow-file-access-from-files",
    # Without these two, requestAnimationFrame never advances in headless and
    # Reveal's print plugin stalls before it creates a single .pdf-page.
    "--run-all-compositor-stages-before-draw", "--disable-new-content-rendering-timeout",
]


def sub1(text, old, new, label):
    """Replace exactly one occurrence, or die loudly -- a silent miss would ship a
    print deck that still has the live video in it."""
    n = text.count(old)
    if n != 1:
        sys.exit("build-pdf: expected 1 occurrence of %s, found %d" % (label, n))
    return text.replace(old, new)


def subn(text, old, new, count, label):
    """Replace `old` exactly `count` times, or die loudly."""
    n = text.count(old)
    if n != count:
        sys.exit("build-pdf: expected %d occurrences of %s, found %d"
                 % (count, label, n))
    return text.replace(old, new)


CLOSE = "\n      </section>"


def slide_span(text, needle, nth, label):
    """Locate the whole <section> containing the `nth` (1-based) `needle`.

    Returns (start, stop) such that text[start:stop] is the entire slide, opening
    newline included and closing tag consumed. Slides are leaf <section> elements at a
    uniform six-space indent with no nested <section> inside them, so walking out to
    the enclosing tags by index is exact. Callers that edit the text must re-find
    afterwards rather than reusing stale offsets.
    """
    pos = -1
    for _ in range(nth):
        pos = text.find(needle, pos + 1)
        if pos < 0:
            sys.exit("build-pdf: fewer than %d occurrences of %s" % (nth, label))
    start = text.rfind("\n      <section", 0, pos)
    end = text.find(CLOSE, pos)
    if start < 0 or end < 0:
        sys.exit("build-pdf: could not find the <section> around " + label)
    return start, end + len(CLOSE)


def drop_slide(text, needle, nth, label):
    """Delete the whole <section> that contains the `nth` (1-based) `needle`."""
    start, stop = slide_span(text, needle, nth, label)
    return text[:start] + text[stop:]


# --------------------------------------------------------------------------
# Stage 0 -- derive the print copy from the deck
# --------------------------------------------------------------------------

VIDEO_OLD = """          <video src="JEPA/cifar10_jepa_projection_h264.mp4" style="width:902px;"
                 data-autoplay loop muted playsinline controls preload="metadata"></video>"""

# The two stills were pulled out of JEPA/cifar10_jepa_projection_h264.mp4 (1600x800,
# 97.5s) by seeking a headless Chrome <video> to t=24.4s and t=78.0s and drawing each
# frame to a canvas -- epoch 2 / step 243 and epoch 5 / step 780. If they ever need
# regenerating, note that the seek only completes under --virtual-time-budget, and
# that reading the canvas back needs --allow-file-access-from-files.
ALT_EARLY = ("Early in training: the CIFAR-10 latents form an elongated, anisotropic "
             "cloud, and the 1-D sketch density is visibly skewed against the target normal.")
ALT_CONVERGED = ("Later in training: the latents fill the 2-standard-deviation circle "
                 "isotropically and the 1-D sketch density tracks the target normal closely.")

# width:902px is the video's own width, so the plot lands exactly where the video did.
IMG = ('          <img src="JEPA/%s" width="1600" height="800" style="width:902px;"\n'
       '               alt="%s">')


def split_sigreg_slide(src):
    """Give each still pulled from the SIGReg video a slide of its own.

    A single converged frame would lose the point of the slide, which is that SIGReg
    drives the cloud isotropic as training PROCEEDS -- so both frames have to appear.
    Side by side they fit only at 440px, where the axis labels and the SIGReg/MSE
    readout in each plot's title need zooming to read; one per slide gives each the
    902px the video had.

    The second slide is derived from the first rather than written out here, so the
    eyebrow, heading and captions are never copied into this file and cannot drift
    when the deck's wording changes.
    """
    src = sub1(src, VIDEO_OLD, IMG % ("sigreg-early.png", ALT_EARLY), "<video> block")
    start, stop = slide_span(src, "sigreg-early.png", 1, "SIGReg slide")
    copy = src[start:stop]
    copy = sub1(copy, "sigreg-early.png", "sigreg-converged.png", "still filename")
    copy = sub1(copy, ALT_EARLY, ALT_CONVERGED, "still alt text")
    # Leading newline keeps the blank line between sections that the deck uses.
    return src[:stop] + "\n" + copy + src[stop:]


def drop_row1_training(src):
    """Cut the second half of the "Training the model" build.

    The build is four slides: two walk row 0 of the Orders table into the model and
    out to the loss, two do exactly the same for row 1. Live, the repetition makes
    the point that every row is an example. On paper it is two more near-identical
    pages the reader has to diff against the previous two before concluding nothing
    changed, so the row-1 pair goes.

    The catch is that the two slides AFTER the build carry row 1's dots forward --
    two attr-2 dots in the model's input sockets and a green key in the loss slot.
    Drop the row-1 pair without retargeting those and the dots arrive with no slide
    having put them there, in colours that no longer match the row just shown.
    """
    src = drop_slide(src, "<h2>Training the model</h2>", 4, "training slide 4 (row 1)")
    src = drop_slide(src, "<h2>Training the model</h2>", 3, "training slide 3 (row 1)")
    if src.count("<h2>Training the model</h2>") != 2:
        sys.exit("build-pdf: expected 2 training slides left after the cut")

    # Only now: before the cut these same substrings also appear inside the two
    # doomed slides, where the a/b pair sits in the table's cell-slots instead.
    # The row-0 spellings are copied verbatim from the slide that survives.
    src = subn(src, 'class="dot attr-2 fly-dot" data-id="fly-r1-a"',
                    'class="dot attr-3 fly-dot" data-id="fly-r0-a"', 2, "flier r1-a")
    src = subn(src, 'class="dot attr-2 fly-dot" data-id="fly-r1-b"',
                    'class="dot attr-1 fly-dot" data-id="fly-r0-b"', 2, "flier r1-b")
    src = subn(src, 'data-id="fly-r1-key" style="background:var(--green)"',
                    'data-id="fly-r0-key" style="background:var(--red)"', 1, "flier r1-key")
    if "fly-r1" in src:
        sys.exit("build-pdf: a row-1 flier survived the retarget -- the deck grew a "
                 "reference this function does not know about")
    return src


CONFIG_OLD = """  Reveal.initialize({
    width: 1120, height: 760, margin: 0.06,
    minScale: 0.2, maxScale: 3.0,
    hash: true, slideNumber: 'c/t',
    controls: true, progress: true,
    transition: 'fade', transitionSpeed: 'default',
    autoAnimateEasing: 'ease', autoAnimateDuration: 0.6,
    plugins: [RevealNotes]
  });"""

# view:'print' is set in the config rather than via a ?print-pdf query string: the
# query-string route also trips Reveal's scroll view, which lazily DETACHES the
# off-screen slides, and the dump then captures a deck with most of its slides gone.
CONFIG_NEW = """  Reveal.initialize({
    view: 'print',
    pdfSeparateFragments: false,   /* one page per slide, showing its final state */
    pdfMaxPagesPerSlide: 1,
    width: 1120, height: 760, margin: 0.06,
    minScale: 0.2, maxScale: 3.0,
    hash: false, slideNumber: false,
    controls: false, progress: false,
    transition: 'none', transitionSpeed: 'default',
    autoAnimateEasing: 'ease', autoAnimateDuration: 0,
    plugins: [RevealNotes]
  });"""

RAF_SHIM = """
<!-- ===== print-only: put requestAnimationFrame on a timer ==================== -->
<script>
/* Reveal's print plugin awaits two animation frames before it builds a single page,
   and headless Chrome under a virtual clock produces frames erratically -- six in
   four virtual minutes on a bad run, twenty on a good one -- so waiting on real
   frames made the export a coin flip. Timers, by contrast, are exactly what the
   virtual clock drives. Nothing here animates on paper, so trading frames for
   timers costs nothing and makes the build deterministic. Must load BEFORE
   reveal.min.js, which captures rAF at parse time. */
window.requestAnimationFrame = function (cb) {
  return setTimeout(function () { cb(Date.now()); }, 16);
};
window.cancelAnimationFrame = function (id) { clearTimeout(id); };
</script>
"""


PRINT_CSS = """
<!-- ===== print-only overrides (this file only; the live deck is untouched) ===== -->
<style>
  /* Controls are dead pixels on paper. The stepper LABEL and VALUE stay, so each
     demo still reports the width/depth it was captured at. */
  .print-only-hide, .tw-btn, .step-btn { display: none !important; }
  /* .tw-controls and .vmv-foot are flex rows built around the buttons; with the
     buttons gone the remaining readouts need their own centring. */
  .tw-controls, .vmv-foot, .csk-steppers { justify-content: center; }
  /* Nothing animates on paper: a mid-flight transition would be captured half-done. */
  * { transition: none !important; animation: none !important; }
  /* The deck's draw-on arrows are dasharray-animated; force them fully drawn. */
  .fragment.draw .arrow-svg * { stroke-dashoffset: 0 !important; }
</style>
"""

PRINT_JS = """
<!-- ===== print pass: build every slide, then stand still ====================== -->
<script>
(function () {
  /* Reveal only ever lays out the CURRENT slide, and the deck's layout*() helpers
     follow that lead -- they take one slide and bail if it is not theirs. On paper
     every slide is "current", so run the whole battery over every section. */
  var LAYOUTS = ['layoutJoinLines', 'layoutTugOfWar', 'layoutRandomTug', 'layoutJoinSketch',
                 'layoutCountSketch', 'layoutStreamSketch', 'layoutSchemaGraph',
                 'layoutRuntimeBars', 'layoutVmv'];

  function each(sel, fn) { Array.prototype.forEach.call(document.querySelectorAll(sel), fn); }
  function tryIt(fn) { try { return fn(); } catch (e) { console.warn('print:', e); } }

  function showFragments() {
    /* Reveal's print CSS makes fragments opaque, but the deck also keys its own
       styling off the .visible class (.gen-lit.visible, .gen-sk.visible, the
       .s2/.s3 carousel triggers), so the class has to be set explicitly. */
    each('.reveal .fragment', function (f) {
      f.classList.add('visible');
      f.classList.remove('current-fragment');
    });
  }

  function buildSlides() {
    each('.reveal .slides section', function (s) {
      tryIt(function () { renderSignVectors(s); });
      tryIt(function () { typesetSlide(s); });
      LAYOUTS.forEach(function (name) {
        if (typeof window[name] === 'function') tryIt(function () { window[name](s); });
      });
    });
  }

  function click(sel, times) {
    var b = document.querySelector(sel);
    if (!b) return;
    for (var i = 0; i < times; i++) tryIt(function () { b.click(); });
  }

  /* Every demo boots at width 1 / depth 1 with em-dashes for its estimates, which on
     paper just looks broken. Step each one up to a setting that actually shows
     structure and run it far enough that the running averages have numbers in them. */
  function settleDemos() {
    click('[data-csk="w+"]', 3);
    click('[data-csk="d+"]', 2);
    click('[data-str="w+"]', 3);
    click('[data-str="d+"]', 2);
    click('#vmv-wplus', 3);
    for (var i = 0; i < 12; i++) {
      if (typeof twRound === 'function') tryIt(twRound);
      if (typeof strTick === 'function') tryIt(strTick);
      if (typeof vmvDraw === 'function') tryIt(vmvDraw);
    }
    /* Kill the timers those handlers may have started, so the dump is not racing
       an in-flight animation frame. */
    ['twStop', 'strStop', 'vmvStop'].forEach(function (n) {
      if (typeof window[n] === 'function') tryIt(window[n]);
    });
  }

  /* MathJax adds its per-character rules through the CSSOM (sheet.insertRule), and
     those rules live only in memory -- --dump-dom serialises the <style> element's
     text, which stays nearly empty. Without this the snapshot loses every glyph
     rule, and because MathJax's first fallback face is MathJax_Zero (all glyphs
     zero-width) the math does not fall back visibly, it just vanishes. Writing the
     rules back into the element's text makes them part of the dump. */
  function bakeCSSOM() {
    var el = document.getElementById('MJX-CHTML-styles');
    if (!el || !el.sheet) return;
    var out = [], r = el.sheet.cssRules;
    for (var i = 0; i < r.length; i++) out.push(r[i].cssText);
    el.textContent = out.join(String.fromCharCode(10));  /* PRINT_JS is not a raw
       string, so a literal escape here would land in the emitted JS as a real
       newline inside a string literal -- a syntax error that kills the whole pass. */
  }

  function ready() { return document.querySelectorAll('.pdf-page').length > 0; }

  /* Waiting here is fiddly, and both obvious spellings fail:
       - a setTimeout poll runs Chrome's virtual clock forward far faster than real
         frames are produced, so it exhausts its tries in a handful of frames and
         gives up before Reveal has built page one;
       - a requestAnimationFrame poll stalls, because a pending frame request does
         not hold the virtual clock -- Chrome fast-forwards to the budget, no frame
         is ever produced, and the chain simply dies.
     So run both: a self-chaining timer whose only job is to keep the virtual clock
     honest, and a continuous rAF loop that does the actual work in step with the
     frames Reveal's print plugin is itself awaiting. Dropping the timer at the end
     lets the page go idle, which is Chrome's cue to dump. */
  var t0 = Date.now(), tries = 0, oops = '';
  window.addEventListener('error', function (e) { oops += ' JSERR:' + e.message; });

  function mark(why) {
    if (document.getElementById('print-ready')) return;
    var flag = document.createElement('div');
    flag.id = 'print-ready';
    flag.setAttribute('style', 'display:none');
    flag.textContent = 'pages=' + document.querySelectorAll('.pdf-page').length +
                       ' why=' + why + ' tries=' + tries +
                       ' ms=' + (Date.now() - t0) + oops;
    document.documentElement.appendChild(flag);
  }

  function finish() {
    /* Order matters. buildSlides() is what runs the deck's layout*() helpers, and
       those helpers are also what CREATE the demo objects and bind their button
       handlers -- so stepping a demo before the first build silently clicks dead
       buttons and the figure prints at its trivial width-1/depth-1 boot state.
       Each helper defers its real work by a setTimeout(...,0), hence the gaps. */
    showFragments();
    buildSlides();
    setTimeout(function () {
      settleDemos();
      setTimeout(function () {
        /* Final build: MathJax typesetting and the demo re-renders above both
           resize elements, so connectors measured earlier are stale. */
        buildSlides();
        showFragments();
        setTimeout(function () {
          bakeCSSOM();
          mark(ready() ? 'ok' : 'no-pdf-pages');
        }, 400);
      }, 1200);
    }, 1200);
  }

  (function wait() {
    if (ready()) { finish(); return; }
    if (tries++ > 600) { mark('gave-up-waiting-for-print-layout'); return; }
    setTimeout(wait, 50);
  })();
})();
</script>
"""


def build_print_source():
    src = open(SRC, encoding="utf-8").read()
    src = split_sigreg_slide(src)
    src = drop_row1_training(src)
    src = sub1(src, CONFIG_OLD, CONFIG_NEW, "Reveal.initialize block")
    src = sub1(src, "</head>", PRINT_CSS + "</head>", "</head>")
    src = sub1(src, '<script src="vendor/reveal/reveal.min.js"></script>',
               RAF_SHIM + '<script src="vendor/reveal/reveal.min.js"></script>',
               "reveal.min.js tag")
    src = sub1(src, "</body>", PRINT_JS + "</body>", "</body>")
    src = sub1(src, "<title>", "<title>PDF build \u2014 ", "<title>")
    banner = ("<!-- GENERATED FILE -- do not hand-edit. Produced by build-pdf.py from\n"
              "     generative-sketching.html, which stays the deck you present.\n"
              "     Regenerate with: python3 build-pdf.py -->\n")
    src = sub1(src, "<!doctype html>\n", "<!doctype html>\n" + banner, "doctype")
    open(PRINT_SRC, "w", encoding="utf-8").write(src)
    print("stage 0: wrote %s (%d KB)" % (os.path.basename(PRINT_SRC), len(src) // 1024))


def chrome(extra, out=None):
    cmd = [CHROME] + CHROME_FLAGS + extra
    r = subprocess.run(cmd, capture_output=True)
    return r



FONT_CACHE = os.path.join(HERE, "_printfonts")


def static_font(src, weight, italic):
    """Return a path to a plain, static sfnt copy of one webfont file.

    Chrome's PDF backend will not embed either of the two shapes the deck ships:

      * variable fonts -- Inter and JetBrains Mono from Google Fonts both carry an
        fvar table, and print silently substitutes Segoe UI and Consolas for them;
      * the woff/woff2 wrappers themselves -- MathJax's woff files are static CFF
        and still get dropped, which is worse than it sounds, because MathJax's
        first fallback face is MathJax_Zero, whose glyphs are all zero-width. Every
        formula in the deck printed as blank space.

    On screen all of these render correctly, so the bug only ever shows up in the
    PDF. Decompressing to a bare sfnt and pinning any variable axes to the weight
    the @font-face asked for fixes both cases. Results are cached because a full
    rebuild converts ~85 faces.
    """
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    tag = "%s-%s%s" % (os.path.splitext(os.path.basename(src))[0][:40],
                       weight or "n", "i" if italic else "")
    for ext, fmt in ((".ttf", "truetype"), (".otf", "opentype")):
        hit = os.path.join(FONT_CACHE, tag + ext)
        if os.path.exists(hit):
            return hit, fmt
    if not os.path.isdir(FONT_CACHE):
        os.makedirs(FONT_CACHE)
    f = TTFont(src)
    f.flavor = None          # drop the woff/woff2 wrapper
    if "fvar" in f:
        axes = set(a.axisTag for a in f["fvar"].axes)
        pins = {}
        if weight and "wght" in axes:
            pins["wght"] = float(weight)
        if italic and "ital" in axes:
            pins["ital"] = 1
        if italic and "slnt" in axes:
            pins["slnt"] = -10
        f = instancer.instantiateVariableFont(f, pins, inplace=True)
    # MathJax's faces carry CFF outlines, the Google faces carry glyf. Declaring the
    # wrong one in format() is the sort of thing Chrome sometimes forgives and
    # sometimes does not, so key both the extension and the format() off the outlines.
    ext, fmt = (".otf", "opentype") if "CFF " in f else (".ttf", "truetype")
    out = os.path.join(FONT_CACHE, tag + ext)
    f.save(out)
    return out, fmt


# MathJax numbers the faces it generates -- `@font-face /* 12 */ {` -- so the comment
# has to be part of the pattern or none of the math faces are found.
FACE_RE = re.compile(r"@font-face\s*(?:/\*.*?\*/\s*)?\{[^}]*\}", re.I | re.S)
# Swallow any trailing format() too: leaving the original in place produced
# `format('truetype') format('woff2')`, which is invalid, and an invalid src drops
# the whole rule -- that one typo cost the deck every one of its webfonts.
URL_RE = re.compile(r'url\(\s*["\']?([^"\')]+\.woff2?)["\']?\s*\)'
                    r'(?:\s*format\([^)]*\))?', re.I)


def staticize_css(css, base):
    """Rewrite every @font-face in `css` to point at a static, unwrapped font.

    `base` is the directory that the css's relative url()s resolve against.
    """
    def one_face(m):
        block = m.group(0)
        w = re.search(r"font-weight:\s*([0-9]+)", block, re.I)
        weight = w.group(1) if w else None
        italic = bool(re.search(r"font-style:\s*italic", block, re.I))

        def one_url(u):
            raw = u.group(1)
            if raw.startswith("file:///"):
                # MathJax bakes absolute file: URLs into the stylesheet it generates.
                src = urllib.parse.unquote(raw[len("file:///"):])
                src = "/mnt/" + src[0].lower() + src[2:]
            else:
                src = os.path.join(base, raw)
            if not os.path.exists(src):
                sys.exit("build-pdf: font referenced but missing: " + src)
            path, fmt = static_font(src, weight, italic)
            return "url(%s) format('%s')" % (os.path.relpath(path, HERE), fmt)

        return URL_RE.sub(one_url, block)

    out, n = FACE_RE.subn(one_face, css)
    if not n:
        sys.exit("build-pdf: no @font-face rules found to staticize")
    return out


def snapshot():
    r = chrome(["--virtual-time-budget=400000", "--dump-dom",
                URL_BASE + "generative-sketching-print.html"])
    dom = r.stdout.decode("utf-8", "replace")
    m = re.search(r'id="print-ready"[^>]*>([^<]*)<', dom)
    if not m:
        sys.exit("build-pdf: print pass never finished (no #print-ready marker); "
                 "raise --virtual-time-budget or check the console")
    print("       marker:", m.group(1).strip())
    pages = int(m.group(1).split("=")[1].split()[0])
    if pages == 0:
        sys.exit("build-pdf: print pass ran before Reveal built any .pdf-page; "
                 "the readiness poll gave up too early")
    # Strip every script: the dump still carries reveal.min.js et al., and re-running
    # them on the flat file would re-initialize Reveal and undo the baked layout.
    flat = re.sub(r"<script\b[^>]*>.*?</script>", "", dom, flags=re.S | re.I)
    flat = re.sub(r"<script\b[^>]*/?>", "", flat, flags=re.I)
    # The deck's own faces arrive as a <link> to fonts.css, MathJax's arrive as a
    # <style> block it generated at runtime; both need the same treatment.
    deck_css = open(os.path.join(HERE, "vendor/fonts/fonts.css"), encoding="utf-8").read()
    deck_css = staticize_css(deck_css, os.path.join(HERE, "vendor/fonts"))
    flat = sub1(flat, '<link rel="stylesheet" href="vendor/fonts/fonts.css">',
                "<style>" + deck_css + "</style>", "fonts.css link")
    flat = FACE_RE.sub(lambda m: staticize_css(m.group(0), HERE), flat)
    open(FLAT, "w", encoding="utf-8").write(flat)
    print("stage 1: snapshot built, %d pdf pages, flat file %d KB"
          % (pages, len(flat) // 1024))
    return pages


def to_pdf():
    if os.path.exists(PDF):
        os.remove(PDF)
    r = chrome(["--no-pdf-header-footer", "--virtual-time-budget=20000",
                "--print-to-pdf=" + PDF_WIN, URL_BASE + os.path.basename(FLAT)])
    if not os.path.exists(PDF):
        sys.exit("build-pdf: chrome produced no PDF\n" + r.stderr.decode("utf-8", "replace"))
    data = open(PDF, "rb").read()
    n = len(re.findall(rb"/Type\s*/Page[^s]", data))
    print("stage 2: %s -- %d pages, %d KB"
          % (os.path.basename(PDF), n, len(data) // 1024))
    return n


if __name__ == "__main__":
    build_print_source()
    want = snapshot()
    got = to_pdf()
    if got != want:
        print("WARNING: %d pdf-page wrappers but %d PDF pages" % (want, got))
    if "--keep" not in sys.argv and os.path.exists(FLAT):
        os.remove(FLAT)
