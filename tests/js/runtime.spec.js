/**
 * Tests del runtime compartido del Form Builder.
 *
 * Cubre las cuatro responsabilidades principales de
 * `apps/static/assets/js/form_builder/runtime.js`:
 *   1. Visibilidad condicional (`refreshVisibility`/`evalVisible`).
 *   2. IMC en vivo (`updateImc`).
 *   3. Conmutación automática de pestaña activa cuando la actual queda
 *      oculta (`ensureActiveTab`).
 *   4. Repetidores dinámicos (`bindRepeaters`).
 *
 * Estrategia: cargar el script del runtime tal como se sirve en producción
 * (IIFE que registra `window.FBRuntime`) dentro del jsdom de cada test, sin
 * modificar el código de producción.
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
const RUNTIME_SOURCE = fs.readFileSync(RUNTIME_PATH, 'utf8');

function loadRuntime() {
  // Ejecuta el IIFE en el contexto global del jsdom: `this === window`.
  new Function(RUNTIME_SOURCE).call(window);
}

function fire(el, type) {
  el.dispatchEvent(new Event(type, { bubbles: true }));
}

beforeEach(() => {
  document.body.innerHTML = '';
  delete window.FBRuntime;
  loadRuntime();
});

// ---------------------------------------------------------------------------
// 1) Visibilidad condicional
// ---------------------------------------------------------------------------

describe('FBRuntime — visibilidad condicional', () => {
  it('oculta el wrap cuando la condición no se cumple (equals)', () => {
    document.body.innerHTML = `
      <select name="fuma">
        <option value="si">si</option>
        <option value="no" selected>no</option>
      </select>
      <div class="fb-field" data-vw-cond='{"field":"fuma","equals":"si"}'>
        <input name="cigs" type="number">
      </div>
    `;
    window.FBRuntime.init(document);
    const wrap = document.querySelector('.fb-field');
    expect(wrap.style.display).toBe('none');

    document.querySelector('select').value = 'si';
    fire(document.querySelector('select'), 'change');
    expect(wrap.style.display).toBe('');
  });

  it('soporta operador not_equals', () => {
    document.body.innerHTML = `
      <select name="tipo">
        <option value="A" selected>A</option>
        <option value="B">B</option>
      </select>
      <div class="fb-field"
           data-vw-cond='{"field":"tipo","op":"not_equals","value":"A"}'>x</div>
    `;
    window.FBRuntime.init(document);
    const wrap = document.querySelector('.fb-field');
    expect(wrap.style.display).toBe('none');

    document.querySelector('select').value = 'B';
    fire(document.querySelector('select'), 'change');
    expect(wrap.style.display).toBe('');
  });

  it('soporta operador contains sobre multi-checkbox', () => {
    document.body.innerHTML = `
      <input type="checkbox" name="tags" value="rojo">
      <input type="checkbox" name="tags" value="azul">
      <div class="fb-field"
           data-vw-cond='{"field":"tags","op":"contains","value":"rojo"}'>x</div>
    `;
    window.FBRuntime.init(document);
    const wrap = document.querySelector('.fb-field');
    expect(wrap.style.display).toBe('none');

    const rojo = document.querySelector('input[value="rojo"]');
    rojo.checked = true;
    fire(rojo, 'change');
    expect(wrap.style.display).toBe('');
  });

  it('soporta operador contains sobre substring de texto', () => {
    document.body.innerHTML = `
      <input name="obs" type="text">
      <div class="fb-field"
           data-vw-cond='{"field":"obs","op":"contains","value":"urg"}'>x</div>
    `;
    window.FBRuntime.init(document);
    const wrap = document.querySelector('.fb-field');
    const obs = document.querySelector('[name="obs"]');

    obs.value = 'sin nada relevante';
    fire(obs, 'input');
    expect(wrap.style.display).toBe('none');

    obs.value = 'es urgente revisar';
    fire(obs, 'input');
    expect(wrap.style.display).toBe('');
  });

  it('coerciona equals:true con checkbox marcado', () => {
    document.body.innerHTML = `
      <input type="checkbox" name="acepta">
      <div class="fb-field"
           data-vw-cond='{"field":"acepta","equals":true}'>x</div>
    `;
    window.FBRuntime.init(document);
    const wrap = document.querySelector('.fb-field');
    const cb = document.querySelector('[name="acepta"]');
    expect(wrap.style.display).toBe('none');

    cb.checked = true;
    fire(cb, 'change');
    expect(wrap.style.display).toBe('');
  });

  it('oculta de nuevo al pasar de Sí a No en radio boolean', () => {
    document.body.innerHTML = `
      <input type="radio" name="activo" id="activo_si" value="true">
      <input type="radio" name="activo" id="activo_no" value="false" checked>
      <div class="fb-field"
           data-vw-cond='{"field":"activo","equals":true}'>x</div>
    `;
    window.FBRuntime.init(document);
    const wrap = document.querySelector('.fb-field');
    const si = document.querySelector('#activo_si');
    const no = document.querySelector('#activo_no');
    expect(wrap.style.display).toBe('none');

    si.checked = true;
    fire(si, 'change');
    expect(wrap.style.display).toBe('');

    no.checked = true;
    fire(no, 'change');
    expect(wrap.style.display).toBe('none');
  });

  it('cae al catch ante JSON malformado y deja el wrap visible', () => {
    document.body.innerHTML = `
      <div class="fb-field" data-vw-cond='not-json'>x</div>
    `;
    window.FBRuntime.init(document);
    expect(document.querySelector('.fb-field').style.display).toBe('');
  });

  it('soporta atributos legacy data-vw-field/data-vw-eq', () => {
    document.body.innerHTML = `
      <select name="x">
        <option value="a" selected>a</option>
        <option value="b">b</option>
      </select>
      <div class="fb-field" data-vw-field="x" data-vw-eq="b">y</div>
    `;
    window.FBRuntime.init(document);
    const wrap = document.querySelector('.fb-field');
    expect(wrap.style.display).toBe('none');

    document.querySelector('select').value = 'b';
    fire(document.querySelector('select'), 'change');
    expect(wrap.style.display).toBe('');
  });

  it('encadena dependencias A→B→C', () => {
    document.body.innerHTML = `
      <input name="a" type="text">
      <div class="fb-field" data-vw-cond='{"field":"a","equals":"go"}'>
        <input name="b" type="text" value="">
      </div>
      <div class="fb-field" data-vw-cond='{"field":"b","equals":"yes"}'>
        <span data-tag="c">contenido C</span>
      </div>
    `;
    window.FBRuntime.init(document);
    const [wrapB, wrapC] = document.querySelectorAll('.fb-field');
    expect(wrapB.style.display).toBe('none');
    expect(wrapC.style.display).toBe('none');

    const a = document.querySelector('[name="a"]');
    a.value = 'go';
    fire(a, 'input');
    expect(wrapB.style.display).toBe('');

    const b = document.querySelector('[name="b"]');
    b.value = 'yes';
    fire(b, 'input');
    expect(wrapC.style.display).toBe('');
  });
});

// ---------------------------------------------------------------------------
// 2) IMC en vivo
// ---------------------------------------------------------------------------

describe('FBRuntime — IMC en vivo', () => {
  it('calcula IMC y se actualiza al cambiar peso o talla', () => {
    document.body.innerHTML = `
      <input name="peso_kg" type="number" value="70">
      <input name="talla_cm" type="number" value="170">
      <div class="fb-computed" data-formula="imc" data-id="imc"
           data-depends="peso_kg,talla_cm">
        <input id="computed_imc">
      </div>
    `;
    window.FBRuntime.init(document);
    expect(document.getElementById('computed_imc').value).toBe('24.22');

    const peso = document.querySelector('[name="peso_kg"]');
    peso.value = '80';
    fire(peso, 'input');
    expect(document.getElementById('computed_imc').value).toBe('27.68');
  });

  it('vacía el resultado cuando talla=0 (sin Infinity)', () => {
    document.body.innerHTML = `
      <input name="peso_kg" value="70">
      <input name="talla_cm" value="0">
      <div class="fb-computed" data-formula="imc" data-id="imc"
           data-depends="peso_kg,talla_cm">
        <input id="computed_imc">
      </div>
    `;
    window.FBRuntime.init(document);
    expect(document.getElementById('computed_imc').value).toBe('');
  });

  it('vacía el resultado cuando falta peso', () => {
    document.body.innerHTML = `
      <input name="peso_kg" value="">
      <input name="talla_cm" value="170">
      <div class="fb-computed" data-formula="imc" data-id="imc"
           data-depends="peso_kg,talla_cm">
        <input id="computed_imc" value="oldvalue">
      </div>
    `;
    window.FBRuntime.init(document);
    expect(document.getElementById('computed_imc').value).toBe('');
  });

  it('soporta múltiples computados independientes en el mismo formulario', () => {
    document.body.innerHTML = `
      <input name="peso_kg" value="60">
      <input name="talla_cm" value="160">
      <input name="otro_peso" value="80">
      <input name="otra_talla" value="180">
      <div class="fb-computed" data-formula="imc" data-id="imc1"
           data-depends="peso_kg,talla_cm">
        <input id="computed_imc1">
      </div>
      <div class="fb-computed" data-formula="imc" data-id="imc2"
           data-depends="otro_peso,otra_talla">
        <input id="computed_imc2">
      </div>
    `;
    window.FBRuntime.init(document);
    expect(document.getElementById('computed_imc1').value).toBe('23.44');
    expect(document.getElementById('computed_imc2').value).toBe('24.69');
  });
});

// ---------------------------------------------------------------------------
// 2bis) Calculados encadenados en vivo
// ---------------------------------------------------------------------------

describe('FBRuntime — calculados encadenados', () => {
  it('suma subtotales de dos secciones en un calculado global', () => {
    document.body.innerHTML = `
      <input name="a1" type="number" value="10">
      <input name="a2" type="number" value="5">
      <input name="b1" type="number" value="3">
      <input name="b2" type="number" value="7">
      <div class="fb-computed" data-formula="a1+a2" data-id="total_a"
           data-depends="a1,a2" data-precision="0">
        <input id="computed_total_a">
      </div>
      <div class="fb-computed" data-formula="b1+b2" data-id="total_b"
           data-depends="b1,b2" data-precision="0">
        <input id="computed_total_b">
      </div>
      <div class="fb-computed" data-formula="total_a+total_b" data-id="gran_total"
           data-depends="total_a,total_b" data-precision="0">
        <input id="computed_gran_total">
      </div>
    `;
    window.FBRuntime.init(document);
    expect(document.getElementById('computed_total_a').value).toBe('15');
    expect(document.getElementById('computed_total_b').value).toBe('10');
    expect(document.getElementById('computed_gran_total').value).toBe('25');

    const a1 = document.querySelector('[name="a1"]');
    a1.value = '20';
    fire(a1, 'input');
    expect(document.getElementById('computed_total_a').value).toBe('25');
    expect(document.getElementById('computed_gran_total').value).toBe('35');
  });
});

// ---------------------------------------------------------------------------
// 3) Conmutación de pestañas
// ---------------------------------------------------------------------------

describe('FBRuntime — conmutación de pestañas', () => {
  it('al ocultarse la pestaña activa, salta a la primera visible', () => {
    document.body.innerHTML = `
      <select name="fuma">
        <option value="si">si</option>
        <option value="no" selected>no</option>
      </select>
      <div data-fb-tabs-wrap>
        <ul>
          <li class="fb-tab-li"><a class="nav-link" href="#tabA">A</a></li>
          <li class="fb-tab-li"
              data-vw-cond='{"field":"fuma","equals":"si"}'>
            <a class="nav-link active" href="#tabB" aria-selected="true">B</a>
          </li>
        </ul>
        <div class="tab-content">
          <div id="tabA"></div>
          <div id="tabB" class="active show"></div>
        </div>
      </div>
    `;
    window.FBRuntime.init(document);
    const liB = document.querySelectorAll('.fb-tab-li')[1];
    expect(liB.style.display).toBe('none');

    const linkA = document.querySelector('a[href="#tabA"]');
    expect(linkA.classList.contains('active')).toBe(true);
    expect(linkA.getAttribute('aria-selected')).toBe('true');
    expect(document.getElementById('tabA').classList.contains('active')).toBe(true);
    expect(document.getElementById('tabA').classList.contains('show')).toBe(true);
  });

  it('mantiene la pestaña activa si su condición se cumple', () => {
    document.body.innerHTML = `
      <select name="fuma">
        <option value="si" selected>si</option>
        <option value="no">no</option>
      </select>
      <div data-fb-tabs-wrap>
        <ul>
          <li class="fb-tab-li"><a class="nav-link" href="#tabA">A</a></li>
          <li class="fb-tab-li"
              data-vw-cond='{"field":"fuma","equals":"si"}'>
            <a class="nav-link active" href="#tabB" aria-selected="true">B</a>
          </li>
        </ul>
        <div class="tab-content">
          <div id="tabA"></div>
          <div id="tabB" class="active show"></div>
        </div>
      </div>
    `;
    window.FBRuntime.init(document);
    const linkB = document.querySelector('a[href="#tabB"]');
    expect(linkB.classList.contains('active')).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// 4) Repetidores
// ---------------------------------------------------------------------------

describe('FBRuntime — repeaters', () => {
  it('al hacer click en + agrega fila con índices reescritos', () => {
    document.body.innerHTML = `
      <div class="fb-repeater">
        <div class="repeater-rows">
          <div class="repeater-row" data-index="0">
            <input name="meds__0__nombre" value="Ibuprofeno">
            <input name="meds__0__dosis" type="number" value="400">
          </div>
        </div>
        <button type="button" class="fb-add-row">+</button>
      </div>
    `;
    window.FBRuntime.init(document);

    document.querySelector('.fb-add-row').click();
    const rows = document.querySelectorAll('.repeater-row');
    expect(rows.length).toBe(2);

    const newNombre = rows[1].querySelector('[name="meds__1__nombre"]');
    const newDosis = rows[1].querySelector('[name="meds__1__dosis"]');
    expect(newNombre).toBeTruthy();
    expect(newDosis).toBeTruthy();
    // La nueva fila debe estar limpia.
    expect(newNombre.value).toBe('');
    expect(newDosis.value).toBe('');
  });

  it('agregar 3 filas mantiene los índices contiguos', () => {
    document.body.innerHTML = `
      <div class="fb-repeater">
        <div class="repeater-rows">
          <div class="repeater-row" data-index="0">
            <input name="meds__0__nombre">
          </div>
        </div>
        <button type="button" class="fb-add-row">+</button>
      </div>
    `;
    window.FBRuntime.init(document);
    const btn = document.querySelector('.fb-add-row');
    btn.click();
    btn.click();
    btn.click();

    const names = Array.from(document.querySelectorAll('.repeater-row [name]'))
      .map((i) => i.getAttribute('name'));
    expect(names).toEqual([
      'meds__0__nombre',
      'meds__1__nombre',
      'meds__2__nombre',
      'meds__3__nombre',
    ]);
  });

  it('bindRepeaters es idempotente (no duplica handlers)', () => {
    document.body.innerHTML = `
      <div class="fb-repeater">
        <div class="repeater-rows">
          <div class="repeater-row" data-index="0">
            <input name="x__0__a">
          </div>
        </div>
        <button type="button" class="fb-add-row">+</button>
      </div>
    `;
    window.FBRuntime.init(document);
    // Init de nuevo sobre el mismo árbol.
    window.FBRuntime.init(document);
    document.querySelector('.fb-add-row').click();
    expect(document.querySelectorAll('.repeater-row').length).toBe(2);
  });

  it('los nuevos checkboxes/radios quedan deseleccionados', () => {
    document.body.innerHTML = `
      <div class="fb-repeater">
        <div class="repeater-rows">
          <div class="repeater-row" data-index="0">
            <input type="checkbox" name="x__0__c" checked>
            <input type="radio" name="x__0__r" value="A" checked>
          </div>
        </div>
        <button type="button" class="fb-add-row">+</button>
      </div>
    `;
    window.FBRuntime.init(document);
    document.querySelector('.fb-add-row').click();

    const newCheckbox = document.querySelector('[name="x__1__c"]');
    const newRadio = document.querySelector('[name="x__1__r"]');
    expect(newCheckbox.checked).toBe(false);
    expect(newRadio.checked).toBe(false);
  });

  it('oculta eliminar cuando solo hay una fila', () => {
    document.body.innerHTML = `
      <div class="fb-repeater">
        <div class="repeater-rows">
          <div class="repeater-row" data-index="0">
            <button type="button" class="fb-remove-row">Eliminar</button>
            <input name="meds__0__nombre">
          </div>
        </div>
        <button type="button" class="fb-add-row">+</button>
      </div>
    `;
    window.FBRuntime.init(document);
    expect(document.querySelector('.fb-remove-row').style.display).toBe('none');
  });

  it('elimina una fila y reindexa las restantes', () => {
    document.body.innerHTML = `
      <div class="fb-repeater">
        <div class="repeater-rows">
          <div class="repeater-row" data-index="0">
            <button type="button" class="fb-remove-row">Eliminar</button>
            <input name="meds__0__nombre" value="A">
          </div>
          <div class="repeater-row" data-index="1">
            <button type="button" class="fb-remove-row">Eliminar</button>
            <input name="meds__1__nombre" value="B">
          </div>
          <div class="repeater-row" data-index="2">
            <button type="button" class="fb-remove-row">Eliminar</button>
            <input name="meds__2__nombre" value="C">
          </div>
        </div>
        <button type="button" class="fb-add-row">+</button>
      </div>
    `;
    window.FBRuntime.init(document);
    document.querySelectorAll('.fb-remove-row')[1].click();

    const rows = document.querySelectorAll('.repeater-row');
    expect(rows.length).toBe(2);
    expect(document.querySelector('[name="meds__0__nombre"]').value).toBe('A');
    expect(document.querySelector('[name="meds__1__nombre"]').value).toBe('C');
    expect(document.querySelector('[name="meds__2__nombre"]')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// 5) API pública
// ---------------------------------------------------------------------------

describe('FBRuntime — API pública', () => {
  it('expone init y refresh en window.FBRuntime', () => {
    expect(typeof window.FBRuntime).toBe('object');
    expect(typeof window.FBRuntime.init).toBe('function');
    expect(typeof window.FBRuntime.refresh).toBe('function');
  });

  it('init con root=null no lanza', () => {
    expect(() => window.FBRuntime.init(null)).not.toThrow();
  });

  it('refresh re-evalúa visibilidad sin necesidad de evento', () => {
    document.body.innerHTML = `
      <input name="x" value="a">
      <div class="fb-field" data-vw-cond='{"field":"x","equals":"b"}'>x</div>
    `;
    window.FBRuntime.init(document);
    const wrap = document.querySelector('.fb-field');
    expect(wrap.style.display).toBe('none');

    // Cambio el valor sin disparar evento; refresh fuerza re-evaluación.
    document.querySelector('[name="x"]').value = 'b';
    window.FBRuntime.refresh(document);
    expect(wrap.style.display).toBe('');
  });
});
