# -*- encoding: utf-8 -*-
"""
PDF generation for clinical history (Historia Clínica Electrónica).

Exposes:
    - generar_pdf_historia_clinica_visita  (view — download PDF)
    - construir_pdf_visita                 (reusable builder used by firmar_visita)
    - _extraer_informacion_resultado       (field extractor kept for backward compat)
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from datetime import datetime
from ..models import *
import logging
import os

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from io import BytesIO

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour palette — institutional, sober
# ---------------------------------------------------------------------------
_CLR_PRIMARY = colors.HexColor("#2c3e50")      # dark navy
_CLR_ACCENT  = colors.HexColor("#1a5632")      # GRUNECO green
_CLR_HEADER  = colors.HexColor("#ecf0f1")      # light grey header bg
_CLR_ROW_ALT = colors.HexColor("#f7f9fa")      # row alternation
_CLR_BORDER  = colors.HexColor("#bdc3c7")      # grid borders
_CLR_SCORE   = colors.HexColor("#d4edda")      # score highlight bg
_CLR_CLASSIF = colors.HexColor("#fff3cd")      # classification highlight bg
_CLR_MUTED   = colors.HexColor("#6c757d")      # muted text

# ---------------------------------------------------------------------------
# Logo discovery (try user-specified path first, fallback to previous)
# ---------------------------------------------------------------------------
def _get_logo_path():
    candidates = [
        os.path.join(settings.BASE_DIR, "staticfiles", "assets", "img", "theme", "GRUNECO_CPT_T.png"),
        os.path.join(settings.BASE_DIR, "apps", "static", "assets", "img", "brand", "Logo_GRUNECO_Sin_Fondo.png"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _get_udea_logo_path():
    candidates = [
        os.path.join(settings.BASE_DIR, "staticfiles", "assets", "img", "theme", "UdeA.jpeg"),
        os.path.join(settings.BASE_DIR, "apps", "static", "assets", "img", "theme", "UdeA.jpeg"),
        os.path.join(settings.BASE_DIR, "staticfiles", "assets", "img", "theme", "universidad-antioquia.jpg"),
        os.path.join(settings.BASE_DIR, "apps", "static", "assets", "img", "theme", "universidad-antioquia.jpg"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


# ---------------------------------------------------------------------------
# Shared styles factory
# ---------------------------------------------------------------------------
def _make_styles():
    base = getSampleStyleSheet()
    s = {}
    s["title"] = ParagraphStyle(
        "hce_title", parent=base["Heading1"],
        fontSize=15, fontName="Helvetica-Bold",
        textColor=_CLR_PRIMARY, alignment=TA_CENTER,
        spaceAfter=2, spaceBefore=0,
    )
    s["subtitle"] = ParagraphStyle(
        "hce_subtitle", parent=base["Normal"],
        fontSize=8, fontName="Helvetica",
        textColor=_CLR_MUTED, alignment=TA_CENTER,
        spaceAfter=6,
    )
    s["heading"] = ParagraphStyle(
        "hce_heading", parent=base["Heading2"],
        fontSize=11, fontName="Helvetica-Bold",
        textColor=_CLR_PRIMARY, spaceBefore=14, spaceAfter=6,
    )
    s["normal"] = ParagraphStyle(
        "hce_normal", parent=base["Normal"],
        fontSize=9, fontName="Helvetica",
        alignment=TA_JUSTIFY, spaceAfter=4,
        leading=12,
    )
    s["small"] = ParagraphStyle(
        "hce_small", parent=base["Normal"],
        fontSize=8, fontName="Helvetica",
        textColor=_CLR_MUTED, spaceAfter=2,
    )
    s["label"] = ParagraphStyle(
        "hce_label", parent=base["Normal"],
        fontSize=9, fontName="Helvetica-Bold",
        textColor=_CLR_PRIMARY,
    )
    s["score"] = ParagraphStyle(
        "hce_score", parent=base["Normal"],
        fontSize=11, fontName="Helvetica-Bold",
        alignment=TA_CENTER, textColor=_CLR_ACCENT,
    )
    s["classif"] = ParagraphStyle(
        "hce_classif", parent=base["Normal"],
        fontSize=10, fontName="Helvetica-Bold",
        alignment=TA_CENTER, textColor=colors.HexColor("#856404"),
    )
    s["footer"] = ParagraphStyle(
        "hce_footer", parent=base["Normal"],
        fontSize=7, fontName="Helvetica-Oblique",
        textColor=_CLR_MUTED, alignment=TA_CENTER,
    )
    return s


# ---------------------------------------------------------------------------
# Table style helpers
# ---------------------------------------------------------------------------
_PATIENT_TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), _CLR_PRIMARY),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME",  (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE",  (0, 0), (-1, 0), 10),
    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ("TOPPADDING",    (0, 0), (-1, 0), 8),
    ("BACKGROUND", (0, 1), (0, -1), _CLR_HEADER),
    ("FONTNAME",   (0, 1), (0, -1), "Helvetica-Bold"),
    ("FONTSIZE",   (0, 1), (-1, -1), 9),
    ("GRID",       (0, 0), (-1, -1), 0.5, _CLR_BORDER),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _CLR_ROW_ALT]),
    ("TOPPADDING",    (0, 1), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
    ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
])

_EXAM_FIELD_TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), _CLR_HEADER),
    ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE",   (0, 0), (-1, 0), 8),
    ("TEXTCOLOR",  (0, 0), (-1, 0), _CLR_PRIMARY),
    ("FONTSIZE",   (0, 1), (-1, -1), 8),
    ("GRID",       (0, 0), (-1, -1), 0.4, _CLR_BORDER),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _CLR_ROW_ALT]),
    ("TOPPADDING",    (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ("VALIGN",        (0, 0), (-1, -1), "TOP"),
])


# ---------------------------------------------------------------------------
# Field extraction utilities
# ---------------------------------------------------------------------------
_SKIP_FIELDS = frozenset([
    "id", "visita_examen", "visita_examen_id",
    "created_at", "updated_at",
    "puntaje_total", "puntuacion_total", "puntuacion",
    "interpretacion", "clasificacion",
    "factor1_interpretacion", "factor2_interpretacion", "factor3_interpretacion",
    "cdr_interpretacion",
])

_SCORE_FIELD_NAMES = frozenset([
    "puntaje_total", "puntuacion_total", "puntuacion",
])

_CLASSIF_FIELD_NAMES = frozenset([
    "interpretacion", "clasificacion",
    "factor1_interpretacion", "factor2_interpretacion", "factor3_interpretacion",
    "cdr_interpretacion",
])


def _format_value(valor):
    """Human-friendly formatting for a single field value."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, bool):
        return "Si" if valor else "No"
    if isinstance(valor, float):
        return f"{valor:.1f}"
    if hasattr(valor, "strftime"):
        return valor.strftime("%d/%m/%Y")
    s = str(valor).strip()
    return s if s else None


