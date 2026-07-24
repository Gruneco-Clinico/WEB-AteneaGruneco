from django.db import models

from .visit import ResultadoExamenBase


### Anosognosia


class LawtonBrodyResult(ResultadoExamenBase):
    genero = models.CharField(max_length=10, verbose_name="Género")

    usar_telefono = models.CharField(max_length=255, verbose_name="Usar teléfono")
    hacer_compras = models.CharField(max_length=255, verbose_name="Hacer compras")
    preparar_comida = models.CharField(max_length=255, verbose_name="Preparar comida")
    cuidado_casa = models.CharField(max_length=255, verbose_name="Cuidado de la casa")
    lavar_ropa = models.CharField(max_length=255, verbose_name="Lavar ropa")
    uso_transporte = models.CharField(max_length=255, verbose_name="Uso de transporte")
    medicacion = models.CharField(max_length=255, verbose_name="Medicación")
    manejo_dinero = models.CharField(max_length=255, verbose_name="Manejo de dinero")

    puntaje_total = models.IntegerField(verbose_name="Puntaje total")
    # D-18: etiqueta clínica «Interpretación» (campo histórico `diagnostico`)
    diagnostico = models.CharField(max_length=100, verbose_name="Interpretación")

    def __str__(self):
        return f"Lawton & Brody - {self.visita_examen_id}"


class CuidadorNPIResult(ResultadoExamenBase):
    ideas_delirantes = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
        verbose_name="Ideas delirantes",
    )
    ideas_delirantes_frecuencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Frecuencia ideas delirantes")
    ideas_delirantes_gravedad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Gravedad ideas delirantes")
    ideas_delirantes_F_G = models.IntegerField(blank=True, null=True, verbose_name="F x G ideas delirantes")
    ideas_delirantes_distres = models.CharField(max_length=50, blank=True, null=True, verbose_name="Distrés ideas delirantes")

    alucinaciones = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
        verbose_name="Alucinaciones",
    )
    alucinaciones_frecuencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Frecuencia alucinaciones")
    alucinaciones_gravedad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Gravedad alucinaciones")
    alucinaciones_F_G = models.IntegerField(blank=True, null=True, verbose_name="F x G alucinaciones")
    alucinaciones_distres = models.CharField(max_length=50, blank=True, null=True, verbose_name="Distrés alucinaciones")

    agitacion = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
        verbose_name="Agitación/Agresión",
    )
    agitacion_frecuencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Frecuencia agitación")
    agitacion_gravedad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Gravedad agitación")
    agitacion_F_G = models.IntegerField(blank=True, null=True, verbose_name="F x G agitación")
    agitacion_distres = models.CharField(max_length=50, blank=True, null=True, verbose_name="Distrés agitación")

    depresion = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
        verbose_name="Depresión/Disforia",
    )
    depresion_frecuencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Frecuencia depresión")
    depresion_gravedad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Gravedad depresión")
    depresion_F_G = models.IntegerField(blank=True, null=True, verbose_name="F x G depresión")
    depresion_distres = models.CharField(max_length=50, blank=True, null=True, verbose_name="Distrés depresión")

    ansiedad = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
        verbose_name="Ansiedad",
    )
    ansiedad_frecuencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Frecuencia ansiedad")
    ansiedad_gravedad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Gravedad ansiedad")
    ansiedad_F_G = models.IntegerField(blank=True, null=True, verbose_name="F x G ansiedad")
    ansiedad_distres = models.CharField(max_length=50, blank=True, null=True, verbose_name="Distrés ansiedad")

    euforia = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
        verbose_name="Euforia/Alegría",
    )
    euforia_frecuencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Frecuencia euforia")
    euforia_gravedad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Gravedad euforia")
    euforia_F_G = models.IntegerField(blank=True, null=True, verbose_name="F x G euforia")
    euforia_distres = models.CharField(max_length=50, blank=True, null=True, verbose_name="Distrés euforia")

    apatia = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
        verbose_name="Apatía/Indiferencia",
    )
    apatia_frecuencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Frecuencia apatía")
    apatia_gravedad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Gravedad apatía")
    apatia_F_G = models.IntegerField(blank=True, null=True, verbose_name="F x G apatía")
    apatia_distres = models.CharField(max_length=50, blank=True, null=True, verbose_name="Distrés apatía")

    desinhibicion = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
        verbose_name="Desinhibición",
    )
    desinhibicion_frecuencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Frecuencia desinhibición")
    desinhibicion_gravedad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Gravedad desinhibición")
    desinhibicion_F_G = models.IntegerField(blank=True, null=True, verbose_name="F x G desinhibición")
    desinhibicion_distres = models.CharField(max_length=50, blank=True, null=True, verbose_name="Distrés desinhibición")

    irritabilidad = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
        verbose_name="Irritabilidad/Labilidad",
    )
    irritabilidad_frecuencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Frecuencia irritabilidad")
    irritabilidad_gravedad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Gravedad irritabilidad")
    irritabilidad_F_G = models.IntegerField(blank=True, null=True, verbose_name="F x G irritabilidad")
    irritabilidad_distres = models.CharField(max_length=50, blank=True, null=True, verbose_name="Distrés irritabilidad")

    conducta_motor = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
        verbose_name="Conducta Motora Aberrante",
    )
    conducta_motor_frecuencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Frecuencia conducta motora")
    conducta_motor_gravedad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Gravedad conducta motora")
    conducta_motor_F_G = models.IntegerField(blank=True, null=True, verbose_name="F x G conducta motora")
    conducta_motor_distres = models.CharField(max_length=50, blank=True, null=True, verbose_name="Distrés conducta motora")

    sueno = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
        verbose_name="Sueño",
    )
    sueno_frecuencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Frecuencia problemas de sueño")
    sueno_gravedad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Gravedad problemas de sueño")
    sueno_F_G = models.IntegerField(blank=True, null=True, verbose_name="F x G sueño")
    sueno_distres = models.CharField(max_length=50, blank=True, null=True, verbose_name="Distrés sueño")

    apetito = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
        verbose_name="Apetito/Alimentación",
    )
    apetito_frecuencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Frecuencia problemas de apetito")
    apetito_gravedad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Gravedad problemas de apetito")
    apetito_F_G = models.IntegerField(blank=True, null=True, verbose_name="F x G apetito")
    apetito_distres = models.CharField(max_length=50, blank=True, null=True, verbose_name="Distrés apetito")

    carga_total = models.IntegerField(blank=True, null=True, default=0, verbose_name="Carga total")
    puntaje_total = models.IntegerField(blank=True, null=True, default=0, verbose_name="Puntaje total")

    def calcular_puntaje_total(self):
        items_fg = [
            self.ideas_delirantes_F_G,
            self.alucinaciones_F_G,
            self.agitacion_F_G,
            self.depresion_F_G,
            self.ansiedad_F_G,
            self.euforia_F_G,
            self.apatia_F_G,
            self.desinhibicion_F_G,
            self.irritabilidad_F_G,
            self.conducta_motor_F_G,
            self.sueno_F_G,
            self.apetito_F_G,
        ]

        return sum(int(x) for x in items_fg if x not in (None, ""))

    def calcular_carga_total(self):
        distres_fields = [
            "ideas_delirantes_distres",
            "alucinaciones_distres",
            "agitacion_distres",
            "depresion_distres",
            "ansiedad_distres",
            "euforia_distres",
            "apatia_distres",
            "desinhibicion_distres",
            "irritabilidad_distres",
            "conducta_motor_distres",
            "sueno_distres",
            "apetito_distres",
        ]
        total = 0
        for name in distres_fields:
            raw = getattr(self, name, None)
            if raw in (None, ""):
                continue
            try:
                total += int(str(raw).strip().split()[0])
            except (TypeError, ValueError):
                continue
        return total

    def save(self, *args, **kwargs):
        self.puntaje_total = self.calcular_puntaje_total()
        # Recalcular carga si hay distrés; conservar POST si ya vino
        calculated = self.calcular_carga_total()
        if calculated or self.carga_total in (None, ""):
            self.carga_total = calculated
        super().save(*args, **kwargs)

    def __str__(self):
        return f"NPI - Paciente {self.visita_examen_id}"


