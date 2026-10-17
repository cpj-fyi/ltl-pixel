#!/usr/bin/env python3
"""Build installable LTL Pixel fonts from the canonical JavaScript parser.

Requires Node.js, Python 3, fonttools and brotli. Run python3 font-build/build.py.
All outlines are unions of the original square cells, with shared edges removed.
"""
from collections import defaultdict
from pathlib import Path
import json
import math
import subprocess
import unicodedata
import zipfile

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'fonts'
SCALE = 100
UPM = 1600
STYLES = [('roman', 'Regular', 400, False), ('italic', 'Italic', 400, True),
          ('bold', 'Bold', 700, False), ('bold-italic', 'BoldItalic', 700, True)]
SHAPES = ['circle', 'triangle', 'parallelogram', 'square', 'star', 'pentagon']


def glyph_name(name):
    if len(name) == 1:
        return ('uni%04X' if ord(name) <= 0xFFFF else 'u%05X') % ord(name)
    if name[1:2] == '.':
        return glyph_name(name[0]) + name[1:]
    return name


def outline(cells):
    """Trace the union boundary; clockwise outside, counterclockwise holes."""
    edges = set()
    for cell in cells:
        x, y = cell['x'], -cell['y'] - 1
        corners = [(x, y), (x, y + 1), (x + 1, y + 1), (x + 1, y)]
        for a, b in zip(corners, corners[1:] + corners[:1]):
            if (b, a) in edges:
                edges.remove((b, a))
            else:
                edges.add((a, b))
    by_start = defaultdict(set)
    for a, b in edges:
        by_start[a].add(b)
    pen = TTGlyphPen(None)
    area = 0
    while edges:
        start, point = min(edges)
        previous = start
        contour = [start]
        while True:
            edges.remove((previous, point))
            by_start[previous].remove(point)
            contour.append(point)
            if point == start:
                break
            candidates = by_start[point]
            if not candidates:
                raise ValueError('Open cell boundary')
            # At diagonal contacts, take the sharpest right turn so each
            # connected filled region gets a simple, correctly wound contour.
            vx, vy = point[0] - previous[0], point[1] - previous[1]
            def turn(p):
                wx, wy = p[0] - point[0], p[1] - point[1]
                return math.atan2(vx * wy - vy * wx, vx * wx + vy * wy)
            following = min(candidates, key=turn)
            previous, point = point, following
        contour.pop()
        area += sum(a[0] * b[1] - b[0] * a[1]
                    for a, b in zip(contour, contour[1:] + contour[:1])) / 2
        # Straight cell edges need only their endpoints.
        simple = []
        for i, p in enumerate(contour):
            a, b = contour[i - 1], contour[(i + 1) % len(contour)]
            if (p[0] - a[0]) * (b[1] - p[1]) != (p[1] - a[1]) * (b[0] - p[0]):
                simple.append(p)
        pen.moveTo(tuple(v * SCALE for v in simple[0]))
        for p in simple[1:]:
            pen.lineTo(tuple(v * SCALE for v in p))
        pen.closePath()
    assert area == -len({(c['x'], c['y']) for c in cells}), (area, len(cells))
    return pen.glyph()


