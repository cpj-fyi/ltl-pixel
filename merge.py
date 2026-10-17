# Build glyphs.txt for LTL Pixel: glyphs-base.txt (cut A) + parts/*.txt
# (new drawings and shift rules) + compose.txt (accented letters) + an @ kern section that this script
# measures from the bitmaps (kerning pairs listed in KERN_PAIRS, tightened toward a 2-cell gap, never
# closer than 1 cell including diagonals, at most 3 cells).
# usage: python3 merge.py   (run from the repository root)
import re, glob
base = open('glyphs-base.txt').read()
parts = [open(p).read() for p in sorted(glob.glob('parts/*.txt'))]
compose = open('compose.txt').read()

def parse(text):
    T = {}; s = cur = None
    for line in text.split('\n'):
        line = line.rstrip()
        if line.startswith('@'): s = line[1:].strip(); T.setdefault(s, {}); cur = None; continue
        m = re.match(r'^= (\S+) (-?\d+)$', line)
        if m: cur = m.group(1); T[s][cur] = (int(m.group(2)), []); continue
        if cur and re.fullmatch(r'[#.]+', line): T[s][cur][1].append(line); continue
        cur = None
    return T

R = {}
for t in [base] + parts: R.update(parse(t).get('roman', {}))

def cells(n):
    top, rows = R[n]
    return {(1 + c, top + i) for i, r in enumerate(rows) for c, v in enumerate(r) if v == '#'}
def adv(n): return max(len(r) for r in R[n][1]) + 2

def measure(a, b):
    A, B = cells(a), {(x + adv(a), y) for x, y in cells(b)}
    gap = 99
    for xa, ya in A:
        for xb, yb in B:
            if abs(ya - yb) <= 1:   # same row, or diagonal neighbour rows
                d = xb - xa - 1 + (0 if ya == yb else 1)
                gap = min(gap, d)
    return gap

LC = 'acdegmnopqrsuvwxyz'
PUNCT = '.,:;'
KERN_PAIRS = []
for L in 'TVWYPF':
    KERN_PAIRS += [(L, r) for r in LC + PUNCT + '…']
for a, b in ['AV', 'AW', 'AY', 'AT', 'VA', 'WA', 'YA', 'TA', 'LT', 'LV', 'LW', 'LY', 'PA', 'FA', 'Av', 'Aw', 'Ay', 'L’', 'L”', 'A’', 'A”', '‘A', '“A',
             'r.', 'r,', 'f.', 'f,', 'v.', 'v,', 'w.', 'w,', 'y.', 'y,', 'Ty', 'To', 'Te', 'Ta', 'Th']:
    KERN_PAIRS.append((a, b))
KERN_PAIRS += [(q, p) for q in '’”' for p in '.,'] + [(p, q) for p in '.,' for q in '’”']

out = ['@ kern', '# measured by merge.py: <left> <right> <cells>']
for a, b in KERN_PAIRS:
    if a not in R or b not in R: continue
    g = measure(a, b)
    if g > 2:
        k = -min(3, g - 2)
        out.append(f'{a} {b} {k}')
open('glyphs.txt', 'w').write('\n\n'.join([base.rstrip()] + [p.rstrip() for p in parts] + [compose.rstrip(), '\n'.join(out)]) + '\n')
print('glyphs', len(R), 'kern pairs', len(out) - 2)
