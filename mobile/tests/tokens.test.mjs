// global.css y lib/theme.ts tienen que coincidir con design/tokens.json
// (docs/09-DISENO.md, Implementación).
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const tokens = JSON.parse(read('../../design/tokens.json'));
const css = read('../global.css');
const theme = read('../lib/theme.ts');

function hsl(hex) {
  const n = parseInt(hex.slice(1), 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) => c / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  let h = 0;
  let s = 0;
  if (d) {
    s = d / (1 - Math.abs(2 * l - 1));
    h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
    h *= 60;
    if (h < 0) h += 360;
  }
  const f = (x) => String(Math.round(x * 10) / 10);
  return `${f(h)} ${f(s * 100)}% ${f(l * 100)}%`;
}

function cssVars() {
  const vars = {};
  for (const [, name, value] of css.matchAll(/--([\w-]+):\s*([^;]+);/g)) vars[name] = value.trim();
  return vars;
}

test('los colores de global.css salen de tokens.json', () => {
  const vars = cssVars();
  for (const [name, hex] of Object.entries(tokens.color)) assert.equal(vars[name], hsl(hex), name);
  for (const [name, hex] of Object.entries(tokens.state)) {
    assert.equal(vars[`state-${name}`], hsl(hex), `state-${name}`);
  }
});

test('destructive es foreground, nunca rojo', () => {
  const vars = cssVars();
  assert.equal(vars.destructive, vars.foreground);
});

test('las variables que no están en tokens.json reusan un token monocromático', () => {
  const vars = cssVars();
  const allowed = new Set(Object.values(tokens.color).map(hsl));
  for (const name of [
    'card-foreground',
    'popover',
    'popover-foreground',
    'secondary',
    'secondary-foreground',
    'accent',
    'accent-foreground',
  ]) {
    assert.ok(allowed.has(vars[name]), name);
  }
});

test('no hay modo oscuro', () => {
  assert.doesNotMatch(css, /\.dark/);
});

test('lib/theme.ts coincide con global.css', () => {
  const vars = cssVars();
  const kebab = (name) => name.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);
  const entries = [...theme.matchAll(/(\w+): '(?:hsl\(([^)]+)\)|([^']+))'/g)];
  assert.ok(entries.length > 0);
  for (const [, name, color, other] of entries)
    assert.equal(color ?? other, vars[kebab(name)], name);
});