class AdherenciaTerapeuticaResult(ResultadoExamenBase):
    # Factores
    factor1 = models.IntegerField(default=0, verbose_name="Factor 1")
    factor2 = models.IntegerField(default=0, verbose_name="Factor 2")
    factor3 = models.IntegerField(default=0, verbose_name="Factor 3")

    # Preguntas
    dieta_rigurosa = models.CharField(max_length=20, verbose_name="Dieta rigurosa")  # P1
    asistir_consultas = models.CharField(max_length=20, verbose_name="Asistir a consultas")  # P2
    pendiente_sintomas = models.CharField(max_length=20, verbose_name="Pendiente de síntomas")  # P3
    recomendacion_medico = models.CharField(max_length=20, verbose_name="Recomendación del médico")  # P4
    alimentos_permitidos = models.CharField(max_length=20, verbose_name="Alimentos permitidos")  # P5
    seguir_tratamiento = models.CharField(max_length=20, verbose_name="Seguir tratamiento")  # P6
    regresar_consulta = models.CharField(max_length=20, verbose_name="Regresar a consulta")  # P7
    seguridad_tratamiento = models.CharField(max_length=20, verbose_name="Seguridad del tratamiento")  # P8
    olvido_medicamentos = models.CharField(max_length=20, verbose_name="Olvido de medicamentos")  # P9
    dejar_tratamiento = models.CharField(max_length=20, verbose_name="Dejar tratamiento")  # P10
    sin_mejoria = models.CharField(max_length=20, verbose_name="Sin mejoría")  # P11
    hacer_ejercicio = models.CharField(max_length=20, verbose_name="Hacer ejercicio")  # P12
    recordar_medicamentos = models.CharField(max_length=20, verbose_name="Recordar medicamentos")  # P13
    analisis_periodicos = models.CharField(max_length=20, verbose_name="Análisis periódicos")  # P14
    confianza_medico = models.CharField(max_length=20, verbose_name="Confianza en el médico")  # P15
    mejorar_enfermedad = models.CharField(max_length=200, verbose_name="Mejorar enfermedad")  # P16
    apego_tratamiento = models.CharField(max_length=20, verbose_name="Apego al tratamiento")  # P17
    adherencia_tratamiento = models.CharField(max_length=20, verbose_name="Adherencia al tratamiento")  # P18
    menos_medicamento = models.CharField(max_length=20, verbose_name="Menos medicamento")  # P19
    confianza_medicamento = models.CharField(max_length=20, verbose_name="Confianza en medicamento")  # P20
    dosis_indicada = models.CharField(max_length=20, verbose_name="Dosis indicada")  # P21
    revisiones_periodicas = models.CharField(max_length=20, verbose_name="Revisiones periódicas")  # P22
    medico_sintoma = models.CharField(max_length=20, verbose_name="Médico por síntoma")  # P23
    mejoria_salud = models.CharField(max_length=20, verbose_name="Mejoría de salud")  # P24
    sintomas_deterioro = models.CharField(max_length=20, verbose_name="Síntomas de deterioro")  # P25
    mediciones_indicadas = models.CharField(max_length=20, verbose_name="Mediciones indicadas")  # P26
    respeto_dieta = models.CharField(max_length=20, verbose_name="Respeto a la dieta")  # P27
    modificacion_tratamiento = models.CharField(max_length=20, verbose_name="Modificación del tratamiento")  # P28
    mantener_controlado = models.CharField(max_length=20, verbose_name="Mantener controlado")  # P29
    seguridad_resultados = models.CharField(max_length=20, verbose_name="Seguridad de resultados")  # P30

    # Factores calculados
    factor1 = models.IntegerField(blank=True, null=True, verbose_name="Factor 1 - Atención médica")  # Atención médica
    factor2 = models.IntegerField(blank=True, null=True, verbose_name="Factor 2 - Estilo de vida")  # Estilo de vida
    factor3 = models.IntegerField(blank=True, null=True, verbose_name="Factor 3 - Barreras ante la medicación")  # Barreras ante la medicación

    # Interpretaciones
    factor1_interpretacion = models.CharField(max_length=50, blank=True, null=True, verbose_name="Interpretación factor 1")
    factor2_interpretacion = models.CharField(max_length=50, blank=True, null=True, verbose_name="Interpretación factor 2")
    factor3_interpretacion = models.CharField(max_length=50, blank=True, null=True, verbose_name="Interpretación factor 3")

    def __str__(self):
        return f"Adherencia Terapéutica - {self.visita_examen_id}"


class EuroQol5D5LResult(ResultadoExamenBase):
    movilidad = models.CharField(max_length=255, verbose_name="Movilidad")
    cuidado_personal = models.CharField(max_length=255, verbose_name="Cuidado personal")
    actividades = models.CharField(max_length=255, verbose_name="Actividades")
    dolor = models.CharField(max_length=255, verbose_name="Dolor")
    ansiedad = models.CharField(max_length=255, verbose_name="Ansiedad")
    # D-20: código de estado EQ-5D-5L (ej. "11243"); sin índice de utilidad
    estado_salud = models.CharField(
        max_length=5, blank=True, null=True, verbose_name="Estado de salud (código EQ-5D)"
    )

    def __str__(self):
        return f"EuroQol-5D-5L - {self.visita_examen}"


class EuroQolEVASaludResult(ResultadoExamenBase):
    # Valor reportado en el "termómetro" de 0 a 100
    termometro_estado_salud = models.IntegerField(
        help_text="Autovaloración del estado de salud en la escala de 0 (peor) a 100 (mejor).",
        verbose_name="Estado de salud (0-100)"
    )

    def __str__(self):
        return f"EuroQol EVA Salud - {self.visita_examen}"


class MoCAResult(ResultadoExamenBase):
    # ===== 1–4: Visuoespacial y denominación =====
    alternancia = models.PositiveSmallIntegerField(default=0, verbose_name="Alternancia")  # 0–1
    cubo = models.PositiveSmallIntegerField(default=0, verbose_name="Cubo")  # 0–1
    reloj = models.PositiveSmallIntegerField(default=0, verbose_name="Reloj")  # 0–3
    denominacion = models.PositiveSmallIntegerField(default=0, verbose_name="Denominación")  # 0–3

    # ===== 6: Atención =====
    atencion_secuencia = models.PositiveSmallIntegerField(default=0, verbose_name="Atención secuencia")  # 0–1
    atencion_inversa = models.PositiveSmallIntegerField(default=0, verbose_name="Atención inversa")  # 0–1

    # Concentración
    errores_concentracion = models.PositiveSmallIntegerField(default=0, verbose_name="Errores de concentración")
    concentracion_resultado = models.CharField(
        max_length=10,
        choices=[("no_fallo", "No falló"), ("fallo", "Falló")],
        blank=True,
        null=True,
        verbose_name="Resultado concentración"
    )

    # Sustracción seriada
    sustraccion_1 = models.BooleanField(default=False, verbose_name="Sustracción 1 (93)")  # 93
    sustraccion_2 = models.BooleanField(default=False, verbose_name="Sustracción 2 (86)")  # 86
    sustraccion_3 = models.BooleanField(default=False, verbose_name="Sustracción 3 (79)")  # 79
    sustraccion_4 = models.BooleanField(default=False, verbose_name="Sustracción 4 (72)")  # 72
    sustraccion_5 = models.BooleanField(default=False, verbose_name="Sustracción 5 (65)")  # 65

    # Total atención (calculado)
    atencion = models.PositiveSmallIntegerField(default=0, verbose_name="Total atención")  # 0–6

    # ===== 7: Repetición =====
    repeticion_frase_1 = models.BooleanField(default=False, verbose_name="Repetición frase 1")
    repeticion_frase_2 = models.BooleanField(default=False, verbose_name="Repetición frase 2")
    repeticion = models.PositiveSmallIntegerField(default=0, verbose_name="Total repetición")  # 0–2

    # ===== 8: Fluidez =====
    numero_palabras_fluidez = models.PositiveSmallIntegerField(default=0, verbose_name="Número de palabras en fluidez")
    fluidez = models.PositiveSmallIntegerField(default=0, verbose_name="Puntaje fluidez")  # 0–1

    # ===== 9: Abstracción =====
    abstraccion = models.PositiveSmallIntegerField(default=0, verbose_name="Abstracción")  # 0–2

    # ===== 10: Recuerdo diferido =====
    palabra_rostro = models.BooleanField(default=False, verbose_name="Palabra: rostro")
    palabra_seda = models.BooleanField(default=False, verbose_name="Palabra: seda")
    palabra_iglesia = models.BooleanField(default=False, verbose_name="Palabra: iglesia")
    palabra_clavel = models.BooleanField(default=False, verbose_name="Palabra: clavel")
    palabra_rojo = models.BooleanField(default=False, verbose_name="Palabra: rojo")

    diferido = models.PositiveSmallIntegerField(default=0, verbose_name="Total recuerdo diferido")  # 0–5

    # D-19: MIS — recuerdo con pistas (categoría / opción múltiple)
    pista_cat_rostro = models.BooleanField(default=False, verbose_name="Pista categoría: rostro")
    pista_cat_seda = models.BooleanField(default=False, verbose_name="Pista categoría: seda")
    pista_cat_iglesia = models.BooleanField(default=False, verbose_name="Pista categoría: iglesia")
    pista_cat_clavel = models.BooleanField(default=False, verbose_name="Pista categoría: clavel")
    pista_cat_rojo = models.BooleanField(default=False, verbose_name="Pista categoría: rojo")
    pista_opcion_rostro = models.BooleanField(default=False, verbose_name="Pista opción: rostro")
    pista_opcion_seda = models.BooleanField(default=False, verbose_name="Pista opción: seda")
    pista_opcion_iglesia = models.BooleanField(default=False, verbose_name="Pista opción: iglesia")
    pista_opcion_clavel = models.BooleanField(default=False, verbose_name="Pista opción: clavel")
    pista_opcion_rojo = models.BooleanField(default=False, verbose_name="Pista opción: rojo")
    mis = models.PositiveSmallIntegerField(
        blank=True, null=True, default=0, verbose_name="MIS (índice de memoria)"
    )

    # ===== 11: Orientación =====
    orientacion_fecha = models.BooleanField(default=False, verbose_name="Orientación: fecha")
    orientacion_mes = models.BooleanField(default=False, verbose_name="Orientación: mes")
    orientacion_anio = models.BooleanField(default=False, verbose_name="Orientación: año")
    orientacion_dia_semana = models.BooleanField(default=False, verbose_name="Orientación: día de la semana")
    orientacion_lugar = models.BooleanField(default=False, verbose_name="Orientación: lugar")
    orientacion_localidad = models.BooleanField(default=False, verbose_name="Orientación: localidad")

    orientacion = models.PositiveSmallIntegerField(default=0, verbose_name="Total orientación")  # 0–6

    # ===== Escolaridad =====
    educacion_baja = models.BooleanField(default=False, verbose_name="Educación baja")

    # ===== Totales =====
    puntaje_total = models.PositiveSmallIntegerField(default=0, verbose_name="Puntaje total")
    interpretacion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Interpretación")

    # D-19: impresión por dominios (no ítem a ítem)
    PRINT_SECCIONES_INICIOS = [
        ("alternancia", "Visuoespacial / Ejecutiva"),
        ("denominacion", "Denominación"),
        ("atencion_secuencia", "Atención"),
        ("repeticion_frase_1", "Lenguaje"),
        ("abstraccion", "Abstracción"),
        ("palabra_rostro", "Memoria diferida / MIS"),
        ("orientacion_fecha", "Orientación"),
        ("educacion_baja", "Totales"),
    ]

    def __str__(self):
        return f"MoCA - {self.visita_examen_id}"


