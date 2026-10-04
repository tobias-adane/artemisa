// Los textos de la app son copia exacta de docs/i18n/ y los dos idiomas tienen
// las mismas claves (docs/07-APP.md, Idiomas).
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');

function keys(obj, prefix = '') {
  return Object.entries(obj).flatMap(([k, v]) =>
    v !== null && typeof v === 'object' ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`]
  );
}

for (const locale of ['en', 'es-AR']) {
  test(`lib/i18n/${locale}.json es igual a docs/i18n/${locale}.json`, () => {
    assert.equal(read(`../lib/i18n/${locale}.json`), read(`../../docs/i18n/${locale}.json`));
  });
}

test('en y es-AR tienen las mismas claves', () => {
  const en = keys(JSON.parse(read('../lib/i18n/en.json'))).sort();
  const es = keys(JSON.parse(read('../lib/i18n/es-AR.json'))).sort();
  assert.deepEqual(es, en);
});

test('las variables usan llaves simples', () => {
  for (const locale of ['en', 'es-AR'])
    assert.doesNotMatch(read(`../lib/i18n/${locale}.json`), /\{\{/);
});
