from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from .visit import ResultadoExamenBase


# examenes generales


class AnalisisGeneralResult(ResultadoExamenBase):
    """
    Modelo para almacenar los resultados del examen general de análisis y diagnóstico
    """

    # ========================================
    # ANÁLISIS PRINCIPAL
    # ========================================
    analisis_historia = models.TextField(
        blank=True, null=True, verbose_name="Análisis de Historia Clínica"
    )

    plan_tratamiento = models.TextField(
        blank=True, null=True, verbose_name="Plan de Tratamiento"
    )

    fecha_proximo_seguimiento = models.DateField(
        blank=True,
        null=True,
        verbose_name="Próxima fecha de seguimiento",
    )

    def __str__(self):
        return f"Análisis General - {self.visita_examen_id}"


class DiagnosticoCIE10(models.Model):
    """
    Modelo para diagnósticos CIE-10 relacionados con el análisis general
    """

    analisis_result = models.ForeignKey(
        AnalisisGeneralResult,
        on_delete=models.CASCADE,
        related_name="diagnosticos_cie10",
    )

    codigo = models.CharField(
        max_length=20,
        verbose_name="Código CIE-10",
        help_text="Código CIE-10 (ej. F32.9)",
    )

    diagnostico = models.CharField(
        max_length=500, verbose_name="Descripción del Diagnóstico"
    )

    # Los checkboxes pueden tener múltiples valores seleccionados
    confirmado_nuevo = models.BooleanField(default=False, verbose_name="Confirmado nuevo")
    confirmado_antiguo = models.BooleanField(default=False, verbose_name="Confirmado antiguo")
    en_estudio = models.BooleanField(default=False, verbose_name="En estudio")

    orden = models.PositiveIntegerField(default=1, verbose_name="Orden de aparición")

    class Meta:
        verbose_name = "Diagnóstico CIE-10"
        verbose_name_plural = "Diagnósticos CIE-10"
        ordering = ["orden"]

    def __str__(self):
        return f"{self.codigo} - {self.diagnostico[:50]}"


class DiagnosticoDSMV(models.Model):
    """
    Modelo para diagnósticos DSM-V relacionados con el análisis general
    """

    analisis_result = models.ForeignKey(
        AnalisisGeneralResult,
        on_delete=models.CASCADE,
        related_name="diagnosticos_dsmv",
    )

    codigo = models.CharField(
        max_length=20,
        verbose_name="Código DSM-V",
        help_text="Código DSM-V (ej. 296.2x)",
    )

    diagnostico = models.CharField(
        max_length=500, verbose_name="Descripción del Diagnóstico"
    )

    # Estados como campos booleanos separados
    confirmado_nuevo = models.BooleanField(default=False, verbose_name="Confirmado nuevo")
    confirmado_antiguo = models.BooleanField(default=False, verbose_name="Confirmado antiguo")
    en_estudio = models.BooleanField(default=False, verbose_name="En estudio")

    orden = models.PositiveIntegerField(default=1, verbose_name="Orden de aparición")

    class Meta:
        verbose_name = "Diagnóstico DSM-V"
        verbose_name_plural = "Diagnósticos DSM-V"
        ordering = ["orden"]

    def __str__(self):
        return f"{self.codigo} - {self.diagnostico[:50]}"


class DiagnosticoICSD3(models.Model):
    """
    Modelo para diagnósticos ICSD-3 relacionados con el análisis general
    """

    analisis_result = models.ForeignKey(
        AnalisisGeneralResult,
        on_delete=models.CASCADE,
        related_name="diagnosticos_icsd3",
    )

    codigo = models.CharField(
        max_length=20,
        verbose_name="Código ICSD-3",
        help_text="Código ICSD-3 (ej. G47.00)",
    )

    diagnostico = models.CharField(
        max_length=500, verbose_name="Descripción del Diagnóstico"
    )

    # Estados como campos booleanos separados
    confirmado_nuevo = models.BooleanField(default=False)
    confirmado_antiguo = models.BooleanField(default=False)
    en_estudio = models.BooleanField(default=False)

    orden = models.PositiveIntegerField(default=1, verbose_name="Orden de aparición")

    class Meta:
        verbose_name = "Diagnóstico ICSD-3"
        verbose_name_plural = "Diagnósticos ICSD-3"
        ordering = ["orden"]

    def __str__(self):
        return f"{self.codigo} - {self.diagnostico[:50]}"


class DiagnosticoNoClasificado(models.Model):
    """
    Modelo para diagnósticos no clasificados relacionados con el análisis general
    """

    analisis_result = models.ForeignKey(
        AnalisisGeneralResult,
        on_delete=models.CASCADE,
        related_name="diagnosticos_no_clasificados",
    )

    diagnostico = models.CharField(
        max_length=500, verbose_name="Descripción del Diagnóstico No Clasificado"
    )

    # Estados como campos booleanos separados
    confirmado_nuevo = models.BooleanField(default=False)
    confirmado_antiguo = models.BooleanField(default=False)
    en_estudio = models.BooleanField(default=False)

    orden = models.PositiveIntegerField(default=1, verbose_name="Orden de aparición")

    class Meta:
        verbose_name = "Diagnóstico No Clasificado"
        verbose_name_plural = "Diagnósticos No Clasificados"
        ordering = ["orden"]

    def __str__(self):
        return f"{self.diagnostico[:50]}"


class ExamenFisicoResult(ResultadoExamenBase):
    """Modelo para el Examen Físico General"""

    # Signos Vitales
    talla = models.FloatField(
        verbose_name="Talla (cm)", help_text="Rango normal adultos: 150-190 cm"
    )
    peso = models.FloatField(
        verbose_name="Peso (kg)", help_text="Rango normal adultos: 45-100 kg"
    )
    imc = models.FloatField(
        verbose_name="Índice de Masa Corporal", null=True, blank=True
    )
    temperatura = models.FloatField(
        verbose_name="Temperatura (°C)", help_text="Normal: 36.1-37.2°C"
    )
    frecuencia_cardiaca = models.IntegerField(
        verbose_name="Frecuencia Cardíaca (lpm)", help_text="Normal adultos: 60-100 lpm"
    )
    frecuencia_respiratoria = models.IntegerField(
        verbose_name="Frecuencia Respiratoria (rpm)",
        help_text="Normal adultos: 12-20 rpm",
    )
    presion_arterial_sistolica = models.IntegerField(
        verbose_name="Presión Arterial Sistólica (mmHg)", help_text="Normal: <140 mmHg"
    )
    presion_arterial_diastolica = models.IntegerField(
        verbose_name="Presión Arterial Diastólica (mmHg)", help_text="Normal: <90 mmHg"
    )

    # Cabeza y Cuello
    perimetro_cefalico = models.FloatField(
        verbose_name="Perímetro Cefálico (cm)",
        null=True,
        blank=True,
        help_text="Para pacientes pediátricos",
    )

    cuero_cabelludo_normal = models.BooleanField(
        default=False, verbose_name="Cuero Cabelludo Normal"
    )
    cuero_cabelludo_anormal = models.BooleanField(
        default=False, verbose_name="Cuero Cabelludo Anormal"
    )
    observaciones_cuero_cabelludo = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Cuero Cabelludo"
    )

    oidos_normal = models.BooleanField(default=False, verbose_name="Oídos Normal")
    oidos_anormal = models.BooleanField(default=False, verbose_name="Oídos Anormal")
    observaciones_oidos = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Oídos"
    )

    nariz_normal = models.BooleanField(default=False, verbose_name="Nariz Normal")
    nariz_anormal = models.BooleanField(default=False, verbose_name="Nariz Anormal")
    observaciones_nariz = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Nariz"
    )

    cuello_normal = models.BooleanField(default=False, verbose_name="Cuello Normal")
    cuello_anormal = models.BooleanField(default=False, verbose_name="Cuello Anormal")
    observaciones_cuello = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Cuello"
    )

    otros_hallazgos_importantes = models.TextField(
        blank=True, null=True, verbose_name="Otros Hallazgos Importantes"
    )

    # Tórax / Respiratorio / Cardiovascular
    forma_torax = models.CharField(
        max_length=20,
        choices=[("normal", "Normal"), ("anormal", "Anormal")],
        default="normal",
        verbose_name="Forma del Tórax",
    )
    observaciones_forma_torax = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Forma del Tórax"
    )

    murmullo_vesicular = models.CharField(
        max_length=20,
        choices=[
            ("conservado", "Conservado"),
            ("ausente", "Ausente"),
            ("disminuido", "Disminuido"),
        ],
        default="conservado",
        verbose_name="Murmullo Vesicular",
    )
    observaciones_murmullo_vesicular = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Murmullo Vesicular"
    )

    ruidos_sobreagregados = models.BooleanField(
        default=False, verbose_name="Ruidos Sobreagregados"
    )
    observaciones_ruidos_sobreagregados = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Ruidos Sobreagregados"
    )

    ruidos_cardiacos = models.CharField(
        max_length=20,
        choices=[
            ("ritmicos", "Rítmicos"),
            ("arritmicos", "Arrítmicos"),
            ("soplos", "Soplos"),
        ],
        default="ritmicos",
        verbose_name="Ruidos Cardíacos",
    )
    observaciones_ruidos_cardiacos = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Ruidos Cardíacos"
    )

    # Abdomen
    peristaltismo = models.CharField(
        max_length=20,
        choices=[
            ("presente", "Presente"),
            ("ausente", "Ausente"),
        ],
        default="presente",
        verbose_name="Peristaltismo",
    )

    pared_abdominal_normal = models.BooleanField(
        default=False, verbose_name="Pared Abdominal Normal"
    )
    pared_abdominal_anormal = models.BooleanField(
        default=False, verbose_name="Pared Abdominal Anormal"
    )

    masas = models.BooleanField(default=False, verbose_name="Masas Presentes")

    megalias = models.BooleanField(default=False, verbose_name="Megalias Presentes")

    observaciones_abdomen = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Abdomen"
    )

    # Sistema Osteomuscular
    curvatura_cervical_normal = models.BooleanField(
        default=False, verbose_name="Curvatura Cervical Normal"
    )
    curvatura_cervical_anormal = models.BooleanField(
        default=False, verbose_name="Curvatura Cervical Anormal"
    )

    curvatura_toracica_normal = models.BooleanField(
        default=False, verbose_name="Curvatura Torácica Normal"
    )
    curvatura_toracica_anormal = models.BooleanField(
        default=False, verbose_name="Curvatura Torácica Anormal"
    )

    curvatura_lumbar_normal = models.BooleanField(
        default=False, verbose_name="Curvatura Lumbar Normal"
    )
    curvatura_lumbar_anormal = models.BooleanField(
        default=False, verbose_name="Curvatura Lumbar Anormal"
    )

    arcos_movimiento_superiores_normal = models.BooleanField(
        default=False, verbose_name="Arcos Movimiento Superiores Normal"
    )
    arcos_movimiento_superiores_anormal = models.BooleanField(
        default=False, verbose_name="Arcos Movimiento Superiores Anormal"
    )

    arcos_movimiento_inferiores_normal = models.BooleanField(
        default=False, verbose_name="Arcos Movimiento Inferiores Normal"
    )
    arcos_movimiento_inferiores_anormal = models.BooleanField(
        default=False, verbose_name="Arcos Movimiento Inferiores Anormal"
    )

    asimetrias_inferiores_normal = models.BooleanField(
        default=False, verbose_name="Asimetrías Inferiores Normal"
    )
    asimetrias_inferiores_anormal = models.BooleanField(
        default=False, verbose_name="Asimetrías Inferiores Anormal"
    )

    asimetrias_superiores_normal = models.BooleanField(
        default=False, verbose_name="Asimetrías Superiores Normal"
    )
    asimetrias_superiores_anormal = models.BooleanField(
        default=False, verbose_name="Asimetrías Superiores Anormal"
    )

    observaciones_osteomuscular = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Sistema Osteomuscular"
    )

    # Piel y Anexos
    maculas = models.BooleanField(default=False, verbose_name="Máculas")
    papulas = models.BooleanField(default=False, verbose_name="Pápulas")
    vesiculas = models.BooleanField(default=False, verbose_name="Vesículas")
    pustulas = models.BooleanField(default=False, verbose_name="Pústulas")
    fisuras = models.BooleanField(default=False, verbose_name="Fisuras")
    escaras = models.BooleanField(default=False, verbose_name="Escaras")
    petequias = models.BooleanField(default=False, verbose_name="Petequias")
    equimosis = models.BooleanField(default=False, verbose_name="Equímosis")
    ulceras = models.BooleanField(default=False, verbose_name="Úlceras")
    observaciones_piel_anexos = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Piel y Anexos"
    )

    def save(self, *args, **kwargs):
        """Calcular IMC automáticamente al guardar"""
        if self.talla and self.peso:
            talla_metros = self.talla / 100  # Convertir cm a metros
            self.imc = round(self.peso / (talla_metros * talla_metros), 2)
        super().save(*args, **kwargs)

    def get_interpretacion_imc(self):
        """Interpretación del IMC"""
        if not self.imc:
            return ""

        if self.imc < 18.5:
            return "Bajo peso"
        elif 18.5 <= self.imc < 24.9:
            return "Peso normal"
        elif 25 <= self.imc < 29.9:
            return "Sobrepeso"
        elif self.imc >= 30:
            return "Obesidad"
        return ""

    def get_resumen_signos_vitales(self):
        """Resumen de signos vitales para mostrar en vistas"""
        return {
            "temperatura": f"{self.temperatura}°C"
            if self.temperatura
            else "No registrada",
            "presion_arterial": f"{self.presion_arterial_sistolica}/{self.presion_arterial_diastolica} mmHg",
            "frecuencia_cardiaca": f"{self.frecuencia_cardiaca} lpm"
            if self.frecuencia_cardiaca
            else "No registrada",
            "frecuencia_respiratoria": f"{self.frecuencia_respiratoria} rpm"
            if self.frecuencia_respiratoria
            else "No registrada",
            "imc": f"{self.imc} ({self.get_interpretacion_imc()})"
            if self.imc
            else "No calculado",
        }

    def has_alteraciones(self):
        """Verificar si hay alteraciones en el examen"""
        alteraciones = []

        # Verificar alteraciones por sistema
        if (
            self.cuero_cabelludo_anormal
            or self.oidos_anormal
            or self.nariz_anormal
            or self.cuello_anormal
        ):
            alteraciones.append("Cabeza y Cuello")

        if (
            self.forma_torax == "anormal"
            or self.ruidos_sobreagregados
            or self.ruidos_cardiacos == "soplos"
        ):
            alteraciones.append("Cardiorrespiratorio")

        if self.pared_abdominal_anormal or self.masas or self.megalias:
            alteraciones.append("Abdomen")

        if any(
            [
                self.curvatura_cervical_anormal,
                self.curvatura_toracica_anormal,
                self.curvatura_lumbar_anormal,
                self.arcos_movimiento_superiores_anormal,
                self.arcos_movimiento_inferiores_anormal,
                self.asimetrias_inferiores_anormal,
                self.asimetrias_superiores_anormal,
            ]
        ):
            alteraciones.append("Osteomuscular")

        if any(
            [
                self.maculas,
                self.papulas,
                self.vesiculas,
                self.pustulas,
                self.fisuras,
                self.escaras,
                self.petequias,
                self.equimosis,
                self.ulceras,
            ]
        ):
            alteraciones.append("Piel y Anexos")

        return alteraciones

    class Meta:
        verbose_name = "Resultado Examen Físico"
        verbose_name_plural = "Resultados Exámenes Físicos"

    def __str__(self):
        alteraciones = self.has_alteraciones()
        estado = (
            f"Con alteraciones en: {', '.join(alteraciones)}"
            if alteraciones
            else "Sin alteraciones significativas"
        )
        return f"Examen Físico - {self.visita_examen.visita.paciente} - {estado}"


