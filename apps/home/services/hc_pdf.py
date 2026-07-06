# -*- encoding: utf-8 -*-
"""Generación PDF Historia Clínica vía WeasyPrint."""
import logging
import os

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from django.core.exceptions import ObjectDoesNotExist

from .exam_view_context import get_context_ver_examen

logger = logging.getLogger(__name__)


def _first_existing_path(candidates):
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def _project_dir():
    return getattr(settings, "CORE_DIR", os.path.dirname(str(settings.BASE_DIR)))


def _static_asset_path(*parts):
    return os.path.join(_project_dir(), "apps", "static", "assets", "img", *parts)


def _staticfiles_asset_path(*parts):
    return os.path.join(_project_dir(), "staticfiles", "assets", "img", *parts)


def _logo_gruneco_path():
    """Banner GRUNECO (image1 del .docx = GRUNECO_CPT_T.png)."""
    return _first_existing_path(
        [
            _static_asset_path("theme", "GRUNECO_CPT_T.png"),
            _staticfiles_asset_path("theme", "GRUNECO_CPT_T.png"),
            _static_asset_path("brand", "Logo_GRUNECO_Sin_Fondo.png"),
        ]
    )


def _logo_udea_path():
    """Logo Universidad de Antioquia / Facultad de Medicina (image2 del .docx)."""
    return _first_existing_path(
        [
            _static_asset_path("theme", "UdeA_FacultadMedicina_HC.png"),
            _staticfiles_asset_path("theme", "UdeA_FacultadMedicina_HC.png"),
            _static_asset_path("theme", "UdeA.jpeg"),
            _staticfiles_asset_path("theme", "UdeA.jpeg"),
        ]
    )


def _nombre_completo_paciente(paciente):
    partes = [
        paciente.primer_nombre,
        paciente.segundo_nombre,
        paciente.primer_apellido,
        paciente.segundo_apellido,
    ]
    return " ".join(p for p in partes if p)


def _file_url(*parts):
    path = os.path.join(_project_dir(), "apps", "static", *parts)
    if os.path.isfile(path):
        return f"file://{path}"
    return None


def _ver_embed_stylesheets():
    """Solo iconos para el PDF; Argon/Bootstrap no se cargan (inflan páginas en blanco)."""
    return [
        u
        for u in (
            _file_url(
                "assets",
                "vendor",
                "@fortawesome",
                "fontawesome-free",
                "css",
                "all.min.css",
            ),
        )
        if u
    ]


def _render_examen_ver_html(visita_examen):
    """Renderiza el mismo HTML que la vista 'Ver' (sin layout app)."""
    from ..exam_legacy import is_legacy_examen
    from ..form_builder.schema import normalize_schema

    embed_ctx = {
        "print_mode": True,
        "parent_template": "pdf/layouts/base_ver_embed.html",
    }

    if not is_legacy_examen(visita_examen.examen_id):
        try:
            submission = visita_examen.builder_submission
            return render_to_string(
                "examenes_builder/resultado_builder.html",
                {
                    "visita_examen": visita_examen,
                    "submission": submission,
                    "builder_fields": normalize_schema(visita_examen.examen.campos),
                    "paciente": visita_examen.visita.paciente,
                    **embed_ctx,
                },
            )
        except ObjectDoesNotExist:
            pass

    web_tpl, ctx = get_context_ver_examen(visita_examen)
    return render_to_string(web_tpl, {**ctx, **embed_ctx})


def _build_exam_sections(visita):
    sections = []
    for ve in visita.visita_examenes.filter(estado="completado").select_related(
        "examen"
    ):
        try:
            sections.append(
                {
                    "visita_examen": ve,
                    "examen_nombre": ve.examen.nombre,
                    "html": _render_examen_ver_html(ve),
                }
            )
        except Exception as exc:
            logger.warning(
                "PDF: omitiendo examen %s (%s): %s",
                ve.examen_id,
                ve.examen.nombre,
                exc,
            )
    return sections


def _load_print_css():
    for path in (
        os.path.join(_project_dir(), "apps", "static", "pdf", "print.css"),
        os.path.join(_project_dir(), "staticfiles", "pdf", "print.css"),
    ):
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return f.read()
    return ""


def render_historia_clinica_html(visita):
    paciente = visita.paciente
    evaluador = ""
    if visita.evaluador:
        evaluador = visita.evaluador.get_full_name() or visita.evaluador.username
    firmante = ""
    if visita.firmado_por:
        firmante = visita.firmado_por.get_full_name() or visita.firmado_por.username

    nombre_completo = _nombre_completo_paciente(paciente)
    tipo_doc = paciente.get_tipo_documento_display() if paciente.tipo_documento else ""
    documento_identidad = f"{tipo_doc} {paciente.numero_documento}".strip()
    doc_line = f"{nombre_completo} – {documento_identidad}".strip()

    context = {
        "visita": visita,
        "paciente": paciente,
        "nombre_completo": nombre_completo,
        "documento_identidad": documento_identidad,
        "doc_line": doc_line,
        "evaluador": evaluador,
        "firmante": firmante,
        "tipo_visita": visita.Tipo_visita.nombre if visita.Tipo_visita else "",
        "proyecto": (
            visita.Tipo_visita.proyecto.nombre
            if visita.Tipo_visita and visita.Tipo_visita.proyecto
            else ""
        ),
        "logo_gruneco_path": _logo_gruneco_path(),
        "logo_udea_path": _logo_udea_path(),
        "print_css": mark_safe(_load_print_css()),
        "ver_css_urls": _ver_embed_stylesheets(),
        "exam_sections": _build_exam_sections(visita),
    }
    return render_to_string("pdf/historia_clinica.html", context)


def html_to_pdf_bytes(html_string):
    from weasyprint import HTML

    base_url = _project_dir()
    return HTML(string=html_string, base_url=base_url).write_pdf()


def construir_pdf_weasyprint(visita):
    """Devuelve bytes del PDF o None si WeasyPrint falla."""
    try:
        html = render_historia_clinica_html(visita)
        return html_to_pdf_bytes(html)
    except Exception as exc:
        logger.exception("WeasyPrint falló para visita %s: %s", visita.id, exc)
        return None
