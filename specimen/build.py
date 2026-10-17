# Build the standalone specimen and GitHub Pages entry point.
# Run merge.py and font-build/build.py first if glyph sources changed.
from base64 import b64encode
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parent
lib = (root / 'ltlpixel.js').read_text(encoding='utf-8').replace('export const', 'const').replace('export function', 'function')
glyphs = (root / 'glyphs.txt').read_text(encoding='utf-8')
assert '</script' not in glyphs.lower()
faces = []
for name, weight, style in [('Regular', 400, 'normal'), ('Italic', 400, 'italic'), ('Bold', 700, 'normal'), ('BoldItalic', 700, 'italic')]:
    data = b64encode((root / 'fonts' / f'LTLPixel-{name}.woff2').read_bytes()).decode('ascii')
    faces.append(f"@font-face {{ font-family: 'LTL Pixel'; src: url(data:font/woff2;base64,{data}) format('woff2'); font-weight: {weight}; font-style: {style}; font-display: block; }}")
page = (here / 'template.html').read_text(encoding='utf-8').replace('__GLYPHS__', glyphs).replace('__LIB__', lib).replace('__FONT_FACES__', '\n'.join(faces))
for target in (here / 'ltl-pixel-specimen.html', root / 'index.html'):
    target.write_text(page, encoding='utf-8')
    print('wrote', target.relative_to(root))
