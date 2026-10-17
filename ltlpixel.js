// LTL Pixel v5.2: original pixel-serif drawings with OpenType-style features in the layout engine.
// There is no font binary. merge.py builds glyphs.txt from glyphs-base.txt, parts/*.txt and compose.txt,
// then adds kerning measured from the bitmaps.
//
// Table syntax (glyphs.txt):
//   ! cap 10 x 7 desc 3 stair 4         metrics
//   @ roman | @ italic | @ kern         section
//   = <name> <top>  + rows of # and .   a glyph (name is the character, or base.suffix, or a_b for ligatures)
//   > <name> <src> <dx> <dy>            a shifted copy of src (case forms, inferiors, denominators)
//   + <name> <base> <mark> [dx] [dy]    a composite: mark centred over base (accented letters)
//   (in @ kern)  class :<cls> <names…>   and   <left> <right> <cells>   (left/right: a name or :class)
//   (in @ alias) <shortcode> <glyph>     so :<shortcode>: in text sets that glyph (v5.1: Hidden Patterns shapes)
// Italic glyphs are stored upright; finish() slants them one cell every `stair` rows. A glyph missing from
// italic is the roman one slanted, except ligatures and composites whose parts have their own italic.
//
//   const T = parseTable(await (await fetch('glyphs.txt')).text());
//   layout(T, text | [{text, style:'roman'|'italic'|'bold'|'bold-italic', tag, features}], {maxWidthCells, align, leading,
//          wordSpace, tracking, features})
//     -> { lines:[{baseline, width, cells, words}], cells, words:[{text, tag, style, x0, x1, y0, y1, cells}],
//          width, height, lineH }       (cell units; a line's baseline is the boundary under row -1)
//   paint(ctx, cells, {x, y, pitch, color, gap = 0, variant = 'square'|'dot'})
//
// features (all optional; defaults in DEFAULT_FEATURES):
//   liga  ff fi fl ffi ffl            dlig  Th ct st
//   kern  pair kerning                case  'auto' (all-caps words) | true | false: punctuation for capitals
//   onum  oldstyle figures            tnum  tabular (fixed-width) figures
//   smcp  lowercase -> small caps     c2sc  capitals -> small caps
//   sups  superior figures            sinf  inferior figures
//   frac  1/2 -> ½-style fractions (½ ¼ ¾ and friends are always built this way)
//   ordn  ordinals: 1a 2o -> 1ª 2º, No. 5 -> № 5
//   smartQuotes  ' " -- --- ... -> ’ “ ” – — …  (applied before shaping)
//
// Hidden Patterns shapes: :foundations: :structuring: :direction: :practice: :learning:
// :space: (or :circle: :triangle: :parallelogram: :square: :star: :pentagon:) and :logo:. Add .open for the
// outline or .cap for cap height: :practice.open:  :learning.cap:. Start & End has no shape. Every laid-out cell
// carries n (its glyph name), so a page can colour the shapes with HP_COLORS.

export const HP_COLORS = { 'hp.circle': '#FF3252', 'hp.triangle': '#E9306B', 'hp.parallelogram': '#D83586',
  'hp.square': '#BD31BF', 'hp.star': '#9F36CE', 'hp.pentagon': '#8438F2' };
export const hpColor = name => HP_COLORS[name.replace(/\.(open|cap)$/, '')] || null;
export const METRICS = { cap: 10, xHeight: 7, descender: 3, gapCells: 2, wordSpace: 6, italicStair: 4 };
export const DEFAULT_FEATURES = { liga: true, dlig: false, kern: true, case: 'auto', onum: false, tnum: false,
  smcp: false, c2sc: false, sups: false, sinf: false, frac: false, ordn: false, smartQuotes: false };
const mOf = T => T.metrics || METRICS;

