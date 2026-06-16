from django.db import models

from .visit import ResultadoExamenBase


################################################################################################################################################
# sueno examenes


class PittsburghResult(ResultadoExamenBase):
    hora_acostarse = models.CharField(max_length=10, verbose_name="Hora de acostarse")
    latencia_sueno = models.CharField(max_length=100, verbose_name="Latencia del sueño")
    hora_levantarse = models.CharField(max_length=10, verbose_name="Hora de levantarse")
    horas_dormidas = models.FloatField(verbose_name="Horas dormidas")
    conciliar_sueno = models.CharField(max_length=100, verbose_name="Dificultad para conciliar el sueño")
    despertarse_sueno = models.CharField(max_length=100, verbose_name="Despertarse durante la noche")
    levantarse_servicio_sueno = models.CharField(max_length=100, verbose_name="Levantarse para ir al baño")
    respirar = models.CharField(max_length=100, verbose_name="Dificultad para respirar")
    toser_roncar_sueno = models.CharField(max_length=100, verbose_name="Toser o roncar")
    sentir_frio_sueno = models.CharField(max_length=100, verbose_name="Sentir frío")
    calor_sueno = models.CharField(max_length=100, verbose_name="Sentir calor")
    pesadillas_sueno = models.CharField(max_length=100, verbose_name="Pesadillas")
    dolores_sueno = models.CharField(max_length=100, verbose_name="Dolores")
    otras_razones = models.CharField(max_length=100, blank=True, null=True, verbose_name="Otras razones")
    otras_sueno = models.CharField(max_length=100, blank=True, null=True, verbose_name="Descripción de otras razones")
    calidad_sueno = models.CharField(max_length=100, verbose_name="Calidad del sueño")
    medicinas_sueno = models.CharField(max_length=100, verbose_name="Uso de medicinas para dormir")
    somnolencia_sueno = models.CharField(max_length=100, verbose_name="Somnolencia diurna")
    problemas_animos_sueno = models.CharField(max_length=100, verbose_name="Problemas de ánimo")
    duerme_acompanado = models.CharField(max_length=100, verbose_name="Duerme acompañado")
    ronquidos_ruidosos = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ronquidos ruidosos")
    pausas_respiracion = models.CharField(max_length=100, blank=True, null=True, verbose_name="Pausas en la respiración")
    sacudidas_piernas = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sacudidas de piernas")
    desorientacion_confusion = models.CharField(max_length=100, blank=True, null=True, verbose_name="Desorientación o confusión")
    otros_inconvenientes = models.CharField(max_length=100, blank=True, null=True, verbose_name="Otros inconvenientes")
    descripcion_inconvenientes = models.CharField(max_length=100, blank=True, null=True, verbose_name="Descripción de inconvenientes")
    puntuacion_total = models.IntegerField(default=0, blank=True, null=True, verbose_name="Puntuación total")


class EpworthResult(ResultadoExamenBase):
    sentado_leyendo = models.IntegerField(verbose_name="Sentado leyendo")
    viendo_tv = models.IntegerField(verbose_name="Viendo televisión")
    sentado_teatro = models.IntegerField(verbose_name="Sentado en teatro/cine")
    pasajero_coche = models.IntegerField(verbose_name="Pasajero en coche")
    tumbado_tarde = models.IntegerField(verbose_name="Tumbado por la tarde")
    charlando = models.IntegerField(verbose_name="Charlando sentado")
    despues_comer = models.IntegerField(verbose_name="Después de comer")
    trafico = models.IntegerField(verbose_name="En el tráfico")
    puntaje_total = models.IntegerField(verbose_name="Puntaje total")