def features(glyphs, data):
    n = glyph_name
    lines = ['languagesystem DFLT dflt;', 'languagesystem latn dflt;']
    def feature(tag, rules):
        if rules:
            lines.extend(['feature %s {' % tag, *rules, '} %s;' % tag])
    def substitutions(suffix, bases=None):
        bases = bases or [g for g in glyphs if len(g) == 1]
        return [f'sub {n(g)} by {n(g + suffix)};' for g in bases if g + suffix in glyphs]
    # Smart punctuation is optional; source characters stay untouched in editors.
    all_names = ' '.join(n(g) for g in glyphs)
    lines.append('@All = [%s];' % all_names)
    quote_rules = [f'sub {n("-")} {n("-")} {n("-")} by {n("—")};',
                   f'sub {n("-")} {n("-")} by {n("–")};',
                   f'sub {n(".")} {n(".")} {n(".")} by {n("…")};']
    feature('ss01', quote_rules)
    for label, straight, opening, closing in [('Double', '"', '“', '”'), ('Single', "'", '‘', '’')]:
        context = '([{“‘—–-' if label == 'Double' else '([{“—–-'
        starts = ['space', 'nbsp', 'nnbsp'] + [n(c) for c in context]
        lines += [f'lookup {label}Initial {{', f'ignore sub @All {n(straight)}\';',
                  f'sub {n(straight)}\' by {n(opening)};', f'}} {label}Initial;',
                  f'lookup {label}Opening {{', f'sub [{" ".join(starts)}] {n(straight)}\' by {n(opening)};',
                  f'}} {label}Opening;', f'lookup {label}Closing {{ sub {n(straight)} by {n(closing)}; }} {label}Closing;']
        feature('ss01', [f'lookup {label}Initial;', f'lookup {label}Opening;', f'lookup {label}Closing;'])
    # Expand names before small caps or letter ligatures can change their input.
    aliases = []
    for alias, names in data['alias'].items():
        for suffix in ['', '.open', '.cap']:
            target = 'alias.logo' + suffix if alias == 'logo' else names[0] + suffix
            shortcode = ':' + alias + suffix + ':'
            aliases.append((shortcode, target))
    feature('ss02', ['sub %s by %s;' % (' '.join(n(c) for c in text), n(target))
                     for text, target in sorted(aliases, key=lambda x: -len(x[0]))])
    digits = [str(i) for i in range(10)]
    for label, suffix in [('Digits', ''), ('Numerators', '.numr'), ('Denominators', '.dnom')]:
        lines.append('@%s = [%s];' % (label, ' '.join(n(d + suffix) for d in digits)))
    # Reverse chaining walks to the beginning of an arbitrarily long numerator;
    # the forward denominator lookup propagates from the fraction slash.
    lines += ['lookup FractionSlash {', f'sub @Digits {n("/")}\' @Digits by {n("⁄")};', '} FractionSlash;',
              'lookup FractionNumerators {', f'rsub @Digits\' [{n("⁄")} @Numerators] by @Numerators;', '} FractionNumerators;',
              'lookup MakeDenominator { sub @Digits by @Denominators; } MakeDenominator;',
              'lookup FractionDenominators {', f'sub [{n("⁄")} @Denominators] @Digits\' lookup MakeDenominator;', '} FractionDenominators;']
    feature('frac', ['lookup FractionSlash;', 'lookup FractionNumerators;', 'lookup FractionDenominators;'])
    for tag in ['numr', 'dnom', 'sups', 'sinf']:
        feature(tag, substitutions('.' + tag))
    lines.append('@Letters = [%s];' % ' '.join(n(chr(c)) for c in list(range(65, 91)) + list(range(97, 123))))
    lines.append('@NonSpace = [%s];' % ' '.join(n(g) for g in glyphs if g not in ['space', 'nbsp', 'nnbsp', 'zwspace']))
    lines += ['lookup OrdinalLetters {',
              f'ignore sub @Digits [{n("a")} {n("o")}]\' @Letters;',
              f'sub @Digits {n("a")}\' by {n("ª")};', f'sub @Digits {n("o")}\' by {n("º")};',
              '} OrdinalLetters;', 'lookup NumeroGlyph {',
              f'sub {n("N")} {n("o")} {n(".")} by {n("№")};', f'sub {n("N")} {n("o")} by {n("№")};',
              '} NumeroGlyph;', 'lookup NumeroWord {',
              f'ignore sub @NonSpace {n("N")}\' {n("o")};',
              f'ignore sub {n("N")}\' {n("o")} {n(".")} @NonSpace;',
              f'sub {n("N")}\' lookup NumeroGlyph {n("o")} {n(".")};',
              f'ignore sub {n("N")}\' {n("o")} @NonSpace;',
              f'sub {n("N")}\' lookup NumeroGlyph {n("o")};', '} NumeroWord;']
    feature('ordn', ['lookup OrdinalLetters;', 'lookup NumeroWord;'])
    feature('smcp', substitutions('.sc'))
    case_rules = substitutions('.case')
    feature('c2sc', [f'sub {n(chr(c))} by {n(chr(c + 32) + ".sc")};' for c in range(65, 91)] + case_rules)
    feature('case', case_rules)
    feature('onum', substitutions('.onum', digits))
    feature('tnum', [f'sub {n(d + s)} by {n(d + s + ".tnum")};' for s in ['', '.onum'] for d in digits])
    for tag, names in [('liga', ['f_f_i', 'f_f_l', 'f_f', 'f_i', 'f_l']), ('dlig', ['T_h', 'c_t', 's_t'])]:
        feature(tag, ['sub %s by %s;' % (' '.join(n(c) for c in name.split('_')), n(name))
                      for name in names if name in glyphs])
    kern = dict(data['kern'])
    rules = []
    # The renderer kerns supported accented letters like their decomposed base.
    eligible = [g for g in glyphs if len(g) == 1 or g in ['f_f', 'f_i', 'f_l', 'f_f_i', 'f_f_l', 'T_h', 'c_t', 's_t']]
    for left in eligible:
        for right in eligible:
            base_left = unicodedata.normalize('NFD', left)[0] if len(left) == 1 else left
            base_right = unicodedata.normalize('NFD', right)[0] if len(right) == 1 else right
            value = kern.get(left + ' ' + right, kern.get(base_left + ' ' + base_right, 0))
            if value:
                rules.append(f'pos {n(left)} {n(right)} {value * SCALE};')
    feature('kern', rules)
    return '\n'.join(lines) + '\n'


