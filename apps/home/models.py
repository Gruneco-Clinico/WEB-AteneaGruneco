# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.urls import reverse, NoReverseMatch


class CustomUser(AbstractUser):
    # Campos adicionales
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)

    # Sobrescribir las relaciones con related_name personalizado
    groups = models.ManyToManyField(
        Group,
        verbose_name="groups",
        blank=True,
        related_name="custom_user_set",
        related_query_name="custom_user",
    )

    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name="user permissions",
        blank=True,
        related_name="custom_user_set",
        related_query_name="custom_user",
    )

    def __str__(self):
        return self.username


class DatosDemograficos(models.Model):
    # Información Personal
    primer_nombre = models.CharField(max_length=50)
    segundo_nombre = models.CharField(max_length=50, blank=True, null=True)
    primer_apellido = models.CharField(max_length=50)
    segundo_apellido = models.CharField(max_length=50, blank=True, null=True)
    tipo_documento = models.CharField(
        max_length=50,
        choices=[
            ("CC", "Cédula de Ciudadanía"),
            ("TI", "Tarjeta de Identidad"),
            ("NUIP", "Número Único de Identificación Personal"),
            ("CE", "Cédula de Extranjería"),
            ("PS", "Pasaporte"),
        ],
        default="",
    )
    numero_documento = models.CharField(max_length=20, unique=True)
    celular = models.CharField(max_length=20, unique=True, default="")
    fecha_nacimiento = models.DateField()
    edad = models.IntegerField()
    genero = models.CharField(
        max_length=10,
        choices=[
            ("F", "Femenino"),
            ("M", "Masculino"),
            ("O", "Otro"),
        ],
        default="",
    )
    municipio_nacimiento = models.CharField(max_length=100, default="")
    departamento_nacimiento = models.CharField(max_length=100, default="")
    pais_nacimiento = models.CharField(max_length=100, default="")
    estado_civil = models.CharField(
        max_length=20,
        choices=[
            ("Soltero", "Soltero(a)"),
            ("Casado", "Casado(a)"),
            ("UnionLibre", "Unión libre"),
            ("Viudo", "Viudo(a)"),
        ],
        default="",
    )

    ESCOLARIDAD_CHOICES = [
        ("primario", "Primario"),
        ("bachiller", "Bachiller"),
        ("universidad", "Universidad"),
        ("maestria", "Maestría"),
        ("doctorado", "Doctorado"),
        ("especializacion", "Especialización"),
    ]

    # Campo escolaridad
    escolaridad = models.CharField(
        max_length=20,
        choices=ESCOLARIDAD_CHOICES,
        blank=True,
        null=True,
        verbose_name="Escolaridad",
    )

    ocupacion = models.CharField(max_length=100)
    lateralidad = models.CharField(
        max_length=20,
        choices=[
            ("Diestro", "Diestro"),
            ("Zurdo", "Zurdo"),
            ("Ambidiestro", "Ambidiestro"),
        ],
        default="",
    )
    GRUPO_SANGUINEO_CHOICES = [
        ("O+", "O+"),
        ("O-", "O-"),
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
    ]
    grupo_sanguineo = models.CharField(
        max_length=5,
        choices=GRUPO_SANGUINEO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Grupo Sanguíneo",
    )
    religion = models.CharField(max_length=100)
    eps = models.CharField(max_length=100)
    regimen = models.CharField(
        max_length=20,
        choices=[
            ("Contributivo", "Contributivo"),
            ("Subsidiado", "Subsidiado"),
            ("Vinculado", "Vinculado"),
            ("Otro", "Otro"),
        ],
        default="",
    )
    direccion = models.CharField(max_length=200, default="")
    municipio_residencia = models.CharField(max_length=100, default="")
    departamento_residencia = models.CharField(max_length=100, default="")
    pais_residencia = models.CharField(max_length=100, default="")

    correo = models.EmailField(
        unique=True, verbose_name="Correo Electrónico", default="sincorreo@example.com"
    )

    def __str__(self):
        return f"{self.primer_nombre} {self.primer_apellido}"


class Proyecto(models.Model):
    nombre = models.CharField(
        max_length=255, unique=True, verbose_name="Nombre del Proyecto"
    )
    descripcion = models.TextField(
        blank=True, null=True, verbose_name="Descripción del Proyecto"
    )
    investigador_principal = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Investigador Principal"
    )
    codigo_siu = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Código SIU"
    )
    fecha_inicio = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Inicio"
    )
    fecha_financiacion = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Financiación"
    )
    pacientes = models.ManyToManyField(
        "DatosDemograficos", related_name="proyectos", verbose_name="Pacientes"
    )

    def __str__(self):
        return self.nombre


