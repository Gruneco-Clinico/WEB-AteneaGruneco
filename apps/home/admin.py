# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib import admin
from .models import Proyecto,DatosDemograficos,Visita,VisitaExamen,Examen

admin.site.register(Proyecto)
admin.site.register(Visita)
admin.site.register(Examen)
admin.site.register(VisitaExamen)
admin.site.register(DatosDemograficos)