class MEWResult(ResultadoExamenBase):
    hora_levantarse = models.CharField(max_length=150, blank=True, null=True)
    hora_acostarse = models.CharField(max_length=150, blank=True, null=True)
    uso_despertador = models.CharField(max_length=150, blank=True, null=True)
    facilidad_levantarse = models.CharField(max_length=150, blank=True, null=True)
    alerta_manana = models.CharField(max_length=150, blank=True, null=True)
    apetito_manana = models.CharField(max_length=150, blank=True, null=True)
    descanso_manana = models.CharField(max_length=150, blank=True, null=True)
    hora_acostarse_libre = models.CharField(max_length=150, blank=True, null=True)

    # Pregunta 9: Ejercicio de mañana (7:00-8:00 AM)
    ejercicio_manana = models.CharField(max_length=150, blank=True, null=True)

    ejercicio_fisico = models.CharField(max_length=150, blank=True, null=True)
    hora_cansancio_noche = models.CharField(max_length=150, blank=True, null=True)
    nivel_cansancia_11 = models.CharField(max_length=150, blank=True, null=True)
    prueba_mental = models.CharField(max_length=150, blank=True, null=True)

    # Pregunta 12: Cansancio a las 11 PM
    cansancio_11pm = models.CharField(max_length=150, blank=True, null=True)

    # Pregunta 13: Despertar tarde
    despertar_tarde = models.CharField(max_length=150, blank=True, null=True)

    hora_despertarse_si_tarde = models.CharField(max_length=150, blank=True, null=True)
    guardia_nocturna = models.CharField(max_length=150, blank=True, null=True)
    horario_trabajo_fisico = models.CharField(max_length=150, blank=True, null=True)

    # Pregunta 15: Trabajo físico
    trabajo_fisico = models.CharField(max_length=150, blank=True, null=True)

    ejercicio_nocturno = models.CharField(max_length=150, blank=True, null=True)
    horario_trabajo = models.CharField(max_length=150, blank=True, null=True)
    maximo_bienestar = models.CharField(max_length=150, blank=True, null=True)
    tipo_persona = models.CharField(max_length=150, blank=True, null=True)
    puntuacion = models.IntegerField()

    def __str__(self):
        return f"MEQ - {self.visita_examen_id}"


class BerlinResult(ResultadoExamenBase):
    peso_cambio = models.CharField(max_length=50, verbose_name="Cambio de peso")
    ronca = models.CharField(max_length=10, verbose_name="Ronca")
    tipo_ronquido = models.CharField(max_length=50, verbose_name="Tipo de ronquido")
    frecuencia_ronquidos = models.CharField(max_length=50, verbose_name="Frecuencia de ronquidos")
    ronquido_molesto = models.CharField(max_length=50, verbose_name="Ronquido molesto")
    apnea_observada = models.CharField(max_length=50, verbose_name="Apnea observada")
    fatiga_matutina = models.CharField(max_length=50, verbose_name="Fatiga matutina")
    fatiga_dia = models.CharField(max_length=50, verbose_name="Fatiga durante el día")
    somnolencia_conducir = models.BooleanField(null=True, blank=True, verbose_name="Somnolencia al conducir")
    presion_alta = models.BooleanField(null=True, blank=True, verbose_name="Presión arterial alta")


