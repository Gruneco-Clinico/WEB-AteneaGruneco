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

    ### Para códigos ANG-consecutivos

    codigo = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Código del Paciente"
    )

    def __str__(self):
        return f"{self.primer_nombre} {self.primer_apellido} ({self.codigo or 'sin código'})"


    # Antes estaba esto: 
    # def __str__(self):
    #     return f"{self.primer_nombre} {self.primer_apellido}"


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
    
    # Para códigos ANG-XXX consecutivos
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Asignar código único si aplica
        if (
            self.Tipo_visita
            and self.Tipo_visita.proyecto.nombre == "Anosognosia"
            and self.Tipo_visita.nombre == "PosIntervención"
        ):
            paciente = self.paciente
            if paciente and not paciente.codigo:
                # Obtener el último código asignado
                ultimo = (
                    DatosDemograficos.objects.exclude(codigo__isnull=True)
                    .exclude(codigo__exact="")
                    .order_by("-codigo")
                    .first()
                )
                if ultimo and ultimo.codigo:
                    try:
                        numero = int(ultimo.codigo.split("-")[1])
                    except (IndexError, ValueError):
                        numero = 0
                else:
                    numero = 0

                # Generar nuevo consecutivo
                nuevo_codigo = f"ANG-{numero+1:03d}"
                paciente.codigo = nuevo_codigo
                paciente.save()


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

            # MANEJO ESPECIAL para Antecedentes (que no hereda de ResultadoExamenBase)
            if "antecedentes" in self.examen.nombre.lower():
                try:
                    antecedentes_link = self.antecedentes_link
                    if antecedentes_link and antecedentes_link.antecedentes_result:
                        self._resultado_cache = antecedentes_link.antecedentes_result
                except AttributeError:
                    print(f"❌ No antecedentes_link para {self.examen.nombre}")
                return self._resultado_cache

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
                "euroqol5d5lresult_resultado",
                "euroqolevasaludresult_resultado",
                "participanteyesavageresult_resultado",
                "cuidadornpiresult_resultado",
                "lawtonbrodyresult_resultado",
                "zaritresult_resultado",
                "redlatspanishresult_resultado",
                "mocaresult_resultado",
                "adherenciaterapeuticaresult_resultado",
                "aqdcuidadorresult_resultado",
                "aqdparticipanteresult_resultado",
                "cdrcuidadorresult_resultado",
                "cdrparticipanteresult_resultado",
                "bettyferrelresult_resultado",
                "puntajecdrresult_resultado",
                "consentimientoinformadoparticipanteresult_resultado",
                "consentimientoinformadocuidadorresult_resultado",
                "anamnesiscuidadorresult_resultado",
                "anamnesisparticipanteresult_resultado",
                "seguimientointervencionesresult_resultado",
                "analisisgeneralresult_resultado",  # ✅ ANÁLISIS GENERAL
                "examenfisicoresult_resultado",  # ✅ EXAMEN FÍSICO
                "examenneurologicoresult_resultado",  # ✅ EXAMEN NEUROLÓGICO
                "medicamentosresult_resultado",  # ✅ MEDICAMENTOS
                "revisionsistemrasresult_resultado",  # ✅ REVISIÓN SISTEMAS
            ]

            # 🔧 CORRECCIÓN: Actualizar el bucle para asignar el resultado encontrado
            for related_name in possible_related_names:
                try:
                    resultado = getattr(self, related_name)
                    if resultado:  # Verificar que el resultado existe
                        self._resultado_cache = resultado

                        break  # 🔧 IMPORTANTE: Salir del bucle cuando encontremos algo
                except AttributeError:
                    continue
                except Exception as e:
                    continue

            # DEBUG: Si no encontró nada
            if self._resultado_cache is None:
                # Mostrar qué related_names están disponibles
                available_related = [
                    attr for attr in dir(self) if attr.endswith("_resultado")
                ]

        return self._resultado_cache

    @property
    def esta_realizado(self):
        """Verifica si el examen está completado y tiene un resultado concreto asociado."""

        estado_completado = self.estado == "completado"

        resultado = self.get_resultado_instance()
        tiene_resultado = resultado is not None

        if resultado:
            pass

        final_result = estado_completado and tiene_resultado

        return final_result

    @property
    def puede_editarse(self):
        """Verifica si el examen puede editarse."""
        # NUEVO: Solo puede editarse si la visita está abierta Y el examen está realizado
        visita_abierta = self.visita.estado_visita == "abierta"
        examen_realizado = self.esta_realizado

        puede_editar = visita_abierta and examen_realizado

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
            "euroqol5d5l": "realizar_euroqol",
            "euroqolevasalud": "realizar_euroqolevasalud",
            "participanteyesavage": "realizar_participanteyesavage",
            "cuidadornpi": "realizar_cuidadornpi",
            "lawtonbrody": "realizar_lawtonbrody",
            "moca": "realizar_moca",
            "adherenciaterapeutica": "realizar_adherenciaterapeutica",
            "zarit": "realizar_zarit",
            "aqdcuidador": "realizar_aqdcuidador",
            "aqdparticipante": "realizar_aqdparticipante",
            "redlatspanish": "realizar_redlatspanish",
            "cdrcuidador": "realizar_cdrcuidador",
            "cdrparticipante": "realizar_cdrparticipante",
            "cdrevaluacionclinica": "realizar_cdr_evaluacion_clinica",
            "anamnesiscuidador": "realizar_anamnesis_cuidador",
            "anamnesisparticipante": "realizar_anamnesis_participante",
            "consentimientoinformadocuidador": "realizar_consentimientoinformado_cuidador",
            "consentimientoinformadoparticipante": "realizar_consentimientoinformado_participante",
            "seguimientointervenciones": "realizar_seguimiento_intervenciones",
            "analisisgeneral": "realizar_analisisgeneral",
            "examenfisico": "realizar_examen_fisico",
            "antecedentes": "realizar_antecedentes",
            "examenneurologico": "realizar_examen_neurologico",
            "medicamentos": "realizar_medicamentos",
            "revisionsistemas": "realizar_revision_sistemas",
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
            "euroqol5d5l": "ver_euroqol",
            "euroqolevasalud": "ver_euroqolevasalud",
            "participanteyesavage": "ver_participanteyesavage",
            "cuidadornpi": "ver_cuidadornpi",
            "lawtonbrody": "ver_lawtonbrody",
            "moca": "ver_moca",
            "adherenciaterapeutica": "ver_adherenciaterapeutica",
            "zarit": "ver_zarit",
            "aqdcuidador": "ver_aqdcuidador",
            "aqdparticipante": "ver_aqdparticipante",
            "redlatspanish": "ver_redlatspanish",
            "cdrcuidador": "ver_cdrcuidador",
            "cdrparticipante": "ver_cdrparticipante",
            "cdrevaluacionclinica": "ver_cdr_evaluacion_clinica",
            "anamnesiscuidador": "ver_anamnesis_cuidador",
            "anamnesisparticipante": "ver_anamnesis_participante",
            "consentimientoinformadocuidador": "ver_consentimientoinformado_cuidador",
            "consentimientoinformadoparticipante": "ver_consentimientoinformado_participante",
            "seguimientointervenciones": "ver_seguimiento_intervenciones",
            "analisisgeneral": "ver_analisis_general",
            "examenfisico": "ver_examen_fisico",
            "antecedentes": "ver_antecedentes",
            "examenneurologico": "ver_examen_neurologico",
            "medicamentos": "ver_medicamentos",
            "revisionsistemas": "ver_revision_sistemas",
        }

        url_name = url_mapping.get(examen_nombre)
        if url_name:
            try:
                return reverse(url_name, args=[self.id])
            except NoReverseMatch:
                pass

        return f"/examenes/ver/{self.id}/"

        # try:
        #     return reverse("ver_resultado_examen", args=[self.id])
        # except Exception:
        #     return f"/examenes/ver/{self.id}/"

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
            "euroqol5d5l": "editar_euroqol",
            "euroqolevasalud": "editar_euroqolevasalud",
            "participanteyesavage": "editar_participanteyesavage",
            "cuidadornpi": "editar_cuidadornpi",
            "lawtonbrody": "editar_lawtonbrody",
            "moca": "editar_moca",
            "adherenciaterapeutica": "editar_adherenciaterapeutica",
            "zarit": "editar_zarit",
            "aqdcuidador": "editar_aqdcuidador",
            "aqdparticipante": "editar_aqdparticipante",
            "redlatspanish": "editar_redlatspanish",
            "cdrcuidador": "editar_cdrcuidador",
            "cdrparticipante": "editar_cdrparticipante",
            "cdrevaluacionclinica": "editar_cdr_evaluacion_clinica",
            "anamnesiscuidador": "editar_anamnesis_cuidador",
            "anamnesisparticipante": "editar_anamnesis_participante",
            "consentimientoinformadocuidador": "editar_consentimientoinformado_cuidador",
            "consentimientoinformadoparticipante": "editar_consentimientoinformado_participante",
            "seguimientointervenciones": "editar_seguimiento_intervenciones",
            "analisisgeneral": "editar_analisis_general",
            "examenfisico": "editar_examen_fisico",
            "antecedentes": "editar_antecedentes",
            "examenneurologico": "editar_examen_neurologico",
            "medicamentos": "editar_medicamentos",
            "revisionsistemas": "editar_revision_sistemas",
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
    duerme_acompanado = models.CharField(max_length=100)
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
    somnolencia_conducir = models.BooleanField(null=True, blank=True)
    presion_alta = models.BooleanField(null=True, blank=True)


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