class AntecedentesResult(models.Model):  # CAMBIO: Ya no hereda de ResultadoExamenBase
    """Modelo principal para Antecedentes Médicos - ÚNICO POR PACIENTE"""

    # NUEVO: Relación directa con el paciente (único)
    paciente = models.OneToOneField(
        'DatosDemograficos',
        on_delete=models.CASCADE,
        related_name="antecedentes_medicos",
        verbose_name="Paciente",
        null=True,
        blank=True,
    )

    # MANTENER: Referencia a la visita actual para tracking
    ultima_visita_examen = models.ForeignKey(
        "VisitaExamen",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Última Visita de Actualización",
    )

    # Campos de control general
    tiene_antecedentes = models.BooleanField(
        default=False, verbose_name="¿Presenta algún antecedente médico?"
    )

    observaciones_generales = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Generales"
    )

    # NUEVOS: Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, verbose_name="Fecha de creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")
    creado_por = models.CharField(max_length=100, blank=True, null=True, verbose_name="Creado por")
    actualizado_por = models.CharField(max_length=100, blank=True, null=True, verbose_name="Actualizado por")

    def get_resumen_antecedentes(self):
        """Resumen de todos los antecedentes del paciente"""
        resumen = {}

        # Contar antecedentes por tipo
        resumen["patologicos"] = self.antecedentes_patologicos.filter(
            activo=True
        ).count()
        resumen["quirurgicos"] = self.antecedentes_quirurgicos.filter(
            activo=True
        ).count()
        resumen["farmacologicos"] = self.antecedentes_farmacologicos.filter(
            activo=True
        ).count()
        resumen["toxicos"] = self.antecedentes_toxicos.filter(activo=True).count()
        resumen["familiares"] = self.antecedentes_familiares.count()
        resumen["alergicos"] = self.antecedentes_alergicos.filter(activo=True).count()
        resumen["traumaticos"] = self.antecedentes_traumaticos.filter(
            activo=True
        ).count()
        resumen["gineco"] = (
            self.antecedentes_gineco.count()
            if hasattr(self, "antecedentes_gineco")
            else 0
        )

        # Nuevos antecedentes
        resumen["epidemiologicos"] = self.antecedentes_epidemiologicos.filter(
            activo_actualmente=True
        ).count()
        resumen["ets"] = self.antecedentes_ets.filter(curado=False).count()
        resumen["hospitalizaciones"] = self.antecedentes_hospitalizaciones.count()
        resumen["inmunizaciones"] = self.antecedentes_inmunizaciones.count()
        resumen["transfusionales"] = self.antecedentes_transfusionales.count()

        return resumen

    @classmethod
    def get_or_create_for_patient(cls, paciente, visita_examen=None, usuario=None):
        """
        Obtiene o crea el registro de antecedentes para un paciente específico
        """
        antecedentes, created = cls.objects.get_or_create(
            paciente=paciente,
            defaults={
                "ultima_visita_examen": visita_examen,
                "creado_por": usuario.username if usuario else None,
                "actualizado_por": usuario.username if usuario else None,
            },
        )

        # Si ya existe, actualizar la referencia de la última visita
        if not created and visita_examen:
            antecedentes.ultima_visita_examen = visita_examen
            antecedentes.actualizado_por = usuario.username if usuario else None
            antecedentes.save()

        return antecedentes, created

    class Meta:
        verbose_name = "Antecedentes Médicos del Paciente"
        verbose_name_plural = "Antecedentes Médicos de Pacientes"

    def __str__(self):
        resumen = self.get_resumen_antecedentes()
        total = sum(resumen.values())
        return f"Antecedentes - {self.paciente} - {total} registros - Últ. actualización: {self.fecha_actualizacion.strftime('%d/%m/%Y')}"


class AntecedentesVisitaLink(models.Model):
    """
    Modelo puente que conecta el examen de antecedentes con cada visita
    para mantener el tracking de cuándo se revisa/actualiza
    """

    visita_examen = models.OneToOneField(
        "VisitaExamen", on_delete=models.CASCADE, related_name="antecedentes_link"
    )

    antecedentes_result = models.ForeignKey(
        AntecedentesResult, on_delete=models.CASCADE, related_name="visitas_links"
    )

    # Estado específico para esta visita
    fue_revisado = models.BooleanField(default=False, verbose_name="Fue revisado")
    fue_actualizado = models.BooleanField(default=False, verbose_name="Fue actualizado")
    notas_visita = models.TextField(
        blank=True, null=True, verbose_name="Notas específicas de esta visita"
    )

    fecha_revision = models.DateTimeField(auto_now=True, verbose_name="Fecha de revisión")
    revisado_por = models.CharField(max_length=100, blank=True, null=True, verbose_name="Revisado por")

    class Meta:
        verbose_name = "Enlace Antecedentes-Visita"
        verbose_name_plural = "Enlaces Antecedentes-Visitas"

    def __str__(self):
        return f"Antecedentes {self.antecedentes_result.paciente} - Visita {self.visita_examen.visita.nombre}"


class AntecedentePatologico(models.Model):
    """Antecedentes Patológicos"""

    TIPOS_PATOLOGIA = [
        ("hipertension", "Hipertensión arterial"),
        ("dislipidemia", "Dislipidemia"),
        ("diabetes", "Diabetes"),
        ("cancer", "Cáncer"),
        ("enfermedad_renal", "Enfermedad Renal"),
        ("enfermedad_cardiaca", "Enfermedad Cardíaca"),
        ("enfermedad_respiratoria", "Enfermedad Respiratoria"),
        ("enfermedad_hepatica", "Enfermedad Hepática"),
        ("enfermedad_tiroidea", "Enfermedad Tiroidea"),
        ("enfermedad_cerebrovascular", "Enfermedad Cerebrovascular"),
        ("enfermedad_psiquiatrica", "Enfermedad Psiquiátrica"),
        ("cefalea", "Cefalea"),
        ("crisis_convulsivas", "Crisis Convulsivas"),
        ("enfermedades_neurodegenerativas", "Enfermedades Neurodegenerativas"),
        ("retardo_mental", "Retardo Mental"),
        ("dificultades_aprendizaje", "Dificultades del Aprendizaje"),
        ("sindrome_down", "Síndrome de Down"),
        ("trastorno_desarrollo", "Trastorno del desarrollo psicomotor"),
        ("deficit_atencion", "Déficit de atención o hiperactividad"),
        ("otros", "Otros"),
    ]

    antecedente_result = models.ForeignKey(
        AntecedentesResult,
        on_delete=models.CASCADE,
        related_name="antecedentes_patologicos",
    )
    tipo_patologia = models.CharField(
        max_length=50, choices=TIPOS_PATOLOGIA, verbose_name="Tipo de Patología"
    )
    descripcion_otros = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Descripción (si es otros)"
    )
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    ha_recibido_tratamiento = models.BooleanField(
        default=False, verbose_name="¿Ha recibido tratamiento?"
    )
    detalle_tratamiento = models.TextField(
        blank=True, null=True, verbose_name="Detalle del Tratamiento"
    )
    tiene_complicaciones = models.BooleanField(
        default=False, verbose_name="¿Tiene complicaciones?"
    )
    detalle_complicaciones = models.TextField(
        blank=True, null=True, verbose_name="Detalle de Complicaciones"
    )
    activo = models.BooleanField(default=True, verbose_name="¿Activo actualmente?")
    fecha_finalizacion = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Finalización"
    )
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Antecedente Patológico"
        verbose_name_plural = "Antecedentes Patológicos"

    def __str__(self):
        return f"{self.get_tipo_patologia_display()} - {self.fecha_inicio}"


class AntecedenteQuirurgico(models.Model):
    """Antecedentes Quirúrgicos"""

    antecedente_result = models.ForeignKey(
        AntecedentesResult,
        on_delete=models.CASCADE,
        related_name="antecedentes_quirurgicos",
    )
    descripcion = models.CharField(
        max_length=200, verbose_name="Descripción de la Cirugía"
    )
    fecha_intervencion = models.DateField(verbose_name="Fecha de Intervención")
    ha_recibido_tratamiento = models.BooleanField(
        default=False, verbose_name="¿Ha recibido tratamiento?"
    )
    detalle_tratamiento = models.TextField(
        blank=True, null=True, verbose_name="Detalle del Tratamiento"
    )
    tiene_complicaciones = models.BooleanField(
        default=False, verbose_name="¿Tiene complicaciones?"
    )
    detalle_complicaciones = models.TextField(
        blank=True, null=True, verbose_name="Detalle de Complicaciones"
    )
    activo = models.BooleanField(default=True, verbose_name="¿Activo actualmente?")
    fecha_finalizacion = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Finalización"
    )
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Antecedente Quirúrgico"
        verbose_name_plural = "Antecedentes Quirúrgicos"

    def __str__(self):
        return f"{self.descripcion} - {self.fecha_intervencion}"


