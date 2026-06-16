# ATENEA — Frontend Cleanup Report (Phase 1)

**Fecha:** 2026-02-21  
**Objetivo:** Identificar archivos frontend no utilizados para liberar espacio de forma segura e incremental.  
**Alcance:** `apps/static/`, `staticfiles/`, `core/staticfiles/`, templates (solo lectura)  
**No se toca:** PDFs usados en lógica clínica, templates activos, scoring, backend.

---

## RESUMEN EJECUTIVO

| Categoría | Espacio recuperable | Archivos |
|-----------|-------------------|----------|
| Directorios `collectstatic` duplicados | **~49.3 MB** | ~6,131 |
| Vendor libraries no referenciadas | **~7.7 MB** | ~1,000+ |
| SCSS (fuentes de build, no se usan en runtime) | **~604 KB** | 293 |
| CSS bootstrap standalone (no referenciado) | **~464 KB** | 6 |
| CSS artefactos de build (map, min) | **~1,440 KB** | 2 |
| JS componentes no referenciados | **~103 KB** | 26 |
| Imágenes no referenciadas | **~1.98 MB** | 14 |
| PDF no referenciado | **~246 KB** | 1 |
| Build tools no necesarios en producción | **~4 KB** | 2 |
| **TOTAL ESTIMADO** | **~61.8 MB** | **~7,475+** |

---

## PASO 0 — DIRECTORIOS DUPLICADOS DE `collectstatic`

### Hallazgo crítico

Existen **3 copias** de los archivos estáticos:

| Directorio | Tamaño | Archivos | Rol |
|------------|--------|----------|-----|
| `apps/static/` | 27 MB | 2,947 | **FUENTE** (`STATICFILES_DIRS`) |
| `staticfiles/` | 28.1 MB | 3,077 | **OUTPUT** (`STATIC_ROOT` = `collectstatic`) |
| `core/staticfiles/` | 21.2 MB | 3,054 | **HUÉRFANO** (no es `STATIC_ROOT`, no se usa) |

**Configuración en `settings.py`:**
```python
CORE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # = raíz del proyecto
STATIC_ROOT = os.path.join(CORE_DIR, "staticfiles")       # → /staticfiles/
STATICFILES_DIRS = (os.path.join(CORE_DIR, "apps/static"),)  # → /apps/static/
```

### Recomendación

| Acción | Directorio | Justificación |
|--------|-----------|---------------|
| **ELIMINAR** | `core/staticfiles/` (21.2 MB) | No es el `STATIC_ROOT`. Copia obsoleta. No se referencia en settings. |
| **REGENERABLE** | `staticfiles/` (28.1 MB) | Es output de `collectstatic`. Se regenera con `python manage.py collectstatic`. Puede excluirse de Git con `.gitignore`. |

> ⚠️ **`staticfiles/` NO se debe eliminar del servidor** si WhiteNoise sirve desde ahí. Pero sí se puede excluir de Git y regenerar en deploy.

---

## PASO 1 — VENDOR LIBRARIES NO REFERENCIADAS (7.7 MB)

Las siguientes librerías existen en `apps/static/assets/vendor/` pero **no se cargan en ningún template ni vista**:

| Biblioteca | Tamaño | Archivos | Razón de no uso |
|-----------|--------|----------|-----------------|
| `moment/` | 1,244.6 KB | 133 | No referenciado. CDN de FullCalendar incluye su propio locale. |
| `jekyll/` | 1,152.2 KB | 176 | Herramienta de generación estática. Resto de scaffolding AppSeed. |
| `font-awesome/` (legacy) | 1,093.4 KB | 8 | Duplicado. Se usa `@fortawesome/fontawesome-free/` en su lugar. |
| `fullcalendar/` (local) | 674.4 KB | 78 | Se usa vía CDN (`cdn.jsdelivr.net/npm/fullcalendar@6.1.8`). |
| `prismjs/` | 557.6 KB | 253 | Resaltador de sintaxis. No hay código que mostrar en ATENEA. |
| `quill/` | 579.2 KB | 5 | Editor de texto enriquecido. No se usa en ningún formulario. |
| `chart.js/` (local) | 393.8 KB | 4 | Se usa vía CDN (`cdn.jsdelivr.net/npm/chart.js`). |
| `dropzone/` | 356.2 KB | 8 | Drag & drop upload. No hay upload en ATENEA. |
| `moment.min.js` (archivo suelto) | 328.7 KB | 1 | Duplicado de `moment/`. No referenciado. |
| `lavalamp/` | 219.6 KB | 9 | Efecto de navegación. No se usa. |
| `select2/` | 217.8 KB | 63 | Select mejorado. No referenciado en templates. |
| `bootstrap-datepicker/` | 154.5 KB | 88 | No cargado directamente. Si se usó, se reemplazó. |
| `datatables.net/` + variantes (6 dirs) | 254.7 KB | 17 | Tablas avanzadas. No se usa. |
| `sweetalert2/` | 126.6 KB | 3 | Alertas estilizadas. No referenciado. |
| `jvectormap-next/` | 98.2 KB | 4 | Mapas vectoriales. No hay mapas en ATENEA. |
| `bootstrap-datetimepicker.js` (suelto) | 90.9 KB | 1 | Archivo suelto sin carpeta. No referenciado. |
| `animate.css/` (local) | 85.1 KB | 82 | Se usa vía CDN en `General_Medicamentos.html`. Copia local innecesaria. |
| `bootstrap-tagsinput/` | 65.9 KB | 5 | Tags input. No se usa. |
| `holderjs/` | 32 KB | 2 | Placeholder de imágenes. No se usa. |
| `bootstrap-rtl/` | 32.2 KB | 1 | Right-to-left. No aplica (español). |
| `nouislider/` (vendor copy) | 25.3 KB | 2 | Slider. No referenciado. |
| `minimatch/` | 25.7 KB | 1 | Util Node.js. No aplica en browser. |
| `onscreen/` | 18.2 KB | 2 | Detección on-screen. No se usa. |
| `list.js/` | 17.7 KB | 1 | Filtrado de listas. No se usa. |
| `clipboard/` | 10.5 KB | 1 | Copiar al portapapeles. No referenciado. |
| `bootstrap-notify/` | 7.7 KB | 1 | Notificaciones. No referenciado. |
| `headroom.js/` | 6.5 KB | 3 | Auto-ocultar header. No se usa. |
| `anchor-js/` | 5.7 KB | 1 | Anchor links. No se usa. |
| `gulp-copy/` | 4.2 KB | 2 | Plugin Gulp. No aplica en runtime. |
| `js-cookie/` | — | — | **SÍ SE USA** (en `scripts.html`). **NO MOVER.** |
| `sudo/` | 2.2 KB | 1 | Desconocido. No referenciado. |

### ✅ Acción recomendada
```bash
# Dentro de apps/static/assets/vendor/, mover TODO excepto:
# - @fortawesome/     (SÍ se usa)
# - nucleo/           (SÍ se usa)
# - jquery/           (SÍ se usa)
# - bootstrap/        (SÍ se usa)
# - js-cookie/        (SÍ se usa)
# - jquery.scrollbar/ (SÍ se usa)
# - jquery-scroll-lock/ (SÍ se usa)
```

---

## PASO 2 — SCSS (604 KB, 293 archivos)

**Ruta:** `apps/static/assets/scss/`

Los archivos SCSS son **fuentes de compilación** para generar `argon.css`. No se sirven ni se referencian en runtime. Son necesarios **solo si se planea personalizar estilos y recompilar**.

| Acción | Justificación |
|--------|---------------|
| **Archivar a `backup_frontend/`** | No se usan en runtime. Si no se va a personalizar el tema Argon, son innecesarios. |
| **Mantener si se planea personalizar CSS** | Solo relevantes si se usa el pipeline Gulp. |

---

## PASO 3 — CSS NO REFERENCIADO (1.9 MB)