### Anosognosia


class LawtonBrodyResult(ResultadoExamenBase):
    genero = models.CharField(max_length=10)

    usar_telefono = models.CharField(max_length=255)
    hacer_compras = models.CharField(max_length=255)
    preparar_comida = models.CharField(max_length=255)
    cuidado_casa = models.CharField(max_length=255)
    lavar_ropa = models.CharField(max_length=255)
    uso_transporte = models.CharField(max_length=255)
    medicacion = models.CharField(max_length=255)
    manejo_dinero = models.CharField(max_length=255)

    puntaje_total = models.IntegerField()
    diagnostico = models.CharField(max_length=100)

    def __str__(self):
        return f"Lawton & Brody - {self.visita_examen_id}"


class CuidadorNPIResult(ResultadoExamenBase):
    ideas_delirantes = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
    )
    ideas_delirantes_frecuencia = models.CharField(max_length=50, blank=True, null=True)
    ideas_delirantes_gravedad = models.CharField(max_length=50, blank=True, null=True)
    ideas_delirantes_F_G = models.IntegerField(blank=True, null=True)
    ideas_delirantes_distres = models.CharField(max_length=50, blank=True, null=True)

    alucinaciones = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
    )
    alucinaciones_frecuencia = models.CharField(max_length=50, blank=True, null=True)
    alucinaciones_gravedad = models.CharField(max_length=50, blank=True, null=True)
    alucinaciones_F_G = models.IntegerField(blank=True, null=True)
    alucinaciones_distres = models.CharField(max_length=50, blank=True, null=True)

    agitacion = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
    )
    agitacion_frecuencia = models.CharField(max_length=50, blank=True, null=True)
    agitacion_gravedad = models.CharField(max_length=50, blank=True, null=True)
    agitacion_F_G = models.IntegerField(blank=True, null=True)
    agitacion_distres = models.CharField(max_length=50, blank=True, null=True)

    depresion = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
    )
    depresion_frecuencia = models.CharField(max_length=50, blank=True, null=True)
    depresion_gravedad = models.CharField(max_length=50, blank=True, null=True)
    depresion_F_G = models.IntegerField(blank=True, null=True)
    depresion_distres = models.CharField(max_length=50, blank=True, null=True)

    ansiedad = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
    )
    ansiedad_frecuencia = models.CharField(max_length=50, blank=True, null=True)
    ansiedad_gravedad = models.CharField(max_length=50, blank=True, null=True)
    ansiedad_F_G = models.IntegerField(blank=True, null=True)
    ansiedad_distres = models.CharField(max_length=50, blank=True, null=True)

    euforia = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
    )
    euforia_frecuencia = models.CharField(max_length=50, blank=True, null=True)
    euforia_gravedad = models.CharField(max_length=50, blank=True, null=True)
    euforia_F_G = models.IntegerField(blank=True, null=True)
    euforia_distres = models.CharField(max_length=50, blank=True, null=True)

    apatia = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
    )
    apatia_frecuencia = models.CharField(max_length=50, blank=True, null=True)
    apatia_gravedad = models.CharField(max_length=50, blank=True, null=True)
    apatia_F_G = models.IntegerField(blank=True, null=True)
    apatia_distres = models.CharField(max_length=50, blank=True, null=True)

    desinhibicion = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
    )
    desinhibicion_frecuencia = models.CharField(max_length=50, blank=True, null=True)
    desinhibicion_gravedad = models.CharField(max_length=50, blank=True, null=True)
    desinhibicion_F_G = models.IntegerField(blank=True, null=True)
    desinhibicion_distres = models.CharField(max_length=50, blank=True, null=True)

    irritabilidad = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
    )
    irritabilidad_frecuencia = models.CharField(max_length=50, blank=True, null=True)
    irritabilidad_gravedad = models.CharField(max_length=50, blank=True, null=True)
    irritabilidad_F_G = models.IntegerField(blank=True, null=True)
    irritabilidad_distres = models.CharField(max_length=50, blank=True, null=True)

    conducta_motor = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
    )
    conducta_motor_frecuencia = models.CharField(max_length=50, blank=True, null=True)
    conducta_motor_gravedad = models.CharField(max_length=50, blank=True, null=True)
    conducta_motor_F_G = models.IntegerField(blank=True, null=True)
    conducta_motor_distres = models.CharField(max_length=50, blank=True, null=True)

    sueno = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
    )
    sueno_frecuencia = models.CharField(max_length=50, blank=True, null=True)
    sueno_gravedad = models.CharField(max_length=50, blank=True, null=True)
    sueno_F_G = models.IntegerField(blank=True, null=True)
    sueno_distres = models.CharField(max_length=50, blank=True, null=True)

    apetito = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
    )
    apetito_frecuencia = models.CharField(max_length=50, blank=True, null=True)
    apetito_gravedad = models.CharField(max_length=50, blank=True, null=True)
    apetito_F_G = models.IntegerField(blank=True, null=True)
    apetito_distres = models.CharField(max_length=50, blank=True, null=True)

    puntaje_total = models.IntegerField(blank=True, null=True, default=0)
    carga_total = models.IntegerField(blank=True, null=True, default=0)

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

    def save(self, *args, **kwargs):
        self.puntaje_total = self.calcular_puntaje_total()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"NPI - Paciente {self.visita_examen_id}"