class AntecedenteFarmacologico(models.Model):
    """Antecedentes Farmacológicos (estructura equivalente a `Medicamento`)"""

    PRESENTACION_CHOICES = [
        ("tableta", "Tableta"),
        ("capsula", "Cápsula"),
        ("solucion", "Solución"),
        ("ampolla", "Ampolla"),
        ("spray", "Spray"),
        ("jarabe", "Jarabe"),
        ("crema", "Crema"),
        ("pomada", "Pomada"),
        ("gel", "Gel"),
        ("ovulos", "Óvulos"),
        ("supositorio", "Supositorio"),
        ("parche", "Parche"),
        ("inhalador", "Inhalador"),
        ("gotas", "Gotas"),
        ("otros", "Otros"),
    ]

    UNIDAD_CHOICES = [
        ("microgramos", "Microgramos (μg)"),
        ("miligramos", "Miligramos (mg)"),
        ("gramos", "Gramos (g)"),
        ("mililitros", "Mililitros (ml)"),
        ("porcentaje", "Porcentaje (%)"),
        ("volumen", "Volumen"),
        ("unidades_internacionales", "Unidades Internacionales (UI)"),
        ("miliequivalentes", "Miliequivalentes (mEq)"),
        ("otros", "Otros"),
    ]

    VIA_ADMINISTRACION_CHOICES = [
        ("oral", "Oral"),
        ("topico", "Tópico"),
        ("intramuscular", "Intramuscular"),
        ("subcutaneo", "Subcutáneo"),
        ("intravenoso", "Intravenoso"),
        ("intrarectal", "Intrarectal"),
        ("vaginal", "Vaginal"),
        ("subdermico", "Subdérmico"),
        ("otico", "Ótico"),
        ("optico", "Óptico"),
        ("intranasal", "Intranasal"),
        ("inhalatorio", "Inhalatorio"),
        ("transdermico", "Transdérmico"),
        ("sublingual", "Sublingual"),
        ("otros", "Otros"),
    ]

    antecedente_result = models.ForeignKey(
        AntecedentesResult,
        on_delete=models.CASCADE,
        related_name="antecedentes_farmacologicos",
    )

    # Información del medicamento
    nombre_comercial = models.CharField(null=True, max_length=200, verbose_name="Nombre Comercial")
    nombre_generico = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Nombre Genérico (DCI)"
    )

    # Presentación y dosis
    presentacion = models.CharField(
        null=True,
        max_length=50, choices=PRESENTACION_CHOICES, verbose_name="Presentación"
    )
    concentracion = models.CharField(
        null=True,
        max_length=100, verbose_name="Concentración", help_text="Ej: 500, 25, 10/5"
    )
    unidad = models.CharField(
        max_length=50, choices=UNIDAD_CHOICES, verbose_name="Unidad de Concentración", null=True
    )

    # Administración
    via_administracion = models.CharField(
        null=True,
        max_length=50,
        choices=VIA_ADMINISTRACION_CHOICES,
        verbose_name="Vía de Administración",
    )
    cantidad = models.CharField(
        null=True,
        max_length=100,
        verbose_name="Cantidad por Toma",
        help_text="Ej: 1 tableta, 5 ml, 2 gotas",
    )
    frecuencia = models.CharField(
        max_length=100,
        null=True,
        verbose_name="Frecuencia",
        help_text="Ej: Cada 8 horas, 2 veces al día, PRN",
    )

    # Fechas
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_finalizacion = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de Finalización",
        help_text="Dejar vacío si es tratamiento continuo",
    )

    # Indicaciones
    indicacion = models.TextField(null=True,verbose_name="Indicación/Motivo del Tratamiento")

    # Control adicional
    activo = models.BooleanField(default=True, verbose_name="Medicamento Activo")
    adherencia = models.CharField(
        max_length=20,
        choices=[
            ("buena", "Buena"),
            ("regular", "Regular"),
            ("mala", "Mala"),
            ("no_evaluada", "No Evaluada"),
        ],
        default="no_evaluada",
        verbose_name="Adherencia al Tratamiento",
    )
    efectos_adversos = models.BooleanField(
        default=False, verbose_name="¿Presenta Efectos Adversos?"
    )
    descripcion_efectos_adversos = models.TextField(
        blank=True, null=True, verbose_name="Descripción de Efectos Adversos"
    )
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )

    # Campos de auditoría
    fecha_registro = models.DateTimeField(
        null=True,
        auto_now_add=True, verbose_name="Fecha de Registro"
    )
    fecha_modificacion = models.DateTimeField(
        null=True,
        auto_now=True, verbose_name="Última Modificación"
    )

    class Meta:
        verbose_name = "Antecedente Farmacológico"
        verbose_name_plural = "Antecedentes Farmacológicos"
        ordering = ["-fecha_inicio", "nombre_comercial"]

    def __str__(self):
        estado = "Activo" if self.activo else "Inactivo"
        conc = f" {self.concentracion}" if self.concentracion else ""
        return f"{self.nombre_comercial}{conc} - {estado}"


class AntecedenteToxico(models.Model):
    """Antecedentes Tóxicos"""

    TIPOS_TOXICO = [
        ("tabaquismo", "Tabaquismo"),
        ("alcohol", "Consumo de Alcohol"),
        ("sustancias_psicoactivas", "Sustancias Psicoactivas"),
        ("intoxicaciones", "Intoxicaciones"),
        ("alergias_medicamentos", "Alergias a Medicamentos"),
        ("otros", "Otros"),
    ]

    antecedente_result = models.ForeignKey(
        AntecedentesResult,
        on_delete=models.CASCADE,
        related_name="antecedentes_toxicos",
    )
    tipos_toxico = models.JSONField(
        default=list, verbose_name="Tipos de Antecedente Tóxico"
    )
    descripcion_otros = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Descripción (otros)"
    )
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    ha_recibido_tratamiento = models.BooleanField(
        default=False, verbose_name="¿Ha recibido tratamiento?"
    )
    detalle_tratamiento = models.TextField(
        blank=True, null=True, verbose_name="Detalle del Tratamiento"
    )
    tiene_complicaciones = models.BooleanField(
        default=False, verbose_name="¿Tiene complicaciones?"
    )
    detalle_complicaciones = models.TextField(
        blank=True, null=True, verbose_name="Detalle de Complicaciones"
    )
    activo = models.BooleanField(default=True, verbose_name="¿Activo actualmente?")
    fecha_finalizacion = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Finalización"
    )
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )

    def get_tipos_display(self):
        """Obtener nombres legibles de los tipos tóxicos"""
        tipos_dict = dict(self.TIPOS_TOXICO)
        return [tipos_dict.get(tipo, tipo) for tipo in self.tipos_toxico]

    class Meta:
        verbose_name = "Antecedente Tóxico"
        verbose_name_plural = "Antecedentes Tóxicos"

    def __str__(self):
        tipos = ", ".join(self.get_tipos_display())
        return f"{tipos} - {self.fecha_inicio}"


class AntecedenteFamiliar(models.Model):
    """Antecedentes Familiares"""

    antecedente_result = models.ForeignKey(
        AntecedentesResult,
        on_delete=models.CASCADE,
        related_name="antecedentes_familiares",
    )
    tipo_antecedente = models.CharField(
        max_length=200, verbose_name="Tipo de Antecedente"
    )
    parentesco = models.CharField(max_length=100, verbose_name="Parentesco")
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Antecedente Familiar"
        verbose_name_plural = "Antecedentes Familiares"

    def __str__(self):
        return f"{self.tipo_antecedente} - {self.parentesco}"


class AntecedenteAlergico(models.Model):
    """Antecedentes Alérgicos"""

    antecedente_result = models.ForeignKey(
        AntecedentesResult,
        on_delete=models.CASCADE,
        related_name="antecedentes_alergicos",
    )
    descripcion = models.CharField(
        max_length=200, verbose_name="Descripción de la Alergia"
    )
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    tratamiento_recibido = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Tratamiento Recibido"
    )
    detalle_tratamiento = models.TextField(
        blank=True, null=True, verbose_name="Detalle del Tratamiento"
    )
    complicaciones = models.TextField(
        blank=True, null=True, verbose_name="Complicaciones"
    )
    activo = models.BooleanField(default=True, verbose_name="¿Está activo?")
    fecha_finalizacion = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Finalización"
    )
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Antecedente Alérgico"
        verbose_name_plural = "Antecedentes Alérgicos"

    def __str__(self):
        return f"{self.descripcion} - {self.fecha_inicio}"


class AntecedenteTraumatico(models.Model):
    """Antecedentes Traumáticos"""

    antecedente_result = models.ForeignKey(
        AntecedentesResult,
        on_delete=models.CASCADE,
        related_name="antecedentes_traumaticos",
    )
    descripcion = models.CharField(
        max_length=200, verbose_name="Descripción del Trauma"
    )
    fecha_inicio = models.DateField(verbose_name="Fecha del Trauma")
    tratamiento_recibido = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Tratamiento Recibido"
    )
    detalle_tratamiento = models.TextField(
        blank=True, null=True, verbose_name="Detalle del Tratamiento"
    )
    complicaciones = models.TextField(
        blank=True, null=True, verbose_name="Complicaciones"
    )
    activo = models.BooleanField(default=True, verbose_name="¿Está activo?")
    fecha_finalizacion = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Finalización"
    )
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Antecedente Traumático"
        verbose_name_plural = "Antecedentes Traumáticos"

    def __str__(self):
        return f"{self.descripcion} - {self.fecha_inicio}"


class AntecedenteGinecoObstetrico(models.Model):
    """Antecedentes Gineco-Obstétricos"""

    antecedente_result = models.OneToOneField(
        AntecedentesResult, on_delete=models.CASCADE, related_name="antecedentes_gineco"
    )

    # Menarquia
    tiene_menarquia = models.BooleanField(
        default=False, verbose_name="¿Ha tenido menarquia?"
    )
    edad_menarquia = models.IntegerField(
        blank=True, null=True, verbose_name="Edad de Menarquia"
    )

    # Menopausia
    tiene_menopausia = models.BooleanField(
        default=False, verbose_name="¿Ha tenido menopausia?"
    )
    edad_menopausia = models.IntegerField(
        blank=True, null=True, verbose_name="Edad de Menopausia"
    )

    # Historia obstétrica
    gravidez = models.IntegerField(default=0, verbose_name="Gravidez (G)")
    abortos = models.IntegerField(default=0, verbose_name="Abortos (A)")
    hijos_vivos = models.IntegerField(default=0, verbose_name="Hijos Vivos (HV)")

    # Planificación familiar
    usa_metodo_planificacion = models.BooleanField(
        default=False, verbose_name="¿Usa método de planificación?"
    )
    metodo_detalle = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Método de Planificación"
    )
    dosis_planificacion = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Dosis"
    )
    adherencia_planificacion = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Adherencia"
    )
    tolerancia_planificacion = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Tolerancia"
    )
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )

    def get_formula_obstetrica(self):
        """Obtener fórmula obstétrica G-A-HV"""
        return f"G{self.gravidez}-A{self.abortos}-HV{self.hijos_vivos}"

    class Meta:
        verbose_name = "Antecedente Gineco-Obstétrico"
        verbose_name_plural = "Antecedentes Gineco-Obstétricos"

    def __str__(self):
        formula = self.get_formula_obstetrica()
        return f"Gineco-Obstétrico - {formula}"


