#!/usr/bin/env python
"""
Script de prueba para verificar que la función de extracción de datos
está capturando correctamente los campos de los exámenes
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.home.models import Visita, VisitaExamen
from apps.home.views import _extraer_informacion_resultado

print("=" * 70)
print("TEST: Verificar extracción de información de resultados")
print("=" * 70)

# Obtener una visita con exámenes
visitas = Visita.objects.prefetch_related('visitaexamen_set').filter(visitaexamen__isnull=False).distinct()[:1]

if not visitas:
    print("❌ No hay visitas con exámenes en la base de datos")
    sys.exit(1)

for visita in visitas:
    print(f"\n✓ Visita encontrada: {visita.id}")
    print(f"  Paciente: {visita.paciente.nombre if visita.paciente else 'Sin paciente'}")
    print(f"  Fecha: {visita.fecha}")
    
    exámenes = visita.visitaexamen_set.all()
    print(f"  Total de exámenes: {exámenes.count()}\n")
    
    for i, exam in enumerate(exámenes[:5], 1):
        resultado = exam.get_resultado_instance()
        if resultado:
            print(f"\n  [{i}] {exam.nombre_examen}")
            print(f"      Tipo: {resultado.__class__.__name__}")
            
            # Extraer información usando la nueva función
            info = _extraer_informacion_resultado(resultado)
            
            if info:
                print(f"      ✓ Información extraída:")
                for linea in info.split("<br/>")[:5]:  # Mostrar máximo 5 líneas
                    print(f"        - {linea}")
                if info.count("<br/>") > 5:
                    print(f"        ... y {info.count('<br/>')-4} más campos")
            else:
                print(f"      ❌ No se extrajeron datos")
        else:
            print(f"\n  [{i}] {exam.nombre_examen} - No tiene resultado asociado")

print("\n" + "=" * 70)
print("Test completado")
print("=" * 70)