class AdherenciaTerapeuticaResult(ResultadoExamenBase):
    # Factores
    factor1 = models.IntegerField(default=0)
    factor2 = models.IntegerField(default=0)
    factor3 = models.IntegerField(default=0)

    # Preguntas
    dieta_rigurosa = models.CharField(max_length=20)  # P1
    asistir_consultas = models.CharField(max_length=20)  # P2
    pendiente_sintomas = models.CharField(max_length=20)  # P3
    recomendacion_medico = models.CharField(max_length=20)  # P4
    alimentos_permitidos = models.CharField(max_length=20)  # P5
    seguir_tratamiento = models.CharField(max_length=20)  # P6
    regresar_consulta = models.CharField(max_length=20)  # P7
    seguridad_tratamiento = models.CharField(max_length=20)  # P8
    olvido_medicamentos = models.CharField(max_length=20)  # P9
    dejar_tratamiento = models.CharField(max_length=20)  # P10
    sin_mejoria = models.CharField(max_length=20)  # P11
    hacer_ejercicio = models.CharField(max_length=20)  # P12
    recordar_medicamentos = models.CharField(max_length=20)  # P13
    analisis_periodicos = models.CharField(max_length=20)  # P14
    confianza_medico = models.CharField(max_length=20)  # P15
    mejorar_enfermedad = models.CharField(max_length=200)  # P16
    apego_tratamiento = models.CharField(max_length=20)  # P17
    adherencia_tratamiento = models.CharField(max_length=20)  # P18
    menos_medicamento = models.CharField(max_length=20)  # P19
    confianza_medicamento = models.CharField(max_length=20)  # P20
    dosis_indicada = models.CharField(max_length=20)  # P21
    revisiones_periodicas = models.CharField(max_length=20)  # P22
    medico_sintoma = models.CharField(max_length=20)  # P23
    mejoria_salud = models.CharField(max_length=20)  # P24
    sintomas_deterioro = models.CharField(max_length=20)  # P25
    mediciones_indicadas = models.CharField(max_length=20)  # P26
    respeto_dieta = models.CharField(max_length=20)  # P27
    modificacion_tratamiento = models.CharField(max_length=20)  # P28
    mantener_controlado = models.CharField(max_length=20)  # P29
    seguridad_resultados = models.CharField(max_length=20)  # P30

    # Factores calculados
    factor1 = models.IntegerField(blank=True, null=True)  # Atención médica
    factor2 = models.IntegerField(blank=True, null=True)  # Estilo de vida
    factor3 = models.IntegerField(blank=True, null=True)  # Barreras ante la medicación

    # Interpretaciones
    factor1_interpretacion = models.CharField(max_length=50, blank=True, null=True)
    factor2_interpretacion = models.CharField(max_length=50, blank=True, null=True)
    factor3_interpretacion = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Adherencia Terapéutica - {self.visita_examen_id}"


class EuroQol5D5LResult(ResultadoExamenBase):
    movilidad = models.CharField(max_length=255)
    cuidado_personal = models.CharField(max_length=255)
    actividades = models.CharField(max_length=255)
    dolor = models.CharField(max_length=255)
    ansiedad = models.CharField(max_length=255)

    def __str__(self):
        return f"EuroQol-5D-5L - {self.visita_examen}"


class EuroQolEVASaludResult(ResultadoExamenBase):
    # Valor reportado en el "termómetro" de 0 a 100
    termometro_estado_salud = models.IntegerField(
        help_text="Autovaloración del estado de salud en la escala de 0 (peor) a 100 (mejor)."
    )

    def __str__(self):
        return f"EuroQol EVA Salud - {self.visita_examen}"


class MoCAResult(ResultadoExamenBase):
    # Ítems del MoCA
    alternancia = models.PositiveSmallIntegerField()  # 0–1
    cubo = models.PositiveSmallIntegerField()  # 0–1
    reloj = models.PositiveSmallIntegerField()  # 0–3
    denominacion = models.PositiveSmallIntegerField()  # 0–3

    # Atención y memoria
    atencion = (
        models.PositiveSmallIntegerField()
    )  # 0–6 (suma de secuencia, inversa, concentración, sustracción)
    repeticion = models.PositiveSmallIntegerField()  # 0–2
    fluidez = models.PositiveSmallIntegerField()  # 0–1
    abstraccion = models.PositiveSmallIntegerField()  # 0–2
    diferido = models.PositiveSmallIntegerField()  # 0–5
    orientacion = models.PositiveSmallIntegerField()  # 0–6

    # Corrección por escolaridad baja (checkbox)
    educacion_baja = models.BooleanField(default=False)

    # Totales
    puntaje_total = models.IntegerField(default=0)
    interpretacion = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"MoCA - {self.visita_examen_id}"


class ParticipanteYesavageResult(ResultadoExamenBase):
    # Preguntas (sí/no)
    satisfaccion_vida = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True
    )
    disminuir_actividades = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True
    )
    vida_vacia = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True
    )
    aburrido_frecuente = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True
    )
    buen_animo = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True
    )
    preocupacion = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True
    )
    felicidad = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True
    )
    frecuencia_desamparado = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True
    )
    quedarse_casa = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True
    )
    problemas_memoria = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True
    )
    maravilla_vivir = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True
    )
    inutil = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True
    )
    lleno_energia = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True
    )
    sin_esperanza = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True
    )
    otras_personas_mejor = models.CharField(
        max_length=2, choices=[("si", "Sí"), ("no", "No")], blank=True, null=True
    )

    # Puntaje total (0–15)
    puntaje_total = models.IntegerField(default=0)
    interpretacion = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Yesavage - {self.visita_examen_id}"


class ZaritResult(ResultadoExamenBase):
    pide_ayuda = models.CharField(max_length=50, blank=True, null=True)
    falta_tiempo_propio = models.CharField(max_length=50, blank=True, null=True)
    agobio = models.CharField(max_length=50, blank=True, null=True)
    verguenza_conducta = models.CharField(max_length=50, blank=True, null=True)
    sentir_enfado = models.CharField(max_length=50, blank=True, null=True)
    afectar_relacion_negativamente = models.CharField(
        max_length=50, blank=True, null=True
    )
    miedo_futuro = models.CharField(max_length=50, blank=True, null=True)
    dependencia = models.CharField(max_length=50, blank=True, null=True)
    sentir_tension = models.CharField(max_length=50, blank=True, null=True)
    deterioro_salud = models.CharField(max_length=50, blank=True, null=True)
    menos_intimidad = models.CharField(max_length=50, blank=True, null=True)
    resentir_vida_social = models.CharField(max_length=50, blank=True, null=True)
    desatender_amistades = models.CharField(max_length=50, blank=True, null=True)
    unica_dependencia = models.CharField(max_length=50, blank=True, null=True)
    dinero_insuficiente = models.CharField(max_length=50, blank=True, null=True)
    incapaz_mas_tiempo = models.CharField(max_length=50, blank=True, null=True)
    perder_control_vida = models.CharField(max_length=50, blank=True, null=True)
    cuidado_a_otros = models.CharField(max_length=50, blank=True, null=True)
    indecision_que_hacer = models.CharField(max_length=50, blank=True, null=True)
    hacer_mas = models.CharField(max_length=50, blank=True, null=True)
    cuidar_mejor = models.CharField(max_length=50, blank=True, null=True)
    grado_carga = models.CharField(max_length=50, blank=True, null=True)

    # Resultados globales
    puntaje_total = models.IntegerField(default=0)
    interpretacion = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Escala de Zarit - {self.visita_examen_id}"


