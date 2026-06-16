/**
 * Tests de paridad backend ↔ frontend.
 *
 * Recorre la misma tabla compartida que `test_form_builder_parity.py` y
 * verifica que el runtime JS (`evalVisible` vía `refreshVisibility`) llegue
 * a la misma decisión que `schema.visible_when_match` para cada caso.
 *
 * Estrategia: para cada caso construimos un DOM mínimo con un input por
 * cada `answer` y un wrap con `data-vw-cond` igual a la condición; tras
 * `init()`, el wrap está oculto sii la condición NO se cumple, lo que es
 * exactamente la inversa de `expected`.
 */

import { describe, it, beforeEach, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RUNTIME_PATH = path.resolve(
  __dirname,
  '../../apps/static/assets/js/form_builder/runtime.js'
);
const FIXTURE_PATH = path.resolve(
  __dirname, '../fixtures/visible_when_cases.json'
);
const RUNTIME_SOURCE = fs.readFileSync(RUNTIME_PATH, 'utf8');
const CASES = JSON.parse(fs.readFileSync(FIXTURE_PATH, 'utf8'));

function loadRuntime() {
  new Function(RUNTIME_SOURCE).call(window);
}

function buildDom(answers, cond) {
  const inputs = Object.entries(answers)
    .map(([name, value]) => {
      if (Array.isArray(value)) {
        // Multi-checkbox: un input por cada valor, todos marcados.
        return value
          .map(
            (v) =>
              `<input type="checkbox" name="${name}" value="${v}" checked>`
          )
          .join('\n');
      }
      const v = String(value).replaceAll('"', '&quot;');
      return `<input type="text" name="${name}" value="${v}">`;
    })
    .join('\n');

  const condAttr =
    cond === null
      ? ''
      : `data-vw-cond='${JSON.stringify(cond).replaceAll("'", '&#39;')}'`;
  document.body.innerHTML = `
    ${inputs}
    <div class="fb-field" ${condAttr}>x</div>
  `;
}

beforeEach(() => {
  document.body.innerHTML = '';
  delete window.FBRuntime;
  loadRuntime();
});

describe('Paridad backend ↔ frontend de visible_when', () => {
  for (const c of CASES) {
    it(`caso ${c.name}`, () => {
      buildDom(c.answers, c.cond);
      window.FBRuntime.init(document);

      const wrap = document.querySelector('.fb-field');
      const visible = wrap.style.display !== 'none';
      expect(visible).toBe(c.expected);
    });
  }
});
