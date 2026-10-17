// Export resolved drawings through the same parser used by the canvas renderer.
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = fs.readFileSync(path.join(root, 'ltlpixel.js'));
const { parseTable, shape } = await import(`data:text/javascript;base64,${source.toString('base64')}`);
const table = parseTable(fs.readFileSync(path.join(root, 'glyphs.txt'), 'utf8'));
const styles = ['roman', 'italic', 'bold', 'bold-italic'];
const fractions = '½⅓⅔¼¾⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞';
const output = { metrics: table.metrics, kern: [...table.kern], alias: table.alias, styles: {} };
for (const style of styles) {
  const glyphs = Object.fromEntries(Object.entries(table[style]).map(([name, g]) => [name, { cells: g.cells, adv: g.adv }]));
  for (const ch of fractions) {
    let advance = 0;
    const cells = [];
    for (const item of shape(table, ch, style)) {
      advance += item.kernBefore;
      cells.push(...item.g.cells.map(c => ({ x: c.x + advance, y: c.y })));
      advance += item.g.adv;
    }
    glyphs[ch] = { cells, adv: advance };
  }
  for (const suffix of ['', '.open', '.cap']) {
    let advance = 0;
    const cells = [];
    for (const name of table.alias.logo) {
      const g = table[style][name + suffix];
      cells.push(...g.cells.map(c => ({ x: c.x + advance, y: c.y })));
      advance += g.adv;
    }
    glyphs['alias.logo' + suffix] = { cells, adv: advance };
  }
  output.styles[style] = glyphs;
}
process.stdout.write(JSON.stringify(output));
