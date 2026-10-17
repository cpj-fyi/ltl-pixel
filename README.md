# LTL Pixel

An independently drawn pixel serif with a JavaScript typesetting engine. Roman
and italic letterforms are stored as cell drawings; the engine handles spacing,
ligatures, figures, accents and canvas rendering. There is no font binary to
install. The four styles are roman, italic, bold and bold italic.

Freight was an early visual reference. LTL Pixel uses original cell drawings
and does not include Freight font data.

## Try it

Visit the [live specimen](https://cpj-fyi.github.io/ltl-pixel/) or open
[`index.html`](index.html) in a browser. The self-contained specimen includes a
text tester, feature controls, Hidden Patterns shapes and the character set.
The local file needs no build step or server.

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

## Features

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
`:learning.cap:`. `:logo:` sets all six shapes in order.

Each laid-out cell carries its glyph name as `n`. `hpColor(n)` returns the
corresponding logo color, or `null` for other glyphs.

## Build

Python 3 is needed only to rebuild the tables and specimen. Run from the
repository root:

```sh
python3 merge.py
python3 specimen/build.py
```

The specimen build writes identical standalone pages to `index.html` for
GitHub Pages and `specimen/ltl-pixel-specimen.html` for portable sharing.

| File | Purpose |
| --- | --- |
| `glyphs-base.txt` | Base letterforms, cut A |
| `parts/*.txt` | Additional drawings, shift rules and shape aliases |
| `compose.txt` | Accented letters assembled from bases and marks |
| `merge.py` | Combines the sources and measures pair kerning |
| `glyphs.txt` | Generated table; edit its sources instead |
| `ltlpixel.js` | Parser, shaping, layout and canvas renderer |
| `specimen/template.html` | Editable specimen page |
| `specimen/build.py` | Embeds the table and renderer in the standalone specimen |
| `index.html` | Generated GitHub Pages entry point; edit the template instead |
| `preview.py` | Prints drawn glyphs as text |

For a terminal preview:

```sh
python3 preview.py glyphs.txt roman f_i 3.onum a.sc
```

The terminal preview shows stored drawings. Shifted forms and composites need
the JavaScript renderer.

## Limitations

- ©, ®, ¶, ‰ and @ are rough at this resolution. Primes reuse quote shapes.
- Small-cap c and o reuse lowercase forms. Oldstyle 6 and 8 reuse lining forms.
- Italic has no ct or st ligatures.
- Unsupported accented characters fall back to their base letter. Other
  missing characters become a three-cell gap.
- Whitespace separates words; newlines do not force line breaks. Wrapping is
  controlled by `maxWidthCells`.

## Version

**v5.2 · 2026-10-17** — Standalone specimen and repository documentation.
Presentation and packaging changes only; glyph drawings, composition rules,
metrics and kerning are unchanged from v5.1.

v5.1 added the Hidden Patterns shapes and aliases. v5.0 expanded cut A with
ligatures, figure styles, small caps, symbols, accented letters and kerning.

## License

A reuse license has not yet been selected for this repository.
