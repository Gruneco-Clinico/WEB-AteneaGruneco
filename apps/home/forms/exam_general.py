# -*- encoding: utf-8 -*-
"""
ModelForms for general exam results.

Covers: AnalisisGeneral, ExamenFisico, ExamenNeurologico, Medicamentos,
RevisionSistemas, and CognitivoAnamnesis.

Child models (Diagnostico*, Medicamento, DetalleRevisionSistemas,
ActitudCognitiva, AtencionCognitiva, etc.) are still managed in the
views via getlist / JSON – only the parent form is defined here.
"""
from django import forms

from ..models import (
    AnalisisGeneralResult,
    ExamenFisicoResult,
    ExamenNeurologicoResult,
    MedicamentosResult,
    RevisionSistemasResult,
    CognitivoAnamnesisResult,
)


class AnalisisGeneralForm(forms.ModelForm):
    """Parent form only – child diagnostics (CIE10, DSMV, ICSD3, NoClasificado)
    stay in the view."""

    class Meta:
        model = AnalisisGeneralResult
        exclude = ["visita_examen"]


class ExamenFisicoForm(forms.ModelForm):
    """
    IMC is computed in clean().
    Checkbox groups (cuero_cabelludo, oidos, etc.) send "normal"/"anormal"
    via getlist; __init__ remaps to the two boolean model fields.
    """

    CHECKBOX_GROUPS = [
        "cuero_cabelludo", "oidos", "nariz", "cuello",
        "pared_abdominal", "curvatura_cervical", "curvatura_toracica",
        "curvatura_lumbar", "arcos_movimiento_superiores",
        "arcos_movimiento_inferiores", "asimetrias_inferiores",
        "asimetrias_superiores",
    ]

    class Meta:
        model = ExamenFisicoResult
        exclude = ["visita_examen"]

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            for group in self.CHECKBOX_GROUPS:
                values = data.getlist(group)
                data[f"{group}_normal"] = "normal" in values
                data[f"{group}_anormal"] = "anormal" in values
        super().__init__(data, *args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        talla = float(cleaned.get("talla") or 0)
        peso = float(cleaned.get("peso") or 0)
        if talla > 0 and peso > 0:
            talla_metros = talla / 100
            cleaned["imc"] = round(peso / (talla_metros ** 2), 2)
        else:
            cleaned["imc"] = 0.0
        return cleaned


class ExamenNeurologicoForm(forms.ModelForm):
    """
    Huge model (200+ fields).  ModelForm auto-generates all fields.
    No scoring in this exam, just field persistence.
    Empty strings are converted to None for nullable fields.
    """

    class Meta:
        model = ExamenNeurologicoResult
        exclude = ["visita_examen"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # All fields optional — HTML may send partial data
        for field in self.fields.values():
            field.required = False

    def clean(self):
        cleaned = super().clean()
        # Convert empty strings → None for nullable CharField/TextField
        for name, value in list(cleaned.items()):
            if value != "":
                continue
            try:
                mf = self.Meta.model._meta.get_field(name)
                if getattr(mf, "null", False):
                    cleaned[name] = None
            except Exception:
                pass
        return cleaned


class MedicamentosForm(forms.ModelForm):
    """Parent form only – child Medicamento entries stay in view."""

    class Meta:
        model = MedicamentosResult
        exclude = ["visita_examen"]


class RevisionSistemasForm(forms.ModelForm):
    """Parent form only – child DetalleRevisionSistemas stay in view."""

    class Meta:
        model = RevisionSistemasResult
        exclude = ["visita_examen"]


class CognitivoAnamnesisForm(forms.ModelForm):
    """
    Parent form – child models (ActitudCognitiva, AtencionCognitiva,
    ErrorLenguajeCognitivo, ActividadVidaDiaria, ActividadCompleja) stay in view.
    Note: This model uses a plain OneToOneField, not ResultadoExamenBase.
    """

    class Meta:
        model = CognitivoAnamnesisResult
        exclude = ["visita_examen", "fecha_creacion", "fecha_actualizacion"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