def _field_label(field):
    """Get human-readable label for a model field."""
    if hasattr(field, "verbose_name") and field.verbose_name:
        lbl = str(field.verbose_name)
        return lbl[0].upper() + lbl[1:] if lbl else field.name
    return field.name.replace("_", " ").title()


def _extract_exam_data(resultado):
    """
    Returns (fields_list, score_value, classifications_list) from a result instance.
    fields_list: [(label, value), ...]
    score_value: str or None
    classifications_list: [(label, value), ...]
    """
    if not resultado:
        return [], None, []

    from django.db import models as db_models

    fields_list = []
    score_value = None
    classifications = []

    try:
        model_fields = resultado._meta.get_fields()
        for field in model_fields:
            if isinstance(field, (db_models.ForeignKey, db_models.OneToOneField,
                                  db_models.ManyToManyField, db_models.ManyToOneRel,
                                  db_models.ManyToManyRel, db_models.OneToOneRel)):
                continue
            name = field.name
            if name.startswith("_"):
                continue

            try:
                raw = getattr(resultado, name, None)
            except Exception:
                continue

            formatted = _format_value(raw)
            if formatted is None:
                continue

            label = _field_label(field)

            if name in _SCORE_FIELD_NAMES:
                score_value = formatted
            elif name in _CLASSIF_FIELD_NAMES:
                classifications.append((label, formatted))
            elif name not in _SKIP_FIELDS:
                fields_list.append((label, formatted))
    except Exception as e:
        logger.error("Error extracting exam data: %s", e)

    return fields_list, score_value, classifications


def _extraer_informacion_resultado(resultado):
    """
    Legacy helper kept for backward compatibility (used by firmar_visita in visits.py).
    Returns HTML-ish string with <br/> separators.
    """
    fields, score, classifs = _extract_exam_data(resultado)
    parts = []
    if score:
        parts.append(f"<b>Puntaje Total: {score}</b>")
    for lbl, val in classifs:
        parts.append(f"<b>{lbl}:</b> {val}")
    for lbl, val in fields:
        parts.append(f"{lbl}: {val}")
    return "<br/>".join(parts) if parts else None