class ParticipanteYesavageResult(ResultadoExamenBase):
    # Preguntas (sí/no)
    satisfaccion_vida = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True,
        verbose_name="Satisfacción con la vida"
    )
    disminuir_actividades = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True,
        verbose_name="Disminuir actividades"
    )
    vida_vacia = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True,
        verbose_name="Vida vacía"
    )
    aburrido_frecuente = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True,
        verbose_name="Aburrido frecuentemente"
    )
    buen_animo = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True,
        verbose_name="Buen ánimo"
    )
    preocupacion = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True,
        verbose_name="Preocupación"
    )
    felicidad = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True,
        verbose_name="Felicidad"
    )
    frecuencia_desamparado = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True,
        verbose_name="Frecuencia desamparado"
    )
    quedarse_casa = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True,
        verbose_name="Quedarse en casa"
    )
    problemas_memoria = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True,
        verbose_name="Problemas de memoria"
    )
    maravilla_vivir = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True,
        verbose_name="Maravilla de vivir"
    )
    inutil = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True,
        verbose_name="Inútil"
    )
    lleno_energia = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True,
        verbose_name="Lleno de energía"
    )
    sin_esperanza = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True,
        verbose_name="Sin esperanza"
    )
    otras_personas_mejor = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True,
        verbose_name="Otras personas están mejor"
    )

    # Puntaje total (0–15)
    puntaje_total = models.IntegerField(default=0, verbose_name="Puntaje total")
    interpretacion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Interpretación")

    def __str__(self):
        return f"Yesavage - {self.visita_examen_id}"


class ZaritResult(ResultadoExamenBase):
    pide_ayuda = models.CharField(max_length=50, blank=True, null=True, verbose_name="Pide ayuda")
    falta_tiempo_propio = models.CharField(max_length=50, blank=True, null=True, verbose_name="Falta de tiempo propio")
    agobio = models.CharField(max_length=50, blank=True, null=True, verbose_name="Agobio")
    verguenza_conducta = models.CharField(max_length=50, blank=True, null=True, verbose_name="Vergüenza por conducta")
    sentir_enfado = models.CharField(max_length=50, blank=True, null=True, verbose_name="Sentir enfado")
    afectar_relacion_negativamente = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Afectar relación negativamente"
    )
    miedo_futuro = models.CharField(max_length=50, blank=True, null=True, verbose_name="Miedo al futuro")
    dependencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Dependencia")
    sentir_tension = models.CharField(max_length=50, blank=True, null=True, verbose_name="Sentir tensión")
    deterioro_salud = models.CharField(max_length=50, blank=True, null=True, verbose_name="Deterioro de la salud")
    menos_intimidad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Menos intimidad")
    resentir_vida_social = models.CharField(max_length=50, blank=True, null=True, verbose_name="Resentir vida social")
    desatender_amistades = models.CharField(max_length=50, blank=True, null=True, verbose_name="Desatender amistades")
    unica_dependencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Única dependencia")
    dinero_insuficiente = models.CharField(max_length=50, blank=True, null=True, verbose_name="Dinero insuficiente")
    incapaz_mas_tiempo = models.CharField(max_length=50, blank=True, null=True, verbose_name="Incapaz de cuidar más tiempo")
    perder_control_vida = models.CharField(max_length=50, blank=True, null=True, verbose_name="Perder control de la vida")
    cuidado_a_otros = models.CharField(max_length=50, blank=True, null=True, verbose_name="Cuidado a otros")
    indecision_que_hacer = models.CharField(max_length=50, blank=True, null=True, verbose_name="Indecisión sobre qué hacer")
    hacer_mas = models.CharField(max_length=50, blank=True, null=True, verbose_name="Hacer más")
    cuidar_mejor = models.CharField(max_length=50, blank=True, null=True, verbose_name="Cuidar mejor")
    grado_carga = models.CharField(max_length=50, blank=True, null=True, verbose_name="Grado de carga")

    # Resultados globales
    puntaje_total = models.IntegerField(default=0, verbose_name="Puntaje total")
    interpretacion = models.CharField(max_length=50, blank=True, null=True, verbose_name="Interpretación")

    def __str__(self):
        return f"Escala de Zarit - {self.visita_examen_id}"


class AQDCuidadorResult(ResultadoExamenBase):
    # verbose_name = texto exacto de la pregunta en el template
    # examenes_anosognosia/Anosognosia_Cuidador_AQD.html (para que impresión
    # y vista "Ver" muestren la pregunta completa).
    recordar_fecha = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para recordar la fecha?")
    orientacion_lugares_nuevos = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para orientarse en lugares nuevos?")
    recordar_llamadas = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para recordar llamadas telefónicas?")
    entender_conversacion = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para entender conversaciones?")
    firmar = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para firmar?")
    entender_lectura = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para entender lo que lee?")
    mantener_orden = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para mantener en orden sus cosas?")
    recordar_lugar_objetos = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para recordar dónde deja los objetos en su casa?")
    escribir = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para escribir?")
    manejar_dinero = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para manejar dinero?")
    orientacion_zona_donde_vive = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para orientarse en la zona donde vive?")
    recordar_citas = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para recordar citas (ejemplo: cuándo ir al médico)?")
    pasatiempos = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para practicar sus pasatiempos?")
    comunicarse_con_gente = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para comunicarse con la gente?")
    calculos_mentales = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para hacer cálculos mentales? (por ejemplo: sumar, restar, multiplicar, dividir).")
    recordar_compras = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para recordar las cosas que va a comprar?")
    contener_orina = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para contener la orina?")
    entender_pelicula = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para entender una película?")
    orientacion_en_casa = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para orientarse dentro de su casa?")
    hacer_tareas_hogar = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para realizar tareas del hogar como cocinar, limpiar, etc.?")
    comer_solo = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para comer solo?")
    realizar_tramites = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene el paciente dificultades para realizar trámites? (por ejemplo: ir al banco, a la EPS, etc.).")
    decisiones_y_adaptacion = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Ha notado al paciente menos flexible para tomar decisiones y sin poder adaptarse a cosas nuevas?")
    egoismo = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Ha notado al paciente más egoísta y que no presta atención a las necesidades de los demás?")
    enojo_menos_paciencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Ha notado que el paciente se enoja por pequeñeces y pierde la paciencia con más facilidad?")
    llorar_con_facilidad = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Ha notado que el paciente llora con excesiva facilidad?")
    reir_situaciones_inapropiadas = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="¿Ha notado que el paciente se ríe en situaciones inapropiadas?"
    )
    temas_sexuales = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Ha notado al paciente más interesado en temas sexuales, y habla permanentemente de esos temas?")
    falta_de_interes = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Ha notado al paciente con falta de interés en cosas que antes le interesaban?")
    deprimido = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Ha notado al paciente más deprimido?")

    # B-10: suma de ítems en escala 1–4
    puntaje_total = models.IntegerField(
        blank=True, null=True, default=0, verbose_name="Puntaje total"
    )

    _AQD_ITEM_FIELDS = (
        "recordar_fecha",
        "orientacion_lugares_nuevos",
        "recordar_llamadas",
        "entender_conversacion",
        "firmar",
        "entender_lectura",
        "mantener_orden",
        "recordar_lugar_objetos",
        "escribir",
        "manejar_dinero",
        "orientacion_zona_donde_vive",
        "recordar_citas",
        "pasatiempos",
        "comunicarse_con_gente",
        "calculos_mentales",
        "recordar_compras",
        "contener_orina",
        "entender_pelicula",
        "orientacion_en_casa",
        "hacer_tareas_hogar",
        "comer_solo",
        "realizar_tramites",
        "decisiones_y_adaptacion",
        "egoismo",
        "enojo_menos_paciencia",
        "llorar_con_facilidad",
        "reir_situaciones_inapropiadas",
        "temas_sexuales",
        "falta_de_interes",
        "deprimido",
    )

    def calcular_puntaje_total(self):
        total = 0
        for name in self._AQD_ITEM_FIELDS:
            raw = getattr(self, name, None)
            if raw in (None, ""):
                continue
            try:
                total += int(str(raw).strip().split()[0])
            except (TypeError, ValueError):
                continue
        return total

    def save(self, *args, **kwargs):
        self.puntaje_total = self.calcular_puntaje_total()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"AQ-D Cuidador - {self.visita_examen_id}"


