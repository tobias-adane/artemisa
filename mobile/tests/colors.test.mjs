// Ningún color literal en componentes: solo tokens (CLAUDE.md, regla 3).
// components/ui/ queda afuera: son primitivas de RN Reusables y no se editan.
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const root = fileURLToPath(new URL('..', import.meta.url));
const DIRS = ['app', 'components/artemisa', 'hooks'];

function files(dir) {
  let out = [];
  let entries = [];
  try {
    entries = readdirSync(dir);
  } catch {
    return out;
  }
  for (const name of entries) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out = out.concat(files(p));
    else if (/\.(ts|tsx)$/.test(name)) out.push(p);
  }
  return out;
}

const PALETTE =
  'white|black|slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose';
const LITERAL = [
  /#[0-9a-fA-F]{3,8}\b/,
  /\b(rgb|rgba|hsl|hsla)\(/,
  new RegExp(`\\b(bg|text|border|ring|fill|stroke|shadow)-(${PALETTE})\\b`),
  /\b(color|backgroundColor|borderColor)\s*:\s*['"]/,
];

test('sin colores literales en app/, components/artemisa/ ni hooks/', () => {
  const offenders = [];
  for (const dir of DIRS) {
    for (const file of files(join(root, dir))) {
      readFileSync(file, 'utf8')
        .split('\n')
        .forEach((line, i) => {
          if (LITERAL.some((re) => re.test(line)))
            offenders.push(`${file}:${i + 1}: ${line.trim()}`);
        });
    }
  }
  assert.deepEqual(offenders, []);
});