class AntecedenteEpidemiologico(models.Model):
    """Antecedentes Epidemiológicos"""

    antecedente_result = models.ForeignKey(
        AntecedentesResult,
        on_delete=models.CASCADE,
        related_name="antecedentes_epidemiologicos",
    )
    tipo_antecedente = models.CharField(
        max_length=200, verbose_name="Tipo de Antecedente Epidemiológico"
    )
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    tratamiento_detalle = models.TextField(
        blank=True, null=True, verbose_name="Detalle del Tratamiento"
    )
    complicaciones_asociadas = models.BooleanField(
        default=False, verbose_name="¿Complicaciones asociadas?"
    )
    detallar_complicaciones = models.TextField(
        blank=True, null=True, verbose_name="Detalle de Complicaciones"
    )
    activo_actualmente = models.BooleanField(
        default=True, verbose_name="¿Activo actualmente?"
    )
    fecha_finalizacion = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Finalización"
    )
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Antecedente Epidemiológico"
        verbose_name_plural = "Antecedentes Epidemiológicos"

    def __str__(self):
        return f"{self.tipo_antecedente} - {self.fecha_inicio}"


class AntecedenteETS(models.Model):
    """Antecedentes de Enfermedades de Transmisión Sexual"""

    antecedente_result = models.ForeignKey(
        AntecedentesResult,
        on_delete=models.CASCADE,
        related_name="antecedentes_ets",
    )
    tipo_ets = models.CharField(max_length=200, verbose_name="Tipo de ETS")
    fecha_diagnostico = models.DateField(verbose_name="Fecha de Diagnóstico")
    tratamiento_recibido = models.BooleanField(
        default=False, verbose_name="¿Ha recibido tratamiento?"
    )
    detalle_tratamiento = models.TextField(
        blank=True, null=True, verbose_name="Detalle del Tratamiento"
    )
    complicaciones = models.BooleanField(
        default=False, verbose_name="¿Tuvo complicaciones?"
    )
    detalle_complicaciones = models.TextField(
        blank=True, null=True, verbose_name="Detalle de Complicaciones"
    )
    curado = models.BooleanField(default=False, verbose_name="¿Está curado?")
    fecha_curacion = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Curación"
    )
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Antecedente ETS"
        verbose_name_plural = "Antecedentes ETS"

    def __str__(self):
        return f"{self.tipo_ets} - {self.fecha_diagnostico}"


class AntecedenteHospitalizacion(models.Model):
    """Antecedentes de Hospitalizaciones"""

    antecedente_result = models.ForeignKey(
        AntecedentesResult,
        on_delete=models.CASCADE,
        related_name="antecedentes_hospitalizaciones",
    )
    motivo_hospitalizacion = models.CharField(
        max_length=300, verbose_name="Motivo de Hospitalización"
    )
    fecha_ingreso = models.DateField(verbose_name="Fecha de Ingreso")
    fecha_egreso = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Egreso"
    )
    institucion = models.CharField(max_length=200, verbose_name="Institución/Hospital")
    dias_hospitalizacion = models.IntegerField(
        blank=True, null=True, verbose_name="Días de Hospitalización"
    )
    complicaciones_durante = models.BooleanField(
        default=False, verbose_name="¿Complicaciones durante la hospitalización?"
    )
    detalle_complicaciones = models.TextField(
        blank=True, null=True, verbose_name="Detalle de Complicaciones"
    )
    secuelas = models.BooleanField(default=False, verbose_name="¿Quedaron secuelas?")
    detalle_secuelas = models.TextField(
        blank=True, null=True, verbose_name="Detalle de Secuelas"
    )
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Antecedente de Hospitalización"
        verbose_name_plural = "Antecedentes de Hospitalizaciones"

    def __str__(self):
        return f"{self.motivo_hospitalizacion} - {self.fecha_ingreso}"


class AntecedenteInmunizacion(models.Model):
    """Antecedentes de Inmunizaciones/Vacunas"""

    TIPO_VACUNA_CHOICES = [
        ("covid19", "COVID-19"),
        ("influenza", "Influenza"),
        ("hepatitis_b", "Hepatitis B"),
        ("tetanos", "Tétanos"),
        ("fiebre_amarilla", "Fiebre Amarilla"),
        ("neumococo", "Neumococo"),
        ("otras", "Otras"),
    ]

    antecedente_result = models.ForeignKey(
        AntecedentesResult,
        on_delete=models.CASCADE,
        related_name="antecedentes_inmunizaciones",
    )
    tipo_vacuna = models.CharField(
        max_length=50, choices=TIPO_VACUNA_CHOICES, verbose_name="Tipo de Vacuna"
    )
    nombre_vacuna = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Nombre Específico de la Vacuna",
    )
    fecha_aplicacion = models.DateField(verbose_name="Fecha de Aplicación")
    dosis_numero = models.IntegerField(default=1, verbose_name="Número de Dosis")
    lugar_aplicacion = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Lugar de Aplicación"
    )
    reacciones_adversas = models.BooleanField(
        default=False, verbose_name="¿Tuvo reacciones adversas?"
    )
    detalle_reacciones = models.TextField(
        blank=True, null=True, verbose_name="Detalle de Reacciones Adversas"
    )
    refuerzo_programado = models.BooleanField(
        default=False, verbose_name="¿Necesita refuerzo?"
    )
    fecha_proximo_refuerzo = models.DateField(
        blank=True, null=True, verbose_name="Fecha Próximo Refuerzo"
    )
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Antecedente de Inmunización"
        verbose_name_plural = "Antecedentes de Inmunizaciones"

    def __str__(self):
        return f"{self.get_tipo_vacuna_display()} - Dosis {self.dosis_numero} - {self.fecha_aplicacion}"


class AntecedenteTransfusional(models.Model):
    """Antecedentes Transfusionales"""

    TIPO_COMPONENTE_CHOICES = [
        ("sangre_total", "Sangre Total"),
        ("globulos_rojos", "Glóbulos Rojos"),
        ("plaquetas", "Plaquetas"),
        ("plasma", "Plasma"),
        ("albumina", "Albúmina"),
        ("crioprecipitados", "Crioprecipitados"),
        ("otros", "Otros"),
    ]

    antecedente_result = models.ForeignKey(
        AntecedentesResult,
        on_delete=models.CASCADE,
        related_name="antecedentes_transfusionales",
    )
    tipo_componente = models.CharField(
        max_length=50,
        choices=TIPO_COMPONENTE_CHOICES,
        verbose_name="Tipo de Componente Transfundido",
    )
    fecha_transfusion = models.DateField(verbose_name="Fecha de Transfusión")
    motivo_transfusion = models.CharField(
        max_length=300, verbose_name="Motivo de la Transfusión"
    )
    cantidad_unidades = models.IntegerField(
        default=1, verbose_name="Cantidad de Unidades"
    )
    institucion = models.CharField(
        max_length=200, verbose_name="Institución donde se realizó"
    )
    tuvo_reacciones = models.BooleanField(
        default=False, verbose_name="¿Tuvo reacciones adversas?"
    )
    detalle_reacciones = models.TextField(
        blank=True, null=True, verbose_name="Detalle de Reacciones"
    )
    grupo_sanguineo_confirmado = models.CharField(
        max_length=10, blank=True, null=True, verbose_name="Grupo Sanguíneo Confirmado"
    )
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Antecedente Transfusional"
        verbose_name_plural = "Antecedentes Transfusionales"

    def __str__(self):
        return f"{self.get_tipo_componente_display()} - {self.fecha_transfusion}"


