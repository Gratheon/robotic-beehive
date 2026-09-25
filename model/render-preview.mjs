// Renders Robotic Beehive product images from index.html with headless Chrome
// (WebGL through SwiftShader), using the viewer's #shot hash options.
//   node render-preview.mjs    # ../docs/preview.png + ../docs/hero.png
//   CHROME=/path/to/chrome node render-preview.mjs
import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const chrome = process.env.CHROME || [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
].find(existsSync);
if (!chrome) throw new Error('Chrome not found; set CHROME=/path/to/chrome');

const shots = [
  ['preview.png', 't=19.5&clad=ghost', [1600, 1000]],
  ['hero.png', 't=19.5&clad=ghost&cam=hero', [900, 1125]],
];
const page = pathToFileURL(join(here, 'index.html')).href;
for (const [file, opts, [w, h]] of shots) {
  const out = join(here, '..', 'docs', file);
  execFileSync(chrome, [
    '--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--hide-scrollbars',
    `--window-size=${w},${h}`, '--virtual-time-budget=9000', `--screenshot=${out}`,
    `${page}#shot&theme=light&${opts}`,
  ], { stdio: 'ignore' });
  console.log(`wrote docs/${file}`);
}