class AQDCuidadorResult(ResultadoExamenBase):
    recordar_fecha = models.CharField(max_length=50, blank=True, null=True)
    orientacion_lugares_nuevos = models.CharField(max_length=50, blank=True, null=True)
    recordar_llamadas = models.CharField(max_length=50, blank=True, null=True)
    entender_conversacion = models.CharField(max_length=50, blank=True, null=True)
    firmar = models.CharField(max_length=50, blank=True, null=True)
    entender_lectura = models.CharField(max_length=50, blank=True, null=True)
    mantener_orden = models.CharField(max_length=50, blank=True, null=True)
    recordar_lugar_objetos = models.CharField(max_length=50, blank=True, null=True)
    escribir = models.CharField(max_length=50, blank=True, null=True)
    manejar_dinero = models.CharField(max_length=50, blank=True, null=True)
    orientacion_zona_donde_vive = models.CharField(max_length=50, blank=True, null=True)
    recordar_citas = models.CharField(max_length=50, blank=True, null=True)
    pasatiempos = models.CharField(max_length=50, blank=True, null=True)
    comunicarse_con_gente = models.CharField(max_length=50, blank=True, null=True)
    calculos_mentales = models.CharField(max_length=50, blank=True, null=True)
    recordar_compras = models.CharField(max_length=50, blank=True, null=True)
    contener_orina = models.CharField(max_length=50, blank=True, null=True)
    entender_pelicula = models.CharField(max_length=50, blank=True, null=True)
    orientacion_en_casa = models.CharField(max_length=50, blank=True, null=True)
    hacer_tareas_hogar = models.CharField(max_length=50, blank=True, null=True)
    comer_solo = models.CharField(max_length=50, blank=True, null=True)
    realizar_tramites = models.CharField(max_length=50, blank=True, null=True)
    decisiones_y_adaptacion = models.CharField(max_length=50, blank=True, null=True)
    egoismo = models.CharField(max_length=50, blank=True, null=True)
    enojo_menos_paciencia = models.CharField(max_length=50, blank=True, null=True)
    llorar_con_facilidad = models.CharField(max_length=50, blank=True, null=True)
    reir_situaciones_inapropiadas = models.CharField(
        max_length=50, blank=True, null=True
    )
    temas_sexuales = models.CharField(max_length=50, blank=True, null=True)
    falta_de_interes = models.CharField(max_length=50, blank=True, null=True)
    deprimido = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"AQ-D Cuidador - {self.visita_examen_id}"


class AQDParticipanteResult(ResultadoExamenBase):
    recordar_fecha = models.CharField(max_length=50, blank=True, null=True)
    orientacion_lugares_nuevos = models.CharField(max_length=50, blank=True, null=True)
    recordar_llamadas = models.CharField(max_length=50, blank=True, null=True)
    entender_conversacion = models.CharField(max_length=50, blank=True, null=True)
    firmar = models.CharField(max_length=50, blank=True, null=True)
    entender_lectura = models.CharField(max_length=50, blank=True, null=True)
    mantener_orden = models.CharField(max_length=50, blank=True, null=True)
    recordar_lugar_objetos = models.CharField(max_length=50, blank=True, null=True)
    escribir = models.CharField(max_length=50, blank=True, null=True)
    manejar_dinero = models.CharField(max_length=50, blank=True, null=True)
    orientacion_zona_donde_vive = models.CharField(max_length=50, blank=True, null=True)
    recordar_citas = models.CharField(max_length=50, blank=True, null=True)
    pasatiempos = models.CharField(max_length=50, blank=True, null=True)
    comunicarse_con_gente = models.CharField(max_length=50, blank=True, null=True)
    calculos_mentales = models.CharField(max_length=50, blank=True, null=True)
    recordar_compras = models.CharField(max_length=50, blank=True, null=True)
    contener_orina = models.CharField(max_length=50, blank=True, null=True)
    entender_pelicula = models.CharField(max_length=50, blank=True, null=True)
    orientacion_en_casa = models.CharField(max_length=50, blank=True, null=True)
    hacer_tareas_hogar = models.CharField(max_length=50, blank=True, null=True)
    comer_solo = models.CharField(max_length=50, blank=True, null=True)
    realizar_tramites = models.CharField(max_length=50, blank=True, null=True)
    decisiones_y_adaptacion = models.CharField(max_length=50, blank=True, null=True)
    egoismo = models.CharField(max_length=50, blank=True, null=True)
    enojo_menos_paciencia = models.CharField(max_length=50, blank=True, null=True)
    llorar_con_facilidad = models.CharField(max_length=50, blank=True, null=True)
    reir_situaciones_inapropiadas = models.CharField(
        max_length=50, blank=True, null=True
    )
    temas_sexuales = models.CharField(max_length=50, blank=True, null=True)
    falta_de_interes = models.CharField(max_length=50, blank=True, null=True)
    deprimido = models.CharField(max_length=50, blank=True, null=True)

    # Puntaje total
    # puntaje_total = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"AQ-D Participante - {self.visita_examen_id}"


class CDRCuidadorResult(ResultadoExamenBase):
    # ====================
    # Dominio: Memoria
    # ====================
    memoria_p1 = models.CharField(max_length=10, blank=True, null=True)  # sí/no
    memoria_p1_1 = models.CharField(
        max_length=10, blank=True, null=True
    )  # sí/no, subpregunta
    memoria_p2 = models.CharField(
        max_length=20, blank=True, null=True
    )  # generalmente/a_veces/raramente
    memoria_p3 = models.CharField(max_length=20, blank=True, null=True)
    memoria_p4 = models.CharField(max_length=10, blank=True, null=True)  # sí/no
    memoria_p5 = models.CharField(max_length=10, blank=True, null=True)  # sí/no
    memoria_p6 = models.CharField(max_length=20, blank=True, null=True)
    memoria_p7 = models.CharField(max_length=20, blank=True, null=True)
    memoria_p8 = models.CharField(max_length=20, blank=True, null=True)

    # Evento reciente (respuestas abiertas)
    evento_recuerda_semana = models.TextField(blank=True, null=True)
    evento_recuerda_mes = models.TextField(blank=True, null=True)

    # Datos personales
    nacimiento_fecha = models.DateField(blank=True, null=True)
    nacimiento_lugar = models.CharField(max_length=150, blank=True, null=True)
    colegio_nombre = models.CharField(max_length=150, blank=True, null=True)
    colegio_lugar = models.CharField(max_length=150, blank=True, null=True)
    colegio_grado = models.CharField(max_length=100, blank=True, null=True)
    ocupacion_principal = models.CharField(max_length=150, blank=True, null=True)
    ultimo_trabajo = models.CharField(max_length=150, blank=True, null=True)
    jubilacion = models.TextField(blank=True, null=True)

    # ====================
    # Dominio: Orientación
    # ====================
    orientacion_p1 = models.CharField(max_length=20, blank=True, null=True)
    orientacion_p2 = models.CharField(max_length=20, blank=True, null=True)
    orientacion_p3 = models.CharField(max_length=20, blank=True, null=True)
    orientacion_p4 = models.CharField(max_length=20, blank=True, null=True)
    orientacion_p5 = models.CharField(max_length=20, blank=True, null=True)
    orientacion_p6 = models.CharField(max_length=20, blank=True, null=True)
    orientacion_p7 = models.CharField(max_length=20, blank=True, null=True)
    orientacion_p8 = models.CharField(max_length=20, blank=True, null=True)

    # ====================
    # Dominio: Juicio y resolución de problemas
    # ====================
    juicio_p1 = models.CharField(max_length=100, blank=True, null=True)
    juicio_p2 = models.CharField(max_length=100, blank=True, null=True)
    juicio_p3 = models.CharField(max_length=100, blank=True, null=True)
    juicio_p4 = models.CharField(max_length=150, blank=True, null=True)
    juicio_p5 = models.CharField(max_length=50, blank=True, null=True)
    juicio_p6 = models.CharField(max_length=50, blank=True, null=True)

    # ====================
    # Actividades comunitarias
    # ====================
    trabaja_actualmente = models.CharField(
        max_length=10, blank=True, null=True
    )  # na/si/no
    memoria_causa_jubilacion = models.CharField(
        max_length=10, blank=True, null=True
    )  # si/no/nose
    dificultades_trabajo_memoria = models.CharField(
        max_length=20, blank=True, null=True
    )

    condujo_alguna_vez = models.CharField(max_length=5, blank=True, null=True)  # si/no
    conduce_actualmente = models.CharField(max_length=5, blank=True, null=True)  # si/no
    dejo_de_conducir_por_memoria = models.CharField(
        max_length=5, blank=True, null=True
    )  # si/no
    riesgos_conduccion = models.CharField(max_length=5, blank=True, null=True)  # si/no

    compras_independientes = models.CharField(max_length=50, blank=True, null=True)
    actividades_fuera_hogar = models.CharField(max_length=50, blank=True, null=True)
    asiste_funciones_sociales = models.CharField(
        max_length=5, blank=True, null=True
    )  # si/no
    motivo_no_funciones = models.TextField(blank=True, null=True)

    parece_enfermo = models.CharField(max_length=5, blank=True, null=True)  # si/no
    participa_hogar_geriatrico = models.CharField(
        max_length=5, blank=True, null=True
    )  # si/no
    info_suficiente_comunitarias = models.CharField(
        max_length=5, blank=True, null=True
    )  # si/no
    notas_comunitarias = models.TextField(blank=True, null=True)

    # ====================
    # Actividades domésticas y pasatiempos
    # ====================
    cambios_tareas_domesticas = models.TextField(blank=True, null=True)
    cosas_que_aun_realiza_domesticas = models.TextField(blank=True, null=True)
    cambios_pasatiempos = models.TextField(blank=True, null=True)
    cosas_que_aun_realiza_pasatiempos = models.TextField(blank=True, null=True)
    actividades_no_realiza_en_hogar = models.TextField(blank=True, null=True)

    habilidad_domestica_dementia_scale = models.DecimalField(
        max_digits=2, decimal_places=1, blank=True, null=True
    )
    descripcion_habilidad_domestica = models.TextField(blank=True, null=True)
    nivel_desempeno_domestico = models.CharField(max_length=50, blank=True, null=True)
    notas_domesticas_pasatiempos = models.TextField(blank=True, null=True)

    # ====================
    # Cuidado personal
    # ====================
    cuidado_p1 = models.IntegerField(blank=True, null=True)  # Vestirse
    cuidado_p2 = models.IntegerField(blank=True, null=True)  # Lavado/aseo
    cuidado_p3 = models.IntegerField(blank=True, null=True)  # Alimentación
    cuidado_p4 = models.IntegerField(blank=True, null=True)  # Control de esfínteres

    def __str__(self):
        return f"CDR Cuidador - {self.visita_examen_id}"


