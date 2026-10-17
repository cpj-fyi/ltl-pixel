# Print glyphs from one or more LTL Pixel tables side by side, in table coordinates (row numbers on the left).
# usage: python3 preview.py <table.txt>[,<table2.txt>...] <section> <name> [<name> ...]
#   names are glyph names as written after '= ' (single characters or names like f_i, 3.onum, eacute).
import re, sys
files, sec, names = sys.argv[1].split(','), sys.argv[2], sys.argv[3:]
T = {}
for f in files:
    s = cur = None
    for line in open(f).read().split('\n'):
        line = line.rstrip()
        if line.startswith('@'): s = line[1:].strip(); T.setdefault(s, {}); cur = None; continue
        m = re.match(r'^= (\S+) (-?\d+)$', line)
        if m: cur = m.group(1); T[s][cur] = [int(m.group(2)), []]; continue
        if cur and re.fullmatch(r'[#.]+', line): T[s][cur][1].append(line); continue
        cur = None
gs = []
for n in names:
    if n not in T.get(sec, {}): print('missing:', n); continue
    gs.append((n,) + tuple(T[sec][n]))
if not gs: sys.exit()
y0 = min(min(-10, g[1]) for g in gs); y1 = max(max(3, g[1] + len(g[2])) for g in gs)
wid = lambda g: max(max(len(r) for r in g[2]), len(g[0]))
print('     ' + '  '.join(g[0].ljust(wid(g)) for g in gs))
for y in range(y0, y1):
    mark = '_' if y == -1 else ('-' if y in (-7, -10) else ' ')
    print(f'{y:4d}{mark}' + '  '.join(((g[2][y - g[1]] if 0 <= y - g[1] < len(g[2]) else '').replace('.', ' ').ljust(wid(g))) for g in gs))
