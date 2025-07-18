# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib import admin
from .models import (
    Proyecto,
    DatosDemograficos,
    Visita,
    VisitaExamen,
    Examen,
    PittsburghResult,
    EpworthResult,
    MEWResult,
    BerlinResult,
    SuenoAnamnesisResult,
    TipoQuejaSueno,
    SintomaSueno,
    SintomaDiurnoSueno,
    SustanciaSueno,
    MedicamentoSueno,
    PantallaSueno,
    ActividadEnCamaSueno,
    ActividadFisicaSueno,
    ISIResult,
    AtenasResult,
    SuenoFisicoResult,
    StopBangResult,
)

admin.site.register(Proyecto)
admin.site.register(Visita)
admin.site.register(Examen)
admin.site.register(VisitaExamen)
admin.site.register(DatosDemograficos)
admin.site.register(PittsburghResult)
admin.site.register(EpworthResult)
admin.site.register(MEWResult)
admin.site.register(BerlinResult)
admin.site.register(SuenoAnamnesisResult)
admin.site.register(TipoQuejaSueno)
admin.site.register(SintomaSueno)
admin.site.register(SintomaDiurnoSueno)
admin.site.register(MedicamentoSueno)
admin.site.register(PantallaSueno)
admin.site.register(ActividadEnCamaSueno)
admin.site.register(ActividadFisicaSueno)
admin.site.register(SustanciaSueno)
admin.site.register(ISIResult)
admin.site.register(AtenasResult)
admin.site.register(StopBangResult)
admin.site.register(SuenoFisicoResult)