class CDRParticipanteResult(ResultadoExamenBase):
    # ====================
    # Dominio: Memoria
    # ====================
    memoria_p1 = models.CharField(max_length=5, blank=True, null=True)  # si/no

    evento_recuerda_semana = models.TextField(blank=True, null=True)
    memoria_semana_calificacion = models.DecimalField(
        max_digits=2, decimal_places=1, blank=True, null=True
    )

    evento_recuerda_mes = models.TextField(blank=True, null=True)
    memoria_mes_calificacion = models.DecimalField(
        max_digits=2, decimal_places=1, blank=True, null=True
    )

    # Ensayos (checkboxes del nombre/dirección)
    ensayo1_juan = models.BooleanField(default=False)
    ensayo1_perez = models.BooleanField(default=False)
    ensayo1_calle = models.BooleanField(default=False)
    ensayo1_avenida = models.BooleanField(default=False)
    ensayo1_cali = models.BooleanField(default=False)

    ensayo2_juan = models.BooleanField(default=False)
    ensayo2_perez = models.BooleanField(default=False)
    ensayo2_calle = models.BooleanField(default=False)
    ensayo2_avenida = models.BooleanField(default=False)
    ensayo2_cali = models.BooleanField(default=False)

    ensayo3_juan = models.BooleanField(default=False)
    ensayo3_perez = models.BooleanField(default=False)
    ensayo3_calle = models.BooleanField(default=False)
    ensayo3_avenida = models.BooleanField(default=False)
    ensayo3_cali = models.BooleanField(default=False)

    fecha_nacimiento = models.DateField(blank=True, null=True)
    lugar_nacimiento = models.CharField(max_length=100, blank=True, null=True)

    colegio_nombre = models.CharField(max_length=100, blank=True, null=True)
    colegio_lugar = models.CharField(max_length=100, blank=True, null=True)
    colegio_grado = models.CharField(max_length=50, blank=True, null=True)

    ocupacion_principal = models.CharField(max_length=150, blank=True, null=True)
    ultimo_trabajo = models.CharField(max_length=150, blank=True, null=True)
    jubilacion = models.TextField(blank=True, null=True)

    # Repetición del nombre/dirección
    repeticion_juan = models.BooleanField(default=False)
    repeticion_perez = models.BooleanField(default=False)
    repeticion_calle = models.BooleanField(default=False)
    repeticion_avenida = models.BooleanField(default=False)
    repeticion_cali = models.BooleanField(default=False)

    # ====================
    # Dominio: Orientación
    # ====================
    orientacion_p1 = models.CharField(
        max_length=15, blank=True, null=True
    )  # correcto/incorrecto
    orientacion_p2 = models.CharField(max_length=15, blank=True, null=True)
    orientacion_p3 = models.CharField(max_length=15, blank=True, null=True)
    orientacion_p4 = models.CharField(max_length=15, blank=True, null=True)
    orientacion_p5 = models.CharField(max_length=50, blank=True, null=True)
    orientacion_p6 = models.CharField(max_length=50, blank=True, null=True)
    orientacion_p7 = models.CharField(max_length=15, blank=True, null=True)
    orientacion_p8 = models.CharField(max_length=15, blank=True, null=True)

    # ====================
    # Dominio: Juicio y resolución de problemas
    # ====================
    juicio_p1_respuesta = models.TextField(blank=True, null=True)
    juicio_p1_puntaje = models.IntegerField(blank=True, null=True)

    juicio_p2_respuesta = models.TextField(blank=True, null=True)
    juicio_p2_puntaje = models.IntegerField(blank=True, null=True)

    juicio_p3_respuesta = models.TextField(blank=True, null=True)
    juicio_p3_puntaje = models.IntegerField(blank=True, null=True)

    juicio_p4_respuesta = models.TextField(blank=True, null=True)
    juicio_p4_puntaje = models.IntegerField(blank=True, null=True)

    juicio_p5_correcto = models.BooleanField(default=False)
    juicio_p6_correcto = models.BooleanField(default=False)
    juicio_p7_correcto = models.BooleanField(default=False)

    juicio_p8_puntaje = models.IntegerField(blank=True, null=True)

    juicio_p9 = models.CharField(
        max_length=50, blank=True, null=True
    )  # Buena, parcial, poca percepción

    def __str__(self):
        return f"CDR Participante - {self.visita_examen_id}"