# ---------------------------------------------------------------------------
# PDF element builders
# ---------------------------------------------------------------------------
def _build_header(elements, styles, visita, paciente):
    """Institutional header: dual logos (GRUNECO + UdeA) + title + patient/visit id line."""
    gruneco_path = _get_logo_path()
    udea_path = _get_udea_logo_path()

    # Build a row with logos on each side and title in the centre
    logo_left = ""
    logo_right = ""
    try:
        if gruneco_path:
            logo_left = Image(gruneco_path, width=1.4 * inch, height=0.55 * inch, kind="proportional")
        if udea_path:
            logo_right = Image(udea_path, width=1.0 * inch, height=0.55 * inch, kind="proportional")
    except Exception:
        pass

    if logo_left or logo_right:
        title_para = Paragraph("HISTORIA CLINICA ELECTRONICA", styles["title"])
        logo_row = Table(
            [[logo_left or "", title_para, logo_right or ""]],
            colWidths=[1.6 * inch, 3.8 * inch, 1.1 * inch],
        )
        logo_row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ]))
        elements.append(logo_row)
        elements.append(Spacer(1, 0.06 * inch))
    else:
        elements.append(Paragraph("HISTORIA CLINICA ELECTRONICA", styles["title"]))

    elements.append(Paragraph("Sistema ATENEA - GRUNECO | Universidad de Antioquia", styles["subtitle"]))

    # Thin divider
    elements.append(HRFlowable(
        width="100%", thickness=1.2, color=_CLR_PRIMARY,
        spaceAfter=8, spaceBefore=2,
    ))

    # Quick-reference line (patient, document, date, code)
    codigo = f"ATG-{paciente.id:05d}"
    fecha_str = visita.fecha.strftime("%d/%m/%Y") if visita.fecha else "N/A"
    ref_text = (
        f"<b>Paciente:</b> {paciente.primer_nombre} {paciente.primer_apellido}  |  "
        f"<b>Doc:</b> {paciente.numero_documento}  |  "
        f"<b>Fecha:</b> {fecha_str}  |  "
        f"<b>Codigo:</b> {codigo}"
    )
    elements.append(Paragraph(ref_text, styles["small"]))
    elements.append(Spacer(1, 0.1 * inch))


def _build_patient_section(elements, styles, paciente):
    """Datos del paciente table."""
    elements.append(Paragraph("INFORMACION GENERAL DEL PACIENTE", styles["heading"]))

    nombre_completo = " ".join(filter(None, [
        paciente.primer_nombre,
        getattr(paciente, "segundo_nombre", None) or "",
        paciente.primer_apellido,
        getattr(paciente, "segundo_apellido", None) or "",
    ])).strip()

    rows = [
        ["Campo", "Valor"],
        ["Nombre completo", nombre_completo],
        ["Tipo de documento", getattr(paciente, "tipo_documento", "N/A")],
        ["Numero de documento", str(paciente.numero_documento)],
        ["Edad", str(getattr(paciente, "edad", "N/A"))],
        ["Fecha de nacimiento", str(getattr(paciente, "fecha_nacimiento", "N/A"))],
        ["EPS", getattr(paciente, "eps", None) or "N/A"],
        ["Telefono", getattr(paciente, "celular", None) or "N/A"],
    ]

    t = Table(rows, colWidths=[2.2 * inch, 4.3 * inch])
    t.setStyle(_PATIENT_TABLE_STYLE)
    elements.append(t)
    elements.append(Spacer(1, 0.12 * inch))


def _build_visit_section(elements, styles, visita):
    """Informacion de la visita."""
    elements.append(Paragraph("INFORMACION DE LA VISITA", styles["heading"]))

    evaluador = "N/A"
    if visita.evaluador:
        evaluador = visita.evaluador.get_full_name() or visita.evaluador.username

    rows = [
        ["Campo", "Valor"],
        ["Nombre de visita", visita.nombre or "N/A"],
        ["Tipo de visita", visita.Tipo_visita.nombre if visita.Tipo_visita else "N/A"],
        ["Fecha", visita.fecha.strftime("%d de %B de %Y") if visita.fecha else "N/A"],
        ["Evaluador", evaluador],
        ["Proyecto", visita.Tipo_visita.proyecto.nombre if visita.Tipo_visita and visita.Tipo_visita.proyecto else "N/A"],
        ["Estado", "Firmada y cerrada" if visita.firmado else "Abierta"],
    ]

    if getattr(visita, "acompanante_nombre", None):
        rows.append(["Acompanante", visita.acompanante_nombre])
        rows.append(["Relacion", getattr(visita, "acompanante_relacion", None) or "N/A"])

    t = Table(rows, colWidths=[2.2 * inch, 4.3 * inch])
    t.setStyle(_PATIENT_TABLE_STYLE)
    elements.append(t)
    elements.append(Spacer(1, 0.15 * inch))