def build(style, filename_style, weight, italic, data):
    glyphs = data['styles'][style]
    glyphs['.notdef'] = {'adv': 8, 'cells': [{'x': x, 'y': y} for x in range(1, 7) for y in range(-10, 0)
                                          if x in (1, 6) or y in (-10, -1)]}
    for name, advance in [('space', 4), ('nbsp', 4), ('nnbsp', 2), ('zwspace', 0)]:
        glyphs[name] = {'adv': advance, 'cells': []}
    for suffix in ['', '.onum']:
        width = max(glyphs[str(i) + suffix]['adv'] for i in range(10))
        for i in range(10):
            g = glyphs[str(i) + suffix]
            offset = (width - g['adv']) // 2
            glyphs[str(i) + suffix + '.tnum'] = {'adv': width, 'cells': [{'x': c['x'] + offset, 'y': c['y']} for c in g['cells']]}
    order = ['.notdef'] + sorted(n for n in glyphs if n != '.notdef')
    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder([glyph_name(n) for n in order])
    cmap = {ord(n): glyph_name(n) for n in glyphs if len(n) == 1}
    cmap.update({0x20: 'space', 0xA0: 'nbsp', 0x202F: 'nnbsp', 0x200B: 'zwspace'})
    for block, suffix in enumerate(['', '.cap', '.open']):
        for i, shape in enumerate(SHAPES):
            cmap[0xE000 + block * 6 + i] = 'hp.' + shape + suffix
    cmap[0xE012] = 'alias.logo'
    fb.setupCharacterMap(cmap)
    outlines = {glyph_name(n): outline(glyphs[n]['cells']) for n in order}
    fb.setupGlyf(outlines)
    metrics = {}
    for name in order:
        g = glyphs[name]
        metrics[glyph_name(name)] = (g['adv'] * SCALE, min((c['x'] for c in g['cells']), default=0) * SCALE)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=1400, descent=-300, lineGap=0,
                             caretSlopeRise=4 if italic else 1, caretSlopeRun=1 if italic else 0)
    subfamily = 'Bold Italic' if filename_style == 'BoldItalic' else filename_style
    fb.setupNameTable({'familyName': 'LTL Pixel', 'styleName': subfamily,
                      'typographicFamily': 'LTL Pixel', 'typographicSubfamily': subfamily,
                      'uniqueFontIdentifier': f'CPJ:LTL Pixel {subfamily}:5.3',
                      'fullName': f'LTL Pixel {subfamily}', 'psName': 'LTLPixel-' + filename_style,
                      'version': 'Version 5.300', 'designer': 'Clay Parker Jones',
                      'description': 'A pixellated serif by CPJ.',
                      'copyright': 'Copyright 2026 Clay Parker Jones.',
                      'vendorURL': 'https://github.com/cpj-fyi/ltl-pixel'})
    flags = (1 if italic else 0) | (32 if weight == 700 else 0) | (64 if not italic and weight == 400 else 0) | 128
    fb.setupOS2(sTypoAscender=1400, sTypoDescender=-300, sTypoLineGap=0,
                usWinAscent=1400, usWinDescent=300, sxHeight=700, sCapHeight=1000,
                usWeightClass=weight, usWidthClass=5, fsSelection=flags, fsType=0,
                achVendID='CPJ ', version=4)
    fb.setupPost(italicAngle=-14.0362434679 if italic else 0, underlinePosition=-150, underlineThickness=100)
    fb.font['head'].macStyle = (1 if weight == 700 else 0) | (2 if italic else 0)
    fb.font['head'].fontRevision = 5.3
    # Stable binaries for unchanged input, including the ZIP archive.
    fb.font['head'].created = fb.font['head'].modified = 3875040000
    fea = features(glyphs, data)
    addOpenTypeFeaturesFromString(fb.font, fea)
    basename = 'LTLPixel-' + filename_style
    (OUT / (basename + '.fea')).write_text(fea)
    path = OUT / (basename + '.ttf')
    fb.font.recalcTimestamp = False
    fb.save(path)
    font = TTFont(path, recalcTimestamp=False)
    assert font['head'].unitsPerEm == UPM
    assert font.getBestCmap() == cmap
    tags = {r.FeatureTag for table in ['GSUB', 'GPOS'] for r in font[table].table.FeatureList.FeatureRecord}
    assert {'liga', 'dlig', 'kern', 'case', 'onum', 'tnum', 'smcp', 'c2sc', 'sups', 'sinf', 'frac', 'ordn', 'ss01', 'ss02'} <= tags
    font.flavor = 'woff2'
    font.save(OUT / (basename + '.woff2'))
    webfont = TTFont(OUT / (basename + '.woff2'))
    assert webfont.getBestCmap() == cmap
    print(f'{basename}: {len(order)} glyphs, {len(cmap)} code points; TTF + WOFF2 verified')
    return path


def main():
    OUT.mkdir(exist_ok=True)
    data = json.loads(subprocess.check_output(['node', str(ROOT / 'font-build/export.mjs')], cwd=ROOT))
    paths = [build(*style, data) for style in STYLES]
    with zipfile.ZipFile(OUT / 'LTL-Pixel.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in paths + [OUT / 'INSTALL.txt']:
            info = zipfile.ZipInfo('LTL-Pixel/' + path.name, date_time=(2026, 10, 17, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    print('fonts/LTL-Pixel.zip ready')


if __name__ == '__main__':
    main()