class AQDParticipanteResult(ResultadoExamenBase):
    # verbose_name = texto exacto de la pregunta en el template
    # examenes_anosognosia/Anosognosia_Participante_AQD.html.
    recordar_fecha = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para recordar la fecha?")
    orientacion_lugares_nuevos = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para orientarse en lugares nuevos?")
    recordar_llamadas = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para recordar llamadas telefónicas?")
    entender_conversacion = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para entender conversaciones?")
    firmar = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para firmar?")
    entender_lectura = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para entender lo que lee?")
    mantener_orden = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para mantener en orden sus cosas?")
    recordar_lugar_objetos = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para recordar dónde deja los objetos en su casa?")
    escribir = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para escribir?")
    manejar_dinero = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para manejar dinero?")
    orientacion_zona_donde_vive = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para orientarse en la zona donde vive?")
    recordar_citas = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para recordar citas (ejemplo: cuándo ir al médico)?")
    pasatiempos = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para practicar sus pasatiempos?")
    comunicarse_con_gente = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para comunicarse con las personas?")
    calculos_mentales = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para hacer cálculos mentales? (por ejemplo: sumar, restar, multiplicar, dividir).")
    recordar_compras = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para recordar las cosas que va a comprar?")
    contener_orina = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para contener la orina?")
    entender_pelicula = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para entender una película?")
    orientacion_en_casa = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para orientarse dentro de su casa?")
    hacer_tareas_hogar = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para realizar tareas del hogar como cocinar, limpiar, etc.?")
    comer_solo = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para comer solo?")
    realizar_tramites = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Tiene usted dificultades para realizar trámites? (por ejemplo: ir al banco, a la EPS, etc.).")
    decisiones_y_adaptacion = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Se siente usted menos flexible para tomar decisiones y sin poder adaptarse a cosas nuevas?")
    egoismo = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Ha notado que usted está más egoísta y no presta atención a las necesidades de los demás?")
    enojo_menos_paciencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Ha notado que usted se enoja por pequeñeces y pierde la paciencia con más facilidad?")
    llorar_con_facilidad = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Ha notado usted que llora con excesiva facilidad?")
    reir_situaciones_inapropiadas = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="¿Ha notado usted que se ríe en situaciones inapropiadas?"
    )
    temas_sexuales = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Ha notado que usted está más interesado en temas sexuales, y habla permanentemente de esos temas?")
    falta_de_interes = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Ha notado usted falta de interés en cosas que antes le interesaban?")
    deprimido = models.CharField(max_length=50, blank=True, null=True, verbose_name="¿Se ha sentido más deprimido?")

    # B-10: suma de ítems en escala 1–4
    puntaje_total = models.IntegerField(
        blank=True, null=True, default=0, verbose_name="Puntaje total"
    )

    _AQD_ITEM_FIELDS = AQDCuidadorResult._AQD_ITEM_FIELDS

    def calcular_puntaje_total(self):
        total = 0
        for name in self._AQD_ITEM_FIELDS:
            raw = getattr(self, name, None)
            if raw in (None, ""):
                continue
            try:
                total += int(str(raw).strip().split()[0])
            except (TypeError, ValueError):
                continue
        return total

    def save(self, *args, **kwargs):
        self.puntaje_total = self.calcular_puntaje_total()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"AQ-D Participante - {self.visita_examen_id}"


