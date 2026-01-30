#!/usr/bin/env python
"""
Script de prueba simplificado para verificar que la función de extracción
está capturando correctamente los campos y valores
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.home.models import Visita, VisitaExamen
from apps.home.views import _extraer_informacion_resultado
from django.db import models

def test_extraction():
    """Prueba la extracción de datos de resultados"""
    
    # Obtener una visita con exámenes
    visitas_con_examenes = Visita.objects.prefetch_related(
        'visitaexamen_set'
    ).filter(visitaexamen__isnull=False).distinct()[:1]
    
    if not visitas_con_examenes:
        print("❌ No hay visitas con exámenes")
        return False
    
    print("\n" + "="*70)
    print("TEST DE EXTRACCIÓN DE DATOS DE RESULTADOS")
    print("="*70)
    
    success_count = 0
    fail_count = 0
    
    for visita in visitas_con_examenes:
        print(f"\n✓ Visita: {visita.id} | Paciente: {visita.paciente.nombre if visita.paciente else 'Sin paciente'}")
        
        exámenes = visita.visitaexamen_set.all()[:10]
        
        for exam in exámenes:
            resultado = exam.get_resultado_instance()
            
            if not resultado:
                print(f"  ⚠ {exam.nombre_examen}: Sin resultado")
                continue
            
            print(f"\n  [{resultado.__class__.__name__}] {exam.nombre_examen}")
            
            # Mostrar los campos del modelo
            fields = resultado._meta.get_fields()
            data_fields = []
            for field in fields:
                if isinstance(field, (models.ForeignKey, models.OneToOneField, models.ManyToManyField)):
                    continue
                if field.name.startswith('_') or field.name in ['id', 'created_at', 'updated_at']:
                    continue
                valor = getattr(resultado, field.name, None)
                if valor is not None and valor != '':
                    data_fields.append((field.name, valor))
            
            print(f"    Campos con datos: {len(data_fields)}")
            for fname, fval in data_fields[:3]:
                print(f"      • {fname}: {fval}")
            if len(data_fields) > 3:
                print(f"      ... y {len(data_fields)-3} más")
            
            # Extraer usando la función
            info = _extraer_informacion_resultado(resultado)
            
            if info:
                print(f"    ✓ Extracción exitosa:")
                lines = info.split("<br/>")[:4]
                for line in lines:
                    print(f"      • {line}")
                if len(info.split("<br/>")) > 4:
                    print(f"      ... y {len(info.split('<br/>'))-4} líneas más")
                success_count += 1
            else:
                print(f"    ❌ No se extrajeron datos")
                fail_count += 1
    
    print("\n" + "="*70)
    print(f"RESULTADOS: ✓ {success_count} exitosos | ❌ {fail_count} fallidos")
    print("="*70 + "\n")
    
    return fail_count == 0

if __name__ == "__main__":
    try:
        success = test_extraction()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