| Archivo | Tamaño | Acción | Razón |
|---------|--------|--------|-------|
| `css/bootstrap/bootstrap.css` | ~150 KB | Eliminar | Bootstrap se carga vía CDN o vendor bundle. No referenciado. |
| `css/bootstrap/bootstrap.min.css` | ~120 KB | Eliminar | Ídem. |
| `css/bootstrap/bootstrap-grid.css` | ~65 KB | Eliminar | No referenciado. |
| `css/bootstrap/bootstrap-grid.min.css` | ~45 KB | Eliminar | No referenciado. |
| `css/bootstrap/bootstrap-reboot.css` | ~45 KB | Eliminar | No referenciado. |
| `css/bootstrap/bootstrap-reboot.min.css` | ~40 KB | Eliminar | No referenciado. |
| `css/argon.css.map` | 1,092 KB | Eliminar | Sourcemap de desarrollo. No necesario en producción. |
| `css/argon.min.css` | 348 KB | Eliminar | Solo se usa `argon.css` (no minificado) en templates. |

---

## PASO 4 — JS NO REFERENCIADO (~103 KB)

Estos archivos existen en `apps/static/assets/js/` pero no son cargados por ningún template. `argon.js` es autocontenido y no los importa.

| Archivo | Tamaño | Acción |
|---------|--------|--------|
| `js/argon.min.js` | 11.3 KB | Eliminar — se usa `argon.js` |
| `js/components/charts/chart-bars.js` + `.min.js` | ~3 KB | Eliminar |
| `js/components/charts/chart-line.js` + `.min.js` | ~3 KB | Eliminar |
| `js/components/init/chart-init.js` + `.min.js` | ~4 KB | Eliminar |
| `js/components/init/copy-icon.js` + `.min.js` | ~2 KB | Eliminar |
| `js/components/init/navbar.js` + `.min.js` | ~2 KB | Eliminar |
| `js/components/init/popover.js` + `.min.js` | ~2 KB | Eliminar |
| `js/components/init/scroll-to.js` + `.min.js` | ~2 KB | Eliminar |
| `js/components/init/tooltip.js` + `.min.js` | ~2 KB | Eliminar |
| `js/components/custom/form-control.js` + `.min.js` | ~3 KB | Eliminar |
| `js/components/maps/maps-default.js` + `.min.js` | ~2 KB | Eliminar |
| `js/components/vendor/bootstrap-datepicker.js` + `.min.js` | ~8 KB | Eliminar |
| `js/components/vendor/nouislider.js` + `.min.js` | ~4 KB | Eliminar |
| `js/components/vendor/scrollbar.js` + `.min.js` | ~4 KB | Eliminar |
| `js/components/dinamicForm/antecedentes-editor.js` | ~2 KB | Eliminar — no referenciado en ningún archivo |

> **MANTENER:** `argon.js`, `d-form.js`, `dForm.js` — SÍ se cargan en templates.

---

## PASO 5 — IMÁGENES NO REFERENCIADAS (~1.98 MB)

| Archivo | Tamaño | Acción | Nota |
|---------|--------|--------|------|
| `img/brand/Banner_miembros.jpg` | 1,383.8 KB | Archivar | Imagen grande. Podría usarse en futuro marketing. |
| `img/brand/Principios.jpg` | 187.5 KB | Archivar | Contenido institucional. |
| `img/brand/Logo_GRUNECO_Fondo_Blanco.png` | 176.8 KB | Archivar | Variante del logo. No referenciada actualmente. |
| `img/theme/GRUNECO_logo.png` | 176.8 KB | Archivar | Variante del logo. |
| `img/theme/imagen_2.png` | 54.7 KB | Archivar | Imagen genérica sin referencia. |
| `img/theme/OIP.jpeg` | 15 KB | Eliminar | Nombre genérico (descarga de internet). No referenciado. |
| `img/brand/favicon.ico` | 15 KB | Eliminar | No referenciado. Se usa `favico.png` → `favicon.png` pattern. |
| `img/help_icons/hipertrofiacornetesnasales.jpg` | 3.7 KB | Archivar | Icono clínico. Podría agregarse a examen futuro. |
| `img/help_icons/hipertrofiauvula.jpg` | 5 KB | Archivar | Icono clínico. Podría agregarse a examen futuro. |
| `img/help_icons/desviacionsepto.png` | 6.8 KB | Archivar | Icono clínico. Podría agregarse a examen futuro. |
| `img/icons/common/github.svg` | 2.1 KB | Eliminar | Icono de login social (AppSeed boilerplate). No se usa. |
| `img/icons/common/google.svg` | 2.2 KB | Eliminar | Icono de login social (AppSeed boilerplate). No se usa. |
| `img/brand/favico.png` | 1.6 KB | **⚠️ REVISAR** | Templates referencian `favicon.png` que NO existe. ¿Debería renombrarse? |
| `img/brand/favicon-16x16.png` | 0.7 KB | Eliminar | No referenciado. |