# ---------------------------------------------------------------------------
# Sueño Anamnesis — child model renderer
# ---------------------------------------------------------------------------
_ANAMNESIS_CHILD_SECTIONS = [
    ("tipos_queja_detalle", "Quejas de sueño", ["nombre", "inicio", "evolucion", "frecuencia", "gravedad"]),
    ("sustancias", "Sustancias", ["tipo", "cantidad", "frecuencia", "tiempo", "observaciones"]),
    ("medicamentos", "Medicamentos", ["nombre", "dosis", "presentacion", "veces_dia", "frecuencia", "tiempo", "observaciones"]),
    ("pantallas", "Uso de pantallas", ["tipo", "frecuencia", "tiempo_antes_dormir"]),
    ("actividades_en_cama", "Actividades en cama", ["tipo", "frecuencia", "observaciones"]),
    ("actividades_fisicas", "Actividades físicas", ["tipo", "intensidad", "frecuencia", "observaciones"]),
    ("sintomas_suenos", "Síntomas de sueño", ["tipo", "cuando_inicio", "evolucion", "frecuencia", "gravedad", "observaciones"]),
    ("sintomas_diurno", "Síntomas diurnos", ["tipo", "cuando_inicio", "evolucion", "frecuencia", "gravedad", "observaciones"]),
]


def _build_anamnesis_children(elements, styles, anamnesis):
    """Render child-model tables for SuenoAnamnesisResult."""
    for related_name, title, col_names in _ANAMNESIS_CHILD_SECTIONS:
        qs = getattr(anamnesis, related_name, None)
        if qs is None:
            continue
        items = qs.all()
        if not items.exists():
            continue

        elements.append(Spacer(1, 0.06 * inch))
        elements.append(Paragraph(f"<b>{title}</b>", styles["small"]))

        header = [Paragraph(f"<b>{c.replace('_', ' ').title()}</b>", styles["small"]) for c in col_names]
        rows = [header]
        for item in items:
            row = [Paragraph(str(getattr(item, c, "") or ""), styles["small"]) for c in col_names]
            rows.append(row)

        col_width = 6.5 * inch / len(col_names)
        t = Table(rows, colWidths=[col_width] * len(col_names))
        t.setStyle(_EXAM_FIELD_TABLE_STYLE)
        elements.append(t)