class ExamenNeurologicoResult(ResultadoExamenBase):
    """Modelo para el Examen Neurológico"""

    # A-06: mapa (campo_inicial -> título de subsección) usado para agrupar
    # los campos por subsección en la vista "Ver" y en la impresión PDF.
    # Cada campo abre una nueva subsección que agrupa todos los campos
    # declarados a continuación hasta el siguiente marcador.
    PRINT_SECCIONES_INICIOS = [
        ("clavos_izquierdo", "I Par Craneal — Olfatorio"),
        ("amaurosis", "II Par Craneal — Óptico"),
        ("diplopia", "III, IV y VI Par Craneal — Oculomotores"),
        ("tacto_frente_globo", "V Par Craneal — Trigémino"),
        ("mimica_frente", "VII Par Craneal — Facial"),
        ("hipoacusia", "VIII Par Craneal — Auditivo"),
        ("disfonia", "IX y X Par Craneal — Glosofaríngeo y Vago"),
        ("movimientos_cuello", "XI Par Craneal — Espinal accesorio"),
        ("fasciculaciones_linguales", "XII Par Craneal — Hipogloso"),
        ("dolor_cuello", "Sensibilidad"),
        ("maseteriano_izquierdo", "Reflejos"),
        ("brazo_abduccion_izq", "Fuerza muscular"),
        ("coordinacion_dedo_nariz", "Coordinación"),
        ("postura", "Marcha"),
        ("convulsiones", "Movimientos anormales"),
    ]

    # ===== I PAR CRANEAL (OLFATORIO) =====
    # Clavos
    clavos_izquierdo = models.BooleanField(
        default=False, verbose_name="Clavos - Fosa nasal izquierda"
    )
    clavos_derecho = models.BooleanField(
        default=False, verbose_name="Clavos - Fosa nasal derecha"
    )

    # Pimienta
    pimienta_izquierdo = models.BooleanField(
        default=False, verbose_name="Pimienta - Fosa nasal izquierda"
    )
    pimienta_derecho = models.BooleanField(
        default=False, verbose_name="Pimienta - Fosa nasal derecha"
    )

    # Café
    cafe_izquierdo = models.BooleanField(
        default=False, verbose_name="Café - Fosa nasal izquierda"
    )
    cafe_derecho = models.BooleanField(
        default=False, verbose_name="Café - Fosa nasal derecha"
    )

    # Canela
    canela_izquierdo = models.BooleanField(
        default=False, verbose_name="Canela - Fosa nasal izquierda"
    )
    canela_derecho = models.BooleanField(
        default=False, verbose_name="Canela - Fosa nasal derecha"
    )

    # Alcohol
    alcohol_izquierdo = models.BooleanField(
        default=False, verbose_name="Alcohol - Fosa nasal izquierda"
    )
    alcohol_derecho = models.BooleanField(
        default=False, verbose_name="Alcohol - Fosa nasal derecha"
    )

    # ===== II PAR CRANEAL (ÓPTICO) =====
    NORMAL_ANORMAL_CHOICES = [
        ("normal", "Normal"),
        ("anormal", "Anormal"),
    ]

    # Síntomas visuales
    amaurosis = models.BooleanField(default=False, verbose_name="Amaurosis presente")
    oscurecimientos = models.BooleanField(
        default=False, verbose_name="Oscurecimientos presentes"
    )
    fotopsias = models.BooleanField(default=False, verbose_name="Fotopsias presentes")
    escotomas = models.BooleanField(default=False, verbose_name="Escotomas presentes")
    agudeza_visual = models.BooleanField(
        default=False, verbose_name="Agudeza Visual Alterada"
    )

    # Fundoscopia
    hemorragias = models.BooleanField(
        default=False, verbose_name="Hemorragias presentes"
    )
    exudados = models.BooleanField(default=False, verbose_name="Exudados presentes")
    fundoscopia = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Fundoscopia",
    )

    # Evaluación detallada
    color_disco = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Color del Disco",
    )
    bordes = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Bordes",
    )

    # Pupilas y reflejos
    pupilas = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Pupilas",
    )
    reflejo_fotomotor = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo Fotomotor",
    )
    vision_colores = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Visión de Colores",
    )

    CAMPIMETRIA_CHOICES = [
        ("", "No evaluada"),
        ("CV1", "CV1"),
        ("CV2", "CV2"),
        ("CV3", "CV3"),
        ("CV4", "CV4"),
        ("CV5", "CV5"),
        ("CV6", "CV6"),
        ("CV7", "CV7"),
        ("CV8", "CV8"),
        ("CV9", "CV9"),
    ]

    campimetria = models.CharField(
        max_length=10,
        choices=CAMPIMETRIA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Campimetría",
    )

    observaciones_ii_par = models.TextField(
        blank=True, null=True, verbose_name="Observaciones II Par"
    )

    # ===== III, IV y VI PAR CRANEAL (OCULOMOTORES) =====
    # Síntomas
    diplopia = models.BooleanField(default=False, verbose_name="Diplopía presente")
    ptosis_palpebral = models.BooleanField(
        default=False, verbose_name="Ptosis palpebral presente"
    )
    desviaciones_oculares = models.BooleanField(
        default=False, verbose_name="Desviaciones oculares presentes"
    )

    # Funciones motoras
    elevacion_parpado = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Elevación párpado superior",
    )
    movimientos_oculares = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Movimientos Oculares",
    )

    # Coordinación
    mirada_conjugada = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Mirada conjugada",
    )
    movimientos_seguimiento = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Movimientos seguimiento",
    )

    observaciones_oculomotores = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Pares Oculomotores"
    )

    # ===== V PAR CRANEAL (TRIGÉMINO) =====
    # Tacto superficial
    tacto_frente_globo = models.BooleanField(
        default=False, verbose_name="Tacto superficial - Frente/globo ocular alterado"
    )
    tacto_parpado_labio_sup = models.BooleanField(
        default=False,
        verbose_name="Tacto superficial - Párpado inferior/labio superior alterado",
    )
    tacto_labio_inf_menton = models.BooleanField(
        default=False, verbose_name="Tacto superficial - Labio inferior/mentón alterado"
    )

    # Dolor
    dolor_frente_globo = models.BooleanField(
        default=False, verbose_name="Dolor - Frente/globo ocular alterado"
    )
    dolor_parpado_labio_sup = models.BooleanField(
        default=False, verbose_name="Dolor - Párpado inferior/labio superior alterado"
    )
    dolor_labio_inf_menton = models.BooleanField(
        default=False, verbose_name="Dolor - Labio inferior/mentón alterado"
    )

    # Temperatura
    temp_frente_globo = models.BooleanField(
        default=False, verbose_name="Temperatura - Frente/globo ocular alterado"
    )
    temp_parpado_labio_sup = models.BooleanField(
        default=False,
        verbose_name="Temperatura - Párpado inferior/labio superior alterado",
    )
    temp_labio_inf_menton = models.BooleanField(
        default=False, verbose_name="Temperatura - Labio inferior/mentón alterado"
    )

    # Fuerza muscular
    fuerza_maseteros = models.BooleanField(
        default=False, verbose_name="Fuerza muscular - Maseteros alterada"
    )
    fuerza_temporales = models.BooleanField(
        default=False, verbose_name="Fuerza muscular - Temporales alterada"
    )
    fuerza_pterigoideos = models.BooleanField(
        default=False, verbose_name="Fuerza muscular - Pterigoideos alterada"
    )

    # Trofismo
    trofismo_maseteros = models.BooleanField(
        default=False, verbose_name="Trofismo - Maseteros alterado"
    )
    trofismo_temporales = models.BooleanField(
        default=False, verbose_name="Trofismo - Temporales alterado"
    )
    trofismo_pterigoideos = models.BooleanField(
        default=False, verbose_name="Trofismo - Pterigoideos alterado"
    )

    observaciones_v_par = models.TextField(
        blank=True, null=True, verbose_name="Observaciones V Par"
    )

    # ===== VII PAR CRANEAL (FACIAL) =====
    # Mímica facial
    mimica_frente = models.BooleanField(
        default=False, verbose_name="Mímica facial - Frente alterada"
    )
    mimica_parpados = models.BooleanField(
        default=False, verbose_name="Mímica facial - Párpados alterada"
    )
    mimica_elevacion_nasal = models.BooleanField(
        default=False, verbose_name="Mímica facial - Elevación nasal alterada"
    )
    mimica_buccinadores = models.BooleanField(
        default=False, verbose_name="Mímica facial - Buccinadores alterada"
    )
    mimica_orbicular_labios = models.BooleanField(
        default=False, verbose_name="Mímica facial - Orbicular labios alterada"
    )

    # Gusto
    gusto_anterior = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Gusto tercio anterior de la lengua",
    )

    # ===== VIII PAR CRANEAL (AUDITIVO) =====
    # Síntomas auditivos
    hipoacusia = models.BooleanField(default=False, verbose_name="Hipoacusia presente")
    tinitus = models.BooleanField(default=False, verbose_name="Tínitus presente")
    acufenos = models.BooleanField(default=False, verbose_name="Acúfenos presentes")

    # Pruebas auditivas
    weber = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Prueba de Weber",
    )
    rinne = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Prueba de Rinne",
    )

    # Síntomas vestibulares
    vertigo = models.BooleanField(default=False, verbose_name="Vértigo presente")
    mareo = models.BooleanField(default=False, verbose_name="Mareo presente")
    nistagmus = models.BooleanField(default=False, verbose_name="Nistagmus presente")

    observaciones_viii_par = models.TextField(
        blank=True, null=True, verbose_name="Observaciones VIII Par"
    )

    # ===== IX y X PAR CRANEAL (GLOSOFARÍNGEO Y VAGO) =====
    # Síntomas vocales
    disfonia = models.BooleanField(default=False, verbose_name="Disfonía presente")
    afonia = models.BooleanField(default=False, verbose_name="Afonía presente")
    voz_nasal = models.BooleanField(default=False, verbose_name="Voz nasal presente")

    # Síntomas deglutorios
    disfagia = models.BooleanField(default=False, verbose_name="Disfagia presente")
    sialorrea = models.BooleanField(default=False, verbose_name="Sialorrea presente")
    dolor_faringe = models.BooleanField(
        default=False, verbose_name="Dolor en faringe presente"
    )

    # Exploración física
    reflejo_nauseoso = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo nauseoso",
    )
    uvula = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Posición de la úvula",
    )
    paladar = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Paladar",
    )
    gusto_posterior = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Gusto tercio posterior lengua",
    )

    # ===== XI PAR CRANEAL (ESPINAL ACCESORIO) =====
    movimientos_cuello = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Movimientos del cuello",
    )
    elevacion_hombros = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Elevación de hombros",
    )
    atrofia_lingual = models.BooleanField(
        default=False, verbose_name="Atrofia lingual presente"
    )

    observaciones_xi_par = models.TextField(
        blank=True, null=True, verbose_name="Observaciones XI Par"
    )

    # ===== XII PAR CRANEAL (HIPOGLOSO) =====
    fasciculaciones_linguales = models.BooleanField(
        default=False, verbose_name="Fasciculaciones linguales presentes"
    )
    movimientos_lengua = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Movimientos de la lengua",
    )

    observaciones_xii_par = models.TextField(
        blank=True, null=True, verbose_name="Observaciones XII Par"
    )

    # ===== SENSIBILIDAD =====
    # Dolor al pinchazo
    dolor_cuello = models.BooleanField(
        default=False, verbose_name="Dolor al pinchazo - Cuello alterado"
    )
    dolor_torax = models.BooleanField(
        default=False, verbose_name="Dolor al pinchazo - Tórax alterado"
    )
    dolor_miembros_superiores = models.BooleanField(
        default=False, verbose_name="Dolor al pinchazo - Miembros superiores alterado"
    )
    dolor_abdomen = models.BooleanField(
        default=False, verbose_name="Dolor al pinchazo - Abdomen alterado"
    )
    dolor_miembros_inferiores = models.BooleanField(
        default=False, verbose_name="Dolor al pinchazo - Miembros inferiores alterado"
    )

    # Táctil superficial
    tactil_cuello = models.BooleanField(
        default=False, verbose_name="Táctil superficial - Cuello alterado"
    )
    tactil_torax = models.BooleanField(
        default=False, verbose_name="Táctil superficial - Tórax alterado"
    )
    tactil_miembros_superiores = models.BooleanField(
        default=False, verbose_name="Táctil superficial - Miembros superiores alterado"
    )
    tactil_abdomen = models.BooleanField(
        default=False, verbose_name="Táctil superficial - Abdomen alterado"
    )
    tactil_miembros_inferiores = models.BooleanField(
        default=False, verbose_name="Táctil superficial - Miembros inferiores alterado"
    )

    # Discriminación térmica
    termica_cuello = models.BooleanField(
        default=False, verbose_name="Sensibilidad térmica - Cuello alterada"
    )
    termica_torax = models.BooleanField(
        default=False, verbose_name="Sensibilidad térmica - Tórax alterado"
    )
    termica_miembros_superiores = models.BooleanField(
        default=False,
        verbose_name="Sensibilidad térmica - Miembros superiores alterada",
    )
    termica_abdomen = models.BooleanField(
        default=False, verbose_name="Sensibilidad térmica - Abdomen alterado"
    )
    termica_miembros_inferiores = models.BooleanField(
        default=False,
        verbose_name="Sensibilidad térmica - Miembros inferiores alterada",
    )

    # Sensibilidad especializada
    vibratoria = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Sensibilidad vibratoria",
    )
    propiocepcion_superiores = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Propiocepción miembros superiores",
    )
    propiocepcion_inferiores = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Propiocepción miembros inferiores",
    )
    reconocimiento_objetos = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reconocimiento de objetos",
    )
    discriminacion_dos_puntos = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Discriminación de dos puntos",
    )

    observaciones_sensibilidad = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Sensibilidad"
    )

    # ===== REFLEJOS =====
    REFLEJO_CHOICES = [
        ("0", "0. Sin respuesta (arreflexia)"),
        ("1", "1. Respuesta disminuida (hiporreflexia)"),
        ("2", "2. Respuesta Normal"),
        ("3", "3. Respuesta Aumentada (hiperreflexia)"),
        ("4", "4. Respuesta repetida y rítmica que cesa (clonus agotable)"),
        ("5", "5. Respuesta repetida y rítmica permanente (clonus perm.)"),
    ]

    # Reflejos osteotendinosos
    # Maseteriano
    maseteriano_izquierdo = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo maseteriano izquierdo",
    )
    maseteriano_derecho = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo maseteriano derecho",
    )

    # Miembros superiores
    tricipital_izquierdo = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo tricipital izquierdo",
    )
    tricipital_derecho = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo tricipital derecho",
    )

    bicipital_izquierdo = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo bicipital izquierdo",
    )
    bicipital_derecho = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo bicipital derecho",
    )

    estilorradial_izquierdo = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo estilorradial izquierdo",
    )
    estilorradial_derecho = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo estilorradial derecho",
    )

    cubitopronador_izquierdo = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo cubitopronador izquierdo",
    )
    cubitopronador_derecho = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo cubitopronador derecho",
    )

    # Reflejos cutáneos
    cutaneo_abdominal_izquierdo = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo cutáneo abdominal izquierdo",
    )
    cutaneo_abdominal_derecho = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo cutáneo abdominal derecho",
    )

    # Miembros inferiores
    rotuliano_izquierdo = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo rotuliano izquierdo",
    )
    rotuliano_derecho = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo rotuliano derecho",
    )

    aquiliano_izquierdo = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo aquiliano izquierdo",
    )
    aquiliano_derecho = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo aquiliano derecho",
    )

    # Reflejos patológicos
    glabela = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo glabela",
    )
    succion = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo succión",
    )
    palmomentoniano = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo palmomentoniano",
    )
    hoffman = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo Hoffman",
    )
    palmar = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo palmar",
    )
    marinesco = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo Marinesco",
    )
    prension = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo prensión",
    )

    observaciones_reflejos = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Reflejos"
    )

    # ===== FUERZA MUSCULAR =====
    FUERZA_CHOICES = [
        ("0", "0. No contracción"),
        ("1", "1. Contracción muscular perceptible sin desplazamiento"),
        ("2", "2. Movimiento activo sin vencer la gravedad (plano horizontal)"),
        ("3", "3. Movimiento activo que vence la gravedad (plano vertical)"),
        ("4", "4. Movimiento activo que vence resistencia moderada"),
        ("5", "5. Movimiento de fuerza normal"),
    ]

    # Miembro Superior - Brazo
    brazo_abduccion_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Abducción brazo izquierdo",
    )
    brazo_abduccion_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Abducción brazo derecho",
    )
    brazo_antepulsion_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Antepulsión brazo izquierdo",
    )
    brazo_antepulsion_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Antepulsión brazo derecho",
    )
    brazo_rotacion_interna_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Rotación interna brazo izquierdo",
    )
    brazo_rotacion_interna_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Rotación interna brazo derecho",
    )
    brazo_rotacion_externa_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Rotación externa brazo izquierdo",
    )
    brazo_rotacion_externa_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Rotación externa brazo derecho",
    )

    # Miembro Superior - Antebrazo
    antebrazo_flexion_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Flexión antebrazo izquierdo",
    )
    antebrazo_flexion_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Flexión antebrazo derecho",
    )
    antebrazo_extension_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Extensión antebrazo izquierdo",
    )
    antebrazo_extension_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Extensión antebrazo derecho",
    )

    # Miembro Superior - Mano
    mano_flexion_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Flexión mano izquierda",
    )
    mano_flexion_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Flexión mano derecha",
    )
    mano_extension_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Extensión mano izquierda",
    )
    mano_extension_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Extensión mano derecha",
    )
    mano_prension_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Prensión mano izquierda",
    )
    mano_prension_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Prensión mano derecha",
    )

    # Miembro Inferior - Muslo
    muslo_flexion_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Flexión muslo izquierdo",
    )
    muslo_flexion_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Flexión muslo derecho",
    )
    muslo_abduccion_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Abducción muslo izquierdo",
    )
    muslo_abduccion_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Abducción muslo derecho",
    )
    muslo_aduccion_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Aducción muslo izquierdo",
    )
    muslo_aduccion_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Aducción muslo derecho",
    )

    # Miembro Inferior - Pierna
    pierna_flexion_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Flexión pierna izquierda",
    )
    pierna_flexion_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Flexión pierna derecha",
    )
    pierna_extension_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Extensión pierna izquierda",
    )
    pierna_extension_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Extensión pierna derecha",
    )

    # Miembro Inferior - Pie
    pie_flexion_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Flexión pie izquierdo",
    )
    pie_flexion_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Flexión pie derecho",
    )
    pie_extension_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Extensión pie izquierdo",
    )
    pie_extension_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Extensión pie derecho",
    )
    pie_eversion_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Eversión pie izquierdo",
    )
    pie_eversion_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Eversión pie derecho",
    )
    pie_inversion_izq = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Inversión pie izquierdo",
    )
    pie_inversion_der = models.CharField(
        max_length=1,
        choices=FUERZA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Inversión pie derecho",
    )

    observaciones_fuerza = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Fuerza Muscular"
    )

    # ===== COORDINACIÓN =====
    coordinacion_dedo_nariz = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Coordinación dedo-nariz",
    )
    romberg = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Romberg",
    )
    talon_rodilla = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Talón-Rodilla",
    )
    pronacion_supinacion = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Pronación-supinación manos",
    )

    # ===== MARCHA =====
    # Evaluación básica
    postura = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Postura",
    )
    marcha_lineal = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Marcha lineal",
    )
    marcha_puntillas = models.CharField(
        max_length=10,
        choices=NORMAL_ANORMAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Marcha en puntillas",
    )

    # Patrones patológicos
    marcha_hemiplejica = models.BooleanField(
        default=False, verbose_name="Marcha hemipléjica presente"
    )
    marcha_parkinsoniana = models.BooleanField(
        default=False, verbose_name="Marcha parkinsoniana presente"
    )
    marcha_espastica = models.BooleanField(
        default=False, verbose_name="Marcha espástica presente"
    )
    marcha_polineuritica = models.BooleanField(
        default=False, verbose_name="Marcha polineurítica presente"
    )
    marcha_ataxica = models.BooleanField(
        default=False, verbose_name="Marcha atáxica presente"
    )
    marcha_miopatica = models.BooleanField(
        default=False, verbose_name="Marcha miopática presente"
    )
    marcha_steppage = models.BooleanField(
        default=False, verbose_name="Marcha en steppage presente"
    )

    observaciones_marcha = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Marcha"
    )

    # ===== MOVIMIENTOS ANORMALES =====
    convulsiones = models.BooleanField(
        default=False, verbose_name="Convulsiones presentes"
    )
    fasciculaciones = models.BooleanField(
        default=False, verbose_name="Fasciculaciones presentes"
    )
    mioclonias = models.BooleanField(default=False, verbose_name="Mioclonías presentes")
    temblores = models.BooleanField(default=False, verbose_name="Temblores presentes")
    corea = models.BooleanField(default=False, verbose_name="Corea presente")
    espasmos = models.BooleanField(default=False, verbose_name="Espasmos presentes")
    balismos = models.BooleanField(default=False, verbose_name="Balismos presentes")
    calambres = models.BooleanField(default=False, verbose_name="Calambres presentes")
    tics = models.BooleanField(default=False, verbose_name="Tics presentes")
    distonias = models.BooleanField(default=False, verbose_name="Distonías presentes")

    # ===== MÉTODOS AUXILIARES =====
    def get_alteraciones_pares_craneales(self):
        """Obtener lista de pares craneales con alteraciones"""
        alteraciones = []

        # I Par (Olfatorio)
        if not any(
            [
                self.clavos_izquierdo,
                self.clavos_derecho,
                self.pimienta_izquierdo,
                self.pimienta_derecho,
                self.cafe_izquierdo,
                self.cafe_derecho,
            ]
        ):
            alteraciones.append("I Par (Olfatorio): Sin respuesta olfatoria")

        # II Par (Óptico)
        if self.agudeza_visual_alterada or self.fundoscopia == "anormal":
            alteraciones.append("II Par (Óptico): Alteraciones visuales")

        # III, IV, VI Par (Oculomotores)
        if (
            self.diplopia
            or self.ptosis_palpebral
            or self.movimientos_oculares == "anormal"
        ):
            alteraciones.append(
                "III, IV, VI Par (Oculomotores): Alteraciones oculomotoras"
            )

        # V Par (Trigémino)
        if any(
            [
                self.tacto_frente,
                self.tacto_parpado,
                self.tacto_labio,
                self.fuerza_maseteros,
                self.fuerza_temporales,
                self.fuerza_pterigoideos,
            ]
        ):
            alteraciones.append("V Par (Trigémino): Alteraciones sensitivas o motoras")

        # VII Par (Facial)
        if (
            any([self.mimica_frente, self.mimica_parpados, self.mimica_nasal])
            or self.gusto_tercio_anterior == "anormal"
        ):
            alteraciones.append(
                "VII Par (Facial): Alteraciones de mímica facial o gusto"
            )

        # VIII Par (Auditivo)
        if self.weber == "anormal" or self.rinne == "anormal" or self.nistagmus:
            alteraciones.append(
                "VIII Par (Auditivo): Alteraciones auditivas o vestibulares"
            )

        # IX, X Par (Glosofaríngeo y Vago)
        if self.reflejo_nauseoso == "anormal" or self.posicion_uvula == "anormal":
            alteraciones.append(
                "IX, X Par (Glosofaríngeo y Vago): Alteraciones deglutorias"
            )

        # XI Par (Espinal Accesorio)
        if self.elevacion_hombros == "anormal":
            alteraciones.append(
                "XI Par (Espinal Accesorio): Alteración elevación hombros"
            )

        # XII Par (Hipogloso)
        if self.movimientos_lengua == "anormal":
            alteraciones.append("XII Par (Hipogloso): Alteración movimientos lengua")

        return alteraciones

    def get_alteraciones_sensibilidad(self):
        """Obtener alteraciones de sensibilidad por región"""
        alteraciones = {}

        regiones = [
            "cuello",
            "torax",
            "brazo_izquierdo",
            "brazo_derecho",
            "pierna_izquierda",
            "pierna_derecha",
        ]

        for region in regiones:
            region_alt = []
            if getattr(self, f"dolor_{region}", False):
                region_alt.append("Dolor al pinchazo")
            if getattr(self, f"tactil_{region}", False):
                region_alt.append("Táctil superficial")
            if getattr(self, f"termica_{region}", False):
                region_alt.append("Térmica")

            if region_alt:
                alteraciones[region.replace("_", " ").title()] = region_alt

        return alteraciones

    def get_reflejos_alterados(self):
        """Obtener reflejos alterados (no normales)"""
        reflejos_alterados = {}

        reflejos = [
            "maseteriano",
            "bicipital",
            "tricipital",
            "estiloradial",
            "rotuliano",
            "aquiliano",
        ]
        lados = ["izquierdo", "derecho"]

        for reflejo in reflejos:
            for lado in lados:
                campo = f"{reflejo}_{lado}"
                valor = getattr(self, campo, "2")
                if valor != "2":  # No normal
                    reflejo_nombre = f"{reflejo.title()} {lado}"
                    reflejos_alterados[reflejo_nombre] = dict(self.REFLEJO_CHOICES)[
                        valor
                    ]

        return reflejos_alterados

    def get_resumen_examen(self):
        """Resumen completo del examen neurológico"""
        return {
            "pares_craneales_alterados": len(self.get_alteraciones_pares_craneales()),
            "regiones_sensibilidad_alteradas": len(
                self.get_alteraciones_sensibilidad()
            ),
            "reflejos_alterados": len(self.get_reflejos_alterados()),
            "examen_normal": (
                len(self.get_alteraciones_pares_craneales()) == 0
                and len(self.get_alteraciones_sensibilidad()) == 0
                and len(self.get_reflejos_alterados()) == 0
            ),
        }

    class Meta:
        verbose_name = "Resultado Examen Neurológico"
        verbose_name_plural = "Resultados Exámenes Neurológicos"

    def __str__(self):
        resumen = self.get_resumen_examen()
        if resumen["examen_normal"]:
            estado = "Examen neurológico normal"
        else:
            alteraciones = []
            if resumen["pares_craneales_alterados"] > 0:
                alteraciones.append(
                    f"{resumen['pares_craneales_alterados']} pares craneales"
                )
            if resumen["regiones_sensibilidad_alteradas"] > 0:
                alteraciones.append(
                    f"{resumen['regiones_sensibilidad_alteradas']} regiones sensibilidad"
                )
            if resumen["reflejos_alterados"] > 0:
                alteraciones.append(f"{resumen['reflejos_alterados']} reflejos")
            estado = f"Alteraciones: {', '.join(alteraciones)}"

        return f"Examen Neurológico - {self.visita_examen.visita.paciente} - {estado}"


