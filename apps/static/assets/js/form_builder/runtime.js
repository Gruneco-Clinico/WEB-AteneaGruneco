/**
 * Form Builder — runtime compartido (preview + visita real).
 * Maneja visibilidad condicional (incluye ocultar pestañas), repetidores
 * dinámicos, computado de IMC en vivo y cambio automático de pestaña activa
 * cuando la pestaña actual deja de ser visible.
 *
 * Uso:
 *   FBRuntime.init(rootElement)
 *
 * `rootElement` es el contenedor a observar (ej. `document` para el runtime
 * de la visita; el contenedor del fragmento HTML cuando viene del preview).
 */
(function (global) {
  'use strict';

  /** Alineado con ``schema._parse_simple_value`` para boolean/checkbox. */
  function coerceBooleanValue(val) {
    if (val === true || val === false) return val;
    if (val === 'true' || val === 'True' || val === '1' || val === 'on') return true;
    return false;
  }

  function readControlValue(root, name) {
    var els = root.querySelectorAll('[name="' + name + '"]');
    if (!els.length) return undefined;
    if (els.length > 1 && els[0].type === 'checkbox') {
      var out = [];
      for (var i = 0; i < els.length; i++) {
        if (els[i].checked) out.push(els[i].value);
      }
      return out;
    }
    var el = els[0];
    if (el.type === 'checkbox' && !el.name.includes('__')) return el.checked;
    if (el.type === 'radio') {
      var sel = root.querySelector('[name="' + name + '"]:checked');
      return sel ? sel.value : '';
    }
    return el.value;
  }

  function evalVisible(wrap, root) {
    var j = wrap.getAttribute('data-vw-cond');
    if (j) {
      try {
        var cond = JSON.parse(j);
        var op = (cond.op || 'equals').toLowerCase();
        var f = cond.field;
        // Sin ``field`` la condición está mal formada; alineamos con el
        // backend (``schema.visible_when_match``) y devolvemos ``true``.
        if (!f) return true;
        var expected = 'value' in cond ? cond.value : cond.equals;
        var actual = readControlValue(root, f);
        if (op === 'not_equals') {
          if (typeof expected === 'boolean') return coerceBooleanValue(actual) !== expected;
          return String(actual) !== String(expected);
        }
        if (op === 'contains') {
          if (actual === undefined || actual === null) return false;
          if (Array.isArray(actual)) {
            var es = String(expected);
            return actual.some(function (x) { return String(x) === es; });
          }
          return String(actual).indexOf(String(expected)) !== -1;
        }
        if (typeof expected === 'boolean') return coerceBooleanValue(actual) === expected;
        return String(actual) === String(expected);
      } catch (e) {
        return true;
      }
    }
    var f2 = wrap.getAttribute('data-vw-field');
    if (!f2) return true;
    var want = wrap.getAttribute('data-vw-eq');
    var val = readControlValue(root, f2);
    if (want === 'true') return (val === true || val === 'true' || val === 'on' || val === '1');
    if (want === 'false') return (val === false || val === 'false' || val === '' || val === '0');
    return String(val) === String(want);
  }

  function ensureActiveTab(root) {
    var wraps = root.querySelectorAll('[data-fb-tabs-wrap]');
    wraps.forEach(function (wrap) {
      var navItems = wrap.querySelectorAll('.fb-tab-li');
      var content = wrap.querySelector('.tab-content');
      if (!navItems.length || !content) return;

      var anyVisibleLi = null;
      var activeLi = null;
      navItems.forEach(function (li) {
        var hidden = li.style.display === 'none';
        var link = li.querySelector('.nav-link');
        if (!link) return;
        var isActive = link.classList.contains('active');
        if (!hidden && !anyVisibleLi) anyVisibleLi = li;
        if (isActive) activeLi = li;
      });

      // Si la pestaña activa quedó oculta, activar la primera visible.
      if (activeLi && activeLi.style.display === 'none' && anyVisibleLi && anyVisibleLi !== activeLi) {
        var newLink = anyVisibleLi.querySelector('.nav-link');
        var oldLink = activeLi.querySelector('.nav-link');
        if (newLink && oldLink) {
          oldLink.classList.remove('active');
          oldLink.setAttribute('aria-selected', 'false');
          var oldPaneId = (oldLink.getAttribute('href') || '').replace(/^#/, '');
          var oldPane = oldPaneId ? root.querySelector('#' + cssEscape(oldPaneId)) : null;
          if (oldPane) {
            oldPane.classList.remove('active');
            oldPane.classList.remove('show');
          }
          newLink.classList.add('active');
          newLink.setAttribute('aria-selected', 'true');
          var newPaneId = (newLink.getAttribute('href') || '').replace(/^#/, '');
          var newPane = newPaneId ? root.querySelector('#' + cssEscape(newPaneId)) : null;
          if (newPane) {
            newPane.classList.add('active');
            newPane.classList.add('show');
          }
        }
      }
    });
  }

  function cssEscape(id) {
    if (typeof CSS !== 'undefined' && CSS.escape) return CSS.escape(id);
    return id.replace(/([\.#:\[\],()=])/g, '\\$1');
  }

  function refreshVisibility(root) {
    root.querySelectorAll('[data-vw-cond]').forEach(function (w) {
      w.style.display = evalVisible(w, root) ? '' : 'none';
    });
    root.querySelectorAll('.fb-field[data-vw-field]').forEach(function (w) {
      w.style.display = evalVisible(w, root) ? '' : 'none';
    });
    ensureActiveTab(root);
  }

  function readDepNumeric(root, depId, computedValues) {
    if (computedValues && computedValues[depId] != null && computedValues[depId] !== '') {
      var cached = parseFloat(computedValues[depId]);
      if (!isNaN(cached)) return cached;
    }
    var el = root.querySelector('[name="' + depId + '"]');
    if (el && el.value !== '' && el.value != null) {
      var fromInput = parseFloat(el.value);
      if (!isNaN(fromInput)) return fromInput;
    }
    var computedOut = root.querySelector('#computed_' + cssEscape(depId));
    if (computedOut && computedOut.value !== '') {
      var fromComputed = parseFloat(computedOut.value);
      if (!isNaN(fromComputed)) return fromComputed;
    }
    return null;
  }

  function extractFormulaNames(formula) {
    var names = [];
    var re = /\b([a-zA-Z_][a-zA-Z0-9_]*)\b/g;
    var m;
    while ((m = re.exec(formula)) !== null) {
      if (names.indexOf(m[1]) === -1) names.push(m[1]);
    }
    return names;
  }

  function safeEvalArithmetic(formula, names) {
    if (!formula || !formula.trim()) return null;
    var allowed = Object.keys(names);
    var used = extractFormulaNames(formula);
    for (var i = 0; i < used.length; i++) {
      if (allowed.indexOf(used[i]) === -1) return null;
    }
    try {
      // eslint-disable-next-line no-new-func
      var fn = new Function(allowed.join(','), 'return (' + formula + ')');
      var vals = allowed.map(function (k) { return names[k]; });
      var result = fn.apply(null, vals);
      if (typeof result !== 'number' || !isFinite(result)) return null;
      return result;
    } catch (e) {
      return null;
    }
  }

  function computeImcValue(root, deps, computedValues) {
    var pesoKey = deps[0] || 'peso_kg';
    var tallaKey = deps[1] || 'talla_cm';
    var p = readDepNumeric(root, pesoKey, computedValues);
    var t = readDepNumeric(root, tallaKey, computedValues);
    if (p == null || t == null || t === 0) return null;
    var m = t / 100.0;
    if (!m) return null;
    return p / (m * m);
  }

  function formatComputedValue(val, precision) {
    if (val == null) return '';
    var prec = parseInt(precision, 10);
    if (!isNaN(prec) && prec >= 0) return val.toFixed(prec);
    return String(val);
  }

  function updateComputed(root) {
    var boxes = Array.prototype.slice.call(root.querySelectorAll('.fb-computed'));
    var resolved = {};
    for (var pass = 0; pass < boxes.length + 1; pass++) {
      var progress = false;
      boxes.forEach(function (box) {
        var id = box.getAttribute('data-id');
        if (!id || Object.prototype.hasOwnProperty.call(resolved, id)) return;
        var formula = (box.getAttribute('data-formula') || '').trim();
        var deps = (box.getAttribute('data-depends') || '').split(',').filter(Boolean);
        var precision = box.getAttribute('data-precision');
        var out = root.querySelector('#computed_' + cssEscape(id));
        if (!out || !formula) return;

        var result = null;
        if (formula === 'imc') {
          result = computeImcValue(root, deps, resolved);
          if (result != null) result = parseFloat(result.toFixed(2));
        } else {
          if (!deps.length) return;
          var ctx = {};
          var depsReady = true;
          deps.forEach(function (dep) {
            var num = readDepNumeric(root, dep, resolved);
            if (num == null) depsReady = false;
            else ctx[dep] = num;
          });
          if (!depsReady) return;
          result = safeEvalArithmetic(formula, ctx);
        }

        var formatted = result == null ? '' : formatComputedValue(result, precision);
        resolved[id] = formatted;
        out.value = formatted;
        progress = true;
      });
      if (!progress) break;
    }
  }

  function getDirectRepeaterRows(rowsWrap) {
    return Array.prototype.filter.call(rowsWrap.children, function (el) {
      return el.classList.contains('repeater-row');
    });
  }

  function reindexRepeaterRows(rowsWrap) {
    getDirectRepeaterRows(rowsWrap).forEach(function (row, idx) {
      row.setAttribute('data-index', String(idx));
      row.querySelectorAll('[name]').forEach(function (inp) {
        var n = inp.getAttribute('name');
        if (n) inp.setAttribute('name', n.replace(/__\d+__/g, '__' + idx + '__'));
      });
      row.querySelectorAll('[id]').forEach(function (el) {
        var id = el.getAttribute('id');
        if (id && /__\d+__/.test(id)) {
          el.setAttribute('id', id.replace(/__\d+__/g, '__' + idx + '__'));
        }
      });
      row.querySelectorAll('label[for]').forEach(function (lab) {
        var f = lab.getAttribute('for');
        if (f && /__\d+__/.test(f)) {
          lab.setAttribute('for', f.replace(/__\d+__/g, '__' + idx + '__'));
        }
      });
    });
  }

  function updateRepeaterRemoveButtons(rowsWrap) {
    var rows = getDirectRepeaterRows(rowsWrap);
    var onlyOne = rows.length <= 1;
    rows.forEach(function (row) {
      var rm = row.querySelector('.fb-remove-row');
      if (!rm) return;
      rm.disabled = onlyOne;
      rm.style.display = onlyOne ? 'none' : '';
    });
  }

  function removeRepeaterRow(row, rowsWrap, root) {
    if (getDirectRepeaterRows(rowsWrap).length <= 1) return;
    row.remove();
    reindexRepeaterRows(rowsWrap);
    updateRepeaterRemoveButtons(rowsWrap);
    refreshVisibility(root);
    updateComputed(root);
  }

  function wireRepeaterRemoveButton(row, rowsWrap, root) {
    var rm = row.querySelector('.fb-remove-row');
    if (!rm || rm._fbRmBound) return;
    rm._fbRmBound = true;
    rm.addEventListener('click', function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      removeRepeaterRow(row, rowsWrap, root);
    });
  }

  function wireRepeaterRows(rowsWrap, root) {
    getDirectRepeaterRows(rowsWrap).forEach(function (row) {
      wireRepeaterRemoveButton(row, rowsWrap, root);
    });
  }

  function bindRepeaters(root) {
    root.querySelectorAll('.fb-repeater').forEach(function (rep) {
      if (rep._fbRepBound) return;
      var rowsWrap = rep.querySelector('.repeater-rows');
      var directRows = rowsWrap ? getDirectRepeaterRows(rowsWrap) : [];
      var tplRow = directRows[0];
      var btn = rep.querySelector('.fb-add-row');
      if (!rowsWrap || !tplRow || !btn) return;
      rep._fbRepBound = true;

      btn.addEventListener('click', function (ev) {
        ev.preventDefault();
        var idx = getDirectRepeaterRows(rowsWrap).length;
        var clone = tplRow.cloneNode(true);
        clone.setAttribute('data-index', String(idx));
        clone.querySelectorAll('[name]').forEach(function (inp) {
          var n = inp.getAttribute('name');
          if (!n) return;
          inp.setAttribute('name', n.replace(/__\d+__/g, '__' + idx + '__'));
          if (inp.type === 'checkbox' || inp.type === 'radio') inp.checked = false;
          else inp.value = '';
        });
        clone.querySelectorAll('[id]').forEach(function (el) {
          var id = el.getAttribute('id');
          if (id) el.setAttribute('id', id.replace(/__\d+__/g, '__' + idx + '__'));
        });
        clone.querySelectorAll('label[for]').forEach(function (lab) {
          var f = lab.getAttribute('for');
          if (f) lab.setAttribute('for', f.replace(/__\d+__/g, '__' + idx + '__'));
        });
        rowsWrap.appendChild(clone);
        wireRepeaterRemoveButton(clone, rowsWrap, root);
        updateRepeaterRemoveButtons(rowsWrap);
      });

      wireRepeaterRows(rowsWrap, root);
      updateRepeaterRemoveButtons(rowsWrap);
    });
  }

  var FBRuntime = {
    init: function (root) {
      if (!root) return;
      // Aceptar `document` como root: en ese caso operamos sobre body.
      var actual = root === document ? document.body : root;
      bindRepeaters(actual);
      var handler = function () {
        refreshVisibility(actual);
        updateComputed(actual);
      };
      // Listener en `root` para cubrir casos en los que `actual` se reemplaza.
      (root === document ? document : actual).addEventListener('change', handler);
      (root === document ? document : actual).addEventListener('input', handler);
      handler();
    },
    refresh: function (root) {
      var actual = root === document ? document.body : root;
      refreshVisibility(actual);
      updateComputed(actual);
    },
  };

  global.FBRuntime = FBRuntime;
})(typeof window !== 'undefined' ? window : this);