class CDRCuidadorResult(ResultadoExamenBase):
    # verbose_name = texto de Anosognosia_Cuidador_CDR.html (para Ver/PDF).
    PRINT_SECCIONES_INICIOS = [
        ("memoria_p1", "Memoria"),
        ("orientacion_p1", "Orientación"),
        ("juicio_p1", "Juicio y resolución de problemas"),
        ("trabaja_actualmente", "Actividades comunitarias"),
        ("cambios_tareas_domesticas", "Actividades domésticas y pasatiempos"),
        ("cuidado_p1", "Cuidado personal"),
    ]

    # ====================
    # Dominio: Memoria
    # ====================
    memoria_p1 = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="¿Ha notado pérdida de memoria reciente?",
    )
    memoria_p1_1 = models.CharField(
        max_length=10, blank=True, null=True,
        verbose_name="¿Es este un problema constante (a diferencia de esporádico)?",
    )
    memoria_p2 = models.CharField(
        max_length=20, blank=True, null=True,
        verbose_name="¿Puede él/ella recordar eventos recientes?",
    )
    memoria_p3 = models.CharField(
        max_length=200, blank=True, null=True,
        verbose_name="¿Puede él/ella recordar una lista breve de artículos (compras)?",
    )
    memoria_p4 = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="¿Se ha registrado algún deterioro en su memoria durante el último año?",
    )
    memoria_p5 = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name=(
            "¿Se encuentra su memoria deteriorada a tal punto que habría interferido "
            "con la realización de sus actividades cotidianas habituales de años atrás "
            "(o actividades previas a la jubilación)?"
        ),
    )
    memoria_p6 = models.CharField(
        max_length=200, blank=True, null=True,
        verbose_name=(
            "¿Se olvida él/ella completamente de un evento importante "
            "(ej., viaje, fiesta, matrimonio familiar) a pocas semanas del evento?"
        ),
    )
    memoria_p7 = models.CharField(
        max_length=200, blank=True, null=True,
        verbose_name="¿Se olvida él/ella de detalles relevantes del evento importante?",
    )
    memoria_p8 = models.CharField(
        max_length=200, blank=True, null=True,
        verbose_name=(
            "¿Se olvida él/ella completamente de información importante del pasado lejano "
            "(ej. fecha de cumpleaños, fecha de matrimonio, lugar de trabajo)?"
        ),
    )

    evento_recuerda_semana = models.TextField(
        blank=True, null=True,
        verbose_name="Evento reciente que debería recordar (en el curso de una semana)",
    )
    evento_recuerda_mes = models.TextField(
        blank=True, null=True,
        verbose_name="Evento reciente que debería recordar (en el curso de un mes)",
    )

    nacimiento_fecha = models.DateField(blank=True, null=True, verbose_name="¿Cuándo nació él/ella?")
    nacimiento_lugar = models.CharField(max_length=150, blank=True, null=True, verbose_name="¿Dónde nació él/ella?")
    colegio_nombre = models.CharField(
        max_length=150, blank=True, null=True,
        verbose_name="Último colegio al que asistió — Nombre",
    )
    colegio_lugar = models.CharField(
        max_length=150, blank=True, null=True,
        verbose_name="Último colegio al que asistió — Lugar",
    )
    colegio_grado = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="Último colegio al que asistió — Grado",
    )
    ocupacion_principal = models.CharField(
        max_length=150, blank=True, null=True,
        verbose_name=(
            "¿Cuál fue la principal ocupación de él/ella "
            "(o la ocupación del cónyuge si el sujeto no trabajaba)?"
        ),
    )
    ultimo_trabajo = models.CharField(
        max_length=150, blank=True, null=True,
        verbose_name=(
            "¿Cuál fue el último trabajo de él/ella "
            "(o trabajo del cónyuge si el sujeto no trabajaba)?"
        ),
    )
    jubilacion = models.TextField(
        blank=True, null=True,
        verbose_name="¿Cuándo se jubiló él/ella (o cónyuge) y por qué?",
    )

    # ====================
    # Dominio: Orientación
    # ====================
    orientacion_p1 = models.CharField(
        max_length=200, blank=True, null=True,
        verbose_name="¿Con qué frecuencia sabe él/ella exactamente la fecha del día?",
    )
    orientacion_p2 = models.CharField(
        max_length=200, blank=True, null=True,
        verbose_name="¿Con qué frecuencia sabe él/ella exactamente el mes?",
    )
    orientacion_p3 = models.CharField(
        max_length=200, blank=True, null=True,
        verbose_name="¿Con qué frecuencia sabe él/ella exactamente el año?",
    )
    orientacion_p4 = models.CharField(
        max_length=200, blank=True, null=True,
        verbose_name="¿Con qué frecuencia sabe él/ella exactamente el día de la semana?",
    )
    orientacion_p5 = models.CharField(
        max_length=200, blank=True, null=True,
        verbose_name=(
            "¿Presenta él/ella dificultad para relacionar acontecimientos en el tiempo "
            "(cuándo ocurrieron unos eventos en relación con los otros)?"
        ),
    )
    orientacion_p6 = models.CharField(
        max_length=200, blank=True, null=True,
        verbose_name="¿Puede él/ella orientarse en calles que le son conocidas?",
    )
    orientacion_p7 = models.CharField(
        max_length=200, blank=True, null=True,
        verbose_name=(
            "¿Con qué frecuencia sabe él/ella cómo llegar de un lugar a otro "
            "cuando se encuentra fuera de su vecindario?"
        ),
    )
    orientacion_p8 = models.CharField(
        max_length=200, blank=True, null=True,
        verbose_name="¿Con qué frecuencia puede él/ella orientarse dentro de su casa?",
    )

    # ====================
    # Dominio: Juicio y resolución de problemas
    # ====================
    juicio_p1 = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name=(
            "En general, si Ud. tuviera que evaluar la capacidad de él/ella "
            "para resolver problemas en este momento, Ud. la consideraría:"
        ),
    )
    juicio_p2 = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name=(
            "Evalúe la capacidad de él/ella para manejar pequeñas sumas de dinero "
            "(ej. dar cambio, dejar una pequeña propina):"
        ),
    )
    juicio_p3 = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name=(
            "Evalúe la capacidad de él/ella para manejar transacciones financieras "
            "o de negocios complicadas (ej. balancear una chequera, pagar cuentas):"
        ),
    )
    juicio_p4 = models.CharField(
        max_length=150, blank=True, null=True,
        verbose_name=(
            "¿Puede él/ella manejar una emergencia doméstica "
            "(ej. gotera en las cañerías, pequeño incendio)?"
        ),
    )
    juicio_p5 = models.CharField(
        max_length=500, blank=True, null=True,
        verbose_name="¿Puede él/ella comprender situaciones o explicaciones?",
    )
    juicio_p6 = models.CharField(
        max_length=500, blank=True, null=True,
        verbose_name=(
            "¿Se comporta apropiadamente en situaciones sociales e interacciones "
            "con otra gente (como usualmente se comportaba antes de la enfermedad)?"
        ),
    )

    # ====================
    # Actividades comunitarias
    # ====================
    trabaja_actualmente = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="¿Él/Ella sigue trabajando?",
    )
    memoria_causa_jubilacion = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name=(
            "¿Problemas con la memoria o el pensamiento de él/ella "
            "contribuyeron a su decisión de jubilarse?"
        ),
    )
    dificultades_trabajo_memoria = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name=(
            "¿Él/Ella presenta dificultades significativas en el trabajo "
            "debido a problemas con su memoria o pensamiento?"
        ),
    )

    condujo_alguna_vez = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name="¿Condujo él/ella alguna vez un carro?",
    )
    conduce_actualmente = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name="¿Actualmente, él/ella conduce un carro?",
    )
    dejo_de_conducir_por_memoria = models.CharField(
        max_length=5, blank=True, null=True,
        verbose_name="¿Se debe esto a problemas con su memoria o pensamiento?",
    )
    riesgos_conduccion = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name=(
            "Si él/ella todavía conduce, ¿existen problemas o riesgos "
            "debido a un pensamiento pobre?"
        ),
    )

    compras_independientes = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name="¿Es él/ella todavía capaz de salir a comprar lo que necesita en forma independiente?",
    )
    actividades_fuera_hogar = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name="¿Es él/ella capaz de llevar a cabo actividades fuera del hogar en forma independiente?",
    )
    asiste_funciones_sociales = models.CharField(
        max_length=5, blank=True, null=True,
        verbose_name="¿Asiste él/ella a funciones sociales fuera del hogar familiar?",
    )
    motivo_no_funciones = models.TextField(
        blank=True, null=True,
        verbose_name="En caso negativo, ¿por qué no asiste a funciones sociales?",
    )

    parece_enfermo = models.CharField(
        max_length=5, blank=True, null=True,
        verbose_name=(
            "¿Alguien que no conozca al sujeto y observara su comportamiento "
            "pensaría que éste/a se encuentra enfermo/a?"
        ),
    )
    participa_hogar_geriatrico = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name=(
            "Si el sujeto se encuentra en un hogar geriátrico, ¿participa activamente "
            "él/ella en actividades sociales (con participación intelectual)?"
        ),
    )
    info_suficiente_comunitarias = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name=(
            "¿Existe suficiente información disponible para evaluar el grado de "
            "deterioro del sujeto en las actividades comunitarias?"
        ),
    )
    notas_comunitarias = models.TextField(
        blank=True, null=True,
        verbose_name="Notas adicionales (actividades comunitarias)",
    )

    # ====================
    # Actividades domésticas y pasatiempos
    # ====================
    cambios_tareas_domesticas = models.TextField(
        blank=True, null=True,
        verbose_name="¿Qué cambios se han registrado en las habilidades de él/ella para realizar tareas domésticas?",
    )
    cosas_que_aun_realiza_domesticas = models.TextField(
        blank=True, null=True,
        verbose_name="¿Qué cosas puede él/ella todavía realizar bien? (tareas domésticas)",
    )
    cambios_pasatiempos = models.TextField(
        blank=True, null=True,
        verbose_name="¿Qué cambios se han registrado en las habilidades de él/ella para realizar pasatiempos?",
    )
    cosas_que_aun_realiza_pasatiempos = models.TextField(
        blank=True, null=True,
        verbose_name="¿Qué cosas puede él/ella todavía realizar bien? (pasatiempos)",
    )
    actividades_no_realiza_en_hogar = models.TextField(
        blank=True, null=True,
        verbose_name=(
            "Si el sujeto se encuentra en un hogar geriátrico, ¿qué cosas ya no puede "
            "realizar bien (actividades domésticas y pasatiempos)?"
        ),
    )

    habilidad_domestica_dementia_scale = models.TextField(
        blank=True, null=True,
        verbose_name="Habilidad para realizar tareas domésticas (Dementia Scale of Blessed)",
    )
    descripcion_habilidad_domestica = models.TextField(
        blank=True, null=True,
        verbose_name="Descripción de la habilidad doméstica",
    )
    nivel_desempeno_domestico = models.CharField(
        max_length=2000, blank=True, null=True,
        verbose_name="¿En qué nivel es él/ella capaz de realizar tareas domésticas?",
    )
    notas_domesticas_pasatiempos = models.TextField(
        blank=True, null=True,
        verbose_name="Notas sobre actividades domésticas y pasatiempos",
    )

    # ====================
    # Cuidado personal
    # ====================
    cuidado_p1 = models.TextField(
        blank=True, null=True,
        verbose_name="Vestirse (The Dementia Scale of Blessed)",
    )
    cuidado_p2 = models.TextField(blank=True, null=True, verbose_name="Lavado, aseo")
    cuidado_p3 = models.TextField(blank=True, null=True, verbose_name="Hábitos de alimentación")
    cuidado_p4 = models.TextField(
        blank=True, null=True,
        verbose_name="Control de esfínteres (The Dementia Scale of Blessed)",
    )

    def __str__(self):
        return f"CDR Cuidador - {self.visita_examen_id}"


