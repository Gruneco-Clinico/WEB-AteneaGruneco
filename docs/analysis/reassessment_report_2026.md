# ATENEA GRUNECO — Full Technical Re-Assessment 2026

**Date:** 2026-03-02  
**Scope:** Full architectural, security, performance, and compliance audit  
**Codebase snapshot:** Current `main` branch as of assessment date  
**Assessor posture:** Objective diagnosis — no redesign proposed

---

## Executive Summary

| Dimension | Rating |
|-----------|--------|
| **Overall system maturity** | Early-production — functional but structurally fragile |
| **Technical debt level** | **Moderate** — concentrated in model layer and view duplication |
| **Production risk level** | **HIGH** — single-worker Gunicorn, blocking HTTP calls in request cycle, no caching, no pagination |
| **Compliance risk level** | **HIGH** — clinical data exposed on public endpoints without audit trail, no data-at-rest encryption strategy, no formal RBAC |

The system has evolved positively since initial deployment. The monolithic `models.py` and `views.py` have been split into domain-specific modules under `apps/home/models/` and `apps/home/views/`. Security hardening was added (HSTS, secure cookies, CSRF trusted origins, rate-limiting middleware). However, structural issues remain: a single Django app (`apps.home`) contains the entire domain; the authorization model is binary (superuser vs. authenticated); several files exceed 1000 lines; and clinical data flows through public endpoints with minimal access control.

---

## 1. Architecture

### 1.1 Strengths

- **Module split executed.** Models split into 9 files (`patient.py`, `visit.py`, `project.py`, `scheduling.py`, `results_sleep.py`, `results_anosognosia.py`, `results_general.py`, `analytics.py`). Views split into 13 files. This is a meaningful improvement over a monolithic layout.
- **Domain-oriented naming.** File names reflect clinical domains (sleep, anosognosia, general exams, scheduling), aiding developer orientation.
- **Centralized re-exports.** `models/__init__.py` and `views/__init__.py` use wildcard imports with explicit `__all__`, maintaining backward compatibility with `urls.py`.
- **Middleware layer present.** Custom `RateLimitMiddleware` demonstrates awareness of public-endpoint abuse vectors.
- **Django 5.0.6** in use — a recent LTS-track release.

### 1.2 Weaknesses

| Issue | Severity | Impact |
|-------|----------|--------|
| **Single app contains entire domain** — all models, views, forms, templates live under `apps.home` | [MEDIUM] | Makes independent deployment, testing, and team ownership impossible. Any migration touches the single migration chain. |
| **Wildcard re-exports** (`from .module import *`) in `__init__.py` for both models and views | [LOW] | Namespace pollution, harder to trace imports, risk of name collisions as model count grows (currently ~90 exported names). |
| **No service layer.** Business logic lives in views (`firmar_visita` sends emails, generates PDFs, updates state) and model `save()` overrides (`Visita.save()` generates patient codes). | [MEDIUM] | Untestable without HTTP request context. Tightly couples persistence with side effects. |
| **URL routing monolith** — 358-line `urls.py` with ~80 routes, all flat | [LOW] | No URL namespacing. Difficult to reason about public vs. protected endpoints at a glance. |
| **`_old` files retained** — `models_old.py` (3300+ lines), `views_old.py`, `forms_old.py` remain in the codebase | [LOW] | Dead code increases cognitive load and repository size. Risk of accidental import. |

### 1.3 Monolith fragility signs

- Adding a new exam type requires touching `results_*.py` (model), `exams_*.py` (view), `urls.py` (route), `visit.py` (URL mapping dicts with 30+ entries each for realizar/ver/editar), and templates. The `VisitaExamen.get_resultado_instance()` method maintains a hardcoded list of 30+ `related_name` strings.
- **No plugin or registry pattern** for exam types — each new exam requires ~6 file modifications.

---

## 2. Security

### 2.1 Strengths