---

## PASO 6 — PDF NO REFERENCIADO (~246 KB)

| Archivo | Tamaño | Acción | Nota |
|---------|--------|--------|------|
| `pdfs/CI_ProyectoSueno.pdf` | 245.8 KB | Archivar | Consentimiento informado del proyecto Sueño. No se referencia en código pero podría necesitarse. |
| `pdfs/CONSENTIMIENTOINFORMADOESTUDIANTES.pdf` | ~275 KB | **MANTENER** | Referenciado en `views.py` como adjunto de email. |

---

## PASO 7 — BUILD TOOLS NO NECESARIOS EN PRODUCCIÓN

| Archivo | Tamaño | Acción | Razón |
|---------|--------|--------|-------|
| `apps/static/assets/gulpfile.js` | 1.6 KB | Archivar | Pipeline de build para SCSS. No se ejecuta en producción. |
| `apps/static/assets/package.json` | 2.1 KB | Archivar | Dependencias npm para Gulp. No aplica en runtime. |

---

## PASO 8 — OTROS ARCHIVOS DEL PROYECTO (no frontend, pero candidatos)

| Archivo | Tamaño | Acción | Razón |
|---------|--------|--------|-------|
| `db.sqlite3` | 128 KB | **Eliminar** | Base de datos SQLite legacy. La app usa MariaDB. |
| `Atenea.sql` | 103.6 KB | **Archivar** | Dump SQL. No debe estar en el repo; mover a backups. |

---

## BUGS ENCONTRADOS DURANTE EL ANÁLISIS

| # | Bug | Ubicación | Impacto |
|---|-----|-----------|---------|
| B1 | **`favicon.png` no existe en disco** | Referenciado en `base.html`, `base_public.html`, `base_theme.html`, `base-fullscreen.html` | Icono de pestaña no carga. Existe `favico.png` — probablemente debería renombrarse. |
| B2 | **`logo-udea.png` no existe en disco** | Referenciado en `login.html` línea ~707 | Imagen rota en página de login. |
| B3 | **Placeholder Font Awesome kit** | `ads.html` línea ~262: `your-fontawesome-kit.js` | Script fallido; probablemente error de template AppSeed. |
| B4 | **CSS syntax roto en `ads.html`** | Línea ~74: `background: white;href="/static/..."` | `href` dentro de propiedad CSS. Imagen no se muestra. |
| B5 | **`argon.css` cargado 2 veces** | `base_theme.html` líneas 20 y 22 | Doble carga de CSS (334 KB desperdiciados por request). |
| B6 | **Bootstrap JS cargado 2 veces** | `scripts.html`: local `vendor/bootstrap` + CDN `bootstrap@5.3.2` | Conflicto potencial; definitivamente desperdicio. |

---

## PLAN DE EJECUCIÓN INCREMENTAL Y REVERSIBLE