class CDRParticipanteResult(ResultadoExamenBase):
    # verbose_name = texto de Anosognosia_Participante_CDR.html (para Ver/PDF).
    PRINT_SECCIONES_INICIOS = [
        ("memoria_p1", "Memoria"),
        ("orientacion_p1", "Orientación"),
        ("juicio_p1_respuesta", "Juicio y resolución de problemas"),
    ]

    # ====================
    # Dominio: Memoria
    # ====================
    memoria_p1 = models.CharField(
        max_length=5, blank=True, null=True,
        verbose_name="¿Tiene usted problemas con su memoria o pensamiento?",
    )

    evento_recuerda_semana = models.TextField(
        blank=True, null=True,
        verbose_name="Evento reciente que debería recordar (en el curso de una semana)",
    )
    memoria_semana_calificacion = models.TextField(
        blank=True, null=True,
        verbose_name="Calificación del recuerdo (semana)",
    )

    evento_recuerda_mes = models.TextField(
        blank=True, null=True,
        verbose_name="Evento reciente que debería recordar (en el curso de un mes)",
    )
    memoria_mes_calificacion = models.TextField(
        blank=True, null=True,
        verbose_name="Calificación del recuerdo (mes)",
    )

    # Ensayos (checkboxes del nombre/dirección)
    ensayo1_juan = models.BooleanField(default=False, verbose_name="Ensayo 1 — Juan")
    ensayo1_perez = models.BooleanField(default=False, verbose_name="Ensayo 1 — Pérez")
    ensayo1_calle = models.BooleanField(default=False, verbose_name="Ensayo 1 — Calle 42")
    ensayo1_avenida = models.BooleanField(default=False, verbose_name="Ensayo 1 — Avenida Boyacá")
    ensayo1_cali = models.BooleanField(default=False, verbose_name="Ensayo 1 — Cali")

    ensayo2_juan = models.BooleanField(default=False, verbose_name="Ensayo 2 — Juan")
    ensayo2_perez = models.BooleanField(default=False, verbose_name="Ensayo 2 — Pérez")
    ensayo2_calle = models.BooleanField(default=False, verbose_name="Ensayo 2 — Calle 42")
    ensayo2_avenida = models.BooleanField(default=False, verbose_name="Ensayo 2 — Avenida Boyacá")
    ensayo2_cali = models.BooleanField(default=False, verbose_name="Ensayo 2 — Cali")

    ensayo3_juan = models.BooleanField(default=False, verbose_name="Ensayo 3 — Juan")
    ensayo3_perez = models.BooleanField(default=False, verbose_name="Ensayo 3 — Pérez")
    ensayo3_calle = models.BooleanField(default=False, verbose_name="Ensayo 3 — Calle 42")
    ensayo3_avenida = models.BooleanField(default=False, verbose_name="Ensayo 3 — Avenida Boyacá")
    ensayo3_cali = models.BooleanField(default=False, verbose_name="Ensayo 3 — Cali")

    fecha_nacimiento = models.DateField(blank=True, null=True, verbose_name="¿Cuándo nació?")
    lugar_nacimiento = models.CharField(max_length=100, blank=True, null=True, verbose_name="¿Dónde nació?")

    colegio_nombre = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="Último colegio al que asistió — Nombre",
    )
    colegio_lugar = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="Último colegio al que asistió — Lugar",
    )
    colegio_grado = models.CharField(
        max_length=200, blank=True, null=True,
        verbose_name="Último colegio al que asistió — Grado",
    )

    ocupacion_principal = models.CharField(
        max_length=150, blank=True, null=True,
        verbose_name=(
            "¿Cuál era su principal ocupación/trabajo o la de su cónyuge, "
            "si Ud. no estaba empleado/a?"
        ),
    )
    ultimo_trabajo = models.CharField(
        max_length=150, blank=True, null=True,
        verbose_name=(
            "¿Cuál fue su último trabajo importante "
            "(o el de su cónyuge, si Ud. no estaba empleado/a)?"
        ),
    )
    jubilacion = models.TextField(
        blank=True, null=True,
        verbose_name="¿Cuándo se jubiló (o su cónyuge) y por qué?",
    )

    # Repetición del nombre/dirección
    repeticion_juan = models.BooleanField(default=False, verbose_name="Repetición — Juan")
    repeticion_perez = models.BooleanField(default=False, verbose_name="Repetición — Pérez")
    repeticion_calle = models.BooleanField(default=False, verbose_name="Repetición — Calle 42")
    repeticion_avenida = models.BooleanField(default=False, verbose_name="Repetición — Avenida Boyacá")
    repeticion_cali = models.BooleanField(default=False, verbose_name="Repetición — Cali")

    # ====================
    # Dominio: Orientación
    # ====================
    orientacion_p1 = models.CharField(
        max_length=15, blank=True, null=True,
        verbose_name="¿Qué fecha es hoy?",
    )
    orientacion_p2 = models.CharField(
        max_length=150, blank=True, null=True,
        verbose_name="¿Qué día de la semana es hoy?",
    )
    orientacion_p3 = models.CharField(
        max_length=150, blank=True, null=True,
        verbose_name="¿En qué mes estamos?",
    )
    orientacion_p4 = models.CharField(
        max_length=150, blank=True, null=True,
        verbose_name="¿En qué año estamos?",
    )
    orientacion_p5 = models.CharField(
        max_length=500, blank=True, null=True,
        verbose_name="¿Cómo se llama este lugar?",
    )
    orientacion_p6 = models.CharField(
        max_length=500, blank=True, null=True,
        verbose_name="¿En qué pueblo o ciudad estamos?",
    )
    orientacion_p7 = models.CharField(
        max_length=150, blank=True, null=True,
        verbose_name="¿Qué hora es?",
    )
    orientacion_p8 = models.CharField(
        max_length=150, blank=True, null=True,
        verbose_name="¿Sabe el sujeto quién es el informante (según el criterio del entrevistador)?",
    )

    # ====================
    # Dominio: Juicio y resolución de problemas
    # ====================
    juicio_p1_respuesta = models.TextField(
        blank=True, null=True,
        verbose_name="¿En qué se parecen un rábano y una coliflor? — Respuesta",
    )
    juicio_p1_puntaje = models.IntegerField(
        blank=True, null=True,
        verbose_name="¿En qué se parecen un rábano y una coliflor? — Puntaje",
    )

    juicio_p2_respuesta = models.TextField(
        blank=True, null=True,
        verbose_name="¿En qué se parecen un escritorio y una estantería? — Respuesta",
    )
    juicio_p2_puntaje = models.IntegerField(
        blank=True, null=True,
        verbose_name="¿En qué se parecen un escritorio y una estantería? — Puntaje",
    )

    juicio_p3_respuesta = models.TextField(
        blank=True, null=True,
        verbose_name="¿Cuál es la diferencia entre una mentira y una equivocación? — Respuesta",
    )
    juicio_p3_puntaje = models.IntegerField(
        blank=True, null=True,
        verbose_name="¿Cuál es la diferencia entre una mentira y una equivocación? — Puntaje",
    )

    juicio_p4_respuesta = models.TextField(
        blank=True, null=True,
        verbose_name="¿Cuál es la diferencia entre un río y un canal? — Respuesta",
    )
    juicio_p4_puntaje = models.IntegerField(
        blank=True, null=True,
        verbose_name="¿Cuál es la diferencia entre un río y un canal? — Puntaje",
    )

    juicio_p5 = models.CharField(
        max_length=15,
        choices=[
            ("correcto", "Correcto"),
            ("incorrecto", "Incorrecto"),
        ],
        blank=True,
        null=True,
        verbose_name="¿Cuántos centavos hay en un peso?",
    )

    juicio_p6 = models.CharField(
        max_length=15,
        choices=[
            ("correcto", "Correcto"),
            ("incorrecto", "Incorrecto"),
        ],
        blank=True,
        null=True,
        verbose_name="¿Cuántas monedas de 50 pesos hay en $1,350?",
    )

    juicio_p7 = models.CharField(
        max_length=15,
        choices=[
            ("correcto", "Correcto"),
            ("incorrecto", "Incorrecto"),
        ],
        blank=True,
        null=True,
        verbose_name="Restar 3 de 20 y continuar hasta llegar a 2 o 1",
    )

    juicio_p8_puntaje = models.IntegerField(
        blank=True, null=True,
        verbose_name="Al llegar a una ciudad extraña, ¿cómo localizaría usted a un amigo? — Puntaje",
    )

    juicio_p9 = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name=(
            "Evaluación del sujeto respecto a su discapacidad, posición social "
            "y comprensión de por qué se encuentra en el test"
        ),
    )

    def __str__(self):
        return f"CDR Participante - {self.visita_examen_id}"


