#!/usr/bin/env python3
"""Compare native CoreText shaping with the source renderer (macOS + Swift)."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('font_build', ROOT / 'font-build/build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
cases = [
    ('office', {}), ('office', {'liga': False}), ('Thctst', {'dlig': True}),
    ('AVATARTéÁV', {}), ('AVATARTéÁV', {'kern': False}),
    ('0123456789', {'onum': True}), ('0123456789', {'tnum': True}),
    ('0123456789', {'onum': True, 'tnum': True}),
    ('smallcaps', {'smcp': True}), ('CAPS—', {'c2sc': True}),
    ('—«HELLO»', {'case': True}), ('0123456789+-=()', {'sups': True}),
    ('0123456789', {'sinf': True}), ('123/456', {'frac': True}),
    ('1234567890/9876543210', {'frac': True, 'onum': True, 'tnum': True}),
    ('1a', {'ordn': True}), ('2o', {'ordn': True}), ('1apple', {'ordn': True}),
    ('No.', {'ordn': True}), ('No', {'ordn': True}), ('Nothing', {'ordn': True}),
    ('No.thing', {'ordn': True}), ('xNo', {'ordn': True}),
    (':practice:', {'ss02': True, 'dlig': True, 'smcp': True}),
    (':direction:', {'ss02': True, 'dlig': True, 'smcp': True}),
    (':structuring.cap:', {'ss02': True, 'dlig': True, 'smcp': True}),
    ('"Hello..."', {'smartQuotes': True}), ("'Hello'", {'smartQuotes': True}),
    ('"\'Hello\'"', {'smartQuotes': True}), ("there's", {'smartQuotes': True}),
    ('HELLO---WORLD', {'smartQuotes': True, 'case': True}),
    ('HELLO--WORLD', {'smartQuotes': True, 'c2sc': True}),
]
javascript = r'''
import fs from 'node:fs';
const {parseTable, shape, smartQuotes} = await import('data:text/javascript;base64,' + fs.readFileSync('ltlpixel.js').toString('base64'));
const table = parseTable(fs.readFileSync('glyphs.txt','utf8'));
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
let results=[];
for (const [style, fileStyle] of [['roman','Regular'],['italic','Italic'],['bold','Bold'],['bold-italic','BoldItalic']]) {
 for (const [text, overrides] of cases) {
  const features={liga:true,kern:true,case:false,...overrides};
  const source=features.smartQuotes?smartQuotes(text):text;
  const glyphs=shape(table,source,style,features);
  const names=[];
  let width=0;
  for(const item of glyphs){
   let advance=item.g.adv;
   let name=item.name;
   if(item.tnum){
    const suffix=name.slice(1);
    advance=Math.max(...Array.from({length:10},(_,i)=>table[style][i+suffix].adv));
    name+='.tnum';
   }
   names.push(name);width+=advance+item.kernBefore;
  }
  results.push({style:fileStyle,text,features,names,width:width*100});
 }
}
process.stdout.write(JSON.stringify(results));
'''
fixtures = json.loads(subprocess.check_output(['node', '--input-type=module', '-e', javascript],
                      input=json.dumps(cases).encode(), cwd=ROOT))
with tempfile.TemporaryDirectory(prefix='ltl-font-qa-') as temp:
    program = str(Path(temp) / 'shape')
    subprocess.run(['swiftc', '-module-cache-path', str(Path(temp) / 'cache'),
                    str(ROOT / 'font-build/shape.swift'), '-o', program], check=True)
    for item in fixtures:
        flags = [f'{"ss01" if tag == "smartQuotes" else tag}={int(value)}' for tag, value in item['features'].items()]
        result = json.loads(subprocess.check_output([program, str(ROOT / ('fonts/LTLPixel-' + item['style'] + '.ttf')),
                                                    item['text'], *flags]))
        names = [g['name'] for g in result]
        expected = [builder.glyph_name(n) for n in item['names']]
        width = sum(g['advance'] for g in result)
        assert names == expected, (item, names, expected)
        assert abs(width - item['width']) < 0.01, (item, width)
print(f'{len(fixtures)} native shaping checks passed across four styles.')