class MedicamentosResult(ResultadoExamenBase):
    """Modelo principal para el examen de Medicamentos"""

    observaciones_generales = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones Generales sobre la Medicación",
    )

    def get_total_medicamentos(self):
        """Obtener número total de medicamentos"""
        return self.medicamentos.count()

    def get_medicamentos_activos(self):
        """Obtener medicamentos activos (sin fecha de finalización o fecha futura)"""
        from datetime import date

        return self.medicamentos.filter(
            models.Q(fecha_finalizacion__isnull=True)
            | models.Q(fecha_finalizacion__gte=date.today())
        )

    def get_medicamentos_por_via(self):
        """Agrupar medicamentos por vía de administración"""
        medicamentos_por_via = {}
        for medicamento in self.medicamentos.all():
            via = medicamento.via_administracion
            if via not in medicamentos_por_via:
                medicamentos_por_via[via] = []
            medicamentos_por_via[via].append(medicamento)
        return medicamentos_por_via

    def get_resumen_medicamentos(self):
        """Resumen de la medicación del paciente"""
        total = self.get_total_medicamentos()
        activos = self.get_medicamentos_activos().count()
        vias = len(set(med.via_administracion for med in self.medicamentos.all()))

        return {
            "total_medicamentos": total,
            "medicamentos_activos": activos,
            "vias_diferentes": vias,
            "hay_polifarmacia": total >= 5,  # Criterio común para polifarmacia
        }

    class Meta:
        verbose_name = "Resultado Examen de Medicamentos"
        verbose_name_plural = "Resultados Exámenes de Medicamentos"

    def __str__(self):
        resumen = self.get_resumen_medicamentos()
        estado = (
            f"{resumen['medicamentos_activos']}/{resumen['total_medicamentos']} activos"
        )
        if resumen["hay_polifarmacia"]:
            estado += " (Polifarmacia)"
        return f"Medicamentos - {self.visita_examen.visita.paciente} - {estado}"