class RedLatSpanishResult(ResultadoExamenBase):
    # ---------- Autocuidado ----------
    comer = models.CharField(max_length=255, blank=True, null=True)
    vestirse = models.CharField(max_length=255, blank=True, null=True)
    banarse = models.CharField(max_length=255, blank=True, null=True)
    bano = models.CharField(max_length=255, blank=True, null=True)
    medicamentos = models.CharField(max_length=255, blank=True, null=True)
    apariencia = models.CharField(max_length=255, blank=True, null=True)

    # ---------- Cuidado del hogar ----------
    cocinar = models.CharField(max_length=255, blank=True, null=True)
    poner_mesa = models.CharField(max_length=255, blank=True, null=True)
    aseo_hogar = models.CharField(max_length=255, blank=True, null=True)
    mantener_casa = models.CharField(max_length=255, blank=True, null=True)
    reparar_hogar = models.CharField(max_length=255, blank=True, null=True)
    lavado_ropa = models.CharField(max_length=255, blank=True, null=True)

    # ---------- Trabajo y recreación ----------
    trabajo = models.CharField(max_length=255, blank=True, null=True)
    recreacion = models.CharField(max_length=255, blank=True, null=True)
    organizaciones = models.CharField(max_length=255, blank=True, null=True)
    desplazamiento = models.CharField(max_length=255, blank=True, null=True)

    # ---------- Compras y dinero ----------
    alimentos = models.CharField(max_length=255, blank=True, null=True)
    dinero_efectivo = models.CharField(max_length=255, blank=True, null=True)
    finanzas = models.CharField(max_length=255, blank=True, null=True)

    # ---------- Viajes ----------
    transporte_publico = models.CharField(max_length=255, blank=True, null=True)
    manejo_vehiculos = models.CharField(max_length=255, blank=True, null=True)
    movilidad_barrio = models.CharField(max_length=255, blank=True, null=True)
    viajes_fuera = models.CharField(max_length=255, blank=True, null=True)

    # ---------- Comunicación ----------
    telefono = models.CharField(max_length=255, blank=True, null=True)
    conversacion = models.CharField(max_length=255, blank=True, null=True)
    comprension = models.CharField(max_length=255, blank=True, null=True)
    lectura = models.CharField(max_length=255, blank=True, null=True)
    escritura = models.CharField(max_length=255, blank=True, null=True)

    # ---------- Tecnología ----------
    computador = models.CharField(max_length=255, blank=True, null=True)
    telefono_celular = models.CharField(max_length=255, blank=True, null=True)
    cajero = models.CharField(max_length=255, blank=True, null=True)
    internet = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    redes_sociales = models.CharField(max_length=255, blank=True, null=True)

    puntaje_autocuidado = models.CharField(max_length=20, blank=True, null=True)
    puntaje_cuidado_hogar = models.CharField(max_length=20, blank=True, null=True)
    puntaje_trabajo_recreacion = models.CharField(max_length=20, blank=True, null=True)
    puntaje_compras_dinero = models.CharField(max_length=20, blank=True, null=True)
    puntaje_viajes = models.CharField(max_length=20, blank=True, null=True)
    puntaje_comunicacion = models.CharField(max_length=20, blank=True, null=True)
    puntaje_tecnologia = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"RedLat Spanish - {self.visita_examen}"


class BettyFerrelResult(ResultadoExamenBase):
    # ---------- Bienestar físico ----------
    agotamiento = models.CharField(max_length=255, blank=True, null=True)
    cambios_alimenticios = models.CharField(max_length=255, blank=True, null=True)
    dolor = models.CharField(max_length=255, blank=True, null=True)
    cambios_sueno = models.CharField(max_length=255, blank=True, null=True)
    salud_fisica_general = models.CharField(max_length=255, blank=True, null=True)

    # ---------- bienestar psicológico ----------
    facilidad_enfrentar = models.CharField(max_length=255, blank=True, null=True)
    felicidad = models.CharField(max_length=255, blank=True, null=True)
    control_vida = models.CharField(max_length=255, blank=True, null=True)
    satisfaccion_vida = models.CharField(max_length=255, blank=True, null=True)
    concentracion = models.CharField(max_length=255, blank=True, null=True)
    utilidad_personal = models.CharField(max_length=255, blank=True, null=True)
    angustia_diagnostico = models.CharField(max_length=255, blank=True, null=True)
    angustia_tratamiento = models.CharField(max_length=255, blank=True, null=True)
    ansiedad = models.CharField(max_length=255, blank=True, null=True)
    depresion = models.CharField(max_length=255, blank=True, null=True)
    miedo_otra_enfermedad = models.CharField(max_length=255, blank=True, null=True)
    miedo_retroceso = models.CharField(max_length=255, blank=True, null=True)
    miedo_avance = models.CharField(max_length=255, blank=True, null=True)
    estado_psicologico = models.CharField(max_length=255, blank=True, null=True)

    # ---------- Bienestar social ----------
    angustia_familiar = models.CharField(max_length=255, blank=True, null=True)
    nivel_ayuda = models.CharField(max_length=255, blank=True, null=True)
    relaciones_personales = models.CharField(max_length=255, blank=True, null=True)
    vida_sexual = models.CharField(max_length=255, blank=True, null=True)
    trabajo = models.CharField(max_length=255, blank=True, null=True)
    actividades_hogar = models.CharField(max_length=255, blank=True, null=True)
    aislamiento = models.CharField(max_length=255, blank=True, null=True)
    carga_economica = models.CharField(max_length=255, blank=True, null=True)
    estado_social = models.CharField(max_length=255, blank=True, null=True)

    # ---------- Bienestar espiritual ----------
    actividades_religiosas = models.CharField(max_length=255, blank=True, null=True)
    actividades_espirituales_personales = models.CharField(
        max_length=255, blank=True, null=True
    )
    incertidumbre_futuro = models.CharField(max_length=255, blank=True, null=True)
    cambios_positivos = models.CharField(max_length=255, blank=True, null=True)
    proposito_vida = models.CharField(max_length=255, blank=True, null=True)
    esperanza = models.CharField(max_length=255, blank=True, null=True)
    estado_espiritual = models.CharField(max_length=255, blank=True, null=True)

    puntaje_total = models.IntegerField(default=0)

    def __str__(self):
        return f"Betty Ferrel - {self.visita_examen}"


class PuntajeCDRResult(ResultadoExamenBase):
    cdr_memoria = models.CharField(max_length=10)
    cdr_orientacion = models.CharField(max_length=10)
    cdr_juicio = models.CharField(max_length=10)
    cdr_comunitarias = models.CharField(max_length=10)
    cdr_pasatiempos = models.CharField(max_length=10)
    cdr_cuidado = models.CharField(max_length=10)
    cdr_global = models.CharField(max_length=10)

    def __str__(self):
        return f"CDR - {self.visita_examen_id}"


class ConsentimientoInformadoParticipanteResult(ResultadoExamenBase):
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    investigador = models.CharField(max_length=255)
    version_consentimiento = models.CharField(max_length=50)
    descripcion_proceso = models.TextField(blank=True, null=True)
    preguntas = models.TextField(blank=True, null=True)
    acepta = models.CharField(max_length=10)  # "Si" o "No"
    hora_firma = models.TimeField()
    fecha_firma = models.DateField()
    testigo1 = models.CharField(max_length=255, blank=True, null=True)
    testigo2 = models.CharField(max_length=255, blank=True, null=True)
    copia_entregada = models.CharField(max_length=10)  # "Si" o "No"
    hora_finalizacion = models.TimeField()

    def __str__(self):
        return f"Consentimiento Informado - {self.visita_examen_id}"


class ConsentimientoInformadoCuidadorResult(ResultadoExamenBase):
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    investigador = models.CharField(max_length=255)
    nombre_acompanante = models.CharField(max_length=255)
    nombre_participante = models.CharField(max_length=255)
    version_consentimiento = models.CharField(max_length=50)
    descripcion_proceso = models.TextField(blank=True, null=True)
    preguntas = models.TextField(blank=True, null=True)
    acepta = models.CharField(max_length=10)  # "Si" o "No"
    hora_firma = models.TimeField()
    fecha_firma = models.DateField()
    testigo1 = models.CharField(max_length=255, blank=True, null=True)
    testigo2 = models.CharField(max_length=255, blank=True, null=True)
    copia_entregada = models.CharField(max_length=10)  # "Si" o "No"
    hora_finalizacion = models.TimeField()

    def __str__(self):
        return f"Consentimiento Informado - {self.visita_examen_id}"