export function parseTable(src) {
  const T = { roman: {}, italic: {}, metrics: { ...METRICS }, kern: new Map(), classes: {}, alias: {} };
  const raw = { roman: {}, italic: {} }, rules = { roman: [], italic: [] }, kernLines = [];
  let set = null, cur = null;
  const flush = () => { if (cur) { raw[set][cur.ch] = { top: cur.top, rows: cur.rows }; cur = null; } };
  for (const line0 of src.split('\n')) {
    const line = line0.replace(/\s+$/, '');
    if (line.startsWith('! ')) { const m = line.match(/cap (\d+) x (\d+) desc (\d+) stair (\d+)/);
      Object.assign(T.metrics, { cap: +m[1], xHeight: +m[2], descender: +m[3], italicStair: +m[4] }); continue; }
    if (line.startsWith('@')) { flush(); set = line.slice(1).trim(); continue; }
    if (set === 'alias') { const a = line.trim().split(/\s+/); if (a.length >= 2 && !line.startsWith('#')) T.alias[a[0]] = a.slice(1); continue; }
    if (set === 'kern') { if (line && !line.startsWith('#')) kernLines.push(line.trim().split(/\s+/)); continue; }
    if (line.startsWith('= ')) { flush(); const m = line.match(/^= (\S+) (-?\d+)$/); cur = { ch: m[1], top: +m[2], rows: [] }; continue; }
    if (cur && /^[#.]+$/.test(line)) { cur.rows.push(line); continue; }
    if (/^[>+] /.test(line)) { flush(); rules[set].push(line.split(/\s+/)); continue; }
    if (!line || line.startsWith('#')) flush();
  }
  flush();

  // Resolve shift and composite rules (in file order, repeated until nothing new resolves).
  const ownItalic = new Set(Object.keys(raw.italic));
  const resolve = (S, list, fallback) => {
    let pending = list.slice();
    for (let pass = 0; pass < 4 && pending.length; pass++) {
      const next = [];
      for (const r of pending) {
        const get = n => S[n] || (fallback && fallback[n]);
        if (r[0] === '>') { const s = get(r[2]); if (!s) { next.push(r); continue; }
          S[r[1]] = { top: s.top + +r[4], rows: s.rows.map(row => '.'.repeat(Math.max(0, +r[3])) + row), dx: Math.min(0, +r[3]) }; }
        else { const b = get(r[2]), mk = get(r[3]); if (!b || !mk) { next.push(r); continue; }
          S[r[1]] = compose(b, mk, +(r[4] || 0), +(r[5] || 0)); }
      }
      pending = next;
    }
  };
  resolve(raw.roman, rules.roman, null);
  // Italic: composites and shifted copies whose source has its own italic drawing are rebuilt from it.
  const partsOf = n => n.includes('_') ? n.split('.')[0].split('_') : [n.split('.')[0]];
  const italicRules = rules.roman.filter(r => (r[0] === '+' ? [r[2], r[3]] : [r[2]]).some(n => ownItalic.has(n) || partsOf(n).some(p => ownItalic.has(p))));
  resolve(raw.italic, italicRules.concat(rules.italic), raw.roman);

  for (const [ch, g] of Object.entries(raw.roman)) T.roman[ch] = finish(ch, g, 'roman', T.metrics);
  for (const [ch, g] of Object.entries(raw.italic)) T.italic[ch] = finish(ch, g, 'italic', T.metrics);
  for (const ch of Object.keys(T.roman)) {
    if (T.italic[ch]) continue;
    if (ch.includes('_') && partsOf(ch).some(p => ownItalic.has(p))) continue;   // e.g. roman c_t would clash with italic t
    T.italic[ch] = finish(ch, raw.roman[ch], 'italic', T.metrics);
  }

  // Bold and bold italic are derived: every lit cell also lights the cell to its right, so verticals double
  // and horizontals stay one cell (thick-thin contrast like the serif). Each advance grows by one cell.
  T.bold = embolden(T.roman); T['bold-italic'] = embolden(T.italic);

  for (const k of kernLines) {
    if (k[0] === 'class') { T.classes[k[1]] = k.slice(2); continue; }
    const L = k[0].startsWith(':') ? T.classes[k[0].slice(1)] || [] : [k[0]];
    const R = k[1].startsWith(':') ? T.classes[k[1].slice(1)] || [] : [k[1]];
    for (const l of L) for (const r of R) T.kern.set(l + ' ' + r, +k[2]);
  }
  return T;
}

function embolden(S) {
  const out = {};
  for (const [ch, g] of Object.entries(S)) {
    const seen = new Set(), cells = [];
    for (const c of g.cells) for (const x of [c.x, c.x + 1]) { const k = x + ',' + c.y; if (!seen.has(k)) { seen.add(k); cells.push({ x, y: c.y }); } }
    out[ch] = { ...g, cells, adv: g.adv + 1, w: g.w + 1 };
  }
  return out;
}

function compose(b, mk, dx, dy) {
  const wb = Math.max(...b.rows.map(r => r.length)), wm = Math.max(...mk.rows.map(r => r.length));
  const mx = Math.floor((wb - wm) / 2) + dx, ox = Math.min(0, mx);
  const top = Math.min(b.top, mk.top + dy), bot = Math.max(b.top + b.rows.length, mk.top + dy + mk.rows.length);
  const W = Math.max(wb, mx + wm) - ox, grid = Array.from({ length: bot - top }, () => Array(W).fill('.'));
  const put = (g, x0, y0) => g.rows.forEach((r, i) => { for (let c = 0; c < r.length; c++) if (r[c] === '#') grid[y0 + i - top][x0 + c - ox] = '#'; });
  put(b, 0, b.top); put(mk, mx, mk.top + dy);
  return { top, rows: grid.map(r => r.join('')), dx: ox };
}

function finish(ch, g, set, M = METRICS) {
  const w = Math.max(...g.rows.map(r => r.length)), cells = [];
  g.rows.forEach((r, i) => {
    const y = g.top + i, sh = set === 'italic' ? Math.floor((-y - 1) / M.italicStair) : 0;
    for (let c = 0; c < r.length; c++) if (r[c] === '#') cells.push({ x: 1 + c + sh + (g.dx || 0), y });
  });
  return { cells, adv: w + M.gapCells + (g.dx || 0), w, src: { ch, top: g.top, rows: g.rows } };
}

// ---- shaping ---------------------------------------------------------------------------------------

const FRACTIONS = { '½': '1/2', '⅓': '1/3', '⅔': '2/3', '¼': '1/4', '¾': '3/4', '⅕': '1/5', '⅖': '2/5', '⅗': '3/5',
  '⅘': '4/5', '⅙': '1/6', '⅚': '5/6', '⅛': '1/8', '⅜': '3/8', '⅝': '5/8', '⅞': '7/8' };
const LIGA = [['f', 'f', 'i'], ['f', 'f', 'l'], ['f', 'f'], ['f', 'i'], ['f', 'l']];
const DLIG = [['T', 'h'], ['c', 't'], ['s', 't']];
const isDigit = n => /^[0-9]$/.test(n);
const SUPS_OK = new Set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '+', '-', '=', '(', ')']);