class RedLatSpanishResult(ResultadoExamenBase):
    # ---------- Autocuidado ----------
    comer = models.CharField(max_length=255, blank=True, null=True, verbose_name="Comer")
    vestirse = models.CharField(max_length=255, blank=True, null=True, verbose_name="Vestirse")
    banarse = models.CharField(max_length=255, blank=True, null=True, verbose_name="Bañarse")
    bano = models.CharField(max_length=255, blank=True, null=True, verbose_name="Uso del baño")
    medicamentos = models.CharField(max_length=255, blank=True, null=True, verbose_name="Medicamentos")
    apariencia = models.CharField(max_length=255, blank=True, null=True, verbose_name="Apariencia")

    # ---------- Cuidado del hogar ----------
    cocinar = models.CharField(max_length=255, blank=True, null=True, verbose_name="Cocinar")
    poner_mesa = models.CharField(max_length=255, blank=True, null=True, verbose_name="Poner la mesa")
    aseo_hogar = models.CharField(max_length=255, blank=True, null=True, verbose_name="Aseo del hogar")
    mantener_casa = models.CharField(max_length=255, blank=True, null=True, verbose_name="Mantener la casa")
    reparar_hogar = models.CharField(max_length=255, blank=True, null=True, verbose_name="Reparar en el hogar")
    lavado_ropa = models.CharField(max_length=255, blank=True, null=True, verbose_name="Lavado de ropa")

    # ---------- Trabajo y recreación ----------
    trabajo = models.CharField(max_length=255, blank=True, null=True, verbose_name="Trabajo")
    recreacion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Recreación")
    organizaciones = models.CharField(max_length=255, blank=True, null=True, verbose_name="Organizaciones")
    desplazamiento = models.CharField(max_length=255, blank=True, null=True, verbose_name="Desplazamiento")

    # ---------- Compras y dinero ----------
    alimentos = models.CharField(max_length=255, blank=True, null=True, verbose_name="Compra de alimentos")
    dinero_efectivo = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dinero en efectivo")
    finanzas = models.CharField(max_length=255, blank=True, null=True, verbose_name="Finanzas")

    # ---------- Viajes ----------
    transporte_publico = models.CharField(max_length=255, blank=True, null=True, verbose_name="Transporte público")
    manejo_vehiculos = models.CharField(max_length=255, blank=True, null=True, verbose_name="Manejo de vehículos")
    movilidad_barrio = models.CharField(max_length=255, blank=True, null=True, verbose_name="Movilidad en el barrio")
    viajes_fuera = models.CharField(max_length=255, blank=True, null=True, verbose_name="Viajes fuera del barrio")

    # ---------- Comunicación ----------
    telefono = models.CharField(max_length=255, blank=True, null=True, verbose_name="Teléfono")
    conversacion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Conversación")
    comprension = models.CharField(max_length=255, blank=True, null=True, verbose_name="Comprensión")
    lectura = models.CharField(max_length=255, blank=True, null=True, verbose_name="Lectura")
    escritura = models.CharField(max_length=255, blank=True, null=True, verbose_name="Escritura")

    # ---------- Tecnología ----------
    computador = models.CharField(max_length=255, blank=True, null=True, verbose_name="Computador")
    telefono_celular = models.CharField(max_length=255, blank=True, null=True, verbose_name="Teléfono celular")
    cajero = models.CharField(max_length=255, blank=True, null=True, verbose_name="Cajero automático")
    internet = models.CharField(max_length=255, blank=True, null=True, verbose_name="Internet")
    email = models.CharField(max_length=255, blank=True, null=True, verbose_name="Email")
    redes_sociales = models.CharField(max_length=255, blank=True, null=True, verbose_name="Redes sociales")

    puntaje_autocuidado = models.CharField(max_length=20, blank=True, null=True, verbose_name="Puntaje autocuidado")
    puntaje_cuidado_hogar = models.CharField(max_length=20, blank=True, null=True, verbose_name="Puntaje cuidado del hogar")
    puntaje_trabajo_recreacion = models.CharField(max_length=20, blank=True, null=True, verbose_name="Puntaje trabajo y recreación")
    puntaje_compras_dinero = models.CharField(max_length=20, blank=True, null=True, verbose_name="Puntaje compras y dinero")
    puntaje_viajes = models.CharField(max_length=20, blank=True, null=True, verbose_name="Puntaje viajes")
    puntaje_comunicacion = models.CharField(max_length=20, blank=True, null=True, verbose_name="Puntaje comunicación")
    puntaje_tecnologia = models.CharField(max_length=20, blank=True, null=True, verbose_name="Puntaje tecnología")

    # B-10: suma de componentes
    puntaje_total = models.FloatField(
        blank=True, null=True, default=0, verbose_name="Puntaje total"
    )

    _REDLAT_COMPONENTES = (
        "puntaje_autocuidado",
        "puntaje_cuidado_hogar",
        "puntaje_trabajo_recreacion",
        "puntaje_compras_dinero",
        "puntaje_viajes",
        "puntaje_comunicacion",
        "puntaje_tecnologia",
    )

    def calcular_puntaje_total(self):
        total = 0.0
        for name in self._REDLAT_COMPONENTES:
            raw = getattr(self, name, None)
            if raw in (None, ""):
                continue
            try:
                total += float(str(raw).replace("%", "").strip())
            except (TypeError, ValueError):
                continue
        return total

    def save(self, *args, **kwargs):
        self.puntaje_total = self.calcular_puntaje_total()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"RedLat Spanish - {self.visita_examen}"


class BettyFerrelResult(ResultadoExamenBase):
    # ---------- Bienestar físico ----------
    agotamiento = models.CharField(max_length=255, blank=True, null=True, verbose_name="Agotamiento")
    cambios_alimenticios = models.CharField(max_length=255, blank=True, null=True, verbose_name="Cambios alimenticios")
    dolor = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dolor")
    cambios_sueno = models.CharField(max_length=255, blank=True, null=True, verbose_name="Cambios en el sueño")
    salud_fisica_general = models.CharField(max_length=255, blank=True, null=True, verbose_name="Salud física general")

    # ---------- bienestar psicológico ----------
    facilidad_enfrentar = models.CharField(max_length=255, blank=True, null=True, verbose_name="Facilidad para enfrentar")
    felicidad = models.CharField(max_length=255, blank=True, null=True, verbose_name="Felicidad")
    control_vida = models.CharField(max_length=255, blank=True, null=True, verbose_name="Control de la vida")
    satisfaccion_vida = models.CharField(max_length=255, blank=True, null=True, verbose_name="Satisfacción con la vida")
    concentracion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Concentración")
    utilidad_personal = models.CharField(max_length=255, blank=True, null=True, verbose_name="Utilidad personal")
    angustia_diagnostico = models.CharField(max_length=255, blank=True, null=True, verbose_name="Angustia por diagnóstico")
    angustia_tratamiento = models.CharField(max_length=255, blank=True, null=True, verbose_name="Angustia por tratamiento")
    ansiedad = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ansiedad")
    depresion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Depresión")
    miedo_otra_enfermedad = models.CharField(max_length=255, blank=True, null=True, verbose_name="Miedo a otra enfermedad")
    miedo_retroceso = models.CharField(max_length=255, blank=True, null=True, verbose_name="Miedo al retroceso")
    miedo_avance = models.CharField(max_length=255, blank=True, null=True, verbose_name="Miedo al avance")
    estado_psicologico = models.CharField(max_length=255, blank=True, null=True, verbose_name="Estado psicológico")

    # ---------- Bienestar social ----------
    angustia_familiar = models.CharField(max_length=255, blank=True, null=True, verbose_name="Angustia familiar")
    nivel_ayuda = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nivel de ayuda")
    relaciones_personales = models.CharField(max_length=255, blank=True, null=True, verbose_name="Relaciones personales")
    vida_sexual = models.CharField(max_length=255, blank=True, null=True, verbose_name="Vida sexual")
    trabajo = models.CharField(max_length=255, blank=True, null=True, verbose_name="Trabajo")
    actividades_hogar = models.CharField(max_length=255, blank=True, null=True, verbose_name="Actividades del hogar")
    aislamiento = models.CharField(max_length=255, blank=True, null=True, verbose_name="Aislamiento")
    carga_economica = models.CharField(max_length=255, blank=True, null=True, verbose_name="Carga económica")
    estado_social = models.CharField(max_length=255, blank=True, null=True, verbose_name="Estado social")

    # ---------- Bienestar espiritual ----------
    actividades_religiosas = models.CharField(max_length=255, blank=True, null=True, verbose_name="Actividades religiosas")
    actividades_espirituales_personales = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Actividades espirituales personales"
    )
    incertidumbre_futuro = models.CharField(max_length=255, blank=True, null=True, verbose_name="Incertidumbre sobre el futuro")
    cambios_positivos = models.CharField(max_length=255, blank=True, null=True, verbose_name="Cambios positivos")
    proposito_vida = models.CharField(max_length=255, blank=True, null=True, verbose_name="Propósito de vida")
    esperanza = models.CharField(max_length=255, blank=True, null=True, verbose_name="Esperanza")
    estado_espiritual = models.CharField(max_length=255, blank=True, null=True, verbose_name="Estado espiritual")

    puntaje_total = models.IntegerField(default=0, verbose_name="Puntaje total")
    # D-18: subescalas (promedios 1–4) e interpretación por terciles
    promedio_fisico = models.FloatField(blank=True, null=True, verbose_name="Promedio bienestar físico")
    promedio_psicologico = models.FloatField(blank=True, null=True, verbose_name="Promedio bienestar psicológico")
    promedio_social = models.FloatField(blank=True, null=True, verbose_name="Promedio bienestar social")
    promedio_espiritual = models.FloatField(blank=True, null=True, verbose_name="Promedio bienestar espiritual")
    promedio_global = models.FloatField(blank=True, null=True, verbose_name="Promedio global")
    interpretacion = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Interpretación"
    )

    def __str__(self):
        return f"Betty Ferrel - {self.visita_examen}"


