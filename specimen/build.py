# Build the standalone specimen and GitHub Pages entry point.
# Run merge.py first if glyph sources changed. No third-party dependencies.
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parent
lib = (root / 'ltlpixel.js').read_text(encoding='utf-8').replace('export const', 'const').replace('export function', 'function')
glyphs = (root / 'glyphs.txt').read_text(encoding='utf-8')
assert '</script' not in glyphs.lower()
page = (here / 'template.html').read_text(encoding='utf-8').replace('__GLYPHS__', glyphs).replace('__LIB__', lib)
for target in (here / 'ltl-pixel-specimen.html', root / 'index.html'):
    target.write_text(page, encoding='utf-8')
    print('wrote', target.relative_to(root))