class AnamnesisCuidadorResult(ResultadoExamenBase):
    nombres_apellidos = models.CharField(max_length=255)
    documento = models.CharField(max_length=100)  # Tipo y número
    lugar_nacimiento = models.CharField(max_length=255)
    lugar_procedencia = models.CharField(max_length=255)
    edad = models.IntegerField()
    sexo = models.CharField(max_length=20)
    estado_civil = models.CharField(max_length=50)
    relacion = models.CharField(max_length=100)
    tiempo_acompanando = models.CharField(max_length=100)
    ocupacion = models.CharField(max_length=255, blank=True, null=True)
    escolaridad = models.CharField(max_length=100, blank=True, null=True)
    ingresos_hogar = models.CharField(max_length=50)
    estrato = models.CharField(max_length=20)
    religion = models.CharField(max_length=100, blank=True, null=True)
    lateralidad = models.CharField(max_length=50, blank=True, null=True)
    convivencia = models.TextField(blank=True, null=True)
    eps = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Anamnesis Cuidador - {self.visita_examen_id}"


class AnamnesisParticipanteResult(ResultadoExamenBase):
    nombres_apellidos = models.CharField(max_length=255)
    documento = models.CharField(max_length=100)  # Tipo y número
    lugar_nacimiento = models.CharField(max_length=255)
    edad = models.IntegerField()
    sexo = models.CharField(max_length=20)
    tiempo_acompanando = models.CharField(max_length=100)
    ingresos_hogar = models.CharField(max_length=50)
    estrato = models.CharField(max_length=20)
    religion = models.CharField(max_length=100, blank=True, null=True)
    lateralidad = models.CharField(max_length=50, blank=True, null=True)
    convivencia = models.TextField(blank=True, null=True)
    eps = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Anamnesis Participante - {self.visita_examen_id}"


class SeguimientoIntervencionesResult(models.Model):
    visita_examen = models.ForeignKey(
        "VisitaExamen", on_delete=models.CASCADE, related_name="seguimientointervencionesresult_resultado"
    )
    numero_sesion = models.IntegerField()  # 1–24
    nombre_sesion = models.CharField(max_length=200, blank=True, null=True)
    fecha = models.DateField(blank=True, null=True)
    hora_inicio = models.TimeField(blank=True, null=True)
    hora_fin = models.TimeField(blank=True, null=True)

    ASISTENCIA_CHOICES = [
        ("Sí", "Sí"),
        ("No", "No"),
    ]
    asistencia = models.CharField(
        max_length=2, choices=ASISTENCIA_CHOICES, blank=True, null=True
    )

    participacion = models.IntegerField(blank=True, null=True)  # escala 1–5

    ESTADO_CHOICES = [
        ("Motivado", "Motivado"),
        ("Apático", "Apático"),
        ("Fatigado", "Fatigado"),
        ("Ansioso", "Ansioso"),
        ("Otro", "Otro"),
    ]
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, blank=True, null=True
    )

    tematica = models.CharField(max_length=200, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("visita_examen", "numero_sesion")  # ✅ evita duplicados

    def __str__(self):
        return f"Sesión {self.numero_sesion} - {self.visita_examen}"


#### INTEGRACIÓN RECUÉRDAME


class InteractionMetric(models.Model):
    event = models.CharField(max_length=255)
    distinct_id = models.CharField(max_length=255)
    timestamp = models.DateTimeField()
    properties = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event} - {self.timestamp}"
    