class Examen(models.Model):
    nombre = models.CharField(max_length=255, verbose_name="Nombre del Examen")
    descripcion = models.TextField(
        verbose_name="Descripción del Examen", blank=True, null=True
    )
    campos = models.JSONField(
        verbose_name="Campos del Examen", default=list
    )  # Estructura del formulario

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Examen"
        verbose_name_plural = "Exámenes"


class TipoVisita(models.Model):
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la Visita")
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name="visitas",
        verbose_name="Proyecto",
    )
    observaciones = models.TextField(
        verbose_name="Observaciones", blank=True, null=True
    )
    examenes = models.JSONField(
        default=dict, verbose_name="Exámenes", null=True, blank=True
    )

    def __str__(self):
        return f"{self.nombre} - {self.proyecto.nombre}"


class Visita(models.Model):
    paciente = models.ForeignKey(
        DatosDemograficos,
        on_delete=models.CASCADE,
        related_name="visitas",
        null=True,
        blank=True,
    )
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la Visita")
    Tipo_visita = models.ForeignKey(
        TipoVisita,
        on_delete=models.CASCADE,
        related_name="visitas",
        null=True,
        blank=True,
    )
    fecha = models.DateField(blank=True, null=True)
    evaluador = models.CharField(max_length=50, null=True, blank=True)

    # NUEVO CAMPO: Estado de la visita
    estado_visita = models.CharField(
        max_length=20,
        choices=[
            ("abierta", "Abierta"),
            ("cerrada", "Cerrada"),
        ],
        default="abierta",
        verbose_name="Estado de la Visita",
    )

    # Campos del acompañante
    acompanante_nombre = models.CharField(
        max_length=255, verbose_name="Nombre del Acompañante", blank=True, null=True
    )
    acompanante_relacion = models.CharField(
        max_length=100, verbose_name="Relación con el Paciente", blank=True, null=True
    )
    acompanante_correo = models.EmailField(
        verbose_name="Correo del Acompañante", blank=True, null=True
    )
    acompanante_telefono = models.CharField(
        max_length=20, verbose_name="Teléfono del Acompañante", blank=True, null=True
    )

    def __str__(self):
        return f"{self.nombre} - {self.proyecto.nombre}"