### Fase A — Preparación (Riesgo: NULO)
```powershell
# 1. Crear carpeta de backup
New-Item -ItemType Directory -Path "backup_frontend" -Force
New-Item -ItemType Directory -Path "backup_frontend\vendor" -Force
New-Item -ItemType Directory -Path "backup_frontend\scss" -Force
New-Item -ItemType Directory -Path "backup_frontend\css" -Force
New-Item -ItemType Directory -Path "backup_frontend\js" -Force
New-Item -ItemType Directory -Path "backup_frontend\img" -Force
New-Item -ItemType Directory -Path "backup_frontend\pdfs" -Force
New-Item -ItemType Directory -Path "backup_frontend\build_tools" -Force
New-Item -ItemType Directory -Path "backup_frontend\collectstatic" -Force
New-Item -ItemType Directory -Path "backup_frontend\misc" -Force
```

### Fase B — Mover `core/staticfiles/` (Ahorro: ~21.2 MB)
```powershell
# Directorio huérfano. No es STATIC_ROOT. Seguro de mover.
Move-Item "core\staticfiles" "backup_frontend\collectstatic\core_staticfiles"
```
**Verificación:** Reiniciar servidor → confirmar que el sitio carga correctamente.

### Fase C — Mover vendor libraries no referenciadas (Ahorro: ~7.7 MB)
```powershell
$vendorsToMove = @(
    "anchor-js","animate.css","bootstrap-datepicker","bootstrap-notify",
    "bootstrap-rtl","bootstrap-tagsinput","chart.js","clipboard",
    "datatables.net","datatables.net-bs4","datatables.net-buttons",
    "datatables.net-buttons-bs4","datatables.net-responsive-bs4",
    "datatables.net-select","datatables.net-select-bs4","dropzone",
    "font-awesome","fullcalendar","gulp-copy","headroom.js","holderjs",
    "jekyll","jvectormap-next","lavalamp","list.js","minimatch","moment",
    "nouislider","onscreen","prismjs","quill","select2","sudo","sweetalert2"
)
$vBase = "apps\static\assets\vendor"
foreach($v in $vendorsToMove) {
    $src = Join-Path $vBase $v
    if(Test-Path $src) { Move-Item $src "backup_frontend\vendor\$v" }
}
# Archivos sueltos
Move-Item "$vBase\moment.min.js" "backup_frontend\vendor\moment.min.js"
Move-Item "$vBase\bootstrap-datetimepicker.js" "backup_frontend\vendor\bootstrap-datetimepicker.js"
```
**Verificación:** Navegar por todas las páginas principales. Revisar consola del navegador por errores 404.

### Fase D — Mover SCSS y build tools (Ahorro: ~608 KB)
```powershell
Move-Item "apps\static\assets\scss" "backup_frontend\scss"
Move-Item "apps\static\assets\gulpfile.js" "backup_frontend\build_tools\gulpfile.js"
Move-Item "apps\static\assets\package.json" "backup_frontend\build_tools\package.json"
```

### Fase E — Mover CSS no referenciado (Ahorro: ~1.9 MB)
```powershell
Move-Item "apps\static\assets\css\bootstrap" "backup_frontend\css\bootstrap"
Move-Item "apps\static\assets\css\argon.css.map" "backup_frontend\css\argon.css.map"
Move-Item "apps\static\assets\css\argon.min.css" "backup_frontend\css\argon.min.css"
```

### Fase F — Mover JS no referenciado (Ahorro: ~103 KB)
```powershell
Move-Item "apps\static\assets\js\argon.min.js" "backup_frontend\js\argon.min.js"
Move-Item "apps\static\assets\js\components\charts" "backup_frontend\js\charts"
Move-Item "apps\static\assets\js\components\init" "backup_frontend\js\init"
Move-Item "apps\static\assets\js\components\custom" "backup_frontend\js\custom"
Move-Item "apps\static\assets\js\components\maps" "backup_frontend\js\maps"
Move-Item "apps\static\assets\js\components\vendor" "backup_frontend\js\vendor_components"
Move-Item "apps\static\assets\js\components\dinamicForm\antecedentes-editor.js" "backup_frontend\js\antecedentes-editor.js"
```