def _build_exam_section(elements, styles, visita_examen, index):
    """Build a single exam result section with Q&A table, score box, classification."""
    resultado = visita_examen.get_resultado_instance()
    exam_name = visita_examen.examen.nombre

    # Section title
    title_parts = [f"<b>{index}. {exam_name}</b>"]
    if visita_examen.fecha_completado:
        title_parts.append(
            f"<font size=7 color='#6c757d'>    Completado: "
            f"{visita_examen.fecha_completado.strftime('%d/%m/%Y %H:%M')}</font>"
        )
    elements.append(Paragraph("".join(title_parts), styles["normal"]))

    if not resultado:
        elements.append(Paragraph(
            "<i>Sin resultado registrado para este examen.</i>", styles["small"]
        ))
        elements.append(Spacer(1, 0.08 * inch))
        return

    fields, score_val, classifs = _extract_exam_data(resultado)

    # --- Score highlight box ---
    if score_val is not None:
        score_data = [[Paragraph(f"Puntaje Total: <b>{score_val}</b>", styles["score"])]]
        score_table = Table(score_data, colWidths=[3.5 * inch])
        score_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _CLR_SCORE),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 0.8, _CLR_ACCENT),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        score_table.hAlign = "LEFT"
        elements.append(Spacer(1, 0.04 * inch))
        elements.append(score_table)
        elements.append(Spacer(1, 0.04 * inch))

    # --- Classification / Interpretation box ---
    if classifs:
        for clbl, cval in classifs:
            cls_data = [[Paragraph(f"{clbl}: <b>{cval}</b>", styles["classif"])]]
            cls_table = Table(cls_data, colWidths=[4.5 * inch])
            cls_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), _CLR_CLASSIF),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#ffc107")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            cls_table.hAlign = "LEFT"
            elements.append(cls_table)
            elements.append(Spacer(1, 0.03 * inch))

    # --- Questions / Answers table ---
    if fields:
        header = [
            Paragraph("<b>Pregunta / Campo</b>", styles["small"]),
            Paragraph("<b>Respuesta / Valor</b>", styles["small"]),
        ]
        rows = [header]
        for lbl, val in fields:
            rows.append([
                Paragraph(str(lbl), styles["small"]),
                Paragraph(str(val), styles["small"]),
            ])

        t = Table(rows, colWidths=[3.0 * inch, 3.5 * inch])
        t.setStyle(_EXAM_FIELD_TABLE_STYLE)
        elements.append(Spacer(1, 0.04 * inch))
        elements.append(t)

    # --- Sueño Anamnesis: child model tables ---
    try:
        from ..models import SuenoAnamnesisResult
        if isinstance(resultado, SuenoAnamnesisResult):
            _build_anamnesis_children(elements, styles, resultado)
    except Exception as e:
        logger.debug("Skipping anamnesis children: %s", e)

    # --- Examiner notes ---
    if visita_examen.notas_examinador:
        elements.append(Spacer(1, 0.04 * inch))
        elements.append(Paragraph(
            f"<i>Notas del examinador: {visita_examen.notas_examinador}</i>",
            styles["small"],
        ))

    # Thin separator between exams
    elements.append(Spacer(1, 0.06 * inch))
    elements.append(HRFlowable(
        width="80%", thickness=0.4, color=_CLR_BORDER,
        spaceAfter=6, spaceBefore=2,
    ))


def _build_signature_section(elements, styles, visita):
    """Professional signature block."""
    if not visita.firmado_por:
        return

    elements.append(Spacer(1, 0.15 * inch))
    elements.append(HRFlowable(
        width="100%", thickness=0.6, color=_CLR_BORDER,
        spaceAfter=8, spaceBefore=4,
    ))

    firmante = visita.firmado_por.get_full_name() or visita.firmado_por.username

    try:
        from apps.home.models import UserProfile
        perfil = UserProfile.objects.filter(user=visita.firmado_por).first()

        if perfil and perfil.firma and perfil.firma.startswith("data:"):
            # Decode base64 signature image
            try:
                _header, b64data = perfil.firma.split(",", 1)
                import base64
                sig_bytes = base64.b64decode(b64data)
                sig_buffer = BytesIO(sig_bytes)
                sig_img = Image(sig_buffer, width=2 * inch, height=0.7 * inch, kind="proportional")
                sig_img.hAlign = "LEFT"
                elements.append(sig_img)
                elements.append(Spacer(1, 0.04 * inch))
            except Exception:
                pass

        elements.append(Paragraph(
            f"<b>Firmado por:</b> {firmante}", styles["normal"],
        ))
        elements.append(Paragraph(
            "<i>Firma digital registrada en el sistema</i>", styles["small"],
        ))
    except Exception as e:
        logger.error("Error processing professional signature: %s", e)
        elements.append(Paragraph(f"<b>Firmado por:</b> {firmante}", styles["normal"]))


def _build_footer(elements, styles):
    """Document generation timestamp."""
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(HRFlowable(
        width="100%", thickness=0.5, color=_CLR_BORDER,
        spaceAfter=4, spaceBefore=4,
    ))
    elements.append(Paragraph(
        f"Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')} - "
        "Sistema ATENEA | GRUNECO - Universidad de Antioquia",
        styles["footer"],
    ))


# ---------------------------------------------------------------------------
# Public: reusable PDF builder
# ---------------------------------------------------------------------------
def construir_pdf_visita(buffer, visita, examen_ids=None):
    """
    Build the clinical-history PDF for *visita* into *buffer* (a BytesIO).
    Prefiere WeasyPrint; si falla, usa ReportLab legacy.

    ``examen_ids``: lista opcional de IDs de VisitaExamen a incluir y su orden.
    """
    from ..services.hc_pdf import construir_pdf_weasyprint

    pdf_bytes = construir_pdf_weasyprint(visita, examen_ids=examen_ids)
    if pdf_bytes:
        buffer.write(pdf_bytes)
        buffer.seek(0)
        return

    logger.warning(
        "WeasyPrint no disponible para visita %s; usando ReportLab legacy.",
        visita.id,
    )
    _construir_pdf_visita_reportlab(buffer, visita)