class VisitaExamen(models.Model):
    visita = models.ForeignKey(
        Visita, on_delete=models.CASCADE, related_name="visita_examenes"
    )
    examen = models.ForeignKey(
        Examen, on_delete=models.CASCADE, related_name="examenes_realizados"
    )

    # Estado del examen
    estado = models.CharField(
        max_length=20,
        choices=[
            ("pendiente", "Pendiente"),
            ("en_progreso", "En Progreso"),
            ("completado", "Completado"),
            ("cancelado", "Cancelado"),
        ],
        default="pendiente",
        verbose_name="Estado del Examen",
    )

    # Fechas de seguimiento
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_completado = models.DateTimeField(null=True, blank=True)

    # Metadatos adicionales
    notas_examinador = models.TextField(
        blank=True, null=True, verbose_name="Notas del Examinador"
    )

    # Campos opcionales para seguimiento
    evaluador = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Evaluador"
    )
    tiempo_duracion = models.DurationField(
        null=True, blank=True, verbose_name="Tiempo de Duración"
    )

    class Meta:
        unique_together = ["visita", "examen"]
        verbose_name = "Examen de Visita"
        verbose_name_plural = "Exámenes de Visita"
        ordering = ["fecha_creacion"]

    def __str__(self):
        return (
            f"{self.visita.nombre} - {self.examen.nombre} ({self.get_estado_display()})"
        )

    def get_resultado_instance(self):
        """Retorna la instancia del resultado específico del examen si existe."""
        if not hasattr(self, "_resultado_cache"):
            self._resultado_cache = None
            print(
                f"DEBUG get_resultado_instance - Buscando resultado para VisitaExamen ID: {self.id}"
            )

            # Lista de related_names que Django generará automáticamente
            possible_related_names = [
                "suenofisicoresult_resultado",
                "atenasresult_resultado",
                "pittsburghresult_resultado",
                "epworthresult_resultado",
                "mewresult_resultado",
                "berlinresult_resultado",
                "suenoanamnesisresult_resultado",
                "isiresult_resultado",
                "stopbangresult_resultado",
            ]

            for related_name in possible_related_names:
                try:
                    print(f"DEBUG - Probando: {related_name}")
                    resultado = getattr(self, related_name)
                    self._resultado_cache = resultado
                    print(
                        f"DEBUG - ¡ENCONTRADO! {related_name}: {type(resultado).__name__}"
                    )
                    break
                except AttributeError:
                    print(f"DEBUG - No existe atributo: {related_name}")
                    continue
                except Exception as e:
                    print(f"DEBUG - Error en {related_name}: {str(e)}")
                    continue

            if self._resultado_cache is None:
                print(
                    f"DEBUG - NINGÚN resultado encontrado para VisitaExamen {self.id}"
                )

        return self._resultado_cache

    @property
    def esta_realizado(self):
        """Verifica si el examen está completado y tiene un resultado concreto asociado."""
        print(f"DEBUG esta_realizado - ID: {self.id}, Estado: {self.estado}")

        estado_completado = self.estado == "completado"
        print(f"DEBUG esta_realizado - Estado completado: {estado_completado}")

        resultado = self.get_resultado_instance()
        tiene_resultado = resultado is not None
        print(f"DEBUG esta_realizado - Tiene resultado: {tiene_resultado}")

        if resultado:
            print(
                f"DEBUG esta_realizado - Tipo de resultado: {type(resultado).__name__}"
            )

        final_result = estado_completado and tiene_resultado
        print(f"DEBUG esta_realizado - Resultado final: {final_result}")

        return final_result

    @property
    def puede_editarse(self):
        """Verifica si el examen puede editarse."""
        # NUEVO: Solo puede editarse si la visita está abierta Y el examen está realizado
        visita_abierta = self.visita.estado_visita == "abierta"
        examen_realizado = self.esta_realizado

        puede_editar = visita_abierta and examen_realizado
        print(
            f"DEBUG puede_editarse - ID: {self.id}, Visita abierta: {visita_abierta}, Examen realizado: {examen_realizado}, Puede editar: {puede_editar}"
        )
        return puede_editar

    def get_nombre_examen_normalizado(self):
        """Retorna el nombre del examen normalizado para URLs"""
        return self.examen.nombre.lower().replace(" ", "").replace("-", "")

    def get_url_realizar(self):
        """Retorna la URL para realizar el examen específico"""
        examen_nombre = self.get_nombre_examen_normalizado()

        url_mapping = {
            "pittsburgh": "realizar_pittsburgh",
            "epworth": "realizar_epworth",
            "mew": "realizar_mew",
            "berlin": "realizar_berlin",
            "suenoanamnesis": "realizar_sueno_anamnesis",
            "atenas": "realizar_atenas",
            "suenofisico": "realizar_sueno_fisico",
            "isi": "realizar_isi",
            "stopbang": "realizar_stopbang",
        }

        url_name = url_mapping.get(examen_nombre)
        if url_name:
            try:
                return reverse(
                    url_name,
                    args=[self.visita.id, self.examen.id, self.visita.paciente.id],
                )
            except NoReverseMatch:
                pass

        # URL temporal mientras desarrollas las vistas
        return f"/examenes/realizar/{self.visita.id}/{self.examen.id}/{self.visita.paciente.id}/"

    def get_url_ver(self):
        """Retorna la URL para ver los resultados del examen"""
        if not self.esta_realizado:
            return "#"

        examen_nombre = self.get_nombre_examen_normalizado()

        url_mapping = {
            "pittsburgh": "ver_pittsburgh",
            "epworth": "ver_epworth",
            "mew": "ver_mew",
            "berlin": "ver_berlin",
            "suenoanamnesis": "ver_sueno_anamnesis",
            "atenas": "ver_atenas",
            "suenofisico": "ver_sueno_fisico",
            "isi": "ver_isi",
            "stopbang": "ver_stopbang",
        }

        url_name = url_mapping.get(examen_nombre)
        if url_name:
            try:
                return reverse(url_name, args=[self.id])
            except NoReverseMatch:
                pass

        return f"/examenes/ver/{self.id}/"

    def get_url_editar(self):
        """Retorna la URL para editar el examen"""
        if not self.puede_editarse:
            return "#"

        examen_nombre = self.get_nombre_examen_normalizado()

        url_mapping = {
            "pittsburgh": "editar_pittsburgh",
            "epworth": "editar_epworth",
            "mew": "editar_mew",
            "berlin": "editar_berlin",
            "suenoanamnesis": "editar_sueno_anamnesis",
            "atenas": "editar_atenas",
            "suenofisico": "editar_sueno_fisico",
            "isi": "editar_isi",
            "stopbang": "editar_stopbang",
        }

        url_name = url_mapping.get(examen_nombre)
        if url_name:
            try:
                return reverse(url_name, args=[self.id])
            except NoReverseMatch:
                pass

        return f"/examenes/editar/{self.id}/"

    def get_progreso_porcentaje(self):
        """Retorna el porcentaje de progreso del examen"""
        if self.estado == "completado":
            return 100
        elif self.estado == "en_progreso":
            return 50
        elif self.estado == "cancelado":
            return 0
        else:  # pendiente
            return 0

    def get_icono_estado(self):
        """Retorna el icono FontAwesome para el estado"""
        iconos = {
            "pendiente": "fas fa-hourglass-start",
            "en_progreso": "fas fa-clock",
            "completado": "fas fa-check-circle",
            "cancelado": "fas fa-times-circle",
        }
        return iconos.get(self.estado, "fas fa-question-circle")

    def get_color_badge(self):
        """Retorna la clase CSS para el badge del estado"""
        colores = {
            "pendiente": "badge-secondary",
            "en_progreso": "badge-warning",
            "completado": "badge-success",
            "cancelado": "badge-danger",
        }
        return colores.get(self.estado, "badge-light")