- **Secret management via `python-decouple`.** `SECRET_KEY`, database credentials, and API keys loaded from `.env`. No defaults for critical secrets (`SECRET_KEY` has no fallback — app won't start without it).
- **HTTPS enforcement in production.** `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS=31536000`, `SECURE_HSTS_PRELOAD`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` all enabled when `DEBUG=False`.
- **CSRF middleware active.** Standard Django CSRF middleware is in the middleware stack. `CSRF_TRUSTED_ORIGINS` configured for production domains.
- **No `@csrf_exempt` found in current codebase.** The previously flagged `agendar_cita_ajax` no longer uses `@csrf_exempt` — the decorator was removed. The endpoint now relies on Django's default CSRF protection.
- **Rate-limiting middleware** on 7 public paths (30 req/60s per IP).
- **Click-jacking protection** via `X_FRAME_OPTIONS = "DENY"` in production.
- **Password validators** — all 4 Django default validators enabled.
- **No raw SQL** found in application code (only in vendor JS files matched by grep).

### 2.2 Weaknesses

| Issue | Severity | Impact |
|-------|----------|--------|
| **Binary RBAC: superuser vs. authenticated.** Authorization is `@login_required` + `@user_passes_test(is_superuser)`. No role model (Doctor, Researcher, Nurse, Admin). Any authenticated user can view all patients, create visits, and complete exams. | [HIGH] | A researcher or nurse account can view and modify any patient's clinical data. No principle of least privilege. |
| **Public endpoints expose patient existence.** `consulta_examenes` accepts `documento` (ID number) and returns exam data. Although it returns `{"examenes": []}` for non-existent patients (preventing enumeration), it returns actual exam URLs for existing ones — accessible without authentication. | [HIGH] | Patient exam URLs are exposed to anyone who knows (or brute-forces) a document number. Rate-limiting mitigates but does not prevent this. |
| **Public exam submission endpoints** (`guardar_examen_publico_epworth`, `guardar_examen_publico_mew`, `guardar_examen_publico_pitsburg`) accept `paciente_id` as GET/POST parameter with no authentication token or signed URL. | [HIGH] | Any actor with a valid `paciente_id` can submit or overwrite exam results. Sequential ID guessing is trivial. |
| **No audit trail.** No model tracks who viewed, created, or modified clinical records. `Visita` tracks `firmado_por` but there is no general audit log for reads or edits. | [HIGH] | Impossible to determine who accessed or changed patient data — a fundamental healthcare compliance requirement. |
| **Email sending in request cycle** (`firmar_visita`) — SMTP failure exposes error details in the catch block posted to messages. | [MEDIUM] | Potential information leakage in error messages. Blocking SMTP call can cause request timeout. |
| **`agendar_cita_ajax` accepts JSON body from unauthenticated users.** While CSRF is now enforced and rate-limiting applies, there is no CAPTCHA or email verification. | [MEDIUM] | Automated appointment flooding within rate limits (30 per minute per IP) is still feasible from distributed sources. |
| **Django admin exposed** at `/admin/` with default configuration. No IP restriction or 2FA. | [MEDIUM] | Brute-force attack surface on admin login. Admin access grants full DB manipulation. |
| **Rate-limiting uses `LocMemCache`** (Django default). Single-process only. | [MEDIUM] | With Gunicorn workers > 1, rate-limit counters are not shared. Currently mitigated by `workers=1` but will break on scale-up. |
| **`guardar_firma_usuario` downloads external URLs** (`requests.get(imagen_url)`) from user-supplied input. | [MEDIUM] | SSRF (Server-Side Request Forgery) vector. An attacker could probe internal network services by submitting internal URLs. |
| **Session configuration uses default Django session backend** (database-backed). No explicit session timeout configured. | [LOW] | Sessions persist until browser close (default). No idle timeout for clinical workstations. |

### 2.3 CSRF and Session Summary

- CSRF middleware: **Active**
- CSRF trusted origins: **Configured** (`gruneco.com.co`)
- Session cookies: **Secure in production**
- `@csrf_exempt`: **Not found** (remediated since previous handover)

---

## 3. Database Design

### 3.1 Strengths

- **Referential integrity via ForeignKey constraints.** All relationships use Django ForeignKey/OneToOneField with appropriate `on_delete` behavior (`CASCADE`, `SET_NULL`).
- **`unique_together` on critical pairs.** `VisitaExamen(visita, examen)`, `ProyectoPacienteExtra(proyecto, paciente)`, `DisponibilidadUsuario(usuario, sala, dia_semana, hora_inicio)`.
- **`unique=True` on patient identifiers.** `numero_documento` and `celular` on `DatosDemograficos`.
- **Abstract base class for exam results** (`ResultadoExamenBase`) with `%(class)s` related name — clean inheritance pattern.
- **`JSONField` for flexible exam configuration** on `TipoVisita.examenes` and `Examen.campos`.

### 3.2 Weaknesses

| Issue | Severity | Impact |
|-------|----------|--------|
| **`results_general.py` = 2,959 lines (3,332 including blanks).** Contains `ExamenFisicoResult` with 80+ boolean/text fields for body systems, `ExamenNeurologicoResult`, `AntecedentesResult`, `RevisionSistemasResult`, `MedicamentosResult`, `CognitivoAnamnesisResult` and many child models. | [HIGH] | Maintainability risk. Models like `ExamenFisicoResult` represent "wide tables" with 80+ columns — many boolean fields for each body system finding. Normalization into a key-value or EAV pattern would reduce schema width but add query complexity. Current approach is pragmatic for form-driven clinical data but creates large migration files. |
| **No `db_index` on frequently filtered fields.** `DatosDemograficos.correo`, `Visita.estado_visita`, `Visita.firmado`, `VisitaExamen.estado`, `CitaMedica.estado`, `CitaMedica.email_paciente` lack explicit indexes. `numero_documento` is indexed via `unique=True`. | [MEDIUM] | Slow lookups as data grows. `VisitaExamen.objects.filter(estado="completado")` used in statistics aggregation will degrade. |
| **No `indexes` in `class Meta` on any model.** No composite indexes defined. | [MEDIUM] | Queries filtering on `(visita, estado)` or `(paciente, fecha)` will require full table scans at scale. |
| **Business rules in `save()` overrides.** `Visita.save()` auto-generates patient codes (`ANG-XXX`) based on project name string comparison (`"Anosognosia"`) and visit type name (`"PosIntervención"`). `ExamenFisicoResult.save()` calculates BMI. `CuidadorNPIResult.save()` calculates total score. | [MEDIUM] | Business logic coupled to persistence layer. Impossible to test code-generation logic without writing to DB. String-based project matching is fragile — renaming the project breaks the logic silently. |
| **`CustomUser` model exists but is unused.** `AUTH_USER_MODEL` is not set in `settings.py`, so Django uses the default `auth.User`. Yet `CustomUser(AbstractUser)` is defined in `patient.py` and a separate `UserProfile` provides a firma field via OneToOne to `User`. | [LOW] | Dual user model creates confusion. `CustomUser` has `firma`, `phone`, `address` fields that are never used. |
| **JSONField for exam IDs** in `TipoVisita.examenes` stores `[{"id": 3}, {"id": 5}]`. No foreign-key constraint. | [MEDIUM] | Referential integrity not enforced at DB level. Deleting an `Examen` record does not cascade to JSON references. Orphaned exam IDs can cause runtime errors. |
| **No `created_at`/`updated_at` on core models.** `DatosDemograficos`, `Visita`, `Proyecto` lack timestamp fields. `VisitaExamen` has `fecha_creacion` but many models do not. | [MEDIUM] | Impossible to determine when a patient record was last modified — audit and debugging impediment. |

### 3.3 N+1 Query Risks

| Location | Pattern | Risk |
|----------|---------|------|
| `VisitaExamen.get_resultado_instance()` | Iterates 30+ possible `related_name` strings calling `getattr(self, name).get()` — each triggering a separate query | [HIGH] |
| `Visita.__str__()` | Accesses `self.Tipo_visita.proyecto` — 2 extra queries per string representation if not prefetched | [MEDIUM] |
| `lista_pacientes` | `DatosDemograficos.objects.all()` without pagination or `select_related` — loads entire patient table | [MEDIUM] |
| `proyectos` view | Nested loops: `for proyecto` → `for visita` → `Examen.objects.filter(id__in=...)` — O(P×V) queries | [MEDIUM] |
| `api_eventos_disponibilidad_publica` | `for disponibilidad` → `for fecha` → `CitaMedica.objects.filter(...)` — per-slot DB query | [HIGH] |

### 3.4 Observed `select_related`/`prefetch_related` Usage

- `detalle_paciente`: `Visita.objects.filter(paciente=paciente).prefetch_related("visita_examenes__examen")` — **good**
- `visitas_pendientes_firma`: uses `select_related("paciente", "Tipo_visita", "Tipo_visita__proyecto", "evaluador")` — **good**
- `scheduling` views: several `select_related("usuario", "sala")` calls — **good**
- **All other views:** No `select_related` or `prefetch_related` observed.

---

## 4. Performance

### 4.1 Strengths

- **WhiteNoise** for static file serving — avoids Gunicorn serving static assets.
- **Rate-limiting middleware** protects public endpoints from abuse.
- **Timeouts on external HTTP calls** — all `requests.get/post` calls use `timeout=10` or `timeout=5`.

### 4.2 Weaknesses

| Issue | Severity | Impact |
|-------|----------|--------|
| **Gunicorn: `workers=1`** in `gunicorn-cfg.py`. Single worker process. | [CRITICAL] | Single concurrent request capacity. Any blocking operation (PDF generation, email sending, PostHog API call) blocks **all** other users. Under any real load, requests queue and timeout. |
| **Blocking external HTTP calls in request cycle.** `analytics.py` makes 15+ synchronous `requests.get/post` calls to PostHog API within view functions (each with 10s timeout). | [CRITICAL] | A slow or unresponsive PostHog API blocks the Gunicorn worker for up to 10 seconds per call. With 1 worker, the entire application freezes. |
| **PDF generation in request cycle.** `firmar_visita` calls `construir_pdf_visita()` (ReportLab), then `email.send()` with attachment — both synchronous and CPU/IO-bound. | [HIGH] | Large visit PDFs with many exams could take several seconds to generate. Combined with SMTP send, total latency can exceed 30 seconds. |
| **No caching strategy.** No `CACHES` setting in `settings.py`. Django uses `LocMemCache` by default (in-process only). No template fragment caching, no queryset caching. | [HIGH] | Every page load re-queries the database. Statistics pages recalculate aggregations on every request. |
| **No pagination on any list view.** `lista_pacientes` loads `DatosDemograficos.objects.all()`. `User.objects.all()` in `administrar_usuarios`. No `Paginator` usage found in the entire codebase. | [HIGH] | With hundreds of patients, full-table loads cause increasing memory usage and response times. Client-side DataTables pagination does not reduce server-side resource usage. |
| **Scheduling API generates slots in Python loops.** `api_eventos_disponibilidad_publica` iterates dates × time-slots × DB-query-per-slot. 8 weeks × 5 days × 8 slots = ~320 potential DB queries per request. | [HIGH] | Scheduling endpoint response time grows linearly with number of professionals and availability windows. |
| **No database connection pooling configured.** Default Django MySQL configuration creates a new connection per request. | [MEDIUM] | Connection overhead per request. Not critical at low traffic but becomes bottleneck at moderate scale. |
| **Docker configuration runs migrations at build time** (`RUN python manage.py migrate` in Dockerfile). | [LOW] | Migrations execute during image build, not container start. Requires image rebuild for each migration. May fail if DB is not accessible at build time. |

### 4.3 Areas That Would Cause Production Failure Under Load

1. **Single Gunicorn worker + blocking PostHog calls.** A user accessing statistics pages while another user signs a visit (PDF + email) would cause request queueing. At 5+ concurrent users, response times exceed acceptable thresholds.
2. **Scheduling availability API.** N professionals with M availability slots generates O(N×M×8_weeks) database queries. At 10 professionals with daily availability, this exceeds 2,000 queries per request.
3. **Patient list without pagination.** At 1,000+ patients, `DatosDemograficos.objects.all()` returns full dataset per request, consuming memory and serialization time proportional to patient count.

---

## 5. Code Health

### 5.1 File Size Assessment

| File | Lines | Threshold | Status |
|------|-------|-----------|--------|
| `models/results_general.py` | 2,959 | >1000 | [CRITICAL] — maintainability risk |
| `views/exams_dispatch.py` | 1,346 | >1000 | [HIGH] — maintainability risk |
| `views/exams_general.py` | 1,067 | >1000 | [HIGH] — maintainability risk |
| `models/results_anosognosia.py` | 875 | >500 | [MEDIUM] |
| `views/scheduling.py` | 895 | >500 | [MEDIUM] |
| `views/exams_anosognosia.py` | 932 | >500 | [MEDIUM] |
| `views/analytics.py` | 808 | >500 | [MEDIUM] |
| `views/exams_public.py` | 709 | >500 | [MEDIUM] |

### 5.2 Anti-Patterns Observed

| Pattern | Location | Severity |
|---------|----------|----------|
| **Duplicated import blocks.** Every view file imports the same 15+ modules (reportlab, auth, logging, etc.) regardless of whether they are used. | All `views/*.py` | [MEDIUM] |
| **Hardcoded exam ID → config mapping.** `realizar_examen()` maps exam IDs (3, 4, 5, 7, 8...) to templates and models via a 40-entry dict literal. | `exams_dispatch.py:37-150` | [HIGH] |
| **Triple URL mapping dicts.** `VisitaExamen` has 3 methods (`get_url_realizar`, `get_url_ver`, `get_url_editar`) each containing 30+-entry dicts mapping exam names to URL names. | `visit.py:250-480` | [HIGH] |
| **String-based exam type dispatch.** `get_resultado_instance()` iterates 30+ hardcoded `related_name` strings to find the associated result. | `visit.py:145-210` | [HIGH] |
| **Exception swallowing.** Multiple `except Exception as e: continue` blocks in `get_resultado_instance()` silently hide errors. | `visit.py:175-195` | [MEDIUM] |
| **Business logic in `save()`.** `Visita.save()` generates patient codes; `ExamenFisicoResult.save()` calculates BMI; `CuidadorNPIResult.save()` calculates scores. | Multiple models | [MEDIUM] |
| **No Django form validation on most exam saves.** Public exam endpoints (`exams_public.py`) construct model instances from `request.POST` data with minimal validation. | `exams_public.py` | [MEDIUM] |
| **Dead code.** `models_old.py` (3300+ lines), `views_old.py` (3700+ lines), `forms_old.py` remain in codebase. | Root of `apps/home/` | [LOW] |

### 5.3 Test Coverage

- **`tests.py` exists but content is minimal.** No test runner configuration observed (no `pytest.ini`, `tox.ini`, or CI pipeline for tests).
- **Estimated coverage: near zero.** No test files found under `apps/home/views/`, `apps/home/models/`, or `apps/home/forms/`.
- **Refactor risk: HIGH.** Any modification to the exam dispatch system, URL mapping, or result retrieval logic cannot be validated automatically.

### 5.4 Maintainability Score

| Metric | Assessment |
|--------|-----------|
| Cyclomatic complexity | **Moderate** — exam dispatch functions have many branches but are structurally repetitive |
| Coupling | **High** — views depend directly on 30+ model classes, URL routing hardcodes exam IDs |
| Cohesion | **Moderate** — file splitting improved cohesion but the single-app constraint limits it |
| Readability | **Good** — Spanish comments are consistent, code follows Django conventions |
| Refactor risk | **HIGH** — no tests, hardcoded mappings, tightly coupled URL/model/view relationships |

---

## 6. Compliance & Clinical Risk

### 6.1 Strengths

- **HTTPS enforced** in production with HSTS preload.
- **Patient document number validated** before exposing exam data.
- **Visit signing mechanism** provides a basic "closure" workflow.
- **Email notifications** include clinical history PDF — enables paper-trail for patients.
- **Rate-limiting** on public-facing endpoints reduces automated abuse.

### 6.2 Weaknesses

| Issue | Severity | Impact |
|-------|----------|--------|
| **No audit trail.** No model or middleware logs who accessed, viewed, or modified patient records. | [CRITICAL] | Non-compliant with healthcare data governance requirements (e.g., Colombian Ley 1581/2012, Habeas Data). Impossible to investigate unauthorized access. |
| **No data-at-rest encryption.** Patient PII (names, document numbers, addresses, phone numbers, clinical data) stored in plaintext in MySQL. | [HIGH] | Database compromise exposes all patient data. Regulatory frameworks increasingly require encryption at rest for health records. |
| **Public endpoints return clinical data without authentication.** `consulta_examenes` returns exam names and URLs for any valid document number. Public exam forms (`guardar_examen_publico_*`) accept patient IDs without signed tokens. | [HIGH] | A third party could access a patient's exam list by knowing their document number. No consent verification mechanism exists. |
| **Sequential integer IDs as access tokens.** Patient IDs, visit IDs, and exam IDs are sequential integers used in URLs. No UUID or signed-URL pattern. | [HIGH] | Trivial enumeration attack. An attacker incrementing `/paciente/1/`, `/paciente/2/` can access patient records (mitigated by `@login_required` on these specific endpoints). Public endpoints using `paciente_id` are more vulnerable. |
| **No role-based clinical data access.** Any authenticated user sees all patients, all projects, all exams. No "treating physician" or "research team" scoping. | [HIGH] | Violates minimum-necessary-access principle for health data. A user added for Project A can view and modify data from Project B. |
| **Patient PII in session data.** `formulario_demografico_externo` stores patient name, document number, email, and internal ID in `request.session`. | [MEDIUM] | Session data stored in database (default backend). If sessions are not purged, PII persists in session table indefinitely. |
| **Error messages expose internal details.** Multiple views include `str(e)` in user-facing error messages (`messages.error(request, f"Error: {str(e)}")`). | [MEDIUM] | Stack trace fragments, database errors, or file paths could leak to end users. |
| **No consent management system.** While `ConsentimientoInformadoParticipanteResult` and `ConsentimientoInformadoCuidadorResult` models exist, there is no system-level consent verification before data processing. | [MEDIUM] | Consent is captured as an exam result, not as an access-control gate. Data can be collected before consent is recorded. |
| **Logging configuration absent.** No `LOGGING` dict in `settings.py`. Default Django logging applies. No structured logging, no log rotation, no security event logging. | [HIGH] | No visibility into authentication failures, access patterns, or data modification events. Incident response capability is minimal. |

### 6.3 Regulatory Exposure Risks

1. **Audit trail absence.** Under Colombian data protection law (Ley 1581/2012) and health data regulations (Resolución 1995/1999), organizations must maintain access logs for clinical records. The complete absence of audit logging represents the highest regulatory exposure.

2. **Public endpoint data exposure.** Clinical exam data accessible via document number without authentication violates the purpose-limitation and minimum-access principles in data protection frameworks.

3. **No role-based access control.** All authenticated users having unrestricted access to all patient data violates the principle of minimum necessary access required by healthcare data governance standards.

---

## Top 5 Immediate Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| 1 | **Single Gunicorn worker** causes total application blocking under any concurrent load | [CRITICAL] | Change `workers` to `2 * NUM_CORES + 1` (min 3) in `gunicorn-cfg.py`. When increasing workers, configure a shared cache backend (Redis/Memcached) for rate-limiting. |
| 2 | **No audit trail** for clinical data access and modifications | [CRITICAL] | Implement `django-auditlog` or `django-simple-history` on `DatosDemograficos`, `Visita`, `VisitaExamen`, and all `*Result` models. Minimal code change, significant compliance improvement. |
| 3 | **Blocking PostHog API calls** in analytics views (15+ synchronous HTTP calls per page load) | [CRITICAL] | Move PostHog data fetching to a background task (Celery) or cache results. As immediate fix, add fallback timeouts of 3s and return cached/empty data on failure. |
| 4 | **Public exam endpoints accept unsecured patient IDs** — no signed tokens or authentication | [HIGH] | Generate time-limited signed URLs (Django `signing` module) for public exam access. Replace raw `paciente_id` parameters with HMAC-signed tokens. |
| 5 | **No pagination on patient/user list views** — full table loads on every request | [HIGH] | Add Django `Paginator` to `lista_pacientes`, `administrar_usuarios`. Set page size to 25-50. Immediate, low-risk change. |

---

## Top 5 Structural Improvements (Incremental)

| # | Improvement | Effort | Impact |
|---|-------------|--------|--------|
| 1 | **Introduce exam-type registry pattern.** Replace hardcoded dicts in `visit.py` and `exams_dispatch.py` with a declarative registry (dict or class-based) that maps exam IDs to models, templates, URL names, and related names. Single source of truth. | Medium | Eliminates 4 parallel 30+-entry dicts. Reduces new-exam-type integration from 6 files to 1 registration. |
| 2 | **Add role model.** Create a `UserRole` model or use Django groups (`Investigador`, `Evaluador`, `Admin`) with a `RoleRequiredMixin`. Assign patients/projects to roles. Gate view access by role membership. | Medium | Enables principle-of-least-privilege. Addresses the highest compliance gap. |
| 3 | **Configure `LOGGING` in settings.py.** Add structured JSON logging with security events (login success/failure, patient record access, data modification). Ship to file or external service. | Low | Provides audit capability, incident response data, and debugging visibility. |
| 4 | **Add database indexes.** Add `db_index=True` to `VisitaExamen.estado`, `Visita.estado_visita`, `Visita.firmado`, `CitaMedica.estado`, `CitaMedica.email_paciente`, `DatosDemograficos.correo`. Add composite indexes via `class Meta: indexes`. | Low | Immediate query performance improvement at scale. Zero application code change. |
| 5 | **Extract email/PDF to async tasks.** Use Django-Q, Celery, or `threading.Thread` (simplest) to move PDF generation and SMTP operations out of the request cycle in `firmar_visita`. | Medium | Eliminates the most impactful single-request blocking operation. Improves UX for visit signing. |

---

## Technical Debt Estimate

| Area | Debt Level | Rationale |
|------|-----------|-----------|
| Model layer | **Moderate** | Wide tables are defensible for clinical forms, but 2,959-line file and hardcoded dispatch logic are debt |
| View layer | **Moderate** | Duplicated imports, no service layer, blocking I/O in requests |
| Security/Auth | **Severe** | Binary RBAC, no audit trail, public endpoint exposure |
| Infrastructure | **Moderate** | Single worker, no caching, no logging config |
| Testing | **Severe** | Near-zero automated test coverage |
| **Overall** | **Moderate** | System is functional but carries concentrated risk in security/compliance and performance under load |

---

## Refactor Risk Assessment

| Action | Risk Level | Rationale |
|--------|-----------|-----------|
| Adding indexes | **Low** | Schema-only migration, no code change |
| Adding pagination | **Low** | Additive change to existing views |
| Adding audit logging | **Low** | Middleware or signal-based, no model changes |
| Introducing exam registry | **Medium** | Requires refactoring 4+ files but can coexist with current code |
| Adding role-based access | **Medium** | Requires new model + decorator changes on 30+ views |
| Splitting into multiple apps | **High** | Migration chain split, import path changes, template moves |
| Moving to async tasks | **Medium** | Requires task queue infrastructure (Redis + Celery/Django-Q) |
| Adding comprehensive tests | **Medium** | Large surface area, many integration points, but no existing tests to break |

---

*End of assessment.*