def _construir_pdf_visita_reportlab(buffer, visita):
    """Generación PDF legacy con ReportLab."""
    paciente = visita.paciente

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=0.7 * inch, leftMargin=0.7 * inch,
        topMargin=0.65 * inch, bottomMargin=0.6 * inch,
    )

    styles = _make_styles()
    elements = []

    # 1. Header with logo
    _build_header(elements, styles, visita, paciente)

    # 2. Patient info
    _build_patient_section(elements, styles, paciente)

    # 3. Visit info
    _build_visit_section(elements, styles, visita)

    # 4. Exam results
    examenes_realizados = visita.visita_examenes.filter(estado="completado")
    if examenes_realizados.exists():
        elements.append(Paragraph(
            f"RESULTADOS DE EXAMENES ({examenes_realizados.count()})", styles["heading"],
        ))
        for idx, ve in enumerate(examenes_realizados, 1):
            _build_exam_section(elements, styles, ve, idx)
    else:
        elements.append(Paragraph("EXAMENES REALIZADOS", styles["heading"]))
        elements.append(Paragraph(
            "No hay examenes completados en esta visita.", styles["normal"],
        ))

    # 5. Signature
    _build_signature_section(elements, styles, visita)

    # 6. Notas aclaratorias (editable post-firma)
    if visita.notas_aclaratorias:
        elements.append(Spacer(1, 0.12 * inch))
        elements.append(Paragraph("NOTAS ACLARATORIAS", styles["heading"]))
        elements.append(Paragraph(
            visita.notas_aclaratorias.replace("\n", "<br/>"),
            styles["normal"],
        ))

    # 7. Footer
    _build_footer(elements, styles)

    doc.build(elements)
    buffer.seek(0)


# ---------------------------------------------------------------------------
# Helper: parse selección/orden de exámenes desde el request (A-04)
# ---------------------------------------------------------------------------
def _parse_examen_ids(request, visita):
    """Devuelve la lista ordenada de IDs de VisitaExamen a imprimir.

    Lee ``examen_ids`` del POST (checkboxes) o del GET (``examenes=1,2,3``).
    Retorna ``None`` cuando no hay selección (=> imprimir todo).
    """
    raw = None
    if request.method == "POST":
        raw = request.POST.getlist("examen_ids")
    if not raw:
        qs = request.GET.get("examenes")
        if qs:
            raw = [p for p in qs.split(",") if p]
    if not raw:
        return None
    ids = []
    for value in raw:
        try:
            ids.append(int(value))
        except (TypeError, ValueError):
            continue
    return ids or None


# ---------------------------------------------------------------------------
# View: selección de impresión (A-04)
# ---------------------------------------------------------------------------
@login_required
def seleccionar_impresion_visita(request, visita_id):
    """Muestra el formulario para elegir qué exámenes imprimir y su orden."""
    from django.shortcuts import render

    visita = get_object_or_404(Visita, id=visita_id)
    examenes = list(
        visita.visita_examenes.filter(estado="completado").select_related("examen")
    )
    context = {
        "visita": visita,
        "paciente": visita.paciente,
        "examenes": examenes,
    }
    return render(request, "info_paciente/seleccionar_impresion.html", context)


# ---------------------------------------------------------------------------
# View: download PDF
# ---------------------------------------------------------------------------
@login_required
def generar_pdf_historia_clinica_visita(request, visita_id):
    """Genera y descarga un PDF con la historia clinica de una visita.

    Acepta selección y orden de exámenes vía ``examen_ids`` (POST) o
    ``examenes=1,2,3`` (GET). Sin selección => imprime todos (A-04).
    """
    try:
        visita = get_object_or_404(Visita, id=visita_id)
        examen_ids = _parse_examen_ids(request, visita)
        buffer = BytesIO()
        construir_pdf_visita(buffer, visita, examen_ids=examen_ids)

        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="Resumen_Digital_Atencion_Visita_{visita_id}'
            f'_{datetime.now().strftime("%Y%m%d")}.pdf"'
        )
        return response

    except Exception as e:
        import traceback
        logger.error("Error generando PDF: %s\n%s", e, traceback.format_exc())
        messages.error(request, f"Error al generar el PDF: {e}")
        return redirect(request.META.get("HTTP_REFERER", "home"))