class PuntajeCDRResult(ResultadoExamenBase):
    cdr_memoria = models.CharField(max_length=10, verbose_name="CDR Memoria")
    cdr_orientacion = models.CharField(max_length=10, verbose_name="CDR Orientación")
    cdr_juicio = models.CharField(max_length=10, verbose_name="CDR Juicio")
    cdr_comunitarias = models.CharField(max_length=10, verbose_name="CDR Actividades comunitarias")
    cdr_pasatiempos = models.CharField(max_length=10, verbose_name="CDR Pasatiempos")
    cdr_cuidado = models.CharField(max_length=10, verbose_name="CDR Cuidado personal")
    cdr_global = models.CharField(max_length=10, verbose_name="CDR Global")
    cdr_interpretacion = models.TextField(blank=True, verbose_name="Interpretación CDR")
    # B-10: suma de cajas (suma de dominios; distinta del CDR global algorítmico)
    suma_cajas = models.FloatField(
        blank=True,
        null=True,
        default=0,
        verbose_name="Suma de los 6 dominios (cajas)",
    )

    _CDR_DOMINIOS = (
        "cdr_memoria",
        "cdr_orientacion",
        "cdr_juicio",
        "cdr_comunitarias",
        "cdr_pasatiempos",
        "cdr_cuidado",
    )

    def calcular_suma_cajas(self):
        total = 0.0
        for name in self._CDR_DOMINIOS:
            raw = getattr(self, name, None)
            if raw in (None, ""):
                continue
            try:
                total += float(raw)
            except (TypeError, ValueError):
                continue
        return total

    def save(self, *args, **kwargs):
        self.suma_cajas = self.calcular_suma_cajas()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"CDR - {self.visita_examen_id}"


class ConsentimientoInformadoParticipanteResult(ResultadoExamenBase):
    fecha = models.DateField(verbose_name="Fecha")
    hora_inicio = models.TimeField(verbose_name="Hora de inicio")
    investigador = models.CharField(max_length=255, verbose_name="Investigador")
    version_consentimiento = models.TextField(
    null=True,
    blank=True,
    verbose_name="Versión del consentimiento"
)
    descripcion_proceso = models.TextField(blank=True, null=True, verbose_name="Descripción del proceso")
    preguntas = models.TextField(blank=True, null=True, verbose_name="Preguntas")
    acepta = models.CharField(max_length=10, verbose_name="Acepta")  # "Si" o "No"
    hora_firma = models.TimeField(verbose_name="Hora de firma")
    fecha_firma = models.DateField(verbose_name="Fecha de firma")
    testigo1 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Testigo 1")
    testigo2 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Testigo 2")
    copia_entregada = models.CharField(max_length=10, verbose_name="Copia entregada")  # "Si" o "No"
    hora_finalizacion = models.TimeField(verbose_name="Hora de finalización")
    firma_participante = models.TextField(blank=True, null=True, verbose_name="Firma del participante")  # Guardar como Base64

    def __str__(self):
        return f"Consentimiento Informado - {self.visita_examen_id}"


class ConsentimientoInformadoCuidadorResult(ResultadoExamenBase):
    fecha = models.DateField(verbose_name="Fecha")
    hora_inicio = models.TimeField(verbose_name="Hora de inicio")
    investigador = models.CharField(max_length=255, verbose_name="Investigador")
    nombre_acompanante = models.CharField(max_length=255, verbose_name="Nombre del acompañante")
    nombre_participante = models.CharField(max_length=255, verbose_name="Nombre del participante")
    version_consentimiento = models.TextField(
    null=True,
    blank=True,
    verbose_name="Versión del consentimiento"
)
    descripcion_proceso = models.TextField(blank=True, null=True, verbose_name="Descripción del proceso")
    preguntas = models.TextField(blank=True, null=True, verbose_name="Preguntas")
    acepta = models.CharField(max_length=10, verbose_name="Acepta")  # "Si" o "No"
    hora_firma = models.TimeField(verbose_name="Hora de firma")
    fecha_firma = models.DateField(verbose_name="Fecha de firma")
    testigo1 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Testigo 1")
    testigo2 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Testigo 2")
    copia_entregada = models.CharField(max_length=10, verbose_name="Copia entregada")  # "Si" o "No"
    hora_finalizacion = models.TimeField(verbose_name="Hora de finalización")
    firma_cuidador = models.TextField(blank=True, null=True, verbose_name="Firma del cuidador")  # Guardar como Base64

    def __str__(self):
        return f"Consentimiento Informado - {self.visita_examen_id}"


class AnamnesisCuidadorResult(ResultadoExamenBase):
    nombres_apellidos = models.CharField(max_length=255, verbose_name="Nombres y apellidos")
    documento = models.CharField(max_length=100, verbose_name="Documento")  # Tipo y número
    lugar_nacimiento = models.CharField(max_length=255, verbose_name="Lugar de nacimiento")
    lugar_procedencia = models.CharField(max_length=255, verbose_name="Lugar de procedencia")
    edad = models.IntegerField(verbose_name="Edad")
    sexo = models.CharField(max_length=20, verbose_name="Sexo")
    estado_civil = models.CharField(max_length=50, verbose_name="Estado civil")
    relacion = models.CharField(max_length=100, verbose_name="Relación")
    tiempo_acompanando = models.CharField(max_length=100, verbose_name="Tiempo acompañando")
    ocupacion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ocupación")
    escolaridad = models.CharField(max_length=100, blank=True, null=True, verbose_name="Escolaridad")
    ingresos_hogar = models.CharField(max_length=50, verbose_name="Ingresos del hogar")
    estrato = models.CharField(max_length=20, verbose_name="Estrato")
    religion = models.CharField(max_length=100, blank=True, null=True, verbose_name="Religión")
    lateralidad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Lateralidad")
    convivencia = models.TextField(blank=True, null=True, verbose_name="Convivencia")
    eps = models.CharField(max_length=100, blank=True, null=True, verbose_name="EPS")

    def __str__(self):
        return f"Anamnesis Cuidador - {self.visita_examen_id}"


class AnamnesisParticipanteResult(ResultadoExamenBase):
    nombres_apellidos = models.CharField(max_length=255, verbose_name="Nombres y apellidos")
    documento = models.CharField(max_length=100, verbose_name="Documento")  # Tipo y número
    lugar_nacimiento = models.CharField(max_length=255, verbose_name="Lugar de nacimiento")
    edad = models.IntegerField(verbose_name="Edad")
    sexo = models.CharField(max_length=20, verbose_name="Sexo")
    tiempo_acompanando = models.CharField(max_length=100, verbose_name="Tiempo acompañando")
    ingresos_hogar = models.CharField(max_length=50, verbose_name="Ingresos del hogar")
    estrato = models.CharField(max_length=20, verbose_name="Estrato")
    religion = models.CharField(max_length=100, blank=True, null=True, verbose_name="Religión")
    lateralidad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Lateralidad")
    convivencia = models.TextField(blank=True, null=True, verbose_name="Convivencia")
    eps = models.CharField(max_length=100, blank=True, null=True, verbose_name="EPS")

    def __str__(self):
        return f"Anamnesis Participante - {self.visita_examen_id}"


class SeguimientoIntervencionesResult(models.Model):
    visita_examen = models.ForeignKey(
        "VisitaExamen",
        on_delete=models.CASCADE,
        related_name="seguimientointervencionesresult_resultado",
    )
    numero_sesion = models.IntegerField(verbose_name="Número de sesión")  # 1–18
    nombre_sesion = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nombre de la sesión")
    fecha = models.DateField(blank=True, null=True, verbose_name="Fecha")
    hora_inicio = models.TimeField(blank=True, null=True, verbose_name="Hora de inicio")
    hora_fin = models.TimeField(blank=True, null=True, verbose_name="Hora de fin")

    ASISTENCIA_CHOICES = [
        ("Sí", "Sí"),
        ("No", "No"),
    ]
    asistencia = models.CharField(
        max_length=2, choices=ASISTENCIA_CHOICES, blank=True, null=True, verbose_name="Asistencia"
    )

    participacion = models.IntegerField(blank=True, null=True, verbose_name="Participación (1-5)")  # escala 1–5

    ESTADO_CHOICES = [
        ("Motivado", "Motivado"),
        ("Apático", "Apático"),
        ("Fatigado", "Fatigado"),
        ("Ansioso", "Ansioso"),
        ("Otro", "Otro"),
    ]
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, blank=True, null=True, verbose_name="Estado"
    )

    tematica = models.CharField(max_length=200, blank=True, null=True, verbose_name="Temática")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")

    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Creado en")
    actualizado_en = models.DateTimeField(auto_now=True, verbose_name="Actualizado en")

    class Meta:
        unique_together = ("visita_examen", "numero_sesion")  # ✅ evita duplicados

    def __str__(self):
        return f"Sesión {self.numero_sesion} - {self.visita_examen}"
