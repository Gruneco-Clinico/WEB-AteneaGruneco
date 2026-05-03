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
          if (typeof expected === 'boolean') return Boolean(actual) !== expected;
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
        if (typeof expected === 'boolean') return Boolean(actual) === expected;
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

  function updateImc(root) {
    root.querySelectorAll('.fb-computed[data-formula="imc"]').forEach(function (box) {
      var id = box.getAttribute('data-id');
      var deps = (box.getAttribute('data-depends') || '').split(',').filter(Boolean);
      var peso = deps[0] ? (root.querySelector('[name="' + deps[0] + '"]') || {}).value : '';
      var talla = deps[1] ? (root.querySelector('[name="' + deps[1] + '"]') || {}).value : '';
      var out = root.querySelector('#computed_' + cssEscape(id));
      if (!out) return;
      var p = parseFloat(peso), t = parseFloat(talla);
      if (!p || !t) { out.value = ''; return; }
      var m = t / 100.0;
      out.value = (p / (m * m)).toFixed(2);
    });
  }

  function bindRepeaters(root) {
    root.querySelectorAll('.fb-repeater').forEach(function (rep) {
      if (rep._fbRepBound) return;
      rep._fbRepBound = true;
      var rowsWrap = rep.querySelector('.repeater-rows');
      var tplRow = rep.querySelector('.repeater-row');
      var btn = rep.querySelector('.fb-add-row');
      if (!rowsWrap || !tplRow || !btn) return;
      btn.addEventListener('click', function () {
        var rows = rowsWrap.querySelectorAll('.repeater-row');
        var idx = rows.length;
        var clone = tplRow.cloneNode(true);
        clone.setAttribute('data-index', idx);
        clone.querySelectorAll('[name]').forEach(function (inp) {
          var n = inp.getAttribute('name');
          if (!n) return;
          inp.setAttribute('name', n.replace(/__\d+__/g, '__' + idx + '__'));
          if (inp.type === 'checkbox' || inp.type === 'radio') inp.checked = false;
          else inp.value = '';
        });
        rowsWrap.appendChild(clone);
      });
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
        updateImc(actual);
      };
      // Listener en `root` para cubrir casos en los que `actual` se reemplaza.
      (root === document ? document : actual).addEventListener('change', handler);
      (root === document ? document : actual).addEventListener('input', handler);
      handler();
    },
    refresh: function (root) {
      var actual = root === document ? document.body : root;
      refreshVisibility(actual);
      updateImc(actual);
    },
  };

  global.FBRuntime = FBRuntime;
})(typeof window !== 'undefined' ? window : this);