# Este modelo abstracto servirá como padre para todos los resultados de exámenes.
class ResultadoExamenBase(models.Model):
    # CORRECTO: Usar %(class)s para generar related_names únicos
    visita_examen = models.OneToOneField(
        VisitaExamen,
        on_delete=models.CASCADE,
        related_name="%(class)s_resultado",  # Esto genera nombres únicos
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"Resultado para {self.visita_examen}"


################################################################################################################################################
# sueno examenes


class PittsburghResult(ResultadoExamenBase):
    hora_acostarse = models.CharField(max_length=10)
    latencia_sueno = models.IntegerField()
    hora_levantarse = models.CharField(max_length=10)
    horas_dormidas = models.FloatField()
    conciliar_sueno = models.CharField(max_length=100)
    despertarse_sueno = models.CharField(max_length=100)
    levantarse_servicio_sueno = models.CharField(max_length=100)
    respirar = models.CharField(max_length=100)
    toser_roncar_sueno = models.CharField(max_length=100)
    sentir_frio_sueno = models.CharField(max_length=100)
    calor_sueno = models.CharField(max_length=100)
    pesadillas_sueno = models.CharField(max_length=100)
    dolores_sueno = models.CharField(max_length=100)
    otras_razones = models.CharField(max_length=100, blank=True, null=True)
    otras_sueno = models.CharField(max_length=100, blank=True, null=True)
    calidad_sueno = models.CharField(max_length=100)
    medicinas_sueno = models.CharField(max_length=100)
    somnolencia_sueno = models.CharField(max_length=100)
    problemas_animos_sueno = models.CharField(max_length=100)
    duerme_acompanado = models.CharField(max_length=10)
    ronquidos_ruidosos = models.CharField(max_length=100, blank=True, null=True)
    pausas_respiracion = models.CharField(max_length=100, blank=True, null=True)
    sacudidas_piernas = models.CharField(max_length=100, blank=True, null=True)
    desorientacion_confusion = models.CharField(max_length=100, blank=True, null=True)
    otros_inconvenientes = models.CharField(max_length=100, blank=True, null=True)
    descripcion_inconvenientes = models.CharField(max_length=100, blank=True, null=True)


class EpworthResult(ResultadoExamenBase):
    sentado_leyendo = models.IntegerField()
    viendo_tv = models.IntegerField()
    sentado_teatro = models.IntegerField()
    pasajero_coche = models.IntegerField()
    tumbado_tarde = models.IntegerField()
    charlando = models.IntegerField()
    despues_comer = models.IntegerField()
    trafico = models.IntegerField()
    puntaje_total = models.IntegerField()


class MEWResult(ResultadoExamenBase):
    hora_levantarse = models.CharField(max_length=150)
    hora_acostarse = models.CharField(max_length=150)
    uso_despertador = models.CharField(max_length=150)
    facilidad_levantarse = models.CharField(max_length=150)
    alerta_manana = models.CharField(max_length=150)
    apetito_manana = models.CharField(max_length=150)
    descanso_manana = models.CharField(max_length=150)
    hora_acostarse_libre = models.CharField(max_length=150)
    ejercicio_fisico = models.CharField(max_length=150)
    hora_cansancio_noche = models.CharField(max_length=150)
    nivel_cansancia_11 = models.CharField(max_length=150)
    hora_despertarse_si_tarde = models.CharField(max_length=150)
    guardia_nocturna = models.CharField(max_length=150)
    horario_trabajo_fisico = models.CharField(max_length=150)
    ejercicio_nocturno = models.CharField(max_length=150)
    horario_trabajo = models.CharField(max_length=150)
    maximo_bienestar = models.CharField(max_length=150)
    tipo_persona = models.CharField(max_length=150)
    puntuacion = models.IntegerField()


class BerlinResult(ResultadoExamenBase):
    peso_cambio = models.CharField(max_length=50)
    ronca = models.CharField(max_length=10)
    tipo_ronquido = models.CharField(max_length=50)
    frecuencia_ronquidos = models.CharField(max_length=50)
    ronquido_molesto = models.CharField(max_length=50)
    apnea_observada = models.CharField(max_length=50)
    fatiga_matutina = models.CharField(max_length=50)
    fatiga_dia = models.CharField(max_length=50)
    somnolencia_conducir = models.CharField(max_length=50)
    presion_alta = models.CharField(max_length=50)


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
    periodo_siestas = models.CharField(max_length=100, blank=True, null=True)

    # Ambiente
    iluminacion = models.CharField(max_length=255, blank=True, null=True)
    comodidad = models.CharField(max_length=255, blank=True, null=True)
    ruido = models.CharField(max_length=255, blank=True, null=True)

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
    evolucion = models.CharField(max_length=100, blank=True, null=True)
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
    induccion_dormir = models.CharField(max_length=50)
    despertares_noche = models.CharField(max_length=50)
    despertar_temprano = models.CharField(max_length=50)
    duracion_dormir = models.CharField(max_length=50)
    calidad_dormir = models.CharField(max_length=50)
    bienestar_dia = models.CharField(max_length=50)
    funcionamiento_dia = models.CharField(max_length=50)
    somnolencia_dia = models.CharField(max_length=50)
    puntuacion_total = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"Atenas - {self.visita_examen_id}"


class SuenoFisicoResult(ResultadoExamenBase):
    peso = models.FloatField(blank=True, null=True)
    talla = models.FloatField(blank=True, null=True)
    imc = models.FloatField(blank=True, null=True)
    rango_imc = models.CharField(max_length=50, blank=True, null=True)
    circunferencia_cuello = models.FloatField(blank=True, null=True)
    perimetro_abdominal = models.FloatField(blank=True, null=True)
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
    dificultad_dormir = models.CharField(max_length=50)
    dificultad_mantener_sueno = models.CharField(max_length=50)
    despertar_temprano = models.CharField(max_length=50)
    satisfaccion_sueno = models.CharField(max_length=50)
    notabilidad_problema = models.CharField(max_length=50)
    preocupacion_sueno = models.CharField(max_length=50)
    interferencia_sueno = models.CharField(max_length=50)
    puntuacion_total = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"ISI - {self.visita_examen_id}"


class StopBangResult(ResultadoExamenBase):
    ronca_fuerte = models.BooleanField(default=False)
    cansado_frecuencia = models.BooleanField(default=False)
    deja_respirar = models.BooleanField(default=False)
    presion_arterial = models.BooleanField(default=False)
    imc_alto = models.BooleanField(default=False)
    mayor_50 = models.BooleanField(default=False)
    cuello_grande = models.BooleanField(default=False)
    masculino = models.BooleanField(default=False)
    puntaje_total = models.IntegerField(blank=True, null=True)
    riesgo = models.CharField(max_length=20, blank=True, null=True)
    stop_positivos = models.IntegerField(blank=True, null=True)
    bang_positivos = models.IntegerField(blank=True, null=True)
    alto_riesgo_alternativo = models.BooleanField(default=False)

    def __str__(self):
        return f"STOP-BANG - {self.visita_examen_id}"
