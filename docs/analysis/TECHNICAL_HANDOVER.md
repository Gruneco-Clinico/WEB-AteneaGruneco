# ATENEA GRUNECO — Technical Handover Document

**Project:** ATENEA — Electronic Health Records (EHR) System  
**Organization:** GRUNECO (Grupo de Neuropsicología y Conducta — Universidad de Antioquia)  
**Domain:** https://www.gruneco.com.co  
**Date:** 2026-02-21  
**Version:** 1.0  

---

## TABLE OF CONTENTS

1. [System Overview](#section-1-system-overview)  
2. [Folder Structure Explanation](#section-2-folder-structure-explanation)  
3. [Database Analysis](#section-3-database-analysis)  
4. [Security Review](#section-4-security-review)  
5. [Performance Review](#section-5-performance-review)  
6. [Deployment Analysis](#section-6-deployment-analysis)  
7. [Risk Assessment](#section-7-risk-assessment)  
8. [Refactoring Roadmap](#section-8-refactoring-roadmap)  

---

## SECTION 1: System Overview

### 1.1 High-Level Architecture

ATENEA is a monolithic Django 5.0.6 web application serving as a clinical Electronic Health Records system for GRUNECO, a neuropsychology and behavior research group at the Universidad de Antioquia (Medellín, Colombia). It is deployed on a Bitnami stack on an AWS EC2 instance (IP: `3.85.96.200`).

```
┌──────────────────────────────────────────────────────┐
│                      INTERNET                        │
│              https://www.gruneco.com.co               │
└──────────────────┬───────────────────────────────────┘
                   │
         ┌─────────▼──────────┐
         │   Apache/Nginx     │  (Bitnami reverse proxy)
         │   (Port 443/80)    │
         └─────────┬──────────┘
                   │
         ┌─────────▼──────────┐
         │   Gunicorn WSGI    │  (Port 5005, 1 worker)
         │   Django 5.0.6     │
         └─────────┬──────────┘
                   │
         ┌─────────▼──────────┐
         │   MariaDB          │  (Bitnami, unix socket)
         │   ateneagrunecodb  │
         └─────────┬──────────┘
                   │
         ┌─────────▼──────────┐
         │   WhiteNoise       │  (Static files serving)
         └────────────────────┘
```

**External Integrations:**
- **PostHog** (analytics platform) — DAU metrics, user behavior tracking via personal API key
- **Gmail SMTP** — Transactional emails (appointment confirmations, notifications)

### 1.2 Main Django Apps and Responsibilities

The system contains a single Django app (`apps.home`) that handles **all** functionality:

| Module | Responsibility |
|--------|---------------|
| `apps.home` | Patient registration, clinical visits, medical exams (sleep studies, anosognosia studies, general medical exams), appointment scheduling, user admin, PDF generation, PostHog analytics integration |

**ASSUMPTION:** There are no additional Django apps beyond `apps.home` and the built-in Django admin. The system is currently a monolithic single-app architecture.

### 1.3 Authentication and Role System

- **Authentication:** Django's built-in `django.contrib.auth` with email-based login (custom `CustomLoginForm` overrides `AuthenticationForm` to authenticate via email).
- **User Models:** Two user models exist in parallel:
  - `django.contrib.auth.models.User` — **Primary user model in active use** (FK references throughout models and views).
  - `CustomUser(AbstractUser)` — Defined but **not configured as AUTH_USER_MODEL** in settings. This is dead code/orphaned.
  - `UserProfile` — OneToOne extension of `User` to store digital signatures (`firma`).
- **Authorization:** Minimal. The system uses `@login_required` on most views. A `is_superuser` check exists for user administration. There is **no granular role-based access control** (RBAC) system — no concept of Doctor, Nurse, Admin, Researcher roles.
- **Session:** Django default session-based auth with session middleware.

### 1.4 Main Workflows

1. **Patient Registration:**
   - Internal (authenticated): via `registro_demografico` view
   - External (public): via `formulario_demografico_externo` — unauthenticated patients can self-register with demographic data

2. **Project Management:**
   - Research projects (e.g., "Anosognosia", "Sueño") are created with associated visit types and exam configurations
   - Patients are assigned to projects via M2M relationship

3. **Clinical Visit Flow:**
   - Create a visit for a patient → select visit type → auto-populate associated exams
   - Exams are individually completed, tracked via `VisitaExamen` status
   - Visit can be signed/locked (`firmado` flag) to prevent further edits
   - PDF clinical history can be generated per visit

4. **Medical Exam Lifecycle:**
   - ~35+ distinct clinical instruments (Pittsburgh, Epworth, MoCA, CDR, NPI, etc.)
   - Each exam has a dedicated save view, result model, template, and URL
   - Exams are classified into categories: Sleep, Anosognosia, General Medical

5. **Appointment Scheduling (Public):**
   - Professionals define availability slots via calendar
   - Public users can view available slots and book appointments
   - Email confirmations sent via Gmail SMTP

6. **Analytics Integration (RecuérdaMe):**
   - PostHog integration for tracking user engagement metrics
   - Dedicated statistics views for DAU, session time, per-user analytics

---

## SECTION 2: Folder Structure Explanation

```
WEB-AteneaGruneco/
├── apps/                          # Main application package
│   ├── __init__.py
│   ├── config.py                  # AppConfig: name='apps.home', label='apps_home'
│   ├── home/                      # THE ONLY Django app — handles everything
│   │   ├── models.py             # 5,670 lines — ALL models in one file
│   │   ├── views.py              # 10,911 lines — ALL views in one file
│   │   ├── urls.py               # 329 lines — ALL URL routes
│   │   ├── forms.py              # 216 lines — Only 3 forms defined
│   │   ├── admin.py              # 54 lines — Basic model registrations
│   │   ├── posthog_service.py    # PostHog API integration service
│   │   ├── apps.py               # Django app configuration
│   │   ├── tests.py              # Present but empty/minimal
│   │   ├── templatetags/         # Custom template filters
│   │   │   ├── custom_filters.py
│   │   │   └── exam_filters.py
│   │   └── migrations/           # 18+ migration files
│   ├── static/                    # Static assets source
│   │   └── assets/               # CSS, JS, images, fonts, PDFs
│   └── templates/                 # All HTML templates
│       ├── layouts/              # Base templates (4 layouts)
│       ├── home/                 # Main app pages (17 templates)
│       ├── examenes_sueno/       # Sleep exam forms (9 templates)
│       ├── examenes_anosognosia/ # Anosognosia exam forms (20 templates)
│       ├── examenes_general/     # General exam forms (7 templates)
│       ├── examenes_resultados/  # Exam result views (8 templates)
│       ├── info_paciente/        # Patient forms (4 templates)
│       ├── registro_publico/     # Public registration (6 templates)
│       ├── scheduling/           # Appointment scheduling (3 templates)
│       └── includes/             # Reusable template fragments
├── core/                          # Django project configuration
│   ├── settings.py               # Main settings (all config in one file)
│   ├── urls.py                   # Root URL config (admin + home)
│   ├── wsgi.py                   # WSGI entry (Bitnami path hardcoded)
│   ├── asgi.py                   # ASGI entry (unused)
│   └── staticfiles/              # Collected static files
├── nginx/
│   └── appseed-app.conf          # Nginx config (Docker, port 85)
├── staticfiles/                   # Root-level collected static assets
├── Dockerfile                     # Python 3.9 Docker image
├── docker-compose.yml             # App + Nginx containers
├── gunicorn-cfg.py                # Gunicorn: 1 worker, port 5005
├── Procfile                       # Heroku-compatible (gunicorn)
├── requirements.txt               # 27 Python dependencies
├── manage.py                      # Django management script
├── Atenea.sql                     # Database dump/schema
├── db.sqlite3                     # Legacy SQLite (not in active use)
├── runtime.txt                    # Python runtime specification
├── test_extraction.py             # Standalone test script
└── test_pdf_fix.py                # Standalone test script
```

### Technical Debt & Anti-Patterns Identified

| Issue | Severity | Description |
|-------|----------|-------------|
| **God File: views.py (10,911 lines)** | CRITICAL | Every view in the entire application is in a single file. Extremely difficult to maintain, review, or test. |
| **God File: models.py (5,670 lines)** | CRITICAL | Every model (~60+ models) in a single file. No separation by domain. |
| **Single App Architecture** | HIGH | All functionality (scheduling, patients, exams, analytics, PDF generation) lives in one Django app with no modularity. |
| **No serializers.py** | MEDIUM | API responses are manually constructed dicts. No Django REST Framework or structured serialization layer. |
| **Wildcard import: `from .models import *`** | MEDIUM | views.py imports all models via wildcard. Namespace pollution, unclear dependencies. |
| **CustomUser model defined but unused** | MEDIUM | `CustomUser(AbstractUser)` exists in models but is never set as `AUTH_USER_MODEL`. Dead code that creates confusion. |
| **Debug prints in production code** | HIGH | `Visita.save()` contains emoji debug prints (`🟡`, `🟢`, `🔴`) that execute on every save in production. |
| **No test coverage** | HIGH | `tests.py` appears empty. No unit or integration tests found. |
| **Duplicate static directories** | LOW | `apps/static/`, `core/staticfiles/`, and root `staticfiles/` create ambiguity. |

---

## SECTION 3: Database Analysis

### 3.1 Database Engine & Configuration

- **Engine:** MariaDB via `django.db.backends.mysql`
- **Database Name:** `ateneagrunecodb`
- **Connection:** Unix socket at `/opt/bitnami/mariadb/tmp/mysql.sock`
- **Client Library:** `mysqlclient==2.2.7`

### 3.2 Model Inventory & Relationships

**Core Domain Models (~60+ models total):**

#### Scheduling Domain
| Model | Description | Key Relations |
|-------|-------------|---------------|
| `Sala` | Examination rooms | — |
| `DisponibilidadUsuario` | Professional availability slots | FK → User, FK → Sala |
| `CitaMedica` | Booked appointments | FK → DisponibilidadUsuario |
| `BloqueoDisponibilidad` | Blocked availability dates | FK → DisponibilidadUsuario |

#### Patient Domain
| Model | Description | Key Relations |
|-------|-------------|---------------|
| `DatosDemograficos` | Patient demographic data (primary patient record) | Unique on `numero_documento` and `celular` |
| `UserProfile` | User digital signature storage | OneToOne → User |
| `CustomUser` | **UNUSED** extended user model | — |

#### Research Project Domain
| Model | Description | Key Relations |
|-------|-------------|---------------|
| `Proyecto` | Research projects | M2M → DatosDemograficos |
| `ProyectoPacienteExtra` | Extra per-project patient metadata | FK → Proyecto, FK → DatosDemograficos |
| `Examen` | Exam definitions/templates | JSONField for schema |
| `TipoVisita` | Visit type templates | FK → Proyecto, JSONField for exams |

#### Clinical Visit Domain
| Model | Description | Key Relations |
|-------|-------------|---------------|
| `Visita` | Patient visit instances | FK → DatosDemograficos, FK → TipoVisita, FK → User (evaluator, signer) |
| `VisitaExamen` | Exam-instance within a visit (pivot table) | FK → Visita, FK → Examen. Unique together. |

#### Exam Result Models (inheriting from `ResultadoExamenBase`)
All inherit from abstract `ResultadoExamenBase` with OneToOne → `VisitaExamen`:

**Sleep Study Results:**
- `PittsburghResult` — Pittsburgh Sleep Quality Index
- `EpworthResult` — Epworth Sleepiness Scale
- `MEWResult` — Morningness-Eveningness Questionnaire
- `BerlinResult` — Berlin Questionnaire
- `ISIResult` — Insomnia Severity Index
- `StopBangResult` — STOP-BANG screening
- `AtenasResult` — Athens Insomnia Scale
- `SuenoFisicoResult` — Sleep Physical Exam
- `SuenoAnamnesisResult` — Sleep Anamnesis (+ 7 child models for substances, medications, screens, symptoms, etc.)

**Anosognosia Study Results:**
- `LawtonBrodyResult` — Instrumental ADL Scale
- `CuidadorNPIResult` — Neuropsychiatric Inventory
- `AdherenciaTerapeuticaResult` — Therapeutic Adherence
- `EuroQol5D5LResult` / `EuroQolEVASaludResult` — Quality of Life
- `MoCAResult` — Montreal Cognitive Assessment
- `ParticipanteYesavageResult` — Geriatric Depression Scale
- `ZaritResult` — Caregiver Burden Scale
- `AQDCuidadorResult` / `AQDParticipanteResult` — Awareness Questionnaire
- `CDRCuidadorResult` / `CDRParticipanteResult` — Clinical Dementia Rating
- `RedLatSpanishResult` — RedLat Functional Assessment
- `BettyFerrelResult` — Quality of Life (Caregiver)
- `PuntajeCDRResult` — CDR Global Score
- `ConsentimientoInformadoParticipanteResult` / `ConsentimientoInformadoCuidadorResult` — Informed Consent
- `AnamnesisCuidadorResult` / `AnamnesisParticipanteResult` — Caregiver/Participant Anamnesis
- `SeguimientoIntervencionesResult` — Intervention Follow-up (FK, not OneToOne — multiple sessions)

**General Medical Exam Results:**
- `AnalisisGeneralResult` — General Analysis & Diagnosis (+ 4 child Diagnostic models: CIE-10, DSM-V, ICSD-3, No Clasificado)
- `ExamenFisicoResult` — Physical Examination
- `ExamenNeurologicoResult` — Neurological Examination (~200+ fields)
- `MedicamentosResult` + `Medicamento` — Medication tracking
- `RevisionSistemasResult` + `DetalleRevisionSistemas` — Systems Review
- `CognitivoAnamnesisResult` + 4 child models — Cognitive Anamnesis
- `AntecedentesResult` + 10 child models — Medical History (unique per patient design)

**Analytics Models:**
- `InteractionMetric` — PostHog event storage
- `EstadisticasUsuarioResult` — User statistics cache

### 3.3 Critical Tables

1. **`DatosDemograficos`** — Central patient record. All clinical data links through this via `Visita`.
2. **`Visita`** — Core visit record linking patient, type, evaluator, and all exam results.
3. **`VisitaExamen`** — Pivot between visits and exams. All exam results link here via OneToOne.
4. **`AntecedentesResult`** — Special design: OneToOne per patient (not per visit). Uses `AntecedentesVisitaLink` bridge for per-visit tracking.

### 3.4 Potential Optimization Issues

| Issue | Affected Model(s) | Description |
|-------|-------------------|-------------|
| **No `db_index` on frequently filtered fields** | `DatosDemograficos.numero_documento` | Has `unique=True` (auto-indexed), but `celular`, `correo` used in lookups lack explicit indexes. |
| **No index on `Visita.paciente`+`Visita.estado_visita`** | `Visita` | Common filter pattern in views. Composite index would help. |
| **`VisitaExamen.get_resultado_instance()` brute-force** | `VisitaExamen` | Iterates through 30+ possible `related_name` strings using `getattr()` to find the result. Executes on every call with no efficient dispatch. |
| **`ExamenNeurologicoResult` has 200+ columns** | `ExamenNeurologicoResult` | Extremely wide table. Consider JSON storage or normalization for rarely queried neurological findings. |
| **`CuidadorNPIResult` has 60+ columns** | `CuidadorNPIResult` | Wide table with repetitive column patterns. |
| **No database-level constraints on business rules** | Various | Visit signing, exam completion status enforced only at Python level. |
| **`SeguimientoIntervencionesResult` uses FK instead of OneToOne** | `SeguimientoIntervencionesResult` | Breaks pattern of other results. Uses ForeignKey to `VisitaExamen` with unique_together on `(visita_examen, numero_sesion)`. This is intentional (18 sessions per exam). |
| **Duplicate choice definitions** | Multiple models | `PRESENTACION_CHOICES`, `VIA_ADMINISTRACION_CHOICES`, `UNIDAD_CHOICES` are copy-pasted across `AntecedenteFarmacologico` and `Medicamento`. |

### 3.5 Missing Indexes / Risky Relations

- `CitaMedica`: No index on `(disponibilidad, fecha_cita, estado)` despite being filtered together frequently.
- `Visita.Tipo_visita`: Uses non-Pythonic naming convention (PascalCase field name).
- `Visita.__str__()` triggers additional DB queries (`self.Tipo_visita.proyecto`) without `select_related`.
- `Visita.save()` contains business logic that queries `DatosDemograficos` and saves patient — mixing concerns.

---

## SECTION 4: Security Review

### 4.1 CRITICAL: Hardcoded Secrets in `settings.py`

**SEVERITY: CRITICAL**

The following secrets are hardcoded directly in `settings.py` and committed to version control:

| Secret | Value (truncated) | Risk |
|--------|-------------------|------|
| `SECRET_KEY` | Default `S#perS3crEt_1122` if no env var | Session forgery, CSRF bypass if default is used in production |
| Database `PASSWORD` | `@tene@2025` | Full database access |
| Database `USER` | `root` | Root-level DB access |
| `EMAIL_HOST_PASSWORD` | `kbkznkhskatrpidk` | Gmail app password — email account compromise |
| `POSTHOG_PERSONAL_API_KEY` | `phx_IZAgbd0Yz5...` | Analytics data access |
| All `POSTHOG_*_INSIGHT_ID` values | Various | Information disclosure |

**RECOMMENDATION:** Immediately rotate all credentials. Move all to environment variables or `.env` file via `python-decouple` (already a dependency but not used for DB/email credentials).

### 4.2 DEBUG Configuration

```python
DEBUG = config("DEBUG", default=False, cast=bool)
```

The default is `False`, which is correct. However, this relies on the `.env` file not overriding it. **Verify production `.env`** does not set `DEBUG=True`.

### 4.3 CSRF Handling

- `CSRF_TRUSTED_ORIGINS` is correctly set for the production domain.
- `CsrfViewMiddleware` is in the middleware stack.
- **VULNERABILITY:** `agendar_cita_ajax` uses `@csrf_exempt` decorator — this is a public-facing endpoint that creates records in the database. An attacker can automate appointment booking to flood the system.
- Several public forms (demographic registration) appear to handle CSRF normally.

### 4.4 Improper Permission Checks

| View | Issue |
|------|-------|
| `formulario_demografico_externo` | Public patient registration — by design, but no rate limiting or CAPTCHA |
| `consulta_examenes` | Public exam query — patients access exams by `numero_documento` without authentication |
| `guardar_examen_publico_*` | Public exam submission endpoints — minimal validation of patient identity |
| `api_eventos_disponibilidad_publica` | Public availability API — no rate limiting |
| `agendar_cita_ajax` | `@csrf_exempt` + no authentication — any entity can create appointments |
| `administrar_usuarios` | Only checks `@login_required` — **any authenticated user can manage users** if the `is_superuser` check is bypassed (the view does use `@user_passes_test(is_superuser)` partially) |
| `eliminar_paciente` | Only checks `@login_required` — any authenticated user can delete patient records |
| `eliminar_proyecto` | Only checks `@login_required` — any authenticated user can delete research projects |

### 4.5 SQL Injection

- The application uses Django ORM throughout. **No raw SQL queries were found.** SQL injection risk is low.
- Model fields use proper Django field types with validation.

### 4.6 File Upload Vulnerabilities

- No `FileField` or `ImageField` found in models. No file upload endpoints detected.
- Digital signatures (`firma`) are stored as Base64 text in `TextField`, not as file uploads. This is safe.
- PDF generation uses `reportlab` to write to `BytesIO` buffers — no file system write operations from user input.

### 4.7 Additional Security Concerns

| Concern | Details |
|---------|---------|
| **No HTTPS enforcement in Django** | `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` are not configured. |
| **No `SESSION_COOKIE_SECURE`** | Session cookies may be sent over HTTP. |
| **No `CSRF_COOKIE_SECURE`** | CSRF cookies may be sent over HTTP. |
| **Patient data exposed in public endpoints** | `consulta_examenes` returns patient exam data with only a `numero_documento` lookup — equivalent to querying by ID number. |
| **WhiteNoise serves static files** | Acceptable for production but review for sensitive file exposure. |
| **`*` wildcard import in views.py** | All model classes are in view namespace. Not a direct vulnerability but increases attack surface understanding difficulty. |

---

## SECTION 5: Performance Review

### 5.1 N+1 Query Risks

The application has **severe N+1 query patterns** throughout:

| Location | Issue |
|----------|-------|
| `VisitaExamen.get_resultado_instance()` | Iterates 30+ related names calling `getattr()` and `.get()` on each. Called per exam row. |
| `Visita.__str__()` | Accesses `self.Tipo_visita.proyecto` — triggers lazy load on every string representation (admin, logging, etc.). |
| `Visita.save()` | Queries `DatosDemograficos.objects.exclude(...).order_by("-codigo").first()` on every save of an Anosognosia visit. |
| `detalle_paciente` view | Likely loads patient + visitas + exams with no `select_related`/`prefetch_related` (based on pattern analysis). |
| `lista_pacientes` view | Loads all patients; if template accesses related projects, triggers N+1. |
| `realizar_examen` view | Single massive view (~4,000+ lines) handling all exam types via conditionals. |

### 5.2 Missing `select_related` / `prefetch_related`

**There are virtually no `select_related` or `prefetch_related` calls in the entire codebase.** The only exception found is:

```python
# api_eventos_disponibilidad_publica
disponibilidades = DisponibilidadUsuario.objects.filter(...).select_related("usuario", "sala")
```

All other querysets fetch objects individually, relying on Django's lazy evaluation to trigger extra queries per related object access.

### 5.3 Heavy Views

| View | Lines | Issue |
|------|-------|-------|
| `realizar_examen` | ~900 lines | Single view handles creation/editing of ALL 35+ exam types via giant if/elif chain. |
| `ver_resultado_examen` | ~350 lines | Similar pattern for viewing all result types. |
| `guardar_examen_antecedentes` | ~550 lines | Complex multi-model save logic for patient medical history. |
| `guardar_examen_neurologico` | ~650 lines | Manually extracts 200+ POST fields. |
| `guardar_examen_fisico` | ~380 lines | Manually extracts all physical exam POST fields. |
| `estadisticas` | ~200 lines | Multiple external PostHog API calls per page load — blocks the response. |
| `generar_pdf_historia_clinica_visita` | ~200+ lines | Generates PDF via reportlab per request — CPU-intensive. |

### 5.4 Inefficient Patterns

- **No caching layer:** No Django cache backend configured. No `@cache_page` or `cache.get/set` usage.
- **Synchronous PostHog API calls:** `estadisticas` view makes multiple HTTP requests to PostHog API synchronously, blocking Django workers.
- **No pagination:** `lista_pacientes` and similar list views appear to load all records.
- **Manual form processing:** Most exam views manually extract 20-100+ `request.POST.get()` calls instead of using Django Forms or serializers.
- **PDF generation per request:** No caching of generated PDFs.
- **Gunicorn with 1 worker:** Only 1 process handles all traffic.

---

## SECTION 6: Deployment Analysis

### 6.1 Bitnami Deployment

- **Platform:** Bitnami stack on AWS EC2 (`3.85.96.200`)
- **WSGI server:** Gunicorn with 1 worker, binding to `0.0.0.0:5005`
- **Reverse Proxy:** Apache/Nginx from Bitnami handles TLS termination and proxies to Gunicorn
- **Path:** `/opt/bitnami/Repositories/WEB-AteneaGruneco` (hardcoded in `wsgi.py`)
- **MariaDB:** Bitnami-managed MariaDB, accessed via Unix socket at `/opt/bitnami/mariadb/tmp/mysql.sock`

### 6.2 WSGI Configuration

`core/wsgi.py`:
```python
sys.path.append('/opt/bitnami/Repositories/WEB-AteneaGruneco')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
```

- Hardcoded absolute path — breaks portability.
- ASGI is configured (`core/asgi.py`) but not used.

### 6.3 Gunicorn Configuration

```python
bind = '0.0.0.0:5005'
workers = 1
accesslog = '-'
loglevel = 'debug'
```

**Issues:**
- **1 worker:** Insufficient for production. Recommended formula: `2 * CPU_cores + 1`.
- **Debug log level in production:** Generates excessive logs and may expose sensitive data.
- **No timeout configuration:** Long-running requests (PDF generation, PostHog API calls) can block the single worker indefinitely.

### 6.4 Docker Configuration

`docker-compose.yml` defines:
- `appseed_app` — Django application container
- `nginx` — Nginx reverse proxy on port 85

**ASSUMPTION:** The Docker configuration appears to be a development/alternate deployment. Production uses Bitnami directly based on the MariaDB socket path and WSGI configuration.

### 6.5 Static and Media Configuration

```python
STATIC_ROOT = os.path.join(CORE_DIR, "staticfiles")
STATIC_URL = "/static/"
STATICFILES_DIRS = (os.path.join(CORE_DIR, "apps/static"),)
```

- Static files are served via **WhiteNoise** middleware.
- No `MEDIA_ROOT` or `MEDIA_URL` configured — no user-uploaded media support.
- PDF attachments (consent forms) are served from `apps/static/assets/pdfs/`.
- Multiple `staticfiles` directories exist (root and core), suggesting `collectstatic` output.

### 6.6 Backup Strategy

- **No backup configuration found in the codebase.**
- An `Atenea.sql` file exists at the project root, suggesting manual SQL dumps.
- **ASSUMPTION:** Bitnami may provide automated MariaDB backups, but this is not verified from the codebase.

### 6.7 Logging Configuration

- No Django `LOGGING` setting is configured in `settings.py`.
- Views use `logging.getLogger(__name__)` for email sending operations.
- Gunicorn is set to `loglevel = 'debug'` with `capture_output = True`.
- Debug prints (emoji-prefixed) in `Visita.save()` write directly to stdout.
- **No structured logging, no log rotation, no error alerting.**

---

## SECTION 7: Risk Assessment

### 7.1 Critical Risks

| # | Risk | Impact | Likelihood |
|---|------|--------|------------|
| C1 | **Hardcoded production credentials in settings.py (DB root password, Gmail password, PostHog API key, SECRET_KEY default)** | Complete system compromise. Credential exposure in version control. | HIGH — credentials are in committed code |
| C2 | **Database accessed as `root` user** | An application vulnerability could escalate to full database control including other databases on the server. | HIGH — current configuration |
| C3 | **Single Gunicorn worker** | One slow request (PDF gen, PostHog API call) blocks ALL traffic to the application. Site becomes unresponsive. | HIGH — regular occurrence expected |
| C4 | **No data backup strategy** | Database loss results in total clinical data loss for all patients and research. | MEDIUM — depends on Bitnami/AWS config |
| C5 | **`@csrf_exempt` on public appointment endpoint** | Automated abuse (appointment flooding, denial of service for scheduling). | MEDIUM |
| C6 | **No HTTPS enforcement at Django level** | Man-in-the-middle attacks possible if reverse proxy misconfigured. Session hijacking. | MEDIUM — depends on reverse proxy config |

### 7.2 Medium Risks

| # | Risk | Impact | Likelihood |
|---|------|--------|------------|
| M1 | **No role-based access control** | Any authenticated user can delete patients, projects, and manage other users (if they know the URL). | MEDIUM |
| M2 | **Patient data accessible via public document number lookup** | HIPAA/habeas data compliance violation. Patient exam results viewable by anyone who knows or guesses a `numero_documento`. | MEDIUM |
| M3 | **No test suite** | Regressions go undetected. Refactoring becomes dangerous. | HIGH |
| M4 | **10,911-line views.py / 5,670-line models.py** | Merge conflicts, development bottlenecks, impossible code review. | HIGH |
| M5 | **Debug print statements in production model code** | Performance impact, log pollution, potential information disclosure. | HIGH |
| M6 | **Missing `select_related`/`prefetch_related` everywhere** | Database overload under moderate traffic. Slow page loads. | HIGH |
| M7 | **No rate limiting on public endpoints** | Abuse of registration, scheduling, and exam submission endpoints. | MEDIUM |
| M8 | **Synchronous external API calls in request cycle** | PostHog API failures/slowness directly impacts user experience. | MEDIUM |

### 7.3 Low Risks

| # | Risk | Impact | Likelihood |
|---|------|--------|------------|
| L1 | **Unused `CustomUser` model** | Developer confusion. Potential migration issues if activated. | LOW |
| L2 | **SQLite database file (`db.sqlite3`) in repository** | May contain legacy data. Minor information disclosure. | LOW |
| L3 | **AppSeed copyright headers** | The project was scaffolded from AppSeed template. Verify licensing compliance. | LOW |
| L4 | **No Django security headers configured** | `SECURE_BROWSER_XSS_FILTER`, `X_FRAME_OPTIONS`, `SECURE_CONTENT_TYPE_NOSNIFF` not set. | LOW (browser mitigations exist) |
| L5 | **Duplicate choice definitions across models** | Maintenance burden; inconsistency risk. | LOW |
| L6 | **`rh` field referenced in forms but not visible in model** | Possible orphaned form field or missing model field. | LOW |
| L7 | **Emoji characters in production logs** | Log parsing tools may not handle UTF-8 emojis well. | LOW |

---

## SECTION 8: Refactoring Roadmap

### 8.1 Immediate Fixes (Sprint 1-2 — High Priority)

#### P0: Security Hardening
1. **Extract all secrets to `.env` file**
   - Move DB credentials, SECRET_KEY, EMAIL_HOST_PASSWORD, POSTHOG keys
   - Use `python-decouple` (already installed) for all sensitive values
   - Rotate all credentials immediately
   - Add `.env` to `.gitignore`

2. **Create a dedicated database user** with minimal privileges (SELECT, INSERT, UPDATE, DELETE on `ateneagrunecodb` only). Remove root access.

3. **Add Django security settings:**
   ```python
   SECURE_SSL_REDIRECT = True
   SECURE_HSTS_SECONDS = 31536000
   SESSION_COOKIE_SECURE = True
   CSRF_COOKIE_SECURE = True
   SECURE_BROWSER_XSS_FILTER = True
   SECURE_CONTENT_TYPE_NOSNIFF = True
   X_FRAME_OPTIONS = 'DENY'
   ```

4. **Remove `@csrf_exempt`** from `agendar_cita_ajax` — send CSRF token from the frontend.

5. **Add RBAC** — implement at minimum a `is_superuser` check on all destructive endpoints (delete patient, delete project, manage users).

#### P1: Production Stability
6. **Increase Gunicorn workers** to at least 3-4:
   ```python
   workers = 4
   timeout = 120
   loglevel = 'warning'
   ```

7. **Remove all debug print statements** from `Visita.save()` and any other production code.

8. **Add `select_related`/`prefetch_related`** to the most impacted querysets:
   - `Visita` queries: `select_related('paciente', 'Tipo_visita', 'Tipo_visita__proyecto', 'evaluador')`
   - `VisitaExamen` queries: `select_related('visita', 'examen', 'visita__paciente')`

9. **Configure Django `LOGGING`** with proper handlers, formatters, and rotation.

10. **Implement database backup strategy** — cron job for `mysqldump` with off-site storage (S3).

### 8.2 Mid-Term Improvements (Month 1-3)

#### Architecture
11. **Split `views.py`** into modules:
    ```
    views/
    ├── __init__.py          # re-exports
    ├── auth.py              # login, logout, profile, password
    ├── patients.py          # CRUD patient demographics
    ├── visits.py            # visit management
    ├── exams_sleep.py       # sleep exam save/view/edit
    ├── exams_anosognosia.py # anosognosia exam save/view/edit
    ├── exams_general.py     # general medical exam save/view/edit
    ├── scheduling.py        # appointment scheduling
    ├── projects.py          # project management
    ├── analytics.py         # PostHog integration
    └── pdf.py               # PDF generation
    ```

12. **Split `models.py`** into modules:
    ```
    models/
    ├── __init__.py
    ├── patient.py
    ├── project.py
    ├── visit.py
    ├── scheduling.py
    ├── results_sleep.py
    ├── results_anosognosia.py
    ├── results_general.py
    └── analytics.py
    ```

13. **Replace manual POST extraction with Django Forms/ModelForms** for all exam views. This adds validation, reduces code by ~60%, and prevents data integrity issues.

14. **Refactor `VisitaExamen.get_resultado_instance()`** — use a registry pattern or Django `ContentType` framework instead of iterating 30+ string lookups.

15. **Add pagination** to patient lists and other list views.

16. **Move PostHog API calls to async tasks** using Celery or Django-Q.

17. **Add rate limiting** on public endpoints (django-ratelimit).

18. **Implement proper RBAC** — consider `django-guardian` or custom permission groups (Admin, Doctor/Evaluator, Researcher, Read-Only).

#### Testing
19. **Set up test infrastructure** — pytest-django, factory_boy for model factories.
20. **Add smoke tests** for all URL endpoints (200 responses for authenticated/unauthenticated).
21. **Add unit tests** for all scoring calculations (Pittsburgh, Epworth, CDR, etc.).

### 8.3 Long-Term Architectural Improvements (Month 3-12)

22. **Split into multiple Django apps:**
    ```
    apps/
    ├── core/           # Auth, user management, base models
    ├── patients/       # Patient demographics, CRUD
    ├── clinical/       # Visits, exam framework
    ├── exams_sleep/    # Sleep-specific exams
    ├── exams_neuro/    # Anosognosia-specific exams
    ├── exams_general/  # General medical exams
    ├── scheduling/     # Appointment system
    ├── analytics/      # PostHog integration, statistics
    └── reports/        # PDF generation
    ```

23. **Introduce Django REST Framework** for API endpoints — replace manual JsonResponse construction with proper serializers, viewsets, and API versioning.

24. **Implement audit logging** — track who changed what clinical data and when (django-auditlog or django-simple-history).

25. **Add database migrations CI** — automated migration checks in CI/CD pipeline.

26. **Consider moving to PostgreSQL** — better JSON support, full-text search, and advanced indexing for clinical data.

27. **Implement FHIR compliance** — for interoperability with other health systems if required.

28. **Add monitoring** — Sentry for error tracking, Prometheus/Grafana for performance metrics.

29. **Implement CI/CD pipeline** — automated testing, linting, security scanning on every commit.

30. **Consider moving wide models to JSON storage** — `ExamenNeurologicoResult` (200+ columns) and `CuidadorNPIResult` (60+ columns) could benefit from a JSONField approach for infrequently queried fields while keeping key fields as model columns for filtering.

---

## Appendix A: Technology Stack Summary

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.9 (Dockerfile) |
| Framework | Django | 5.0.6 |
| Database | MariaDB | Bitnami-managed |
| WSGI Server | Gunicorn | 20.1.0 |
| Static Files | WhiteNoise | >=6.6.0 |
| PDF Generation | ReportLab | 4.0.4 |
| HTTP Client | Requests | 2.32.0 |
| Config Management | python-decouple | 3.4 |
| Image Processing | Pillow | 11.1.0 |
| Path Management | Unipath | 1.1 |
| MySQL Client | mysqlclient | 2.2.7 |
| Deployment | Bitnami on AWS EC2 | — |
| Container (Alt) | Docker + docker-compose | 3.8 |
| Reverse Proxy | Nginx (Docker) / Apache (Bitnami) | — |
| Analytics | PostHog | Cloud (us.posthog.com) |
| Email | Gmail SMTP | Port 587/TLS |

## Appendix B: URL Route Summary

| Category | Route Count | Auth Required |
|----------|-------------|---------------|
| Authentication | 4 | Mixed |
| Patient CRUD | 6 | Yes |
| Clinical Visits | 6 | Yes |
| Sleep Exams | 9 | Yes |
| Anosognosia Exams | 18 | Yes |
| General Medical Exams | 6 | Yes |
| Public Registration | 3 | No |
| Public Exams | 3 | No |
| Scheduling | 4 | Mixed |
| Analytics | 4 | Yes |
| Projects | 3 | Yes |
| Visit Types | 3 | Yes |
| PDF Generation | 2 | Yes |
| **Total** | **~71** | — |

## Appendix C: Model Count Summary

| Category | Model Count |
|----------|-------------|
| Scheduling | 4 |
| Patient/User | 3 |
| Project/Visit | 6 |
| Sleep Exam Results | 17 (incl. child models) |
| Anosognosia Results | 17 |
| General Medical Results | 22 (incl. 10 Antecedentes children) |
| Cognitive Anamnesis | 5 |
| Analytics | 2 |
| **Total** | **~76** |

---

*End of Technical Handover Document*