class Medicamento(models.Model):
    """Modelo para cada medicamento individual"""

    PRESENTACION_CHOICES = [
        ("tableta", "Tableta"),
        ("capsula", "Cápsula"),
        ("solucion", "Solución"),
        ("ampolla", "Ampolla"),
        ("spray", "Spray"),
        ("jarabe", "Jarabe"),
        ("crema", "Crema"),
        ("pomada", "Pomada"),
        ("gel", "Gel"),
        ("ovulos", "Óvulos"),
        ("supositorio", "Supositorio"),
        ("parche", "Parche"),
        ("inhalador", "Inhalador"),
        ("gotas", "Gotas"),
        ("otros", "Otros"),
    ]

    UNIDAD_CHOICES = [
        ("microgramos", "Microgramos (μg)"),
        ("miligramos", "Miligramos (mg)"),
        ("gramos", "Gramos (g)"),
        ("mililitros", "Mililitros (ml)"),
        ("porcentaje", "Porcentaje (%)"),
        ("volumen", "Volumen"),
        ("unidades_internacionales", "Unidades Internacionales (UI)"),
        ("miliequivalentes", "Miliequivalentes (mEq)"),
        ("otros", "Otros"),
    ]

    VIA_ADMINISTRACION_CHOICES = [
        ("oral", "Oral"),
        ("topico", "Tópico"),
        ("intramuscular", "Intramuscular"),
        ("subcutaneo", "Subcutáneo"),
        ("intravenoso", "Intravenoso"),
        ("intrarectal", "Intrarectal"),
        ("vaginal", "Vaginal"),
        ("subdermico", "Subdérmico"),
        ("otico", "Ótico"),
        ("optico", "Óptico"),
        ("intranasal", "Intranasal"),
        ("inhalatorio", "Inhalatorio"),
        ("transdermico", "Transdérmico"),
        ("sublingual", "Sublingual"),
        ("otros", "Otros"),
    ]

    medicamentos_result = models.ForeignKey(
        MedicamentosResult, on_delete=models.CASCADE, related_name="medicamentos"
    )

    # Información del medicamento
    nombre_comercial = models.CharField(max_length=200, verbose_name="Nombre Comercial")
    nombre_generico = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Nombre Genérico (DCI)"
    )

    # Presentación y dosis
    presentacion = models.CharField(
        max_length=50, choices=PRESENTACION_CHOICES, verbose_name="Presentación"
    )
    concentracion = models.CharField(
        max_length=100, verbose_name="Concentración", help_text="Ej: 500, 25, 10/5"
    )
    unidad = models.CharField(
        max_length=50, choices=UNIDAD_CHOICES, verbose_name="Unidad de Concentración"
    )

    # Administración
    via_administracion = models.CharField(
        max_length=50,
        choices=VIA_ADMINISTRACION_CHOICES,
        verbose_name="Vía de Administración",
    )
    cantidad = models.CharField(
        max_length=100,
        verbose_name="Cantidad por Toma",
        help_text="Ej: 1 tableta, 5 ml, 2 gotas",
    )
    frecuencia = models.CharField(
        max_length=100,
        verbose_name="Frecuencia",
        help_text="Ej: Cada 8 horas, 2 veces al día, PRN",
    )

    # Fechas
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_finalizacion = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de Finalización",
        help_text="Dejar vacío si es tratamiento continuo",
    )

    # Indicaciones
    indicacion = models.TextField(verbose_name="Indicación/Motivo del Tratamiento")

    # Control adicional
    activo = models.BooleanField(default=True, verbose_name="Medicamento Activo")
    adherencia = models.CharField(
        max_length=20,
        choices=[
            ("buena", "Buena"),
            ("regular", "Regular"),
            ("mala", "Mala"),
            ("no_evaluada", "No Evaluada"),
        ],
        default="no_evaluada",
        verbose_name="Adherencia al Tratamiento",
    )
    efectos_adversos = models.BooleanField(
        default=False, verbose_name="¿Presenta Efectos Adversos?"
    )
    descripcion_efectos_adversos = models.TextField(
        blank=True, null=True, verbose_name="Descripción de Efectos Adversos"
    )
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )

    # Campos de auditoría
    fecha_registro = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de Registro"
    )
    fecha_modificacion = models.DateTimeField(
        auto_now=True, verbose_name="Última Modificación"
    )

    class Meta:
        verbose_name = "Medicamento"
        verbose_name_plural = "Medicamentos"
        ordering = ["-fecha_inicio", "nombre_comercial"]

    def __str__(self):
        estado = "Activo" if self.is_medicamento_activo() else "Inactivo"
        return f"{self.nombre_comercial} {self.get_concentracion_completa()} - {estado}"


class RevisionSistemasResult(ResultadoExamenBase):
    """Modelo para el examen de Revisión por Sistemas"""

    # Campos de control por sistema (hidden inputs del HTML)
    sintoma_general = models.CharField(
        max_length=2,
        choices=[("si", "Sí"), ("no", "No")],
        default="no",
        verbose_name="¿Presenta síntomas generales?",
    )

    sintoma_cabeza_cuello = models.CharField(
        max_length=2,
        choices=[("si", "Sí"), ("no", "No")],
        default="no",
        verbose_name="¿Presenta síntomas de cabeza y cuello?",
    )

    sintoma_cardiopulmonar = models.CharField(
        max_length=2,
        choices=[("si", "Sí"), ("no", "No")],
        default="no",
        verbose_name="¿Presenta síntomas cardiopulmonares?",
    )

    sintoma_gastrointestinal = models.CharField(
        max_length=2,
        choices=[("si", "Sí"), ("no", "No")],
        default="no",
        verbose_name="¿Presenta síntomas gastrointestinales?",
    )

    sintoma_genitourinario = models.CharField(
        max_length=2,
        choices=[("si", "Sí"), ("no", "No")],
        default="no",
        verbose_name="¿Presenta síntomas genitourinarios?",
    )

    sintoma_vascular_periferico = models.CharField(
        max_length=2,
        choices=[("si", "Sí"), ("no", "No")],
        default="no",
        verbose_name="¿Presenta síntomas vasculares periféricos?",
    )

    sintoma_osteomuscular = models.CharField(
        max_length=2,
        choices=[("si", "Sí"), ("no", "No")],
        default="no",
        verbose_name="¿Presenta síntomas osteomusculares?",
    )

    sintoma_piel_faneras = models.CharField(
        max_length=2,
        choices=[("si", "Sí"), ("no", "No")],
        default="no",
        verbose_name="¿Presenta síntomas de piel y faneras?",
    )

    sintoma_otros = models.CharField(
        max_length=2,
        choices=[("si", "Sí"), ("no", "No")],
        default="no",
        verbose_name="¿Presenta otros síntomas?",
    )

    def get_sistemas_con_sintomas(self):
        """Obtener lista de sistemas que presentan síntomas"""
        sistemas_afectados = []

        if self.sintoma_general == "si":
            sistemas_afectados.append("General")
        if self.sintoma_cabeza_cuello == "si":
            sistemas_afectados.append("Cabeza y Cuello")
        if self.sintoma_cardiopulmonar == "si":
            sistemas_afectados.append("Cardiopulmonar")
        if self.sintoma_gastrointestinal == "si":
            sistemas_afectados.append("Gastrointestinal")
        if self.sintoma_genitourinario == "si":
            sistemas_afectados.append("Genitourinario")
        if self.sintoma_vascular_periferico == "si":
            sistemas_afectados.append("Vascular Periférico")
        if self.sintoma_osteomuscular == "si":
            sistemas_afectados.append("Osteomuscular")
        if self.sintoma_piel_faneras == "si":
            sistemas_afectados.append("Piel y Faneras")
        if self.sintoma_otros == "si":
            sistemas_afectados.append("Otros")

        return sistemas_afectados

    class Meta:
        verbose_name = "Resultado Revisión por Sistemas"
        verbose_name_plural = "Resultados Revisión por Sistemas"

    def __str__(self):
        sistemas_afectados = self.get_sistemas_con_sintomas()
        if not sistemas_afectados:
            estado = "Revisión por sistemas negativa"
        else:
            estado = f"{len(sistemas_afectados)} sistemas con síntomas"

        return f"Revisión Sistemas - {self.visita_examen.visita.paciente} - {estado}"


class DetalleRevisionSistemas(models.Model):
    """Modelo para los detalles de síntomas por sistema (arrays del HTML)"""

    revision_sistemas_result = models.ForeignKey(
        RevisionSistemasResult,
        on_delete=models.CASCADE,
        related_name="detalles_sintomas",
    )

    # Campos que corresponden exactamente a los arrays del HTML
    sistema = models.CharField(
        max_length=50,
        verbose_name="Sistema",
        help_text="general, cabeza_cuello, cardiopulmonar, etc.",
    )

    sintoma = models.CharField(
        max_length=200,
        verbose_name="Síntoma",
        help_text="Corresponde a {sistema}_sintoma[]",
    )

    tiempo = models.CharField(
        max_length=100,
        verbose_name="Hace cuánto",
        help_text="Corresponde a {sistema}_tiempo[]",
    )

    caracteristicas = models.CharField(
        max_length=200,
        verbose_name="Características",
        help_text="Corresponde a {sistema}_caracteristicas[]",
    )

    class Meta:
        verbose_name = "Detalle de Síntoma"
        verbose_name_plural = "Detalles de Síntomas"
        ordering = ["sistema", "sintoma"]

    def __str__(self):
        return f"{self.sistema}: {self.sintoma}"


