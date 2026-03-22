# -*- encoding: utf-8 -*-
"""
ModelForms for anosognosia exam results.

Each form maps to a Result model and excludes the 'visita_examen' FK
(which is set in the view via ExamSaveMixin.save_form).
"""
from django import forms

from ..models import (
    LawtonBrodyResult,
    CuidadorNPIResult,
    AdherenciaTerapeuticaResult,
    EuroQol5D5LResult,
    EuroQolEVASaludResult,
    MoCAResult,
    ParticipanteYesavageResult,
    ZaritResult,
    AQDCuidadorResult,
    AQDParticipanteResult,
    CDRCuidadorResult,
    CDRParticipanteResult,
    PuntajeCDRResult,
    RedLatSpanishResult,
    BettyFerrelResult,
    ConsentimientoInformadoParticipanteResult,
    ConsentimientoInformadoCuidadorResult,
    AnamnesisCuidadorResult,
    AnamnesisParticipanteResult,
    SeguimientoIntervencionesResult,
)


# ─── Helper mixin for HTML→model field remapping ───


class _TextoSuffixMixin:
    """
    Auto-remaps POST keys like 'field_texto' → 'field' for all model fields.
    Override _SUFFIX for non-standard suffixes (e.g. '_text' for LawtonBrody).
    _EXTRA_MAP handles one-off renames like 'total' → 'puntaje_total'.
    """
    _SUFFIX = "_texto"
    _EXTRA_MAP: dict = {}

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            model = self.__class__.Meta.model
            model_fields = {
                f.name for f in model._meta.get_fields()
                if hasattr(f, "name") and f.name not in ("id", "visita_examen")
            }
            for field_name in model_fields:
                html_key = f"{field_name}{self._SUFFIX}"
                if html_key in data:
                    data[field_name] = data[html_key]
            for html_key, model_key in self._EXTRA_MAP.items():
                if html_key in data:
                    data[model_key] = data[html_key]
        super().__init__(data, *args, **kwargs)


# ─── Simple ModelForms (no scoring, no field-name mapping needed) ───


class LawtonBrodyForm(_TextoSuffixMixin, forms.ModelForm):
    _SUFFIX = "_text"
    _EXTRA_MAP = {"total": "puntaje_total"}

    class Meta:
        model = LawtonBrodyResult
        exclude = ["visita_examen"]


class CuidadorNPIForm(forms.ModelForm):
    """
    NPI has complex HTML→model field mapping:
    - item_frecuencia_texto → item_frecuencia
    - item_gravedad_texto → item_gravedad
    - item_distres_texto → item_distres
    - item_resultado → item_F_G
    """

    NPI_ITEMS = [
        "ideas_delirantes", "alucinaciones", "agitacion", "depresion",
        "ansiedad", "euforia", "apatia", "desinhibicion",
        "irritabilidad", "conducta_motor", "sueno", "apetito",
    ]

    class Meta:
        model = CuidadorNPIResult
        exclude = ["visita_examen"]

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            for item in self.NPI_ITEMS:
                for suffix in ("_frecuencia", "_gravedad", "_distres"):
                    html_key = f"{item}{suffix}_texto"
                    if html_key in data:
                        data[f"{item}{suffix}"] = data[html_key]
                html_key = f"{item}_resultado"
                if html_key in data:
                    data[f"{item}_F_G"] = data[html_key]
        super().__init__(data, *args, **kwargs)


class AdherenciaTerapeuticaForm(forms.ModelForm):
    class Meta:
        model = AdherenciaTerapeuticaResult
        exclude = ["visita_examen"]


class EuroQol5D5LForm(forms.ModelForm):
    class Meta:
        model = EuroQol5D5LResult
        exclude = ["visita_examen"]


class EuroQolEVASaludForm(forms.ModelForm):
    class Meta:
        model = EuroQolEVASaludResult
        exclude = ["visita_examen"]


class ParticipanteYesavageForm(forms.ModelForm):
    class Meta:
        model = ParticipanteYesavageResult
        exclude = ["visita_examen"]


class ZaritForm(_TextoSuffixMixin, forms.ModelForm):
    class Meta:
        model = ZaritResult
        exclude = ["visita_examen"]


class AQDCuidadorForm(_TextoSuffixMixin, forms.ModelForm):
    class Meta:
        model = AQDCuidadorResult
        exclude = ["visita_examen"]


class AQDParticipanteForm(_TextoSuffixMixin, forms.ModelForm):
    class Meta:
        model = AQDParticipanteResult
        exclude = ["visita_examen"]


class CDRCuidadorForm(forms.ModelForm):
    class Meta:
        model = CDRCuidadorResult
        exclude = ["visita_examen"]


class CDRParticipanteForm(forms.ModelForm):
    class Meta:
        model = CDRParticipanteResult
        exclude = ["visita_examen"]


class PuntajeCDRForm(forms.ModelForm):
    class Meta:
        model = PuntajeCDRResult
        exclude = ["visita_examen"]


class RedLatSpanishForm(_TextoSuffixMixin, forms.ModelForm):
    class Meta:
        model = RedLatSpanishResult
        exclude = ["visita_examen"]


class BettyFerrelForm(_TextoSuffixMixin, forms.ModelForm):
    class Meta:
        model = BettyFerrelResult
        exclude = ["visita_examen"]


class ConsentimientoParticipanteForm(forms.ModelForm):
    class Meta:
        model = ConsentimientoInformadoParticipanteResult
        exclude = ["visita_examen"]