class SuenoAnamnesisResult(ResultadoExamenBase):
    # Motivo de consulta y enfermedad actual
    motivo_consulta = models.TextField(blank=True, null=True)
    enfermedad_actual = models.TextField(blank=True, null=True)

    # Queja de sueño - CORREGIDO: CharField en lugar de Boolean
    presenta_queja = models.CharField(
        max_length=10, blank=True, null=True, default="no"
    )
    observaciones_queja = models.TextField(blank=True, null=True)
    causa_conocida = models.CharField(
        max_length=10, blank=True, null=True, default="no"
    )
    especificacion_causa = models.TextField(blank=True, null=True)

    # Rutina de sueño
    rutina_dormir = models.CharField(max_length=10, blank=True, null=True, default="no")
    describa_rutina = models.TextField(blank=True, null=True)

    # Horarios laborales - CORREGIDO: Campos más flexibles
    jornada_laboral = models.CharField(max_length=255, blank=True, null=True)
    hora_acostarse_laboral = models.CharField(max_length=20, blank=True, null=True)
    tiempo_dormirse_laboral = models.CharField(max_length=20, blank=True, null=True)
    hora_intencion_dormir_laboral = models.CharField(
        max_length=20, blank=True, null=True
    )
    hora_despertar_laboral = models.CharField(max_length=20, blank=True, null=True)
    tiempo_salir_cama_laboral = models.CharField(max_length=20, blank=True, null=True)
    sueno_reparador_laboral = models.CharField(max_length=20, blank=True, null=True)
    companero_cama_laboral = models.CharField(max_length=10, blank=True, null=True)
    despertador_laboral = models.CharField(max_length=10, blank=True, null=True)

    # Fin de semana
    jornada_fds = models.CharField(max_length=255, blank=True, null=True)
    hora_acostarse_fds = models.CharField(max_length=20, blank=True, null=True)
    tiempo_dormirse_fds = models.CharField(max_length=20, blank=True, null=True)
    hora_intencion_dormir_fds = models.CharField(max_length=20, blank=True, null=True)
    hora_despertar_fds = models.CharField(max_length=20, blank=True, null=True)
    tiempo_salir_cama_fds = models.CharField(max_length=20, blank=True, null=True)
    sueno_reparador_fds = models.CharField(max_length=20, blank=True, null=True)
    companero_cama_fds = models.CharField(max_length=10, blank=True, null=True)
    despertador_fds = models.CharField(max_length=10, blank=True, null=True)

    # Vacaciones
    hora_acostarse_vacaciones = models.CharField(max_length=20, blank=True, null=True)
    tiempo_dormirse_vacaciones = models.CharField(max_length=20, blank=True, null=True)
    hora_intencion_dormir_vacaciones = models.CharField(
        max_length=20, blank=True, null=True
    )
    hora_despertar_vacaciones = models.CharField(max_length=20, blank=True, null=True)
    tiempo_salir_cama_vacaciones = models.CharField(
        max_length=20, blank=True, null=True
    )
    sueno_reparador_vacaciones = models.CharField(max_length=20, blank=True, null=True)
    companero_cama_vacaciones = models.CharField(max_length=10, blank=True, null=True)
    despertador_vacaciones = models.CharField(max_length=10, blank=True, null=True)

    # Siestas - CORREGIDO: CharField para compatibilidad
    realiza_siestas = models.CharField(
        max_length=10, blank=True, null=True, default="no"
    )
    numero_siestas = models.CharField(max_length=10, blank=True, null=True)
    duracion_siestas = models.CharField(max_length=20, blank=True, null=True)
    siesta_frecuencia = models.CharField(max_length=100, blank=True, null=True)
    siesta_reparadora = models.CharField(max_length=10, blank=True, null=True)
    periodo_siestas = models.CharField(max_length=500, blank=True, null=True)
    momento_dia_siesta = models.CharField(max_length=50, blank=True, null=True)

    # Ambiente
    iluminacion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Condiciones de iluminación")
    comodidad = models.CharField(max_length=255, blank=True, null=True, verbose_name="Comodidad del espacio")
    ruido = models.CharField(max_length=255, blank=True, null=True, verbose_name="Condiciones de ruido")
    
    # Posición al dormir
    posicion_dormir = models.CharField(max_length=100, blank=True, null=True, verbose_name="Posición al dormir")
    posicion_dormir_otra = models.CharField(max_length=255, blank=True, null=True, verbose_name="Descripción de otra posición")

    # Consumo - CORREGIDO: CharField
    consume = models.CharField(max_length=10, blank=True, null=True, default="no")
    consume_medicamento = models.CharField(
        max_length=10, blank=True, null=True, default="no"
    )
    usa_pantallas = models.CharField(max_length=10, blank=True, null=True, default="no")

    # Actividades
    cama_actividades = models.TextField(blank=True, null=True)
    actividad_fisica = models.TextField(blank=True, null=True)

    # Síntomas
    sintomas_sueno = models.TextField(blank=True, null=True)
    sintomas_diurnos = models.TextField(blank=True, null=True)

    # Observaciones
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Anamnesis de Sueño - {self.visita_examen}"


class TipoQuejaSueno(models.Model):
    anamnesis = models.ForeignKey(
        SuenoAnamnesisResult,
        on_delete=models.CASCADE,
        related_name="tipos_queja_detalle",
    )
    nombre = models.CharField(max_length=100)
    inicio = models.CharField(max_length=100, blank=True, null=True)
    evolucion = models.TextField(blank=True, null=True)
    frecuencia = models.CharField(max_length=100, blank=True, null=True)
    gravedad = models.CharField(max_length=100, blank=True, null=True)


class SustanciaSueno(models.Model):
    anamnesis = models.ForeignKey(
        SuenoAnamnesisResult, on_delete=models.CASCADE, related_name="sustancias"
    )
    tipo = models.CharField(max_length=100)
    cantidad = models.CharField(max_length=50, blank=True, null=True)
    frecuencia = models.CharField(max_length=50, blank=True, null=True)
    tiempo = models.CharField(max_length=50, blank=True, null=True)
    observaciones = models.CharField(max_length=255, blank=True, null=True)