class CognitivoAnamnesisResult(models.Model):
    visita_examen = models.OneToOneField(
        "VisitaExamen",
        on_delete=models.CASCADE,
        related_name="cognitivo_anamnesis_resultado",
        verbose_name="Visita examen"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    # ========== ANAMNESIS ==========
    motivo_consulta = models.TextField(blank=True, null=True, verbose_name="Motivo de consulta")
    descripcion_general = models.TextField(blank=True, null=True, verbose_name="Descripción general")

    # ========== APARIENCIA/ACTITUD ==========
    apariencia_descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción de apariencia")
    apariencia_estado = models.CharField(
        max_length=50,
        choices=[("Adecuada", "Adecuada"), ("Inadecuada", "Inadecuada")],
        blank=True,
        null=True,
        verbose_name="Estado de apariencia"
    )
    actitud_descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción de actitud")

    # ========== ESTADO DE ALERTA/ORIENTACIÓN ==========
    estado_alerta_descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción del estado de alerta")
    estado_alerta_seleccion = models.CharField(
        max_length=50,
        choices=[
            ("Alerta", "Alerta"),
            ("Somnolencia", "Somnolencia"),
            ("Obnubilación", "Obnubilación"),
            ("Estupor", "Estupor"),
            ("Coma", "Coma"),
        ],
        blank=True,
        null=True,
        verbose_name="Estado de alerta"
    )

    orientacion_descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción de orientación")
    orientacion_seleccion = models.CharField(
        max_length=50,
        choices=[
            ("Desorientación temporal", "Desorientación temporal"),
            ("Desorientación espacial", "Desorientación espacial"),
            ("Desorientación en persona", "Desorientación en persona"),
        ],
        blank=True,
        null=True,
    )

    # ========== ATENCIÓN ==========
    atencion_descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción de atención")

    # ========== MEMORIA ==========
    memoria_descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción de memoria")
    memoria_lopera_vida = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)], blank=True, null=True
    )
    memoria_lopera_actual = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)], blank=True, null=True
    )
    memoria_quejas = models.CharField(
        max_length=2, choices=[("Si", "Sí"), ("No", "No")], blank=True, null=True
    )
    memoria_edad_inicio = models.IntegerField(blank=True, null=True)
    memoria_progresivas = models.CharField(
        max_length=2, choices=[("Si", "Sí"), ("No", "No")], blank=True, null=True
    )
    memoria_cambio_previo = models.CharField(
        max_length=2, choices=[("Si", "Sí"), ("No", "No")], blank=True, null=True
    )
    memoria_compromete_basicas = models.CharField(
        max_length=2, choices=[("Si", "Sí"), ("No", "No")], blank=True, null=True
    )
    memoria_compromete_complejas = models.CharField(
        max_length=2, choices=[("Si", "Sí"), ("No", "No")], blank=True, null=True
    )
    memoria_compromete_cotidiana = models.CharField(
        max_length=2, choices=[("Si", "Sí"), ("No", "No")], blank=True, null=True
    )

    # ========== LENGUAJE ==========
    lenguaje_descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción del lenguaje")
    lenguaje_cantidad = models.CharField(
        max_length=50,
        choices=[
            ("Normal", "Normal"),
            ("Logorrea", "Logorrea"),
            ("Locuacidad", "Locuacidad"),
            ("Laconismo", "Laconismo"),
            ("Concretismo", "Concretismo"),
        ],
        blank=True,
        null=True,
    )
    lenguaje_fluido = models.CharField(
        max_length=2, choices=[("Si", "Sí"), ("No", "No")], blank=True, null=True
    )
    lenguaje_tono = models.CharField(
        max_length=50,
        choices=[
            ("Normal", "Normal"),
            ("Altisonante", "Altisonante"),
            ("Musitación", "Musitación"),
            ("Aprosodia", "Aprosodia"),
        ],
        blank=True,
        null=True,
    )
    lenguaje_articulacion = models.CharField(
        max_length=50,
        choices=[("Normal", "Normal"), ("Anormal", "Anormal")],
        blank=True,
        null=True,
    )
    lenguaje_comprension = models.CharField(
        max_length=50,
        choices=[("Normal", "Normal"), ("Anormal", "Anormal")],
        blank=True,
        null=True,
    )
    lenguaje_escritura = models.CharField(
        max_length=50,
        choices=[("Normal", "Normal"), ("Anormal", "Anormal")],
        blank=True,
        null=True,
    )
    lenguaje_lectura = models.CharField(
        max_length=50,
        choices=[("Normal", "Normal"), ("Anormal", "Anormal")],
        blank=True,
        null=True,
    )
    lenguaje_repeticion = models.CharField(
        max_length=50,
        choices=[("Normal", "Normal"), ("Anormal", "Anormal")],
        blank=True,
        null=True,
    )

    # ========== PENSAMIENTO ==========
    pensamiento_descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción del pensamiento")
    pensamiento_forma = models.CharField(
        max_length=100,
        choices=[
            ("Velocidad", "Velocidad"),
            ("Coherencia", "Coherencia"),
            ("Lógica", "Lógica"),
            ("Organización", "Organización"),
            ("Fuga de ideas", "Fuga de ideas"),
            ("Ensalada de palabras", "Ensalada de palabras"),
            ("Perseverancia", "Perseverancia"),
            ("Circunstancialidad", "Circunstancialidad"),
            ("Tangencialidad", "Tangencialidad"),
            ("Soliloquio", "Soliloquio"),
        ],
        blank=True,
        null=True,
    )
    pensamiento_contenido = models.CharField(
        max_length=100,
        choices=[
            ("Ideas delirantes", "Ideas delirantes"),
            ("Ideas sobrevaloradas", "Ideas sobrevaloradas"),
            ("Ideas obsesivas", "Ideas obsesivas"),
            ("Ideas fantasiosas", "Ideas fantasiosas"),
        ],
        blank=True,
        null=True,
    )
    pensamiento_juicio = models.CharField(
        max_length=50,
        choices=[
            ("En construcción", "En construcción"),
            ("Conservado", "Conservado"),
            ("Distorsionado", "Distorsionado"),
            ("Debilitado", "Debilitado"),
            ("Nulo", "Nulo"),
        ],
        blank=True,
        null=True,
    )
    pensamiento_introspeccion = models.CharField(
        max_length=50,
        choices=[
            ("Adecuada", "Adecuada"),
            ("Aceptable", "Aceptable"),
            ("Pobre", "Pobre"),
            ("Precaria", "Precaria"),
            ("Nula", "Nula"),
        ],
        blank=True,
        null=True,
    )
    pensamiento_prospeccion = models.CharField(
        max_length=50,
        choices=[
            ("Conservada", "Conservada"),
            ("Grandiosidad", "Grandiosidad"),
            ("Delirante", "Delirante"),
            ("Desesperanzadora", "Desesperanzadora"),
            ("Nula", "Nula"),
        ],
        blank=True,
        null=True,
    )

    # ========== SENSOPERCEPCIÓN ==========
    sensopercepcion_descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción de sensopercepción")
    sensopercepcion_alteraciones = models.CharField(
        max_length=100,
        choices=[
            ("Alucinaciones", "Alucinaciones"),
            ("Pseudoalucinaciones", "Pseudoalucinaciones"),
            ("Alucinosis", "Alucinosis"),
            ("Ilusiones", "Ilusiones"),
            ("Anomalías en integración", "Anomalías en integración"),
        ],
        blank=True,
        null=True,
    )

    # ========== FUNCIÓN EJECUTIVA ==========
    funcion_ejecutiva_descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción de función ejecutiva")
    funcion_ejecutiva_comportamientos = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Comportamientos"
    )
    comportamiento_edad_inicio = models.CharField(max_length=50, blank=True, null=True, verbose_name="Edad de inicio del comportamiento")
    comportamiento_caracteristicas = models.TextField(blank=True, null=True, verbose_name="Características del comportamiento")

    funcion_ejecutiva_sintomas = models.CharField(max_length=200, blank=True, null=True, verbose_name="Síntomas")
    sintomas_edad_inicio = models.CharField(max_length=50, blank=True, null=True, verbose_name="Edad de inicio de síntomas")
    sintomas_caracteristicas = models.TextField(blank=True, null=True, verbose_name="Características de síntomas")

    # ========== ESTADO DE ÁNIMO/AFECTO ==========
    estado_animo_descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción del estado de ánimo")
    estado_animo_cualidades = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cualidades del estado de ánimo")
    estado_animo_expresiones = models.CharField(max_length=100, blank=True, null=True, verbose_name="Expresiones del estado de ánimo")

    # ========== APETITO ==========
    apetito_descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción del apetito")
    apetito_cambios = models.CharField(max_length=200, blank=True, null=True, verbose_name="Cambios en el apetito")
    apetito_edad_inicio = models.CharField(max_length=50, blank=True, null=True, verbose_name="Edad de inicio de cambios")
    apetito_caracteristicas = models.TextField(blank=True, null=True, verbose_name="Características de los cambios")

    # ========== FUNCIONALIDAD ==========
    funcionalidad_descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción de funcionalidad")
    independencia_vida_diaria = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], default="no", verbose_name="Independencia en vida diaria"
    )
    independencia_actividades_complejas = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], default="no", verbose_name="Independencia en actividades complejas"
    )

    # ========== CONDUCTA MOTORA ==========
    conducta_motora_descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción de conducta motora")
    trastornos_cuantitativos = models.CharField(
        max_length=100,
        choices=[
            ("hiperactividad", "Hiperactividad"),
            ("inquietud", "Inquietud"),
            ("agitacion", "Agitación"),
            ("retardo_psicomotor", "Retardo psicomotor"),
            ("hipoactividad", "Hipoactividad"),
        ],
        blank=True,
        null=True,
    )
    trastornos_cualitativos = models.CharField(
        max_length=100,
        choices=[
            ("catatonia", "Catatonía"),
            ("estereotipias", "Estereotipias"),
            ("manierismos", "Manierismos"),
            ("mimica_gestualidad", "Alteraciones de la mímica y gestualidad"),
            ("ambitendencia", "Ambitendencia"),
            ("perseveracion", "Perseveración"),
        ],
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Resultado Examen Cognitivo Anamnesis"
        verbose_name_plural = "Resultados Exámenes Cognitivo Anamnesis"
        ordering = ["fecha_creacion"]

    def __str__(self):
        return f"Cognitivo Anamnesis - {self.visita_examen.visita.paciente.nombres} {self.visita_examen.visita.paciente.apellidos}"


# ========== MODELOS RELACIONADOS ==========


class ActitudCognitiva(models.Model):
    anamnesis = models.ForeignKey(
        CognitivoAnamnesisResult, on_delete=models.CASCADE, related_name="actitudes"
    )
    tipo = models.CharField(
        max_length=50,
        choices=[
            ("Colaborador", "Colaborador"),
            ("Desinteresado", "Desinteresado"),
            ("Hostil", "Hostil"),
            ("Intrusivo", "Intrusivo"),
            ("Evasivo", "Evasivo"),
            ("Seductor", "Seductor"),
            ("Suspicaz", "Suspicaz"),
            ("Hiperfamiliar", "Hiperfamiliar"),
            ("Complaciente", "Complaciente"),
            ("Pueril", "Pueril"),
            ("Amable", "Amable"),
            ("Agresivo", "Agresivo"),
            ("Negativista", "Negativista"),
        ],
    )

    class Meta:
        verbose_name = "Actitud Cognitiva"
        verbose_name_plural = "Actitudes Cognitivas"
        ordering = ["tipo"]


class AtencionCognitiva(models.Model):
    anamnesis = models.ForeignKey(
        CognitivoAnamnesisResult, on_delete=models.CASCADE, related_name="atenciones"
    )
    tipo = models.CharField(
        max_length=100,
        choices=[
            ("Quejas atencionales", "Quejas atencionales"),
            ("Alteración atención sostenida", "Alteración atención sostenida"),
            ("Alteración atención dividida", "Alteración atención dividida"),
            ("Incapacidad para quedarse quieto", "Incapacidad para quedarse quieto"),
            (
                "Dificultad para finalizar una tarea",
                "Dificultad para finalizar una tarea",
            ),
            (
                "Dificultad para seguir instrucciones",
                "Dificultad para seguir instrucciones",
            ),
            (
                "Distracción con estímulos irrelevantes",
                "Distracción con estímulos irrelevantes",
            ),
        ],
    )
    edad_inicio = models.CharField(max_length=50, blank=True, null=True)
    caracteristicas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Atención Cognitiva"
        verbose_name_plural = "Atenciones Cognitivas"
        ordering = ["tipo"]


class ErrorLenguajeCognitivo(models.Model):
    anamnesis = models.ForeignKey(
        CognitivoAnamnesisResult,
        on_delete=models.CASCADE,
        related_name="errores_lenguaje",
    )
    tipo = models.CharField(
        max_length=50,
        choices=[
            ("Errores sintácticos", "Errores sintácticos"),
            ("Errores fonéticos", "Errores fonéticos"),
            ("Errores semánticos", "Errores semánticos"),
        ],
    )

    class Meta:
        verbose_name = "Error Lenguaje Cognitivo"
        verbose_name_plural = "Errores de Lenguaje Cognitivo"
        ordering = ["tipo"]


class ActividadVidaDiaria(models.Model):
    anamnesis = models.ForeignKey(
        CognitivoAnamnesisResult,
        on_delete=models.CASCADE,
        related_name="actividades_vida_diaria",
    )
    tipo = models.CharField(
        max_length=50,
        choices=[
            ("comer", "Comer"),
            ("asearse", "Asearse"),
            ("vestirse", "Vestirse"),
            ("desplazarse", "Desplazarse"),
            ("comunicarse", "Comunicarse"),
            ("control_esfinteres", "Control de esfínteres"),
        ],
    )

    class Meta:
        verbose_name = "Actividad de Vida Diaria"
        verbose_name_plural = "Actividades de Vida Diaria"
        ordering = ["tipo"]


class ActividadCompleja(models.Model):
    anamnesis = models.ForeignKey(
        CognitivoAnamnesisResult,
        on_delete=models.CASCADE,
        related_name="actividades_complejas",
    )
    tipo = models.CharField(
        max_length=50,
        choices=[
            ("telefono", "Teléfono"),
            ("compras", "Compras"),
            ("cocinar", "Cocinar"),
            ("cuidado_hogar", "Cuidado del hogar"),
            ("lavar_ropa", "Lavar ropa"),
            ("transporte", "Transporte"),
            ("medicacion", "Manejo de medicación"),
            ("asuntos_economicos", "Asuntos económicos"),
        ],
    )

    class Meta:
        verbose_name = "Actividad Compleja"
        verbose_name_plural = "Actividades Complejas"
        ordering = ["tipo"]