class ConsentimientoCuidadorForm(forms.ModelForm):
    class Meta:
        model = ConsentimientoInformadoCuidadorResult
        exclude = ["visita_examen"]


class AnamnesisCuidadorForm(forms.ModelForm):
    class Meta:
        model = AnamnesisCuidadorResult
        exclude = ["visita_examen"]


class AnamnesisParticipanteForm(forms.ModelForm):
    class Meta:
        model = AnamnesisParticipanteResult
        exclude = ["visita_examen"]


# ─── MoCA: Complex scoring in clean() ───


class MoCAForm(forms.ModelForm):
    """
    MoCA has extensive scoring computed from raw answers.
    The clean() method replicates the scoring logic currently in the view.
    """

    HTML_FIELD_MAP = {
        "frase_1": "repeticion_frase_1",
        "frase_2": "repeticion_frase_2",
    }

    class Meta:
        model = MoCAResult
        exclude = ["visita_examen",
                   "puntaje_total",
        "interpretacion",
        "atencion",
        "repeticion",
        "fluidez",
        "diferido",
        "orientacion",
        "concentracion_resultado",]

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            for html_key, model_key in self.HTML_FIELD_MAP.items():
                if html_key in data and model_key not in data:
                    data[model_key] = data[html_key]
        super().__init__(data, *args, **kwargs)

    def clean(self):
        cleaned = super().clean()

        # ── Atención composite ──
        atencion_secuencia = cleaned.get("atencion_secuencia", 0) or 0
        atencion_inversa = cleaned.get("atencion_inversa", 0) or 0

        # Concentración: 0 errors → 1pt
        errores = cleaned.get("errores_concentracion", 0) or 0
        concentracion_val = 1 if errores == 0 else 0
        cleaned["concentracion_resultado"] = "no_fallo" if concentracion_val else "fallo"

        # Sustracción: count correct answers
        sustraccion_count = sum(
            1 for i in range(1, 6) if cleaned.get(f"sustraccion_{i}", False)
        )
        # Scoring: 4-5 correct →3pts, 2-3 →2pts, 1 →1pt, 0 →0pts
        if sustraccion_count >= 4:
            sustraccion_puntaje = 3
        elif sustraccion_count >= 2:
            sustraccion_puntaje = 2
        elif sustraccion_count == 1:
            sustraccion_puntaje = 1
        else:
            sustraccion_puntaje = 0

        atencion_total = int(atencion_secuencia) + int(atencion_inversa) + concentracion_val + sustraccion_puntaje
        cleaned["atencion"] = min(atencion_total, 6)

        # ── Repetición ──
        rep1 = 1 if cleaned.get("repeticion_frase_1", False) else 0
        rep2 = 1 if cleaned.get("repeticion_frase_2", False) else 0
        cleaned["repeticion"] = rep1 + rep2

        # ── Fluidez ──
        num_palabras = cleaned.get("numero_palabras_fluidez", 0) or 0
        cleaned["fluidez"] = 1 if int(num_palabras) >= 11 else 0

        # ── Diferido (recuerdo) ──
        recall_fields = ["palabra_rostro", "palabra_seda", "palabra_iglesia", "palabra_clavel", "palabra_rojo"]
        cleaned["diferido"] = sum(1 for f in recall_fields if cleaned.get(f, False))

        # ── Orientación ──
        orient_fields = [
            "orientacion_fecha", "orientacion_mes", "orientacion_anio",
            "orientacion_dia_semana", "orientacion_lugar", "orientacion_localidad",
        ]
        cleaned["orientacion"] = sum(1 for f in orient_fields if cleaned.get(f, False))

        # ── Puntaje total ──
        alternancia = int(cleaned.get("alternancia", 0) or 0)
        cubo = int(cleaned.get("cubo", 0) or 0)
        reloj = int(cleaned.get("reloj", 0) or 0)
        denominacion = int(cleaned.get("denominacion", 0) or 0)
        abstraccion = int(cleaned.get("abstraccion", 0) or 0)

        puntaje = (
            alternancia + cubo + reloj + denominacion
            + cleaned["atencion"]
            + cleaned["repeticion"]
            + cleaned["fluidez"]
            + abstraccion
            + cleaned["diferido"]
            + cleaned["orientacion"]
        )

        # Educación baja: +1 point
        if cleaned.get("educacion_baja", False):
            puntaje += 1

        cleaned["puntaje_total"] = min(puntaje, 30)

        # ── Interpretación ──
        pt = cleaned["puntaje_total"]
        if pt >= 26:
            cleaned["interpretacion"] = "Normal"
        elif pt >= 18:
            cleaned["interpretacion"] = "Deterioro cognitivo leve"
        else:
            cleaned["interpretacion"] = "Deterioro cognitivo significativo"

        return cleaned


# ─── Intervenciones: uses ForeignKey (not OneToOne), composite key ───


class SeguimientoIntervencionesForm(forms.ModelForm):
    """
    SeguimientoIntervencionesResult uses ForeignKey + unique_together
    instead of the standard OneToOneField pattern.
    The view must handle lookup by (visita_examen, numero_sesion).
    """

    HTML_FIELD_MAP = {
        "num_sesion": "numero_sesion",
        "nombre": "nombre_sesion",
    }

    class Meta:
        model = SeguimientoIntervencionesResult
        exclude = ["visita_examen"]

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            for html_key, model_key in self.HTML_FIELD_MAP.items():
                if html_key in data and model_key not in data:
                    data[model_key] = data[html_key]
        super().__init__(data, *args, **kwargs)