class EstadisticasUsuarioResult(models.Model):
    email = models.EmailField()
    ingresos = models.IntegerField(default=0)  # user_values
    sesiones_ingresadas = models.IntegerField(default=0)
    sesiones_convertidas = models.IntegerField(default=0)
    sesiones_abandonadas = models.IntegerField(default=0)
    conversion_rate = models.FloatField(default=0.0)
    tiempo_promedio = models.CharField(max_length=50, blank=True, null=True)
    tiempo_mediano = models.CharField(max_length=50, blank=True, null=True)
    total_clicks = models.IntegerField(default=0)

    def __str__(self):
        return f"Estadísticas Usuario - {self.email}"


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
    confirmado_nuevo = models.BooleanField(default=False)
    confirmado_antiguo = models.BooleanField(default=False)
    en_estudio = models.BooleanField(default=False)

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
    confirmado_nuevo = models.BooleanField(default=False)
    confirmado_antiguo = models.BooleanField(default=False)
    en_estudio = models.BooleanField(default=False)

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
        DatosDemograficos,
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
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    creado_por = models.CharField(max_length=100, blank=True, null=True)
    actualizado_por = models.CharField(max_length=100, blank=True, null=True)

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
    fue_revisado = models.BooleanField(default=False)
    fue_actualizado = models.BooleanField(default=False)
    notas_visita = models.TextField(
        blank=True, null=True, verbose_name="Notas específicas de esta visita"
    )

    fecha_revision = models.DateTimeField(auto_now=True)
    revisado_por = models.CharField(max_length=100, blank=True, null=True)

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
    """Antecedentes Farmacológicos"""

    antecedente_result = models.ForeignKey(
        AntecedentesResult,
        on_delete=models.CASCADE,
        related_name="antecedentes_farmacologicos",
    )
    descripcion = models.CharField(
        max_length=200, verbose_name="Descripción del Medicamento/Reacción"
    )
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    recibio_tratamiento = models.BooleanField(
        default=False, verbose_name="¿Recibió tratamiento?"
    )
    detalle_tratamiento = models.TextField(
        blank=True, null=True, verbose_name="Detalle del Tratamiento"
    )
    tuvo_complicaciones = models.BooleanField(
        default=False, verbose_name="¿Tuvo complicaciones?"
    )
    detalle_complicaciones = models.TextField(
        blank=True, null=True, verbose_name="Detalle de Complicaciones"
    )
    activo = models.BooleanField(default=True, verbose_name="¿Está activo?")
    fecha_finalizacion = models.DateField(
        blank=True, null=True, verbose_name="Fecha de Finalización"
    )
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Antecedente Farmacológico"
        verbose_name_plural = "Antecedentes Farmacológicos"

    def __str__(self):
        return f"{self.descripcion} - {self.fecha_inicio}"


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

    # ===== II PAR CRANEAL (ÓPTICO) =====
    agudeza_visual_alterada = models.BooleanField(
        default=False, verbose_name="Agudeza Visual Alterada"
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

    FUNDOSCOPIA_CHOICES = [
        ("normal", "Normal"),
        ("anormal", "Anormal"),
    ]

    fundoscopia = models.CharField(
        max_length=10,
        choices=FUNDOSCOPIA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Fundoscopia",
    )

    # ===== III, IV y VI PAR CRANEAL (OCULOMOTORES) =====
    diplopia = models.BooleanField(default=False, verbose_name="Diplopía presente")

    ptosis_palpebral = models.BooleanField(
        default=False, verbose_name="Ptosis palpebral presente"
    )

    MOVIMIENTOS_CHOICES = [
        ("normal", "Normal"),
        ("anormal", "Anormal"),
    ]

    movimientos_oculares = models.CharField(
        max_length=10,
        choices=MOVIMIENTOS_CHOICES,
        blank=True,
        null=True,
        verbose_name="Movimientos Oculares",
    )

    # ===== V PAR CRANEAL (TRIGÉMINO) =====
    # Tacto superficial
    tacto_frente = models.BooleanField(
        default=False, verbose_name="Tacto superficial - Frente/globo ocular alterado"
    )
    tacto_parpado = models.BooleanField(
        default=False,
        verbose_name="Tacto superficial - Párpado inferior/labio superior alterado",
    )
    tacto_labio = models.BooleanField(
        default=False, verbose_name="Tacto superficial - Labio inferior/mentón alterado"
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

    # ===== VII PAR CRANEAL (FACIAL) =====
    # Mímica facial
    mimica_frente = models.BooleanField(
        default=False, verbose_name="Mímica facial - Frente alterada"
    )
    mimica_parpados = models.BooleanField(
        default=False, verbose_name="Mímica facial - Párpados alterada"
    )
    mimica_nasal = models.BooleanField(
        default=False, verbose_name="Mímica facial - Elevación nasal alterada"
    )

    gusto_tercio_anterior = models.CharField(
        max_length=10,
        choices=MOVIMIENTOS_CHOICES,
        blank=True,
        null=True,
        verbose_name="Gusto tercio anterior de la lengua",
    )

    # ===== VIII PAR CRANEAL (AUDITIVO) =====
    weber = models.CharField(
        max_length=10,
        choices=MOVIMIENTOS_CHOICES,
        blank=True,
        null=True,
        verbose_name="Prueba de Weber",
    )

    rinne = models.CharField(
        max_length=10,
        choices=MOVIMIENTOS_CHOICES,
        blank=True,
        null=True,
        verbose_name="Prueba de Rinne",
    )

    nistagmus = models.BooleanField(default=False, verbose_name="Nistagmus presente")

    # ===== IX y X PAR CRANEAL (GLOSOFARÍNGEO Y VAGO) =====
    reflejo_nauseoso = models.CharField(
        max_length=10,
        choices=MOVIMIENTOS_CHOICES,
        blank=True,
        null=True,
        verbose_name="Reflejo nauseoso",
    )

    posicion_uvula = models.CharField(
        max_length=10,
        choices=MOVIMIENTOS_CHOICES,
        blank=True,
        null=True,
        verbose_name="Posición de la úvula",
    )

    # ===== XI PAR CRANEAL (ESPINAL ACCESORIO) =====
    elevacion_hombros = models.CharField(
        max_length=10,
        choices=MOVIMIENTOS_CHOICES,
        blank=True,
        null=True,
        verbose_name="Elevación de hombros",
    )

    # ===== XII PAR CRANEAL (HIPOGLOSO) =====
    movimientos_lengua = models.CharField(
        max_length=10,
        choices=MOVIMIENTOS_CHOICES,
        blank=True,
        null=True,
        verbose_name="Movimientos de la lengua",
    )

    # ===== SENSIBILIDAD =====
    # Dolor al pinchazo
    dolor_cuello = models.BooleanField(
        default=False, verbose_name="Dolor al pinchazo - Cuello alterado"
    )
    dolor_torax = models.BooleanField(
        default=False, verbose_name="Dolor al pinchazo - Tórax alterado"
    )
    dolor_brazo_izquierdo = models.BooleanField(
        default=False, verbose_name="Dolor al pinchazo - Brazo izquierdo alterado"
    )
    dolor_brazo_derecho = models.BooleanField(
        default=False, verbose_name="Dolor al pinchazo - Brazo derecho alterado"
    )
    dolor_pierna_izquierda = models.BooleanField(
        default=False, verbose_name="Dolor al pinchazo - Pierna izquierda alterada"
    )
    dolor_pierna_derecha = models.BooleanField(
        default=False, verbose_name="Dolor al pinchazo - Pierna derecha alterada"
    )

    # Táctil superficial
    tactil_cuello = models.BooleanField(
        default=False, verbose_name="Táctil superficial - Cuello alterado"
    )
    tactil_torax = models.BooleanField(
        default=False, verbose_name="Táctil superficial - Tórax alterado"
    )
    tactil_brazo_izquierdo = models.BooleanField(
        default=False, verbose_name="Táctil superficial - Brazo izquierdo alterado"
    )
    tactil_brazo_derecho = models.BooleanField(
        default=False, verbose_name="Táctil superficial - Brazo derecho alterado"
    )
    tactil_pierna_izquierda = models.BooleanField(
        default=False, verbose_name="Táctil superficial - Pierna izquierda alterada"
    )
    tactil_pierna_derecha = models.BooleanField(
        default=False, verbose_name="Táctil superficial - Pierna derecha alterada"
    )

    # Térmica
    termica_cuello = models.BooleanField(
        default=False, verbose_name="Sensibilidad térmica - Cuello alterada"
    )
    termica_torax = models.BooleanField(
        default=False, verbose_name="Sensibilidad térmica - Tórax alterado"
    )
    termica_brazo_izquierdo = models.BooleanField(
        default=False, verbose_name="Sensibilidad térmica - Brazo izquierdo alterada"
    )
    termica_brazo_derecho = models.BooleanField(
        default=False, verbose_name="Sensibilidad térmica - Brazo derecho alterada"
    )
    termica_pierna_izquierda = models.BooleanField(
        default=False, verbose_name="Sensibilidad térmica - Pierna izquierda alterada"
    )
    termica_pierna_derecha = models.BooleanField(
        default=False, verbose_name="Sensibilidad térmica - Pierna derecha alterada"
    )

    # ===== REFLEJOS =====
    REFLEJO_CHOICES = [
        ("0", "0. Sin respuesta"),
        ("1", "1. Disminuido"),
        ("2", "2. Normal"),
        ("3", "3. Aumentado"),
        ("4", "4. Clonus agotable"),
        ("5", "5. Clonus permanente"),
    ]

    # Maseteriano
    maseteriano_izquierdo = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        default="2",
        verbose_name="Reflejo maseteriano izquierdo",
    )
    maseteriano_derecho = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        default="2",
        verbose_name="Reflejo maseteriano derecho",
    )

    # Bicipital
    bicipital_izquierdo = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        default="2",
        verbose_name="Reflejo bicipital izquierdo",
    )
    bicipital_derecho = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        default="2",
        verbose_name="Reflejo bicipital derecho",
    )

    # Tricipital
    tricipital_izquierdo = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        default="2",
        verbose_name="Reflejo tricipital izquierdo",
    )
    tricipital_derecho = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        default="2",
        verbose_name="Reflejo tricipital derecho",
    )

    # Estiloradial
    estiloradial_izquierdo = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        default="2",
        verbose_name="Reflejo estiloradial izquierdo",
    )
    estiloradial_derecho = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        default="2",
        verbose_name="Reflejo estiloradial derecho",
    )

    # Rotuliano
    rotuliano_izquierdo = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        default="2",
        verbose_name="Reflejo rotuliano izquierdo",
    )
    rotuliano_derecho = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        default="2",
        verbose_name="Reflejo rotuliano derecho",
    )

    # Aquiliano
    aquiliano_izquierdo = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        default="2",
        verbose_name="Reflejo aquiliano izquierdo",
    )
    aquiliano_derecho = models.CharField(
        max_length=1,
        choices=REFLEJO_CHOICES,
        default="2",
        verbose_name="Reflejo aquiliano derecho",
    )

    # ===== OBSERVACIONES GENERALES =====
    observaciones_pares_craneales = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Pares Craneales"
    )

    observaciones_sensibilidad = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Sensibilidad"
    )

    observaciones_reflejos = models.TextField(
        blank=True, null=True, verbose_name="Observaciones Reflejos"
    )

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
