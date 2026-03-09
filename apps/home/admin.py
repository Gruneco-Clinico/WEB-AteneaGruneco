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
    BerlinResult,
    SuenoAnamnesisResult,
    TipoQuejaSueno,
    SintomaSueno,
)


class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'investigador_principal', 'fecha_inicio', 'tiene_consentimiento')
    list_filter = ('fecha_inicio',)
    search_fields = ('nombre', 'investigador_principal', 'codigo_siu')
    fieldsets = (
        ('Información General', {
            'fields': ('nombre', 'descripcion', 'investigador_principal', 'codigo_siu')
        }),
        ('Fechas', {
            'fields': ('fecha_inicio', 'fecha_financiacion')
        }),
        ('Consentimiento Informado', {
            'fields': ('consentimiento_pdf',),
            'description': 'Suba el PDF del consentimiento informado que se enviará automáticamente por correo al agendar citas para este proyecto.'
        }),
        ('Configuración de Registro Público', {
            'fields': ('crear_visita_automatica', 'tipo_visita_automatica', 'nombre_visita_automatica'),
            'classes': ('collapse',)
        }),
    )
    
    def tiene_consentimiento(self, obj):
        return "✅ Sí" if obj.consentimiento_pdf else "❌ No"
    tiene_consentimiento.short_description = 'Consentimiento'


admin.site.register(Proyecto, ProyectoAdmin)
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