class MedicamentoSueno(models.Model):
    anamnesis = models.ForeignKey(
        SuenoAnamnesisResult, on_delete=models.CASCADE, related_name="medicamentos"
    )
    nombre = models.CharField(max_length=100)
    dosis = models.CharField(max_length=50, blank=True, null=True)
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    presentacion = models.CharField(max_length=50, blank=True, null=True)
    veces_dia = models.CharField(max_length=50, blank=True, null=True)
    frecuencia = models.CharField(max_length=50, blank=True, null=True)
    tiempo = models.CharField(max_length=50, blank=True, null=True)


class PantallaSueno(models.Model):
    anamnesis = models.ForeignKey(
        SuenoAnamnesisResult, on_delete=models.CASCADE, related_name="pantallas"
    )
    tipo = models.CharField(max_length=100)
    frecuencia = models.CharField(max_length=50, blank=True, null=True)
    tiempo_antes_dormir = models.CharField(max_length=50, blank=True, null=True)


class ActividadEnCamaSueno(models.Model):
    anamnesis = models.ForeignKey(
        SuenoAnamnesisResult,
        on_delete=models.CASCADE,
        related_name="actividades_en_cama",
    )
    tipo = models.CharField(max_length=100)
    frecuencia = models.CharField(max_length=50, blank=True, null=True)
    observaciones = models.CharField(max_length=255, blank=True, null=True)


class ActividadFisicaSueno(models.Model):
    anamnesis = models.ForeignKey(
        SuenoAnamnesisResult,
        on_delete=models.CASCADE,
        related_name="actividades_fisicas",
    )
    tipo = models.CharField(max_length=100)
    otro_texto = models.CharField(max_length=100, blank=True, null=True)
    intensidad = models.CharField(max_length=50, blank=True, null=True)
    frecuencia = models.CharField(max_length=50, blank=True, null=True)
    observaciones = models.CharField(max_length=255, blank=True, null=True)


class SintomaSueno(models.Model):
    anamnesis = models.ForeignKey(
        SuenoAnamnesisResult, on_delete=models.CASCADE, related_name="sintomas_suenos"
    )
    tipo = models.CharField(max_length=100)
    cuando_inicio = models.CharField(max_length=100, blank=True, null=True)
    evolucion = models.CharField(max_length=100, blank=True, null=True)
    frecuencia = models.CharField(max_length=100, blank=True, null=True)
    gravedad = models.CharField(max_length=100, blank=True, null=True)
    observaciones = models.CharField(max_length=255, blank=True, null=True)


class SintomaDiurnoSueno(models.Model):
    anamnesis = models.ForeignKey(
        SuenoAnamnesisResult, on_delete=models.CASCADE, related_name="sintomas_diurno"
    )
    tipo = models.CharField(max_length=100)
    cuando_inicio = models.CharField(max_length=100, blank=True, null=True)
    evolucion = models.CharField(max_length=100, blank=True, null=True)
    frecuencia = models.CharField(max_length=100, blank=True, null=True)
    gravedad = models.CharField(max_length=100, blank=True, null=True)
    observaciones = models.CharField(max_length=255, blank=True, null=True)


class AtenasResult(ResultadoExamenBase):
    induccion_dormir = models.CharField(max_length=50, verbose_name="Inducción al sueño")
    despertares_noche = models.CharField(max_length=50, verbose_name="Despertares durante la noche")
    despertar_temprano = models.CharField(max_length=50, verbose_name="Despertar temprano")
    duracion_dormir = models.CharField(max_length=50, verbose_name="Duración del sueño")
    calidad_dormir = models.CharField(max_length=50, verbose_name="Calidad del sueño")
    bienestar_dia = models.CharField(max_length=50, verbose_name="Bienestar durante el día")
    funcionamiento_dia = models.CharField(max_length=50, verbose_name="Funcionamiento diurno")
    somnolencia_dia = models.CharField(max_length=50, verbose_name="Somnolencia diurna")
    puntuacion_total = models.IntegerField(blank=True, null=True, verbose_name="Puntuación total")

    def __str__(self):
        return f"Atenas - {self.visita_examen_id}"