### Fase G — Mover imágenes no referenciadas (Ahorro: ~1.98 MB)
```powershell
$imagesToMove = @(
    "brand\favicon.ico","brand\favicon-16x16.png",
    "brand\Logo_GRUNECO_Fondo_Blanco.png","brand\Banner_miembros.jpg",
    "brand\Principios.jpg","theme\OIP.jpeg","theme\imagen_2.png",
    "theme\GRUNECO_logo.png","icons\common\github.svg",
    "icons\common\google.svg","help_icons\hipertrofiauvula.jpg",
    "help_icons\hipertrofiacornetesnasales.jpg","help_icons\desviacionsepto.png"
)
$imgBase = "apps\static\assets\img"
foreach($i in $imagesToMove) {
    $src = Join-Path $imgBase $i
    $dest = "backup_frontend\img\$(Split-Path $i -Leaf)"
    if(Test-Path $src) { Move-Item $src $dest }
}
```
> **NO mover `favico.png`** — puede ser la fuente del favicon aunque el nombre no coincida con el template.

### Fase H — Mover PDF no referenciado y archivos misc
```powershell
Move-Item "apps\static\assets\pdfs\CI_ProyectoSueno.pdf" "backup_frontend\pdfs\CI_ProyectoSueno.pdf"
Move-Item "db.sqlite3" "backup_frontend\misc\db.sqlite3"
Move-Item "Atenea.sql" "backup_frontend\misc\Atenea.sql"
```

### Fase I — Regenerar `staticfiles/` (post-limpieza)
```powershell
python manage.py collectstatic --clear --noinput
```
Esto regenera `staticfiles/` solo con los archivos que permanecen en `apps/static/`.

---

## RESUMEN DE ARCHIVOS QUE SE MANTIENEN

### `apps/static/assets/vendor/` — Solo quedan:
- `@fortawesome/fontawesome-free/` (7.4 MB) — Font Awesome, referenciado en 4 layouts
- `nucleo/` (189 KB) — Nucleo icons, referenciado en 4 layouts
- `jquery/` (165 KB) — jQuery, referenciado en `scripts.html`
- `bootstrap/` (347 KB) — Bootstrap JS, referenciado en `scripts.html`
- `js-cookie/` (4 KB) — Cookies, referenciado en `scripts.html`
- `jquery.scrollbar/` (54 KB) — Scrollbar, referenciado en `scripts.html`
- `jquery-scroll-lock/` (4.5 KB) — Scroll lock, referenciado en `scripts.html`

### `apps/static/assets/css/` — Solo queda:
- `argon.css` (334 KB) — El CSS principal, referenciado en todos los layouts

### `apps/static/assets/js/` — Solo queda:
- `argon.js` (22.3 KB) — JS principal, referenciado en scripts y base templates
- `components/dinamicForm/d-form.js` (4.3 KB) — Formularios dinámicos activos
- `components/dinamicForm/dForm.js` (3.7 KB) — Formularios dinámicos activos

### `apps/static/assets/img/` — Todo lo referenciado en templates
### `apps/static/assets/pdfs/` — Solo `CONSENTIMIENTOINFORMADOESTUDIANTES.pdf`
### `apps/static/assets/fonts/nucleo/` — 5 archivos de fuente Nucleo Icons

---

## PRÓXIMAS MEJORAS SUGERIDAS (fuera del alcance de esta fase)

1. **Corregir favicon:** Renombrar `favico.png` → `favicon.png` o actualizar los templates.
2. **Eliminar carga duplicada de `argon.css`** en `base_theme.html`.
3. **Eliminar carga duplicada de Bootstrap JS** en `scripts.html` (elegir CDN o local, no ambos).
4. **Investigar `@fortawesome`:** Con 7.4 MB y 1,589 archivos, es el vendor más pesado. Considerar:
   - Usar solo la versión CSS/webfont (eliminar SVGs individuales)
   - O migrar completamente a CDN (ya se usa CDN en algunos templates)
5. **Agregar `.gitignore` para `staticfiles/`** — es output regenerable.
6. **Corregir `logo-udea.png`** — imagen faltante en login.

---

*Fin del reporte de limpieza frontend.*
