const fs = require('fs');
const {mathjax} = require('mathjax-full/js/mathjax.js');
const {TeX} = require('mathjax-full/js/input/tex.js');
const {SVG} = require('mathjax-full/js/output/svg.js');
const {liteAdaptor} = require('mathjax-full/js/adaptors/liteAdaptor.js');
const {RegisterHTMLHandler} = require('mathjax-full/js/handlers/html.js');
const {AllPackages} = require('mathjax-full/js/input/tex/AllPackages.js');

try {
  const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
  const adaptor = liteAdaptor();
  RegisterHTMLHandler(adaptor);
  const tex = new TeX({packages: AllPackages});
  const svg = new SVG({fontCache: 'none'});
  const html = mathjax.document('', {InputJax: tex, OutputJax: svg});
  html.convert(payload.latex, {display: true});
  process.stdout.write(JSON.stringify({ok:true}));
  process.exit(0);
} catch (e) {
  process.stderr.write(String(e && e.stack ? e.stack : e));
  process.exit(2);
}
