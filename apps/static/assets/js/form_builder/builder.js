/**
 * Form Builder — editor visual (vanilla JS + SortableJS).
 * Expone window.FormBuilder.mount(rootEl, options)
 */
(function (global) {
  'use strict';

  var TYPE_LABELS = {
    section: 'Sección',
    text: 'Texto corto',
    textarea: 'Texto largo',
    number: 'Número',
    date: 'Fecha',
    time: 'Hora',
    email: 'Correo',
    select: 'Lista desplegable',
    radio: 'Opción única (radio)',
    checkbox: 'Casilla',
    boolean: 'Sí / No',
    multiselect: 'Múltiple opción',
    repeater: 'Repetidor',
    computed: 'Calculado',
    info: 'Instrucciones / texto',
  };

  var SOFT_SECTION_LIMIT = 9;

  function isAllowedTypeIn(type, parentType) {
    if (parentType === 'section') return type !== 'section';
    if (parentType === 'repeater') return type !== 'section' && type !== 'repeater';
    return true;
  }

  function countTopLevelSections(fields) {
    var c = 0;
    for (var i = 0; i < fields.length; i++) if ((fields[i].type || '') === 'section') c++;
    return c;
  }

  function slugify(s) {
    if (!s) return 'campo';
    var x = String(s)
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9_]+/g, '_')
      .replace(/^_+|_+$/g, '');
    return (x || 'campo').substring(0, 48);
  }

  function genKey() {
    return 'fbk_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
  }

  function assignKeysDeep(nodes) {
    if (!nodes || !nodes.length) return;
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      if (!n._bk) n._bk = genKey();
      if (n.fields && n.fields.length) assignKeysDeep(n.fields);
    }
  }

  function stripKeys(nodes) {
    if (!nodes || !nodes.length) return [];
    return nodes.map(function (n) {
      var o = {};
      Object.keys(n).forEach(function (k) {
        if (k === '_bk') return;
        o[k] = n[k];
      });
      if (o.fields && o.fields.length) o.fields = stripKeys(o.fields);
      return o;
    });
  }

  function findNode(fields, key, par) {
    for (var i = 0; i < fields.length; i++) {
      var n = fields[i];
      if (n._bk === key) return { node: n, list: fields, index: i, parent: par };
      if (n.fields && n.fields.length) {
        var hit = findNode(n.fields, key, n);
        if (hit) return hit;
      }
    }
    return null;
  }

  /** Busca un nodo por `id` en todo el árbol (sección / repetidor). */
  function findFieldById(nodes, fid) {
    if (!nodes || !fid) return null;
    for (var i = 0; i < nodes.length; i++) {
      var node = nodes[i];
      if (node.id === fid) return node;
      if (node.fields && node.fields.length) {
        var sub = findFieldById(node.fields, fid);
        if (sub) return sub;
      }
    }
    return null;
  }

  /** Campos con id que aparecen antes que targetKey en recorrido DFS del árbol. */
  function collectPriorFieldIdsDFS(fields, targetKey) {
    var acc = [];
    function walk(nodes) {
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (n._bk === targetKey) return true;
        var t = n.type || 'text';
        if (t !== 'section' && t !== 'repeater' && t !== 'computed' && t !== 'info' && n.id) acc.push(n.id);
        if (n.fields && n.fields.length && walk(n.fields)) return true;
      }
      return false;
    }
    walk(fields);
    return acc;
  }

  /** Ids disponibles como dependencia de un calculado (incluye otros calculados previos). */
  function collectPriorIdsForComputedDeps(fields, targetKey) {
    var acc = [];
    function walk(nodes) {
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (n._bk === targetKey) return true;
        var t = n.type || 'text';
        if (t !== 'section' && t !== 'repeater' && n.id) acc.push(n.id);
        if (n.fields && n.fields.length && walk(n.fields)) return true;
      }
      return false;
    }
    walk(fields);
    return acc;
  }

  function allFieldIdsForDeps(fields, excludeKey, acc) {
    acc = acc || [];
    for (var i = 0; i < fields.length; i++) {
      var n = fields[i];
      if (n._bk === excludeKey) continue;
      var t = n.type || 'text';
      if (t !== 'section' && t !== 'repeater' && t !== 'computed' && t !== 'info' && n.id) acc.push(n.id);
      if (n.fields && n.fields.length) allFieldIdsForDeps(n.fields, excludeKey, acc);
    }
    return acc;
  }

  function defaultNode(type) {
    var id = slugify(TYPE_LABELS[type] || 'campo') + '_' + Math.random().toString(36).slice(2, 5);
    switch (type) {
      case 'section':
        return { _bk: genKey(), type: 'section', label: 'Nueva sección', fields: [] };
      case 'textarea':
        return { _bk: genKey(), type: 'textarea', id: id, label: 'Texto largo', required: false };
      case 'number':
        return { _bk: genKey(), type: 'number', id: id, label: 'Número', required: false };
      case 'date':
        return { _bk: genKey(), type: 'date', id: id, label: 'Fecha', required: false };
      case 'time':
        return { _bk: genKey(), type: 'time', id: id, label: 'Hora', required: false };
      case 'email':
        return { _bk: genKey(), type: 'email', id: id, label: 'Correo', required: false };
      case 'select':
        return {
          _bk: genKey(),
          type: 'select',
          id: id,
          label: 'Seleccione',
          required: false,
          options: [
            { value: 'a', label: 'Opción A' },
            { value: 'b', label: 'Opción B' },
          ],
        };
      case 'radio':
        return {
          _bk: genKey(),
          type: 'radio',
          id: id,
          label: 'Elija una',
          required: false,
          options: [
            { value: 'si', label: 'Sí' },
            { value: 'no', label: 'No' },
          ],
        };
      case 'checkbox':
        return { _bk: genKey(), type: 'checkbox', id: id, label: 'Opción', required: false };
      case 'boolean':
        return { _bk: genKey(), type: 'boolean', id: id, label: '¿Activo?', required: false };
      case 'multiselect':
        return {
          _bk: genKey(),
          type: 'multiselect',
          id: id,
          label: 'Seleccione varias',
          required: false,
          options: [
            { value: 'a', label: 'A' },
            { value: 'b', label: 'B' },
          ],
        };
      case 'repeater':
        return {
          _bk: genKey(),
          type: 'repeater',
          id: slugify('items') + '_' + Math.random().toString(36).slice(2, 5),
          label: 'Ítems repetidos',
          add_label: 'Agregar fila',
          remove_label: 'Eliminar',
          required: false,
          fields: [
            {
              _bk: genKey(),
              type: 'text',
              id: 'nombre',
              label: 'Nombre',
              required: true,
            },
          ],
        };
      case 'computed':
        return {
          _bk: genKey(),
          type: 'computed',
          id: id,
          label: 'Valor calculado',
          formula: '',
          precision: 2,
          depends_on: [],
        };
      case 'info':
        return {
          _bk: genKey(),
          type: 'info',
          label: 'Instrucciones',
          content: '',
          variant: 'plain',
        };
      default:
        return { _bk: genKey(), type: 'text', id: id, label: 'Texto', required: false };
    }
  }

  function reorderListByKeys(list, orderedKeys) {
    var map = {};
    list.forEach(function (n) {
      map[n._bk] = n;
    });
    var next = [];
    orderedKeys.forEach(function (k) {
      if (map[k]) next.push(map[k]);
    });
    list.length = 0;
    next.forEach(function (n) {
      list.push(n);
    });
  }

  function validateState(fields, errs, warns) {
    errs = errs || [];
    warns = warns || [];
    var seen = {};
    function walk(nodes, parentType) {
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        var t = n.type || 'text';
        if (parentType === 'section' && t === 'section') {
          errs.push('No se permite anidar secciones (sección «' + (n.label || '') + '»).');
        }
        if (parentType === 'repeater' && (t === 'section' || t === 'repeater')) {
          errs.push('Dentro de un repetidor no se permiten ' + (t === 'section' ? 'secciones' : 'repetidores anidados') + ' (en «' + (n.label || n.id || '') + '»).');
        }
        if (t !== 'section' && t !== 'info') {
          if (!n.id || !String(n.id).trim()) errs.push('Cada campo (excepto sección) necesita un id.');
          else {
            if (seen[n.id]) errs.push('Id duplicado: ' + n.id);
            seen[n.id] = true;
          }
        }
        if (t === 'info') {
          if (!n.content || !String(n.content).trim()) {
            errs.push('El bloque «' + (n.label || 'Instrucciones') + '» necesita contenido.');
          }
          var variant = (n.variant || 'plain').toLowerCase();
          if (variant !== 'info' && variant !== 'warning' && variant !== 'plain') {
            errs.push('Variante no válida en «' + (n.label || 'Instrucciones') + '».');
          }
        }
        if (t === 'select' || t === 'radio' || t === 'multiselect') {
          var opts = n.options || [];
          if (!opts.length) errs.push('El campo «' + (n.label || n.id) + '» necesita al menos una opción.');
          opts.forEach(function (o, j) {
            if (!o || String(o.value).trim() === '') errs.push('Opción ' + (j + 1) + ' sin valor en «' + (n.label || n.id) + '».');
          });
        }
        if (t === 'computed') {
          if (!n.formula || !String(n.formula).trim()) errs.push('Campo calculado «' + (n.label || n.id) + '»: indique una fórmula.');
          if (!n.depends_on || !n.depends_on.length)
            errs.push('Campo calculado «' + (n.label || n.id) + '»: indique al menos una dependencia.');
        }
        if (n.fields && n.fields.length) walk(n.fields, t);
      }
    }
    walk(fields, null);

    var topSections = countTopLevelSections(fields);
    if (topSections > SOFT_SECTION_LIMIT) {
      warns.push(
        'Hay ' + topSections + ' secciones (recomendado ≤ ' + SOFT_SECTION_LIMIT +
        '). En la vista del paciente se mostrarán como pestañas y podrían ser muchas.'
      );
    }
    var seenSectionLabels = {};
    fields.forEach(function (n) {
      if ((n.type || '') !== 'section') return;
      var lbl = String(n.label || '').trim();
      if (!lbl) {
        warns.push('Hay una sección sin etiqueta; revise la pestaña que verá el paciente.');
        return;
      }
      if (seenSectionLabels[lbl]) warns.push('Etiqueta de sección duplicada: «' + lbl + '».');
      seenSectionLabels[lbl] = true;
      if (lbl.length > 28) warns.push('Etiqueta de sección muy larga (>28): «' + lbl + '». Se truncará en pestañas.');
    });
    return errs;
  }

  /**
   * Inicializa visibilidad condicional, repetidores y cómputos en un fragmento
   * cargado por el preview. Usa el runtime compartido (`window.FBRuntime`) si
   * está disponible (preferido). Si no, omite la inicialización y solo dispara
   * un evento custom para que el host pueda reaccionar.
   */
  function initVisibilityAndRepeater(root) {
    if (global.FBRuntime && typeof global.FBRuntime.init === 'function') {
      global.FBRuntime.init(root);
      return;
    }
  }

  function FormBuilder() {}

  FormBuilder.mount = function (rootEl, options) {
    var state = { fields: [], selectedKey: null };
    var previewUrl = options.previewUrl || '';
    var csrf = options.csrfToken || '';
    var sortables = [];

    try {
      state.fields = JSON.parse(JSON.stringify(options.initialFields || []));
    } catch (e) {
      state.fields = [];
    }
    assignKeysDeep(state.fields);

    var el = {
      palette: rootEl.querySelector('[data-fb-palette]'),
      canvas: rootEl.querySelector('[data-fb-canvas]'),
      props: rootEl.querySelector('[data-fb-props]'),
      jsonOut: rootEl.querySelector('[data-fb-json-readonly]'),
      preview: rootEl.querySelector('[data-fb-preview]'),
      hiddenJson: rootEl.querySelector('input[name="campos_json"]'),
      form: rootEl.querySelector('form[data-fb-main-form]'),
      paletteTarget: null,
      paletteRootToggle: null,
      aria: null,
    };

    if (!el.form || !el.hiddenJson || !el.canvas || !el.props) {
      return;
    }

    el.aria = document.createElement('div');
    el.aria.className = 'sr-only fb-aria-live';
    el.aria.setAttribute('aria-live', 'polite');
    el.aria.setAttribute('aria-atomic', 'true');
    rootEl.appendChild(el.aria);

    function destroySortables() {
      sortables.forEach(function (s) {
        try {
          s.destroy();
        } catch (e) {}
      });
      sortables = [];
    }

    function syncHiddenJson() {
      var data = stripKeys(state.fields);
      var str = JSON.stringify(data, null, 2);
      if (el.hiddenJson) el.hiddenJson.value = JSON.stringify(data);
      if (el.jsonOut) el.jsonOut.textContent = str;
    }

    /**
     * Redibuja el lienzo. Si skipProps es true, no reconstruye el panel de
     * propiedades (evita perder el foco al teclear en id/etiqueta/etc.).
     */
    function renderCanvas(opts) {
      opts = opts || {};
      destroySortables();
      el.canvas.innerHTML = '';
      if (!state.fields.length) {
        var empty = document.createElement('div');
        empty.className = 'fb-canvas-empty';
        empty.textContent =
          'Use la paleta para añadir una sección o campo. Puede arrastrar para reordenar.';
        el.canvas.appendChild(empty);
      } else {
        var ul = document.createElement('ul');
        ul.className = 'fb-nested-list list-unstyled';
        ul.setAttribute('data-parent-key', '');
        state.fields.forEach(function (n) {
          ul.appendChild(renderCard(n, ''));
        });
        el.canvas.appendChild(ul);
        initSortable(ul, '');
      }
      syncHiddenJson();
      if (!opts.skipProps) renderProps();
      if (typeof renderPaletteTarget === 'function') renderPaletteTarget();
    }

    function renderCard(node, parentKey) {
      var li = document.createElement('li');
      li.setAttribute('data-key', node._bk);
      var card = document.createElement('div');
      card.className = 'fb-card' + (state.selectedKey === node._bk ? ' fb-card-selected' : '') + (t === 'info' ? ' fb-card-info' : '');
      card.setAttribute('data-key', node._bk);

      var head = document.createElement('div');
      head.className = 'fb-card-header';
      var handle = document.createElement('span');
      handle.className = 'fb-card-handle';
      handle.innerHTML = '&#9776;';
      handle.title = 'Arrastrar';
      handle.setAttribute('aria-label', 'Arrastrar para reordenar');
      handle.setAttribute('role', 'button');
      var title = document.createElement('div');
      title.className = 'fb-card-title';
      var t = node.type || 'text';

      if (t === 'section' && !parentKey) {
        var idx = state.fields.indexOf(node);
        if (idx >= 0) {
          var badge = document.createElement('span');
          badge.className = 'fb-section-badge';
          badge.textContent = String(idx + 1);
          badge.title = 'Pestaña ' + (idx + 1) + ' en la vista del paciente';
          title.appendChild(badge);
        }
      }

      var typeTag = document.createElement('span');
      typeTag.className = 'fb-card-type';
      typeTag.textContent = '[' + (TYPE_LABELS[t] || t) + ']';
      title.appendChild(typeTag);

      var titleText = document.createElement('span');
      titleText.className = 'fb-card-label';
      titleText.textContent = ' ' + (node.label || node.id || '');
      title.appendChild(titleText);

      if (t === 'info' && node.content) {
        var preview = document.createElement('div');
        preview.className = 'fb-card-info-preview text-muted small';
        var snippet = String(node.content).replace(/\s+/g, ' ').trim();
        preview.textContent = snippet.length > 72 ? snippet.substring(0, 72) + '…' : snippet;
        title.appendChild(preview);
      }

      if (node.visible_when) {
        var vwIcon = document.createElement('span');
        vwIcon.className = 'fb-card-vw';
        vwIcon.innerHTML = '&#9678;';
        vwIcon.title = 'Visibilidad condicional activa';
        vwIcon.setAttribute('aria-label', 'Visibilidad condicional');
        title.appendChild(vwIcon);
      }

      var actions = document.createElement('div');
      actions.className = 'fb-card-actions btn-group';

      function mkBtn(label, ariaLabel, fn) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'btn btn-sm btn-outline-secondary';
        b.textContent = label;
        b.setAttribute('aria-label', ariaLabel);
        b.title = ariaLabel;
        b.addEventListener('click', function (e) {
          e.stopPropagation();
          fn();
        });
        return b;
      }

      actions.appendChild(
        mkBtn('↑', 'Mover arriba', function () {
          moveKey(node._bk, -1);
        })
      );
      actions.appendChild(
        mkBtn('↓', 'Mover abajo', function () {
          moveKey(node._bk, 1);
        })
      );
      actions.appendChild(
        mkBtn('Dup', 'Duplicar', function () {
          duplicateKey(node._bk);
        })
      );
      actions.appendChild(
        mkBtn('✕', 'Eliminar', function () {
          removeKey(node._bk);
        })
      );

      head.appendChild(handle);
      head.appendChild(title);
      head.appendChild(actions);
      card.appendChild(head);

      card.addEventListener('click', function (e) {
        if (e.target.closest('button')) return;
        e.stopPropagation();
        state.selectedKey = node._bk;
        renderCanvas();
      });

      if ((t === 'section' || t === 'repeater') && node.fields) {
        var nest = document.createElement('div');
        nest.className = 'fb-nested-wrap';

        var addBar = document.createElement('div');
        addBar.className = 'fb-nested-addbar mb-1';

        var addBtn = document.createElement('button');
        addBtn.type = 'button';
        addBtn.className = 'btn btn-sm btn-outline-primary fb-nested-add';
        addBtn.textContent = '+ Añadir campo';
        addBtn.setAttribute('aria-label', 'Añadir campo dentro de ' + (TYPE_LABELS[t] || t) + ' «' + (node.label || '') + '»');

        var addMenu = document.createElement('div');
        addMenu.className = 'fb-nested-menu';
        addMenu.setAttribute('hidden', 'hidden');
        Object.keys(TYPE_LABELS).forEach(function (pt) {
          if (!isAllowedTypeIn(pt, t)) return;
          var item = document.createElement('button');
          item.type = 'button';
          item.className = 'fb-nested-menu-item';
          item.textContent = TYPE_LABELS[pt];
          item.addEventListener('click', function (ev) {
            ev.stopPropagation();
            addMenu.setAttribute('hidden', 'hidden');
            addField(pt, node._bk);
          });
          addMenu.appendChild(item);
        });

        addBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          var hidden = addMenu.hasAttribute('hidden');
          // Close any other open menus
          document.querySelectorAll('.fb-nested-menu').forEach(function (m) {
            if (m !== addMenu) m.setAttribute('hidden', 'hidden');
          });
          if (hidden) addMenu.removeAttribute('hidden');
          else addMenu.setAttribute('hidden', 'hidden');
        });

        addBar.appendChild(addBtn);
        addBar.appendChild(addMenu);
        nest.appendChild(addBar);

        var ul = document.createElement('ul');
        ul.className = 'fb-nested-list list-unstyled';
        ul.setAttribute('data-parent-key', node._bk);
        node.fields.forEach(function (ch) {
          ul.appendChild(renderCard(ch, node._bk));
        });
        nest.appendChild(ul);
        card.appendChild(nest);
        initSortable(ul, node._bk);
      }

      li.appendChild(card);
      return li;
    }

    function getUlParentInfo(ulEl) {
      var pk = ulEl.getAttribute('data-parent-key') || '';
      if (!pk) return { parentKey: null, parentType: null, list: state.fields };
      var hit = findNode(state.fields, pk);
      if (!hit) return { parentKey: null, parentType: null, list: state.fields };
      return { parentKey: pk, parentType: hit.node.type || null, list: hit.node.fields };
    }

    function inferDraggedType(draggedEl) {
      if (!draggedEl) return null;
      var paletteType = draggedEl.getAttribute('data-fb-type');
      if (paletteType) return paletteType;
      var k = draggedEl.getAttribute('data-key');
      if (k) {
        var hit = findNode(state.fields, k);
        if (hit) return hit.node.type || 'text';
      }
      return null;
    }

    function clearDropMarkers() {
      document.querySelectorAll('.fb-drop-target, .fb-drop-invalid').forEach(function (n) {
        n.classList.remove('fb-drop-target');
        n.classList.remove('fb-drop-invalid');
      });
    }

    function scheduleAutoExpand(toUl) {
      // En el editor las secciones/repetidores ya están expandidos; conservamos el
      // hook por si en el futuro hay colapso. Solo marca el contenedor como
      // "objetivo activo" para que el usuario tenga retroalimentación clara.
      clearTimeout(state._expandTimer);
      state._expandTimer = setTimeout(function () {
        if (toUl && toUl.parentNode) {
          toUl.parentNode.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }, 600);
    }

    function initSortable(ul, parentKey) {
      if (typeof global.Sortable === 'undefined') return;
      var s = global.Sortable.create(ul, {
        handle: '.fb-card-handle',
        animation: 150,
        group: { name: 'fb', pull: true, put: ['fb'] },
        ghostClass: 'fb-sortable-ghost',
        chosenClass: 'fb-sortable-chosen',
        dragClass: 'fb-sortable-drag',
        revertOnSpill: true,
        emptyInsertThreshold: 24,
        fallbackOnBody: true,
        onMove: function (evt) {
          var draggedType = inferDraggedType(evt.dragged);
          var toUl = evt.to;
          var info = getUlParentInfo(toUl);
          var allowed = !draggedType || isAllowedTypeIn(draggedType, info.parentType);
          clearDropMarkers();
          var container = toUl.parentNode;
          if (!container) return allowed;
          if (allowed) {
            container.classList.add('fb-drop-target');
            scheduleAutoExpand(toUl);
          } else {
            container.classList.add('fb-drop-invalid');
          }
          return allowed;
        },
        onAdd: function (evt) {
          clearTimeout(state._expandTimer);
          var item = evt.item;
          var paletteType = item.getAttribute('data-fb-type');
          var movedKey = item.getAttribute('data-key');
          var info = getUlParentInfo(ul);

          if (item.parentNode) item.parentNode.removeChild(item);
          clearDropMarkers();

          if (paletteType) {
            if (!isAllowedTypeIn(paletteType, info.parentType)) {
              announce('No permitido aquí.');
              return;
            }
            var node = defaultNode(paletteType);
            info.list.splice(evt.newIndex, 0, node);
            state.selectedKey = node._bk;
            setTimeout(function () {
              renderCanvas();
              announce(
                'Añadido: ' + (TYPE_LABELS[paletteType] || paletteType) +
                ' en ' + (info.parentKey ? '«' + ((findNode(state.fields, info.parentKey) || {}).node || {}).label + '»' : 'raíz') +
                ', posición ' + (evt.newIndex + 1) + '.'
              );
            }, 0);
            return;
          }

          if (movedKey) {
            var hit = findNode(state.fields, movedKey);
            if (!hit) {
              setTimeout(function () { renderCanvas(); }, 0);
              return;
            }
            var draggedType = hit.node.type || 'text';
            if (!isAllowedTypeIn(draggedType, info.parentType)) {
              announce('Movimiento bloqueado: tipo no permitido en este contenedor.');
              setTimeout(function () { renderCanvas(); }, 0);
              return;
            }
            hit.list.splice(hit.index, 1);
            // Re-leer la lista de destino: si el destino y origen comparten lista, los índices cambian
            var freshInfo = getUlParentInfo(ul);
            var insertIdx = Math.min(evt.newIndex, freshInfo.list.length);
            freshInfo.list.splice(insertIdx, 0, hit.node);
            setTimeout(function () {
              renderCanvas();
              announce(
                'Movido: ' + (TYPE_LABELS[draggedType] || draggedType) +
                ' a posición ' + (insertIdx + 1) + '.'
              );
            }, 0);
          }
        },
        onUpdate: function (evt) {
          // Reordenamiento intra-lista: actualizar el orden en estado por keys del DOM.
          clearDropMarkers();
          var keys = [];
          for (var i = 0; i < ul.children.length; i++) {
            keys.push(ul.children[i].getAttribute('data-key'));
          }
          var list;
          if (!parentKey) list = state.fields;
          else {
            var hit = findNode(state.fields, parentKey);
            list = hit && hit.node.fields ? hit.node.fields : null;
          }
          if (list) reorderListByKeys(list, keys);
          syncHiddenJson();
          announce('Reordenado.');
        },
        onEnd: function () {
          clearTimeout(state._expandTimer);
          clearDropMarkers();
          document.body.classList.remove('fb-dragging');
        },
        onStart: function () {
          document.body.classList.add('fb-dragging');
        },
      });
      sortables.push(s);
    }

    /**
     * Configura la paleta como fuente arrastrable: cada botón clona-y-suelta hacia
     * cualquier `<ul.fb-nested-list>` del lienzo (mismo grupo "fb").
     */
    function initPaletteSortable() {
      if (typeof global.Sortable === 'undefined' || !el.palette) return;
      global.Sortable.create(el.palette, {
        group: { name: 'fb', pull: 'clone', put: false },
        sort: false,
        draggable: '.fb-palette-btn',
        animation: 150,
        ghostClass: 'fb-sortable-ghost',
        chosenClass: 'fb-sortable-chosen',
        dragClass: 'fb-sortable-drag',
        fallbackOnBody: true,
        onStart: function () {
          document.body.classList.add('fb-dragging');
        },
        onEnd: function () {
          document.body.classList.remove('fb-dragging');
          clearTimeout(state._expandTimer);
          clearDropMarkers();
        },
      });
    }

    function moveKey(key, delta) {
      var hit = findNode(state.fields, key);
      if (!hit) return;
      var i = hit.index + delta;
      if (i < 0 || i >= hit.list.length) return;
      var tmp = hit.list[i];
      hit.list[i] = hit.list[hit.index];
      hit.list[hit.index] = tmp;
      renderCanvas();
    }

    function removeKey(key) {
      var hit = findNode(state.fields, key);
      if (!hit) return;
      hit.list.splice(hit.index, 1);
      if (state.selectedKey === key) state.selectedKey = null;
      renderCanvas();
    }

    function duplicateKey(key) {
      var hit = findNode(state.fields, key);
      if (!hit) return;
      var copy = JSON.parse(JSON.stringify(hit.node));
      function rekey(n) {
        n._bk = genKey();
        if (n.id && n.type !== 'section' && n.type !== 'info') n.id = n.id + '_copy_' + Math.random().toString(36).slice(2, 4);
        if (n.fields) n.fields.forEach(rekey);
      }
      rekey(copy);
      hit.list.splice(hit.index + 1, 0, copy);
      state.selectedKey = copy._bk;
      renderCanvas();
    }

    function addField(type, parentKey, opts) {
      opts = opts || {};
      var n = defaultNode(type);
      if (!parentKey) {
        if (typeof opts.afterIndex === 'number' && opts.afterIndex >= -1) {
          state.fields.splice(opts.afterIndex + 1, 0, n);
        } else {
          state.fields.push(n);
        }
      } else {
        var hit = findNode(state.fields, parentKey);
        if (!hit || !hit.node.fields) return;
        if (typeof opts.afterIndex === 'number' && opts.afterIndex >= -1) {
          hit.node.fields.splice(opts.afterIndex + 1, 0, n);
        } else {
          hit.node.fields.push(n);
        }
      }
      state.selectedKey = n._bk;
      renderCanvas();
      announce('Añadido: ' + (TYPE_LABELS[type] || type) + ' «' + (n.label || n.id || '') + '».');
    }

    /**
     * Calcula el contexto de inserción según el campo actualmente seleccionado.
     * - Sin selección o "forzar raíz": inserta al final del nivel raíz.
     * - Selección sobre sección/repetidor: inserta dentro, al final.
     * - Selección sobre un campo hoja: inserta como hermano siguiente.
     * Devuelve también `parentType` para validar tipos permitidos.
     */
    function getInsertionContext() {
      if (state.forceRoot || !state.selectedKey) {
        return { parentKey: null, parentType: null, parentLabel: 'Raíz', afterIndex: state.fields.length - 1 };
      }
      var hit = findNode(state.fields, state.selectedKey);
      if (!hit) {
        return { parentKey: null, parentType: null, parentLabel: 'Raíz', afterIndex: state.fields.length - 1 };
      }
      var n = hit.node;
      var t = n.type || 'text';
      if (t === 'section' || t === 'repeater') {
        var len = (n.fields && n.fields.length) || 0;
        return {
          parentKey: n._bk,
          parentType: t,
          parentLabel: n.label || TYPE_LABELS[t],
          afterIndex: len - 1,
        };
      }
      var parent = hit.parent;
      var parentType = parent ? (parent.type || null) : null;
      var parentKey = parent ? parent._bk : null;
      var parentLabel = parent ? (parent.label || TYPE_LABELS[parentType] || 'Raíz') : 'Raíz';
      return {
        parentKey: parentKey,
        parentType: parentType,
        parentLabel: parentLabel,
        afterIndex: hit.index,
      };
    }

    function addFieldAtSelection(type) {
      var ctx = getInsertionContext();
      if (!isAllowedTypeIn(type, ctx.parentType)) {
        var why =
          ctx.parentType === 'section'
            ? 'No se permite una sección dentro de otra sección.'
            : 'En un repetidor solo se permiten campos simples (no secciones ni repetidores).';
        alert(why);
        announce(why);
        return;
      }
      addField(type, ctx.parentKey, { afterIndex: ctx.afterIndex });
    }

    function announce(msg) {
      if (!el.aria) return;
      el.aria.textContent = '';
      setTimeout(function () { el.aria.textContent = msg; }, 30);
    }

    function renderProps() {
      el.props.innerHTML = '';
      if (!state.selectedKey) {
        el.props.innerHTML = '<p class="text-muted small">Seleccione un campo en el lienzo.</p>';
        return;
      }
      var hit = findNode(state.fields, state.selectedKey);
      if (!hit) return;
      var n = hit.node;
      var t = n.type || 'text';

      var wrap = document.createElement('div');
      wrap.className = 'fb-props-panel';

      function addGroup(title) {
        var h = document.createElement('h6');
        h.textContent = title;
        wrap.appendChild(h);
      }

      function fieldRow(label, input) {
        var fg = document.createElement('div');
        fg.className = 'form-group';
        var l = document.createElement('label');
        l.textContent = label;
        fg.appendChild(l);
        fg.appendChild(input);
        wrap.appendChild(fg);
      }

      function mkInput(val, onchange) {
        var inp = document.createElement('input');
        inp.type = 'text';
        inp.className = 'form-control form-control-sm';
        inp.value = val != null ? val : '';
        inp.addEventListener('input', function () {
          onchange(inp.value);
        });
        return inp;
      }

      function mkCheckbox(checked, onchange) {
        var inp = document.createElement('input');
        inp.type = 'checkbox';
        inp.className = 'form-check-input';
        inp.checked = !!checked;
        inp.addEventListener('change', function () {
          onchange(inp.checked);
        });
        return inp;
      }

      addGroup('Campo seleccionado');
      if (t !== 'section' && t !== 'info') {
        var idInp = mkInput(n.id, function (v) {
          n.id = v.trim();
          syncHiddenJson();
          renderCanvas({ skipProps: true });
        });
        fieldRow('Id (clave en datos)', idInp);

        var autoId = document.createElement('button');
        autoId.type = 'button';
        autoId.className = 'btn btn-sm btn-outline-secondary mb-2';
        autoId.textContent = 'Generar id desde etiqueta';
        autoId.addEventListener('click', function () {
          n.id = slugify(n.label || 'campo');
          renderCanvas({ skipProps: true });
          renderProps();
        });
        wrap.appendChild(autoId);
      }

      var labInp = mkInput(n.label, function (v) {
        n.label = v;
        syncHiddenJson();
        renderCanvas({ skipProps: true });
      });
      fieldRow('Etiqueta', labInp);

      if (t === 'section') {
        var secHt = document.createElement('textarea');
        secHt.className = 'form-control form-control-sm';
        secHt.rows = 2;
        secHt.value = n.help_text || '';
        secHt.addEventListener('input', function () {
          var v = secHt.value || '';
          if (v) n.help_text = v;
          else delete n.help_text;
          syncHiddenJson();
        });
        fieldRow('Texto de ayuda', secHt);
      }

      if (t === 'info') {
        var contentTa = document.createElement('textarea');
        contentTa.className = 'form-control form-control-sm';
        contentTa.rows = 6;
        contentTa.placeholder = '**Importante:** texto en Markdown (negritas, listas, párrafos).';
        contentTa.value = n.content || '';
        contentTa.addEventListener('input', function () {
          n.content = contentTa.value;
          syncHiddenJson();
          renderCanvas({ skipProps: true });
        });
        fieldRow('Contenido (Markdown)', contentTa);

        var variantSel = document.createElement('select');
        variantSel.className = 'form-control form-control-sm';
        ;[
          ['plain', 'Texto simple'],
          ['info', 'Caja informativa (azul)'],
          ['warning', 'Advertencia (amarilla)'],
        ].forEach(function (pair) {
          var o = document.createElement('option');
          o.value = pair[0];
          o.textContent = pair[1];
          if ((n.variant || 'plain') === pair[0]) o.selected = true;
          variantSel.appendChild(o);
        });
        variantSel.addEventListener('change', function () {
          n.variant = variantSel.value;
          syncHiddenJson();
        });
        fieldRow('Estilo visual', variantSel);
      }

      if (t !== 'section' && t !== 'computed' && t !== 'info') {
        var reqWrap = document.createElement('div');
        reqWrap.className = 'form-check';
        var rq = mkCheckbox(!!n.required, function (v) {
          n.required = v;
          syncHiddenJson();
        });
        reqWrap.appendChild(rq);
        var l2 = document.createElement('label');
        l2.className = 'form-check-label';
        l2.textContent = ' Obligatorio';
        reqWrap.appendChild(l2);
        wrap.appendChild(reqWrap);

        var ht = document.createElement('textarea');
        ht.className = 'form-control form-control-sm';
        ht.rows = 2;
        ht.value = n.help_text || '';
        ht.addEventListener('input', function () {
          n.help_text = ht.value || '';
          syncHiddenJson();
        });
        fieldRow('Texto de ayuda', ht);
      }

      if (t === 'number') {
        var row = document.createElement('div');
        row.className = 'form-row';
        ;['min', 'max', 'step'].forEach(function (k) {
          var d = document.createElement('div');
          d.className = 'form-group col-4';
          var lab = document.createElement('label');
          lab.textContent = k;
          var inp = document.createElement('input');
          inp.type = 'text';
          inp.className = 'form-control form-control-sm';
          inp.value = n[k] != null ? n[k] : '';
          inp.addEventListener('input', function () {
            var v = inp.value.trim();
            if (v === '') delete n[k];
            else if (k === 'step') n[k] = v;
            else n[k] = parseFloat(v);
            syncHiddenJson();
          });
          d.appendChild(lab);
          d.appendChild(inp);
          row.appendChild(d);
        });
        wrap.appendChild(row);
      }

      if (t === 'text') {
        var mlRow = document.createElement('div');
        mlRow.className = 'form-check mb-2';
        var mlCb = mkCheckbox(!!n.multiline, function (on) {
          if (on) n.multiline = true;
          else {
            delete n.multiline;
            delete n.rows;
          }
          syncHiddenJson();
          renderProps();
        });
        mlRow.appendChild(mlCb);
        var mlLab = document.createElement('label');
        mlLab.className = 'form-check-label';
        mlLab.textContent = ' Entrada multilínea';
        mlRow.appendChild(mlLab);
        wrap.appendChild(mlRow);
        if (n.multiline) {
          var rowsInp = document.createElement('input');
          rowsInp.type = 'number';
          rowsInp.className = 'form-control form-control-sm';
          rowsInp.min = 2;
          rowsInp.max = 40;
          rowsInp.value = n.rows != null ? n.rows : 3;
          rowsInp.addEventListener('input', function () {
            var r = parseInt(rowsInp.value, 10);
            n.rows = !isNaN(r) && r >= 2 ? r : 3;
            syncHiddenJson();
          });
          fieldRow('Filas (altura)', rowsInp);
        }
      }

      if (t === 'select' || t === 'radio' || t === 'multiselect') {
        addGroup('Opciones');
        var optTable = document.createElement('table');
        optTable.className = 'table table-sm table-bordered small';
        function renderOpts() {
          optTable.innerHTML = '';
          n.options = n.options || [];
          n.options.forEach(function (opt, idx) {
            var tr = document.createElement('tr');
            var td1 = document.createElement('td');
            var td2 = document.createElement('td');
            var td3 = document.createElement('td');
            var td4 = document.createElement('td');
            var v1 = document.createElement('input');
            v1.className = 'form-control form-control-sm';
            v1.value = opt.value;
            v1.addEventListener('input', function () {
              opt.value = v1.value;
              syncHiddenJson();
            });
            var v2 = document.createElement('input');
            v2.className = 'form-control form-control-sm';
            v2.value = opt.label;
            v2.addEventListener('input', function () {
              opt.label = v2.value;
              syncHiddenJson();
            });
            var ord = document.createElement('div');
            ord.className = 'btn-group btn-group-sm';
            var up = document.createElement('button');
            up.type = 'button';
            up.className = 'btn btn-outline-secondary';
            up.textContent = '↑';
            up.addEventListener('click', function () {
              if (idx <= 0) return;
              var tmp = n.options[idx - 1];
              n.options[idx - 1] = n.options[idx];
              n.options[idx] = tmp;
              syncHiddenJson();
              renderOpts();
            });
            var dn = document.createElement('button');
            dn.type = 'button';
            dn.className = 'btn btn-outline-secondary';
            dn.textContent = '↓';
            dn.addEventListener('click', function () {
              if (idx >= n.options.length - 1) return;
              var tmp2 = n.options[idx + 1];
              n.options[idx + 1] = n.options[idx];
              n.options[idx] = tmp2;
              syncHiddenJson();
              renderOpts();
            });
            ord.appendChild(up);
            ord.appendChild(dn);
            var del = document.createElement('button');
            del.type = 'button';
            del.className = 'btn btn-sm btn-danger';
            del.textContent = '×';
            del.addEventListener('click', function () {
              n.options.splice(idx, 1);
              renderProps();
              syncHiddenJson();
            });
            td1.appendChild(v1);
            td2.appendChild(v2);
            td3.appendChild(ord);
            td4.appendChild(del);
            tr.appendChild(td1);
            tr.appendChild(td2);
            tr.appendChild(td3);
            tr.appendChild(td4);
            optTable.appendChild(tr);
          });
        }
        renderOpts();
        wrap.appendChild(optTable);
        var addOpt = document.createElement('button');
        addOpt.type = 'button';
        addOpt.className = 'btn btn-sm btn-outline-primary';
        addOpt.textContent = 'Añadir opción';
        addOpt.addEventListener('click', function () {
          n.options = n.options || [];
          n.options.push({ value: 'nuevo', label: 'Nuevo' });
          renderProps();
          syncHiddenJson();
        });
        wrap.appendChild(addOpt);
      }

      if (t === 'repeater') {
        var al = mkInput(n.add_label || '', function (v) {
          n.add_label = v;
          syncHiddenJson();
        });
        fieldRow('Texto del botón «agregar»', al);
        var rl = mkInput(n.remove_label || '', function (v) {
          n.remove_label = v;
          syncHiddenJson();
        });
        fieldRow('Texto del botón «eliminar»', rl);
      }

      if (t === 'computed') {
        var fo = document.createElement('textarea');
        fo.className = 'form-control form-control-sm';
        fo.rows = 3;
        fo.placeholder = 'Ej: peso_kg / (talla_m * talla_m)  o  imc';
        fo.value = n.formula || '';
        fo.addEventListener('input', function () {
          n.formula = fo.value;
          syncHiddenJson();
        });
        fieldRow('Fórmula', fo);
        var pr = document.createElement('input');
        pr.type = 'number';
        pr.className = 'form-control form-control-sm';
        pr.value = n.precision != null ? n.precision : 2;
        pr.addEventListener('input', function () {
          n.precision = parseInt(pr.value, 10) || 0;
          syncHiddenJson();
        });
        fieldRow('Decimales', pr);

        var cht = document.createElement('textarea');
        cht.className = 'form-control form-control-sm';
        cht.rows = 2;
        cht.value = n.help_text || '';
        cht.addEventListener('input', function () {
          var hv = cht.value || '';
          if (hv) n.help_text = hv;
          else delete n.help_text;
          syncHiddenJson();
        });
        fieldRow('Texto de ayuda', cht);

        addGroup('Dependencias (variables en la fórmula)');
        var deps = collectPriorIdsForComputedDeps(state.fields, n._bk);
        var depBox = document.createElement('div');
        deps.forEach(function (did) {
          var row = document.createElement('div');
          row.className = 'form-check';
          var cb = document.createElement('input');
          cb.type = 'checkbox';
          cb.className = 'form-check-input';
          cb.value = did;
          cb.checked = (n.depends_on || []).indexOf(did) !== -1;
          cb.addEventListener('change', function () {
            n.depends_on = n.depends_on || [];
            var ix = n.depends_on.indexOf(did);
            if (cb.checked && ix === -1) n.depends_on.push(did);
            if (!cb.checked && ix !== -1) n.depends_on.splice(ix, 1);
            syncHiddenJson();
          });
          var lb = document.createElement('label');
          lb.className = 'form-check-label';
          lb.textContent = ' ' + did;
          row.appendChild(cb);
          row.appendChild(lb);
          depBox.appendChild(row);
        });
        if (!deps.length)
          depBox.innerHTML = '<span class="text-muted small">Añada primero campos con id.</span>';
        wrap.appendChild(depBox);
      }

      /* visible_when */
      addGroup('Visibilidad condicional');
      var priors = [];
      priors = collectPriorFieldIdsDFS(state.fields, n._bk);

      var vwEn = mkCheckbox(!!n.visible_when, function (on) {
        if (!on) {
          delete n.visible_when;
        } else {
          n.visible_when = { field: priors[0] || '', op: 'equals', equals: '' };
        }
        syncHiddenJson();
        renderProps();
      });
      var vwRow = document.createElement('div');
      vwRow.className = 'form-check mb-2';
      vwRow.appendChild(vwEn);
      var vwLab = document.createElement('label');
      vwLab.className = 'form-check-label';
      vwLab.textContent = ' Mostrar solo si…';
      vwRow.appendChild(vwLab);
      wrap.appendChild(vwRow);

      if (n.visible_when) {
        var selF = document.createElement('select');
        selF.className = 'form-control form-control-sm';
        priors.forEach(function (pid) {
          var o = document.createElement('option');
          o.value = pid;
          o.textContent = pid;
          if (n.visible_when.field === pid) o.selected = true;
          selF.appendChild(o);
        });
        selF.addEventListener('change', function () {
          n.visible_when.field = selF.value;
          syncHiddenJson();
          rebuildVwValueControl();
        });
        fieldRow('Campo dependiente', selF);

        var selOp = document.createElement('select');
        selOp.className = 'form-control form-control-sm';
        ;[
          ['equals', 'Igual a'],
          ['not_equals', 'Distinto de'],
          ['contains', 'Contiene (texto o multiselect)'],
        ].forEach(function (pair) {
          var o = document.createElement('option');
          o.value = pair[0];
          o.textContent = pair[1];
          if ((n.visible_when.op || 'equals') === pair[0]) o.selected = true;
          selOp.appendChild(o);
        });
        selOp.addEventListener('change', function () {
          n.visible_when.op = selOp.value;
          syncHiddenJson();
          rebuildVwValueControl();
        });
        fieldRow('Condición', selOp);

        var valFg = document.createElement('div');
        valFg.className = 'form-group';
        var valLabEl = document.createElement('label');
        valLabEl.textContent = 'Valor esperado';
        valFg.appendChild(valLabEl);
        var valMount = document.createElement('div');
        valFg.appendChild(valMount);
        wrap.appendChild(valFg);

        function vwSetEquals(v) {
          n.visible_when.equals = v;
          if ('value' in n.visible_when) delete n.visible_when.value;
          syncHiddenJson();
        }

        function rebuildVwValueControl() {
          valMount.innerHTML = '';
          var fid = n.visible_when.field;
          var dep = findFieldById(state.fields, fid);
          var cur = n.visible_when.equals;
          if (cur === undefined && n.visible_when && 'value' in n.visible_when) {
            cur = n.visible_when.value;
          }

          if (!dep) {
            var inpF = mkInput(cur, vwSetEquals);
            valMount.appendChild(inpF);
          } else {
            var dt = dep.type || 'text';
            if (dt === 'boolean' || dt === 'checkbox') {
              var selB = document.createElement('select');
              selB.className = 'form-control form-control-sm';
              ;[
                ['true', 'Sí'],
                ['false', 'No'],
              ].forEach(function (p) {
                var o = document.createElement('option');
                o.value = p[0];
                o.textContent = p[1];
                selB.appendChild(o);
              });
              var isTrue =
                cur === true ||
                cur === 'true' ||
                cur === 1 ||
                cur === '1' ||
                cur === 'on' ||
                cur === 'On';
              selB.value = isTrue ? 'true' : 'false';
              selB.addEventListener('change', function () {
                vwSetEquals(selB.value === 'true');
              });
              valMount.appendChild(selB);
            } else if (
              (dt === 'select' || dt === 'radio' || dt === 'multiselect') &&
              dep.options &&
              dep.options.length
            ) {
              var selO = document.createElement('select');
              selO.className = 'form-control form-control-sm';
              dep.options.forEach(function (opt) {
                var o = document.createElement('option');
                o.value = opt.value;
                o.textContent = opt.label || opt.value;
                selO.appendChild(o);
              });
              if (cur !== undefined && cur !== null && cur !== '') {
                selO.value = String(cur);
              }
              selO.addEventListener('change', function () {
                vwSetEquals(selO.value);
              });
              valMount.appendChild(selO);
            } else if (dt === 'number') {
              var inN = document.createElement('input');
              inN.type = 'number';
              inN.className = 'form-control form-control-sm';
              inN.value = cur != null && cur !== '' ? String(cur) : '';
              inN.addEventListener('input', function () {
                var v = inN.value.trim();
                if (v === '') vwSetEquals('');
                else {
                  var x = parseFloat(v.replace(',', '.'));
                  if (isNaN(x)) vwSetEquals(v);
                  else vwSetEquals(Math.floor(x) === x ? parseInt(v, 10) : x);
                }
              });
              valMount.appendChild(inN);
            } else {
              var inpD = mkInput(cur, vwSetEquals);
              valMount.appendChild(inpD);
            }
          }

          var hint = document.createElement('p');
          hint.className = 'small text-muted mb-0';
          hint.textContent =
            'El valor se ajusta al tipo del campo dependiente (lista, número o sí/no). En «contiene» con multiselect, elija el value de la opción.';
          valMount.appendChild(hint);
        }

        rebuildVwValueControl();
      }

      el.props.appendChild(wrap);
    }

    /* Palette */
    if (el.palette) {
      el.palette.innerHTML = '';

      var searchWrap = document.createElement('div');
      searchWrap.className = 'fb-palette-search';
      var searchInp = document.createElement('input');
      searchInp.type = 'search';
      searchInp.className = 'form-control form-control-sm';
      searchInp.placeholder = 'Buscar tipo… (atajo: /)';
      searchInp.setAttribute('aria-label', 'Buscar tipo de campo');
      searchInp.id = 'fb-palette-search';
      searchWrap.appendChild(searchInp);
      el.paletteSearch = searchInp;
      el.palette.appendChild(searchWrap);

      var targetBox = document.createElement('div');
      targetBox.className = 'fb-palette-target';
      targetBox.setAttribute('aria-live', 'polite');
      el.paletteTarget = targetBox;
      el.palette.appendChild(targetBox);

      var rootRow = document.createElement('div');
      rootRow.className = 'form-check fb-palette-rootcheck';
      var rootCb = document.createElement('input');
      rootCb.type = 'checkbox';
      rootCb.className = 'form-check-input';
      rootCb.id = 'fb-palette-root-toggle';
      rootCb.addEventListener('change', function () {
        state.forceRoot = rootCb.checked;
        renderPaletteTarget();
      });
      var rootLab = document.createElement('label');
      rootLab.className = 'form-check-label small';
      rootLab.htmlFor = 'fb-palette-root-toggle';
      rootLab.textContent = ' Añadir siempre a raíz';
      rootRow.appendChild(rootCb);
      rootRow.appendChild(rootLab);
      el.paletteRootToggle = rootCb;
      el.palette.appendChild(rootRow);

      var sep = document.createElement('hr');
      sep.className = 'my-2';
      el.palette.appendChild(sep);

      Object.keys(TYPE_LABELS).forEach(function (type) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'btn btn-sm btn-outline-secondary fb-palette-btn';
        b.textContent = TYPE_LABELS[type];
        b.setAttribute('data-fb-type', type);
        b.setAttribute('aria-label', 'Añadir ' + TYPE_LABELS[type]);
        b.title = 'Añadir ' + TYPE_LABELS[type];
        b.addEventListener('click', function () {
          addFieldAtSelection(type);
        });
        el.palette.appendChild(b);
      });

      renderPaletteTarget();
      initPaletteSortable();
      bindPaletteSearch();
    }

    function bindPaletteSearch() {
      if (!el.paletteSearch) return;
      el.paletteSearch.addEventListener('input', function () {
        var q = (el.paletteSearch.value || '').trim().toLowerCase();
        el.palette.querySelectorAll('.fb-palette-btn').forEach(function (b) {
          var label = (b.textContent || '').toLowerCase();
          var match = !q || label.indexOf(q) !== -1;
          b.style.display = match ? '' : 'none';
        });
      });
      el.paletteSearch.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          var btn = el.palette.querySelector('.fb-palette-btn:not([style*="display: none"]):not(.fb-palette-btn-disabled)');
          if (btn) {
            var t = btn.getAttribute('data-fb-type');
            if (t) addFieldAtSelection(t);
            el.paletteSearch.value = '';
            el.paletteSearch.dispatchEvent(new Event('input'));
          }
        } else if (e.key === 'Escape') {
          e.preventDefault();
          el.paletteSearch.value = '';
          el.paletteSearch.dispatchEvent(new Event('input'));
          el.paletteSearch.blur();
        }
      });
    }

    function renderPaletteTarget() {
      if (!el.paletteTarget) return;
      var ctx = getInsertionContext();
      var icon = ctx.parentKey ? '↳' : '⌂';
      var nameSpan = ctx.parentKey ? ('«' + (ctx.parentLabel || '') + '»') : 'Raíz';
      el.paletteTarget.innerHTML =
        '<span class="fb-palette-target-icon">' + icon + '</span>' +
        '<span class="fb-palette-target-text">Añadiendo a: <strong>' +
        nameSpan.replace(/[<>&]/g, function (c) { return { '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]; }) +
        '</strong></span>';
      // Disabled state of palette buttons depending on parent type
      var btns = el.palette.querySelectorAll('.fb-palette-btn');
      btns.forEach(function (b) {
        var t = b.getAttribute('data-fb-type');
        var allowed = isAllowedTypeIn(t, ctx.parentType);
        if (allowed) {
          b.removeAttribute('disabled');
          b.classList.remove('fb-palette-btn-disabled');
          b.title = 'Añadir ' + TYPE_LABELS[t];
        } else {
          b.setAttribute('disabled', 'disabled');
          b.classList.add('fb-palette-btn-disabled');
          b.title = ctx.parentType === 'section'
            ? 'No se permite una sección dentro de otra'
            : 'No permitido dentro de un repetidor';
        }
      });
    }

    el.form.addEventListener('submit', function (e) {
      var errs = [];
      var warns = [];
      validateState(state.fields, errs, warns);
      if (errs.length) {
        e.preventDefault();
        alert('Revise el formulario:\n\n' + errs.slice(0, 8).join('\n'));
        return;
      }
      if (warns.length) {
        var msg = 'Aviso (no bloqueante):\n\n' + warns.slice(0, 6).join('\n') + '\n\n¿Continuar y guardar?';
        if (!confirm(msg)) {
          e.preventDefault();
          return;
        }
      }
      syncHiddenJson();
    });

    document.addEventListener('click', function (e) {
      if (e.target.closest('.fb-nested-addbar')) return;
      document.querySelectorAll('.fb-nested-menu').forEach(function (m) {
        m.setAttribute('hidden', 'hidden');
      });
    });

    function isTypingTarget(t) {
      if (!t) return false;
      var tag = (t.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return true;
      if (t.isContentEditable) return true;
      return false;
    }

    document.addEventListener('keydown', function (e) {
      // Esc: cancela drag o cierra menús.
      if (e.key === 'Escape') {
        if (document.body.classList.contains('fb-dragging')) {
          var fakeUp = new MouseEvent('mouseup', { bubbles: true, cancelable: true });
          document.dispatchEvent(fakeUp);
          document.body.classList.remove('fb-dragging');
          clearDropMarkers();
          announce('Arrastre cancelado.');
          return;
        }
        var open = document.querySelectorAll('.fb-nested-menu:not([hidden])');
        if (open.length) {
          open.forEach(function (m) { m.setAttribute('hidden', 'hidden'); });
        }
        return;
      }

      // "/" enfoca el buscador de la paleta cuando no estamos escribiendo.
      if (e.key === '/' && !isTypingTarget(e.target) && el.paletteSearch) {
        // Verificar que el editor esté visible (otherwise skip).
        if (rootEl.offsetParent !== null) {
          e.preventDefault();
          el.paletteSearch.focus();
          el.paletteSearch.select();
        }
        return;
      }

      // Shift + ↑ / ↓ : mover el card seleccionado entre niveles.
      if (e.shiftKey && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
        if (!state.selectedKey) return;
        if (isTypingTarget(e.target)) return;
        e.preventDefault();
        if (e.key === 'ArrowUp') moveOutOfParent(state.selectedKey);
        else moveIntoNextSibling(state.selectedKey);
      }
    });

    /**
     * Sube el nodo seleccionado un nivel: lo saca de su sección/repetidor
     * padre y lo coloca como hermano siguiente del padre.
     */
    function moveOutOfParent(key) {
      var hit = findNode(state.fields, key);
      if (!hit || !hit.parent) {
        announce('El campo ya está en el nivel raíz.');
        return;
      }
      var parent = hit.parent;
      var grandHit = findNode(state.fields, parent._bk);
      if (!grandHit) return;
      var node = hit.node;
      var draggedType = node.type || 'text';
      var grandParent = grandHit.parent;
      var grandParentType = grandParent ? (grandParent.type || null) : null;
      if (!isAllowedTypeIn(draggedType, grandParentType)) {
        announce('No se puede subir el nivel: el contenedor superior no admite este tipo.');
        return;
      }
      hit.list.splice(hit.index, 1);
      grandHit.list.splice(grandHit.index + 1, 0, node);
      renderCanvas();
      announce('Movido un nivel hacia arriba.');
    }

    /**
     * Baja el nodo seleccionado un nivel: lo mete dentro de la siguiente
     * sección/repetidor hermana (si existe).
     */
    function moveIntoNextSibling(key) {
      var hit = findNode(state.fields, key);
      if (!hit) return;
      var siblings = hit.list;
      var nextContainer = null;
      for (var i = hit.index + 1; i < siblings.length; i++) {
        var s = siblings[i];
        var st = s.type || '';
        if (st === 'section' || st === 'repeater') { nextContainer = s; break; }
      }
      if (!nextContainer) {
        announce('No hay sección o repetidor hermano debajo para anidar.');
        return;
      }
      var node = hit.node;
      var draggedType = node.type || 'text';
      if (!isAllowedTypeIn(draggedType, nextContainer.type)) {
        announce('Tipo no permitido dentro del contenedor destino.');
        return;
      }
      hit.list.splice(hit.index, 1);
      nextContainer.fields = nextContainer.fields || [];
      nextContainer.fields.unshift(node);
      renderCanvas();
      announce('Movido dentro de «' + (nextContainer.label || '') + '».');
    }

    // Eliminar un campo de los repetidores
    function removeFieldFromRepeaters(key) {
      var hit = findNode(state.fields, key);
      if (!hit) return;
      var node = hit.node;
      var parent = hit.parent;
      if (parent.type === 'repeater') {
        parent.fields = parent.fields.filter(function (f) { return f._bk !== key; });
      }
      renderCanvas();
      announce('Campo eliminado del repetidor.');
    }

    /* Preview tab */
    var previewBtn = rootEl.querySelector('[data-fb-refresh-preview]');
    if (previewBtn) {
      previewBtn.addEventListener('click', function () {
        if (!previewUrl) return;
        var errs = [];
        validateState(state.fields, errs, []);
        if (errs.length) {
          alert('Corrija errores antes de previsualizar:\n' + errs.slice(0, 6).join('\n'));
          return;
        }
        var fd = new FormData();
        fd.append('csrfmiddlewaretoken', csrf);
        fd.append('campos_json', el.hiddenJson.value);
        var tit = rootEl.querySelector('input[name="nombre"]');
        fd.append('titulo_preview', tit ? tit.value : 'Vista previa');
        fetch(previewUrl, { method: 'POST', body: fd, credentials: 'same-origin' })
          .then(function (r) {
            return r.json();
          })
          .then(function (data) {
            if (!data.ok) {
              alert(data.error || 'Error en vista previa');
              return;
            }
            el.preview.innerHTML = data.html;
            initVisibilityAndRepeater(el.preview);
          })
          .catch(function () {
            alert('No se pudo cargar la vista previa.');
          });
      });
    }

    renderCanvas();
  };

  global.FormBuilder = FormBuilder;
})(typeof window !== 'undefined' ? window : this);