export function smartQuotes(s) {
  return s.replace(/\.\.\./g, '…').replace(/---/g, '—').replace(/--/g, '–')
    .replace(/(^|[\s(\[{“‘—–-])"/g, '$1“').replace(/"/g, '”')
    .replace(/(^|[\s(\[{“—–-])'/g, '$1‘').replace(/'/g, '’');
}

// One word -> [{name, g, kernBefore, tnum}] in one style.
export function shape(T, word, style = 'roman', features = {}) {
  const F = { ...DEFAULT_FEATURES, ...features };
  const S = T[style] || T.roman, has = n => !!(S[n] || T.roman[n]);
  // 1. characters -> names; precomposed fractions expand; unknown accented letters fall back to their base.
  let names = [];
  const pieces = word.split(/(:[a-z]+(?:\.(?:open|cap))?:)/);
  for (const piece of pieces) {
    const sc = piece.match(/^:([a-z]+)(\.(?:open|cap))?:$/);
    if (sc && T.alias[sc[1]]) { for (const t of T.alias[sc[1]]) { const g = t + (sc[2] || ''); names.push({ n: has(g) ? g : t }); } continue; }
  for (const ch of piece) {
    if (FRACTIONS[ch]) { const [a, b] = FRACTIONS[ch].split('/'); names.push({ n: a, frac: 'numr' }, { n: '⁄' }, { n: b, frac: 'dnom' }); continue; }
    if (has(ch)) { names.push({ n: ch }); continue; }
    const base = ch.normalize('NFD')[0];
    names.push({ n: has(base) ? base : ch });
  }
  }
  // 2. fractions: digits / digits
  if (F.frac) {
    const s = names.map(x => x.n);
    for (let i = 0; i < s.length; i++) if ((s[i] === '/' || s[i] === '⁄') && i > 0 && isDigit(s[i - 1]) && isDigit(s[i + 1] || '')) {
      names[i].n = '⁄';
      for (let j = i - 1; j >= 0 && isDigit(s[j]) && !names[j].frac; j--) names[j].frac = 'numr';
      for (let j = i + 1; j < s.length && isDigit(s[j]); j++) names[j].frac = 'dnom';
    }
  }
  // 3. ordinals
  if (F.ordn) {
    for (let i = 1; i < names.length; i++) if (isDigit(names[i - 1].n) && (names[i].n === 'a' || names[i].n === 'o') && !(names[i + 1] && /^[a-z]$/i.test(names[i + 1].n)))
      names[i].n = names[i].n === 'a' ? 'ª' : 'º';
    if (names.length >= 2 && names[0].n === 'N' && names[1].n === 'o' && (names.length === 2 || (names.length === 3 && names[2].n === '.')))
      names = [{ n: '№' }];
  }
  // 4. per-glyph substitutions
  const allCaps = /[A-Z]/.test(word) && !/[a-z]/.test(word);
  const useCase = F.case === true || (F.case === 'auto' && allCaps) || F.c2sc;
  for (const x of names) {
    const n = x.n;
    if (x.frac) { if (has(n + '.' + x.frac)) x.n = n + '.' + x.frac; continue; }
    if (F.sups && SUPS_OK.has(n) && has(n + '.sups')) { x.n = n + '.sups'; continue; }
    if (F.sinf && SUPS_OK.has(n) && has(n + '.sinf')) { x.n = n + '.sinf'; continue; }
    if (F.smcp && /^[a-zß]$/.test(n) && has(n + '.sc')) { x.n = n + '.sc'; continue; }
    if (F.c2sc && /^[A-Z]$/.test(n) && has(n.toLowerCase() + '.sc')) { x.n = n.toLowerCase() + '.sc'; continue; }
    if (isDigit(n)) { if (F.onum && has(n + '.onum')) x.n = n + '.onum'; x.tnum = F.tnum; continue; }
    if (useCase && has(n + '.case')) x.n = n + '.case';
  }
  // 5. ligatures (longest first), only where the ligature exists in this style
  const ligs = [...(F.liga ? LIGA : []), ...(F.dlig ? DLIG : [])].sort((a, b) => b.length - a.length);
  if (ligs.length) {
    const out = [];
    for (let i = 0; i < names.length;) {
      const hit = ligs.find(L => L.every((p, k) => names[i + k] && names[i + k].n === p) && S[L.join('_')]);
      if (hit) { out.push({ n: hit.join('_') }); i += hit.length; } else out.push(names[i++]);
    }
    names = out;
  }
  // 6. glyphs + kerning
  const res = [];
  for (let i = 0; i < names.length; i++) {
    const n = names[i].n, g = S[n] || T.roman[n];
    const p = names[i - 1] && names[i - 1].n, kb = s => s.length === 1 ? s.normalize('NFD')[0] : s;   // é kerns like e
    const k = F.kern && i ? (T.kern.get(p + ' ' + n) ?? T.kern.get(kb(p) + ' ' + kb(n)) ?? 0) : 0;
    res.push({ name: n, g, kernBefore: k, tnum: names[i].tnum });
  }
  return res;
}

// Widest figure in a set, so tabular figures share one advance.
function tabAdv(T, S, suffix) {
  let m = 0;
  for (let d = 0; d <= 9; d++) { const g = S[d + suffix] || T.roman[d + suffix]; if (g) m = Math.max(m, g.adv); }
  return m;
}

export function layout(T, text, { maxWidthCells = Infinity, align = 'left', leading = 1.6, wordSpace, tracking = 0, features = {} } = {}) {
  const M = mOf(T); wordSpace ??= M.wordSpace;
  const runs = typeof text === 'string' ? [{ text }] : text;
  const words = [];
  for (const r of runs) {
    const F = { ...features, ...(r.features || {}) };
    const t = F.smartQuotes ? smartQuotes(r.text) : r.text;
    for (const w of t.split(/[ \t\n\r\f\v\u2028\u2029]+/).filter(Boolean)) words.push(   // no-break spaces (U+00A0, U+202F) stay inside a word
      { text: w, style: r.style || 'roman', tag: r.tag ?? null, F, tracking: r.tracking ?? tracking });
  }
  for (const w of words) {
    const S = T[w.style] || T.roman;
    let x = 0; w.cells = [];
    const glyphs = shape(T, w.text, w.style, w.F);
    glyphs.forEach((gl, i) => {
      if (i) x += w.tracking;
      x += gl.kernBefore;
      const g = gl.g;
      if (gl.name === '\u00A0') { x += wordSpace - M.gapCells; return; }
      if (gl.name === '\u202F') { x += 2; return; }
      if (!g) { x += 3; return; }
      let adv = g.adv, off = 0;
      if (gl.tnum) { const suf = gl.name.slice(1); adv = tabAdv(T, S, suf); off = Math.floor((adv - g.adv) / 2); }
      for (const c of g.cells) w.cells.push({ x: c.x + x + off, y: c.y, n: gl.name });
      x += adv;
    });
    w.adv = x;
  }
  const space = wordSpace - M.gapCells;      // glyph advances already carry one empty column each side
  const lines = []; let cur = [], cw = 0;
  for (const w of words) {
    const add = (cur.length ? space : 0) + w.adv;
    if (cur.length && cw + add > maxWidthCells) { lines.push(cur); cur = []; cw = 0; }
    cw += (cur.length ? space : 0) + w.adv; cur.push(w);
  }
  if (cur.length) lines.push(cur);
  const lineH = Math.round(M.cap * leading), asc = M.cap;
  const out = { lines: [], cells: [], words: [], lineH };
  const widths = lines.map(L => L.reduce((a, w, i) => a + w.adv + (i ? space : 0), 0));
  const boxW = Number.isFinite(maxWidthCells) ? maxWidthCells : Math.max(0, ...widths);
  lines.forEach((L, li) => {
    const baseline = asc + li * lineH;
    let x = align === 'center' ? Math.floor((boxW - widths[li]) / 2) : align === 'right' ? boxW - widths[li] : 0;
    const line = { baseline, width: widths[li], cells: [], words: [] };
    for (const w of L) {
      const cells = w.cells.map(c => ({ x: c.x + x, y: c.y + baseline, n: c.n }));
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      for (const c of cells) { x0 = Math.min(x0, c.x); x1 = Math.max(x1, c.x + 1); y0 = Math.min(y0, c.y); y1 = Math.max(y1, c.y + 1); }
      const wb = { text: w.text, tag: w.tag, style: w.style, x0, x1, y0, y1, baseline, cells };
      line.words.push(wb); out.words.push(wb); line.cells.push(...cells);
      x += w.adv + space;
    }
    out.lines.push(line); out.cells.push(...line.cells);
  });
  out.width = boxW;
  out.height = asc + (lines.length - 1) * lineH + M.descender;
  return out;
}

export function paint(ctx, cells, { x = 0, y = 0, pitch = 8, color = '#222', gap = 0, variant = 'square' } = {}) {
  ctx.fillStyle = color;
  const m = pitch - gap;
  if (variant === 'dot') {
    ctx.beginPath();
    for (const c of cells) { const cx = x + c.x * pitch + m / 2, cy = y + c.y * pitch + m / 2; ctx.moveTo(cx + m / 2, cy); ctx.arc(cx, cy, m / 2, 0, Math.PI * 2); }
    ctx.fill(); return;
  }
  for (const c of cells) ctx.fillRect(x + c.x * pitch, y + c.y * pitch, m, m);
}