class SuenoFisicoResult(ResultadoExamenBase):
    peso = models.FloatField(blank=True, null=True)
    talla = models.FloatField(blank=True, null=True)
    imc = models.FloatField(blank=True, null=True)
    rango_imc = models.CharField(max_length=50, blank=True, null=True)
    circunferencia_cuello = models.FloatField(blank=True, null=True)
    perimetro_abdominal = models.FloatField(blank=True, null=True)

    frecuencia_cardiaca = models.PositiveIntegerField(
        blank=True, null=True, verbose_name="Frecuencia cardiaca (lpm)"
    )
    frecuencia_respiratoria = models.PositiveIntegerField(
        blank=True, null=True, verbose_name="Frecuencia respiratoria (rpm)"
    )
    saturacion_oxigeno = models.PositiveIntegerField(
        blank=True, null=True, verbose_name="SatO₂ (%)"
    )
    presion_arterial_sistolica = models.PositiveIntegerField(
        blank=True, null=True, verbose_name="Presión sistólica (mmHg)"
    )
    presion_arterial_diastolica = models.PositiveIntegerField(
        blank=True, null=True, verbose_name="Presión diastólica (mmHg)"
    )

    simetria_narinas = models.CharField(max_length=50, blank=True, null=True)
    tipo_narina = models.CharField(max_length=50, blank=True, null=True)
    desviacion_septo = models.CharField(max_length=50, blank=True, null=True)
    hipertrofia_cornetes = models.CharField(max_length=50, blank=True, null=True)
    grado = models.CharField(max_length=50, blank=True, null=True)
    hipertrofia_uvula = models.CharField(max_length=50, blank=True, null=True)
    biotipo = models.CharField(max_length=50, blank=True, null=True)
    mallampati = models.CharField(max_length=50, blank=True, null=True)
    amigdalas = models.CharField(max_length=50, blank=True, null=True)
    tipo_mordida = models.CharField(max_length=50, blank=True, null=True)
    alteracion_craneo = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Examen físico de sueño - {self.visita_examen_id}"


class ISIResult(ResultadoExamenBase):
    dificultad_dormir = models.CharField(max_length=50, verbose_name="Dificultad para dormir")
    dificultad_mantener_sueno = models.CharField(max_length=50, verbose_name="Dificultad para mantener el sueño")
    despertar_temprano = models.CharField(max_length=50, verbose_name="Despertar temprano")
    satisfaccion_sueno = models.CharField(max_length=50, verbose_name="Satisfacción con el sueño")
    notabilidad_problema = models.CharField(max_length=50, verbose_name="Notoriedad del problema")
    preocupacion_sueno = models.CharField(max_length=50, verbose_name="Preocupación por el sueño")
    interferencia_sueno = models.CharField(max_length=50, verbose_name="Interferencia en la vida diaria")
    puntuacion_total = models.IntegerField(blank=True, null=True, verbose_name="Puntuación total")

    def __str__(self):
        return f"ISI - {self.visita_examen_id}"


class StopBangResult(ResultadoExamenBase):
    ronca_fuerte = models.BooleanField(default=False, verbose_name="Ronca fuerte")
    cansado_frecuencia = models.BooleanField(default=False, verbose_name="Cansado frecuentemente")
    deja_respirar = models.BooleanField(default=False, verbose_name="Deja de respirar")
    presion_arterial = models.BooleanField(default=False, verbose_name="Presión arterial alta")
    imc_alto = models.BooleanField(default=False, verbose_name="IMC alto")
    mayor_50 = models.BooleanField(default=False, verbose_name="Mayor de 50 años")
    cuello_grande = models.BooleanField(default=False, verbose_name="Cuello grande")
    masculino = models.BooleanField(default=False, verbose_name="Sexo masculino")
    puntaje_total = models.IntegerField(blank=True, null=True, verbose_name="Puntaje total")
    riesgo = models.CharField(max_length=20, blank=True, null=True, verbose_name="Nivel de riesgo")
    stop_positivos = models.IntegerField(blank=True, null=True, verbose_name="STOP positivos")
    bang_positivos = models.IntegerField(blank=True, null=True, verbose_name="BANG positivos")
    alto_riesgo_alternativo = models.BooleanField(default=False, verbose_name="Alto riesgo alternativo")

    def __str__(self):
        return f"STOP-BANG - {self.visita_examen_id}"
