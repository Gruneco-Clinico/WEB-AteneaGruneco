/**
 * Helpers UI del dashboard RecuérdaMe (filtros de tabla + panel de personas).
 */
(function (global) {
  "use strict";

  function norm(v) {
    return String(v == null ? "" : v)
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  /**
   * root: contenedor con [data-filter-root]
   * Filas: [data-filter-row] con data-* attributes.
   * Inputs: [data-filter-key="campo"] (text/select)
   */
  function initTableFilters(root) {
    if (!root) return;
    const rows = Array.from(root.querySelectorAll("[data-filter-row]"));
    const controls = Array.from(root.querySelectorAll("[data-filter-key]"));
    const counter = root.querySelector("[data-filter-count]");

    function apply() {
      const rules = controls.map((el) => ({
        key: el.getAttribute("data-filter-key"),
        value: norm(el.value),
        mode: el.getAttribute("data-filter-mode") || "contains",
      }));
      let visible = 0;
      rows.forEach((row) => {
        let ok = true;
        for (const rule of rules) {
          if (!rule.value) continue;
          const cell = norm(row.getAttribute("data-" + rule.key) || "");
          if (rule.mode === "exact") {
            if (cell !== rule.value) {
              ok = false;
              break;
            }
          } else if (cell.indexOf(rule.value) === -1) {
            ok = false;
            break;
          }
        }
        row.style.display = ok ? "" : "none";
        if (ok) visible += 1;
      });
      if (counter) {
        counter.textContent = visible + " / " + rows.length;
      }
    }

    controls.forEach((el) => {
      el.addEventListener("input", apply);
      el.addEventListener("change", apply);
    });
    apply();
  }

  function renderPersonList(container, personas, titulo) {
    if (!container) return;
    const list = personas || [];
    const head =
      '<div class="d-flex justify-content-between align-items-center mb-2">' +
      "<strong>" +
      (titulo || "Personas") +
      "</strong>" +
      '<span class="badge badge-primary">' +
      list.length +
      "</span></div>";
    if (!list.length) {
      container.innerHTML =
        head +
        '<p class="text-muted small mb-0">Sin person_id para esta selección.</p>';
      return;
    }
    const items = list
      .map(function (p) {
        const badge = p.identificado
          ? '<span class="badge badge-success mr-1">id.</span>'
          : '<span class="badge badge-secondary mr-1">anon</span>';
        const pid = p.person_id
          ? '<code class="small text-muted">' +
            String(p.person_id).slice(0, 12) +
            (p.person_id.length > 12 ? "…" : "") +
            "</code>"
          : "";
        return (
          '<li class="mb-1">' +
          badge +
          '<span class="text-break">' +
          (p.etiqueta || "—") +
          "</span> " +
          pid +
          "</li>"
        );
      })
      .join("");
    container.innerHTML = head + '<ul class="pl-3 mb-0 small">' + items + "</ul>";
  }

  function dateKeyFromPlotly(point) {
    if (!point) return "";
    const x = point.x;
    if (typeof x === "string") return x.slice(0, 10);
    if (x instanceof Date) return x.toISOString().slice(0, 10);
    return String(x || "").slice(0, 10);
  }

  function hourKeyFromPlotly(point) {
    if (!point) return "";
    const x = String(point.x || "");
    // "10:00" o "10"
    const m = x.match(/^(\d{1,2})/);
    if (!m) return "";
    return String(m[1]).padStart(2, "0");
  }

  global.RecuerdameDash = {
    initTableFilters: initTableFilters,
    renderPersonList: renderPersonList,
    dateKeyFromPlotly: dateKeyFromPlotly,
    hourKeyFromPlotly: hourKeyFromPlotly,
  };
})(window);
