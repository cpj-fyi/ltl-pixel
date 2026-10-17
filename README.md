# LTL Pixel

An independently drawn pixel serif in four styles: Regular, Italic, Bold and
Bold Italic. Includes installable TrueType fonts, WOFF2 web fonts and a
JavaScript typesetting engine, all built from the same cell drawings.

Freight was an early visual reference. LTL Pixel uses original cell drawings
and does not include Freight font data.

## Try it

Visit the [live specimen](https://cpj-fyi.github.io/ltl-pixel/) and click the
sample text to edit it directly. Choose a style and cell size with the buttons,
then toggle typographic features.

The self-contained [`index.html`](index.html) embeds the fonts and also works
offline, without a build step or server. It includes feature comparisons,
Hidden Patterns shapes and the character set.

## Download and install

[Download LTL Pixel — all four styles](https://cpj-fyi.github.io/ltl-pixel/fonts/LTL-Pixel.zip).
Unzip the download, double-click each `.ttf` file and choose **Install**
(**Install Font** on macOS).

The [`fonts/`](fonts/) directory also includes `.woff2` files for websites.

The native fonts support standard OpenType features for ligatures, kerning,
case forms, figures, small caps, superiors, inferiors, fractions and ordinals.
They also include `ss01` for smart quotes and dashes, and `ss02` for Hidden
Patterns colon shortcodes. Enable these through your application's OpenType
controls or CSS `font-feature-settings`. Native case forms must be enabled
explicitly; automatic all-caps detection belongs to the JavaScript renderer.
Its feature options are documented below.

## Use the renderer

`ltlpixel.js` is an ES module with no dependencies. Serve it and `glyphs.txt`
alongside your page, then draw into a canvas:

```js
import { parseTable, layout, paint } from './ltlpixel.js';

const table = parseTable(await (await fetch('./glyphs.txt')).text());
const text = layout(table, 'LTL Pixel', {
  maxWidthCells: 120,
  features: { liga: true, kern: true }
});

const canvas = document.querySelector('canvas');
const pitch = 8;
canvas.width = text.width * pitch;
canvas.height = text.height * pitch;
paint(canvas.getContext('2d'), text.cells, { pitch, color: '#000' });
```

Layout measurements use cells. `paint` converts them to canvas pixels using
`pitch`; it also accepts `x`, `y`, `gap` and `variant: 'square' | 'dot'`.

Pass runs to mix styles or features:

```js
const text = layout(table, [
  { text: 'Roman', style: 'roman' },
  { text: 'Italic', style: 'italic' },
  { text: '12345', features: { onum: true } }
]);
```

The engine also exports `shape`, `smartQuotes`, `hpColor`, `HP_COLORS`,
`METRICS` and `DEFAULT_FEATURES`. See the header of
[`ltlpixel.js`](ltlpixel.js) for the table format and full function signatures.

## JavaScript features

Pass features to `layout(table, text, { features })` or on an individual run.

| Option | Behavior |
| --- | --- |
| `liga` | Standard ff, fi, fl, ffi and ffl ligatures; on by default |
| `dlig` | Roman Th, ct and st ligatures |
| `kern` | Pair kerning; on by default |
| `case` | Punctuation for capitals; defaults to `'auto'` for all-caps words |
| `onum`, `tnum` | Oldstyle and tabular figures |
| `smcp`, `c2sc` | Lowercase or capitals to small caps; use `tracking: 1` |
| `sups`, `sinf` | Superior and inferior figures |
| `frac` | Numerator and denominator fractions such as `1/2` |
| `ordn` | Ordinals: `1a` → `1ª`, `2o` → `2º`, `No. 5` → `№ 5` |
| `smartQuotes` | Typographic quotes, dashes and ellipses |

Precomposed fractions such as ½, ¼ and ¾ are always assembled from numerator
and denominator figures. No-break spaces (U+00A0 and U+202F) keep words together.
To disable the default substitutions and spacing adjustments, pass
`features: { liga: false, kern: false, case: false }`.

## Hidden Patterns shapes

Six shapes follow the book's section order: Foundations (circle), Structuring
(triangle), Direction (parallelogram), Practice (square), Learning (star) and
Space (pentagon). Start & End has no shape.

Use section names such as `:foundations:` or shape names such as `:circle:`.
Add `.open` for an outline or `.cap` for cap height: `:practice.open:`,
`:learning.cap:`. `:logo:` sets all six shapes in order. In native fonts,
enable `ss02` to substitute the shortcodes; the live tester enables it for you.
The fonts also map these symbols to Private Use Area characters, listed in
[`fonts/INSTALL.txt`](fonts/INSTALL.txt).

In the JavaScript renderer, each laid-out cell carries its glyph name as `n`.
`hpColor(n)` returns the corresponding logo color, or `null` for other glyphs.

## Build

Rebuilding requires Python 3, Node.js, and the Python packages `fonttools` and
`brotli`. From the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install fonttools brotli
python3 merge.py
python3 font-build/build.py
python3 specimen/build.py
```

The font build writes four TTFs, four WOFF2s and `fonts/LTL-Pixel.zip`. The
specimen build embeds the fonts and writes identical standalone pages to
`index.html` for GitHub Pages and `specimen/ltl-pixel-specimen.html` for
portable sharing. The generated files are included; rebuilding is optional.

| File | Purpose |
| --- | --- |
| `glyphs-base.txt` | Base letterforms, cut A |
| `parts/*.txt` | Additional drawings, shift rules and shape aliases |
| `compose.txt` | Accented letters assembled from bases and marks |
| `merge.py` | Combines the sources and measures pair kerning |
| `glyphs.txt` | Generated table; edit its sources instead |
| `ltlpixel.js` | Parser, shaping, layout and canvas renderer |
| `font-build/build.py` | Generates fonts and the download ZIP |
| `fonts/` | TTFs, WOFF2s, download ZIP and installation notes |
| `specimen/template.html` | Editable specimen page |
| `specimen/build.py` | Embeds the fonts, glyph table and renderer in the specimen |
| `index.html` | Generated GitHub Pages entry point; edit the template instead |
| `preview.py` | Prints drawn glyphs as text |

For a terminal preview:

```sh
python3 preview.py glyphs.txt roman f_i 3.onum a.sc
```

The terminal preview shows stored drawings. Use the specimen to inspect
shifted forms and composites.

## Limitations

- ©, ®, ¶, ‰ and @ are rough at this resolution. Primes reuse quote shapes.
- Small-cap c and o reuse lowercase forms. Oldstyle 6 and 8 reuse lining forms.
- Italic has no ct or st ligatures.
- In the JavaScript renderer, unsupported accented characters fall back to
  their base letter. Other missing characters become a three-cell gap.
- In the JavaScript renderer, whitespace separates words; newlines do not
  force line breaks. Wrapping is controlled by `maxWidthCells`.

## Version

**v5.3 · 2026-10-17** — Installable TrueType and WOFF2 fonts, direct editing
in the live specimen, and button controls for style and cell size.

v5.2 added the standalone specimen and repository documentation without
changing glyph drawings, composition rules, metrics or kerning.

v5.1 added the Hidden Patterns shapes and aliases. v5.0 expanded cut A with
ligatures, figure styles, small caps, symbols, accented letters and kerning.

## License

A reuse license has not yet been selected for this repository.
