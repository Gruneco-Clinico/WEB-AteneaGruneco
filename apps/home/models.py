# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.urls import reverse, NoReverseMatch
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


class Sala(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    capacidad = models.PositiveIntegerField(default=1)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sala"
        verbose_name_plural = "Salas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class DisponibilidadUsuario(models.Model):
    DIAS_SEMANA = [
        (0, "Lunes"),
        (1, "Martes"),
        (2, "Miércoles"),
        (3, "Jueves"),
        (4, "Viernes"),
        (5, "Sábado"),
        (6, "Domingo"),
    ]

    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="disponibilidades"
    )
    sala = models.ForeignKey(
        Sala, on_delete=models.CASCADE, related_name="disponibilidades"
    )
    dia_semana = models.IntegerField(choices=DIAS_SEMANA)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    @property
    def esta_disponible_para_fecha(self, fecha):
        """Verificar si está disponible en una fecha específica"""
        # Verificar que sea el día correcto de la semana
        if fecha.weekday() != self.dia_semana:
            return False

        # Verificar que esté en el rango de fechas válidas
        if fecha < self.fecha_inicio:
            return False

        if self.fecha_fin and fecha > self.fecha_fin:
            return False

        # Verificar que no hay cita agendada para esa fecha
        return not CitaMedica.objects.filter(
            disponibilidad=self, fecha_cita=fecha, estado__in=["agendada", "confirmada"]
        ).exists()

    class Meta:
        verbose_name = "Disponibilidad de Usuario"
        verbose_name_plural = "Disponibilidades de Usuarios"
        unique_together = ["usuario", "sala", "dia_semana", "hora_inicio"]
        ordering = ["dia_semana", "hora_inicio"]

    def clean(self):
        if self.hora_inicio >= self.hora_fin:
            raise ValidationError("La hora de inicio debe ser menor que la hora de fin")

        if self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValidationError(
                "La fecha de inicio debe ser menor que la fecha de fin"
            )

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} - {self.sala.nombre} - {self.get_dia_semana_display()} ({self.hora_inicio}-{self.hora_fin})"


class CitaMedica(models.Model):
    ESTADO_CHOICES = [
        ("agendada", "Agendada"),
        ("confirmada", "Confirmada"),
        ("completada", "Completada"),
        ("cancelada", "Cancelada"),
        ("no_asistio", "No asistió"),
    ]

    # Relación con la disponibilidad (plantilla)
    disponibilidad = models.ForeignKey(
        DisponibilidadUsuario, on_delete=models.CASCADE, related_name="citas"
    )

    # Fecha y hora específicas
    fecha_cita = models.DateField()
    # La hora se toma de disponibilidad.hora_inicio y disponibilidad.hora_fin

    # Datos del paciente
    email_paciente = models.EmailField()
    nombre_paciente = models.CharField(max_length=200)
    telefono_paciente = models.CharField(max_length=20, blank=True)
    motivo_consulta = models.TextField(blank=True)

    # Control
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="agendada")
    fecha_agendamiento = models.DateTimeField(auto_now_add=True)

    # Propiedades de conveniencia
    @property
    def hora_inicio(self):
        return self.disponibilidad.hora_inicio

    @property
    def hora_fin(self):
        return self.disponibilidad.hora_fin

    @property
    def profesional(self):
        return self.disponibilidad.usuario

    @property
    def sala(self):
        return self.disponibilidad.sala

    class Meta:
        unique_together = ["disponibilidad", "fecha_cita"]

    def __str__(self):
        return f"{self.nombre_paciente} - {self.fecha_cita} {self.hora_inicio}"


class BloqueoDisponibilidad(models.Model):
    disponibilidad = models.ForeignKey(
        DisponibilidadUsuario, on_delete=models.CASCADE, related_name="bloqueos"
    )
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    motivo = models.CharField(max_length=200, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bloqueo de Disponibilidad"
        verbose_name_plural = "Bloqueos de Disponibilidad"

    def __str__(self):
        return f"Bloqueo: {self.disponibilidad} - {self.fecha}"


class CustomUser(AbstractUser):
    # Campos adicionales
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    firma = models.TextField(blank=True, null=True)
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


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    firma = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.username
    
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
        verbose_name="Código del Paciente",
    )

    def __str__(self):
        return f"{self.primer_nombre} {self.primer_apellido} "

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
        "DatosDemograficos",
        related_name="proyectos",
        verbose_name="Pacientes",
    )

    def __str__(self):
        return self.nombre


class ProyectoPacienteExtra(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE)
    paciente = models.ForeignKey(DatosDemograficos, on_delete=models.CASCADE)

    codigo_proyecto = models.CharField(max_length=20)

    class Meta:
        unique_together = ("proyecto", "paciente")


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
    evaluador = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="visitas_evaluador"
    )

    estado_visita = models.CharField(
        max_length=20,
        choices=[
            ("abierta", "Abierta"),
            ("cerrada", "Cerrada"),
        ],
        default="abierta",
    )

    # Indica si la visita fue firmada (no se podrán editar exámenes relacionados si es True)
    firmado = models.BooleanField(default=False, verbose_name="Firmado")
    firmado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="visitas_firmadas"
    )

    acompanante_nombre = models.CharField(max_length=255, blank=True, null=True)
    acompanante_relacion = models.CharField(max_length=100, blank=True, null=True)
    acompanante_correo = models.EmailField(blank=True, null=True)
    acompanante_telefono = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        if self.Tipo_visita and self.Tipo_visita.proyecto:
            return f"{self.nombre} - {self.Tipo_visita.proyecto.nombre}"
        return self.nombre

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.Tipo_visita:
            return

        if not self.Tipo_visita.proyecto:
            return

        if (
            self.Tipo_visita.proyecto.nombre == "Anosognosia"
            and self.Tipo_visita.nombre == "PosIntervención"
        ):
            paciente = self.paciente

            if not paciente:
                return

            if paciente.codigo:
                return

            ultimo = (
                DatosDemograficos.objects.exclude(codigo__isnull=True)
                .exclude(codigo__exact="")
                .order_by("-codigo")
                .first()
            )

            if ultimo and ultimo.codigo:
                try:
                    numero = int(ultimo.codigo.split("-")[1])
                except Exception:
                    numero = 0
            else:
                numero = 0

            nuevo_codigo = f"ANG-{numero + 1:03d}"
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
                    pass
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
                "analisisgeneralresult_resultado",  # ✅ ANÁLISIS GENERAL
                "examenfisicoresult_resultado",  # ✅ EXAMEN FÍSICO
                "examenneurologicoresult_resultado",  # ✅ EXAMEN NEUROLÓGICO
                "medicamentosresult_resultado",  # ✅ MEDICAMENTOS
                "revisionsistemrasresult_resultado",  # ✅ REVISIÓN SISTEMAS
                "cognitivo_anamnesis_resultado",  # ✅ COGNITIVO ANAMNESIS
                # este examen es problemático dejar al final
                "seguimientointervencionesresult_resultado",
            ]

            # 🔧 CORRECCIÓN PRINCIPAL: Manejar el RelatedManager correctamente
            for related_name in possible_related_names:
                try:
                    # Obtener el manager relacionado
                    manager = getattr(self, related_name)

                    # 🔧 NUEVO: Si es un manager, obtener la instancia con .get()
                    if hasattr(manager, "get"):
                        try:
                            resultado_instance = manager.get()
                            if resultado_instance:
                                self._resultado_cache = resultado_instance

                                break
                        except manager.model.DoesNotExist:
                            continue
                        except Exception as e:
                            continue
                    # Si no es un manager, manejar como antes
                    elif manager:
                        self._resultado_cache = manager

                        break

                except AttributeError:
                    # El related_name no existe en este modelo
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
        # Solo puede editarse si la visita está abierta, NO está firmada Y el examen está realizado
        visita_abierta = self.visita.estado_visita == "abierta"
        visita_no_firmada = not self.visita.firmado
        examen_realizado = self.esta_realizado

        puede_editar = visita_abierta and visita_no_firmada and examen_realizado

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
            "cognitivoanamnesis": "realizar_cognitivo_anamnesis",
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
            "cognitivoanamnesis": "ver_cognitivo_anamnesis",
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
            "cognitivoanamnesis": "editar_cognitivo_anamnesis",
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
    diagnostico = models.CharField(max_length=100, verbose_name="Diagnóstico")

    def __str__(self):
        return f"Lawton & Brody - {self.visita_examen_id}"


class CuidadorNPIResult(ResultadoExamenBase):
    ideas_delirantes = models.CharField(
        max_length=5,
        choices=[("si", "Sí"), ("no", "No"), ("ns", "No Sabe")],
        blank=True,
        null=True,
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
    )
    apetito_frecuencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Frecuencia problemas de apetito")
    apetito_gravedad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Gravedad problemas de apetito")
    apetito_F_G = models.IntegerField(blank=True, null=True, verbose_name="F x G apetito")
    apetito_distres = models.CharField(max_length=50, blank=True, null=True, verbose_name="Distrés apetito")

    puntaje_total = models.IntegerField(blank=True, null=True, default=0, verbose_name="Puntaje total")
    carga_total = models.IntegerField(blank=True, null=True, default=0, verbose_name="Carga total")

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
    recordar_fecha = models.CharField(max_length=50, blank=True, null=True, verbose_name="Recordar fecha")
    orientacion_lugares_nuevos = models.CharField(max_length=50, blank=True, null=True, verbose_name="Orientación en lugares nuevos")
    recordar_llamadas = models.CharField(max_length=50, blank=True, null=True, verbose_name="Recordar llamadas")
    entender_conversacion = models.CharField(max_length=50, blank=True, null=True, verbose_name="Entender conversación")
    firmar = models.CharField(max_length=50, blank=True, null=True, verbose_name="Firmar")
    entender_lectura = models.CharField(max_length=50, blank=True, null=True, verbose_name="Entender lectura")
    mantener_orden = models.CharField(max_length=50, blank=True, null=True, verbose_name="Mantener orden")
    recordar_lugar_objetos = models.CharField(max_length=50, blank=True, null=True, verbose_name="Recordar lugar de objetos")
    escribir = models.CharField(max_length=50, blank=True, null=True, verbose_name="Escribir")
    manejar_dinero = models.CharField(max_length=50, blank=True, null=True, verbose_name="Manejar dinero")
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
    recordar_fecha = models.CharField(max_length=50, blank=True, null=True, verbose_name="Recordar fecha")
    orientacion_lugares_nuevos = models.CharField(max_length=50, blank=True, null=True, verbose_name="Orientación en lugares nuevos")
    recordar_llamadas = models.CharField(max_length=50, blank=True, null=True, verbose_name="Recordar llamadas")
    entender_conversacion = models.CharField(max_length=50, blank=True, null=True, verbose_name="Entender conversación")
    firmar = models.CharField(max_length=50, blank=True, null=True, verbose_name="Firmar")
    entender_lectura = models.CharField(max_length=50, blank=True, null=True, verbose_name="Entender lectura")
    mantener_orden = models.CharField(max_length=50, blank=True, null=True, verbose_name="Mantener orden")
    recordar_lugar_objetos = models.CharField(max_length=50, blank=True, null=True, verbose_name="Recordar lugar de objetos")
    escribir = models.CharField(max_length=50, blank=True, null=True, verbose_name="Escribir")
    manejar_dinero = models.CharField(max_length=50, blank=True, null=True, verbose_name="Manejar dinero")
    orientacion_zona_donde_vive = models.CharField(max_length=50, blank=True, null=True, verbose_name="Orientación en zona donde vive")
    recordar_citas = models.CharField(max_length=50, blank=True, null=True, verbose_name="Recordar citas")
    pasatiempos = models.CharField(max_length=50, blank=True, null=True, verbose_name="Pasatiempos")
    comunicarse_con_gente = models.CharField(max_length=50, blank=True, null=True, verbose_name="Comunicarse con gente")
    calculos_mentales = models.CharField(max_length=50, blank=True, null=True, verbose_name="Cálculos mentales")
    recordar_compras = models.CharField(max_length=50, blank=True, null=True, verbose_name="Recordar compras")
    contener_orina = models.CharField(max_length=50, blank=True, null=True, verbose_name="Contener orina")
    entender_pelicula = models.CharField(max_length=50, blank=True, null=True, verbose_name="Entender película")
    orientacion_en_casa = models.CharField(max_length=50, blank=True, null=True, verbose_name="Orientación en casa")
    hacer_tareas_hogar = models.CharField(max_length=50, blank=True, null=True, verbose_name="Hacer tareas del hogar")
    comer_solo = models.CharField(max_length=50, blank=True, null=True, verbose_name="Comer solo")
    realizar_tramites = models.CharField(max_length=50, blank=True, null=True, verbose_name="Realizar trámites")
    decisiones_y_adaptacion = models.CharField(max_length=50, blank=True, null=True, verbose_name="Decisiones y adaptación")
    egoismo = models.CharField(max_length=50, blank=True, null=True, verbose_name="Egoísmo")
    enojo_menos_paciencia = models.CharField(max_length=50, blank=True, null=True, verbose_name="Enojo y menos paciencia")
    llorar_con_facilidad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Llorar con facilidad")
    reir_situaciones_inapropiadas = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Reír en situaciones inapropiadas"
    )
    temas_sexuales = models.CharField(max_length=50, blank=True, null=True, verbose_name="Temas sexuales")
    falta_de_interes = models.CharField(max_length=50, blank=True, null=True, verbose_name="Falta de interés")
    deprimido = models.CharField(max_length=50, blank=True, null=True, verbose_name="Deprimido")

    # Puntaje total
    # puntaje_total = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"AQ-D Participante - {self.visita_examen_id}"


class CDRCuidadorResult(ResultadoExamenBase):
    # ====================
    # Dominio: Memoria
    # ====================
    memoria_p1 = models.CharField(max_length=100, blank=True, null=True, verbose_name="Memoria pregunta 1")  # sí/no
    memoria_p1_1 = models.CharField(
        max_length=10, blank=True, null=True, verbose_name="Memoria pregunta 1.1"
    )  # sí/no, subpregunta
    memoria_p2 = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="Memoria pregunta 2"
    )  # generalmente/a_veces/raramente
    memoria_p3 = models.CharField(max_length=200, blank=True, null=True, verbose_name="Memoria pregunta 3")
    memoria_p4 = models.CharField(max_length=100, blank=True, null=True, verbose_name="Memoria pregunta 4")  # sí/no
    memoria_p5 = models.CharField(max_length=100, blank=True, null=True, verbose_name="Memoria pregunta 5")  # sí/no
    memoria_p6 = models.CharField(max_length=200, blank=True, null=True, verbose_name="Memoria pregunta 6")
    memoria_p7 = models.CharField(max_length=200, blank=True, null=True, verbose_name="Memoria pregunta 7")
    memoria_p8 = models.CharField(max_length=200, blank=True, null=True, verbose_name="Memoria pregunta 8")

    # Evento reciente (respuestas abiertas)
    evento_recuerda_semana = models.TextField(blank=True, null=True, verbose_name="Evento que recuerda de la semana")
    evento_recuerda_mes = models.TextField(blank=True, null=True, verbose_name="Evento que recuerda del mes")

    # Datos personales
    nacimiento_fecha = models.DateField(blank=True, null=True, verbose_name="Fecha de nacimiento")
    nacimiento_lugar = models.CharField(max_length=150, blank=True, null=True, verbose_name="Lugar de nacimiento")
    colegio_nombre = models.CharField(max_length=150, blank=True, null=True, verbose_name="Nombre del colegio")
    colegio_lugar = models.CharField(max_length=150, blank=True, null=True, verbose_name="Lugar del colegio")
    colegio_grado = models.CharField(max_length=100, blank=True, null=True, verbose_name="Grado escolar")
    ocupacion_principal = models.CharField(max_length=150, blank=True, null=True, verbose_name="Ocupación principal")
    ultimo_trabajo = models.CharField(max_length=150, blank=True, null=True, verbose_name="Último trabajo")
    jubilacion = models.TextField(blank=True, null=True, verbose_name="Jubilación")

    # ====================
    # Dominio: Orientación
    # ====================
    orientacion_p1 = models.CharField(max_length=200, blank=True, null=True, verbose_name="Orientación pregunta 1")
    orientacion_p2 = models.CharField(max_length=200, blank=True, null=True, verbose_name="Orientación pregunta 2")
    orientacion_p3 = models.CharField(max_length=200, blank=True, null=True, verbose_name="Orientación pregunta 3")
    orientacion_p4 = models.CharField(max_length=200, blank=True, null=True, verbose_name="Orientación pregunta 4")
    orientacion_p5 = models.CharField(max_length=200, blank=True, null=True, verbose_name="Orientación pregunta 5")
    orientacion_p6 = models.CharField(max_length=200, blank=True, null=True, verbose_name="Orientación pregunta 6")
    orientacion_p7 = models.CharField(max_length=200, blank=True, null=True, verbose_name="Orientación pregunta 7")
    orientacion_p8 = models.CharField(max_length=200, blank=True, null=True, verbose_name="Orientación pregunta 8")

    # ====================
    # Dominio: Juicio y resolución de problemas
    # ====================
    juicio_p1 = models.CharField(max_length=100, blank=True, null=True, verbose_name="Juicio pregunta 1")
    juicio_p2 = models.CharField(max_length=100, blank=True, null=True, verbose_name="Juicio pregunta 2")
    juicio_p3 = models.CharField(max_length=100, blank=True, null=True, verbose_name="Juicio pregunta 3")
    juicio_p4 = models.CharField(max_length=150, blank=True, null=True, verbose_name="Juicio pregunta 4")
    juicio_p5 = models.CharField(max_length=500, blank=True, null=True, verbose_name="Juicio pregunta 5")
    juicio_p6 = models.CharField(max_length=500, blank=True, null=True, verbose_name="Juicio pregunta 6")

    # ====================
    # Actividades comunitarias
    # ====================
    trabaja_actualmente = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Trabaja actualmente"
    )  # na/si/no
    memoria_causa_jubilacion = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Memoria como causa de jubilación"
    )  # si/no/nose
    dificultades_trabajo_memoria = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Dificultades en el trabajo por memoria"
    )

    condujo_alguna_vez = models.CharField(max_length=50, blank=True, null=True, verbose_name="Condujo alguna vez")  # si/no
    conduce_actualmente = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Conduce actualmente"
    )  # si/no
    dejo_de_conducir_por_memoria = models.CharField(
        max_length=5, blank=True, null=True, verbose_name="Dejó de conducir por memoria"
    )  # si/no
    riesgos_conduccion = models.CharField(max_length=50, blank=True, null=True, verbose_name="Riesgos de conducción")  # si/no

    compras_independientes = models.CharField(max_length=50, blank=True, null=True, verbose_name="Compras independientes")
    actividades_fuera_hogar = models.CharField(max_length=50, blank=True, null=True, verbose_name="Actividades fuera del hogar")
    asiste_funciones_sociales = models.CharField(
        max_length=5, blank=True, null=True, verbose_name="Asiste a funciones sociales"
    )  # si/no
    motivo_no_funciones = models.TextField(blank=True, null=True, verbose_name="Motivo de no asistir a funciones")

    parece_enfermo = models.CharField(max_length=5, blank=True, null=True, verbose_name="Parece enfermo")  # si/no
    participa_hogar_geriatrico = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Participa en hogar geriátrico"
    )  # si/no
    info_suficiente_comunitarias = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Información suficiente sobre actividades comunitarias"
    )  # si/no
    notas_comunitarias = models.TextField(blank=True, null=True, verbose_name="Notas sobre actividades comunitarias")

    # ====================
    # Actividades domésticas y pasatiempos
    # ====================
    cambios_tareas_domesticas = models.TextField(blank=True, null=True, verbose_name="Cambios en tareas domésticas")
    cosas_que_aun_realiza_domesticas = models.TextField(blank=True, null=True, verbose_name="Cosas que aún realiza (domésticas)")
    cambios_pasatiempos = models.TextField(blank=True, null=True, verbose_name="Cambios en pasatiempos")
    cosas_que_aun_realiza_pasatiempos = models.TextField(blank=True, null=True, verbose_name="Cosas que aún realiza (pasatiempos)")
    actividades_no_realiza_en_hogar = models.TextField(blank=True, null=True, verbose_name="Actividades que no realiza en el hogar")

    habilidad_domestica_dementia_scale = models.TextField(blank=True, null=True, verbose_name="Habilidad doméstica (escala de demencia)")
    descripcion_habilidad_domestica = models.TextField(blank=True, null=True, verbose_name="Descripción de habilidad doméstica")
    nivel_desempeno_domestico = models.CharField(max_length=2000, blank=True, null=True, verbose_name="Nivel de desempeño doméstico")
    notas_domesticas_pasatiempos = models.TextField(blank=True, null=True, verbose_name="Notas sobre actividades domésticas y pasatiempos")

    # ====================
    # Cuidado personal
    # ====================
    cuidado_p1 = models.TextField(blank=True, null=True, verbose_name="Vestirse")  # Vestirse
    cuidado_p2 = models.TextField(blank=True, null=True, verbose_name="Lavado y aseo")  # Lavado/aseo
    cuidado_p3 = models.TextField(blank=True, null=True, verbose_name="Alimentación")  # Alimentación
    cuidado_p4 = models.TextField(blank=True, null=True, verbose_name="Control de esfínteres")  # Control de esfínteres

    def __str__(self):
        return f"CDR Cuidador - {self.visita_examen_id}"


class CDRParticipanteResult(ResultadoExamenBase):
    # ====================
    # Dominio: Memoria
    # ====================
    memoria_p1 = models.CharField(max_length=5, blank=True, null=True, verbose_name="Memoria pregunta 1")  # si/no

    evento_recuerda_semana = models.TextField(blank=True, null=True, verbose_name="Evento que recuerda de la semana")
    memoria_semana_calificacion = models.TextField(blank=True, null=True, verbose_name="Calificación memoria de la semana")

    evento_recuerda_mes = models.TextField(blank=True, null=True, verbose_name="Evento que recuerda del mes")
    memoria_mes_calificacion = models.TextField(blank=True, null=True, verbose_name="Calificación memoria del mes")

    # Ensayos (checkboxes del nombre/dirección)
    ensayo1_juan = models.BooleanField(default=False, verbose_name="Ensayo 1: Juan")
    ensayo1_perez = models.BooleanField(default=False, verbose_name="Ensayo 1: Pérez")
    ensayo1_calle = models.BooleanField(default=False, verbose_name="Ensayo 1: Calle")
    ensayo1_avenida = models.BooleanField(default=False, verbose_name="Ensayo 1: Avenida")
    ensayo1_cali = models.BooleanField(default=False, verbose_name="Ensayo 1: Cali")

    ensayo2_juan = models.BooleanField(default=False, verbose_name="Ensayo 2: Juan")
    ensayo2_perez = models.BooleanField(default=False, verbose_name="Ensayo 2: Pérez")
    ensayo2_calle = models.BooleanField(default=False, verbose_name="Ensayo 2: Calle")
    ensayo2_avenida = models.BooleanField(default=False, verbose_name="Ensayo 2: Avenida")
    ensayo2_cali = models.BooleanField(default=False, verbose_name="Ensayo 2: Cali")

    ensayo3_juan = models.BooleanField(default=False, verbose_name="Ensayo 3: Juan")
    ensayo3_perez = models.BooleanField(default=False, verbose_name="Ensayo 3: Pérez")
    ensayo3_calle = models.BooleanField(default=False, verbose_name="Ensayo 3: Calle")
    ensayo3_avenida = models.BooleanField(default=False, verbose_name="Ensayo 3: Avenida")
    ensayo3_cali = models.BooleanField(default=False, verbose_name="Ensayo 3: Cali")

    fecha_nacimiento = models.DateField(blank=True, null=True, verbose_name="Fecha de nacimiento")
    lugar_nacimiento = models.CharField(max_length=100, blank=True, null=True, verbose_name="Lugar de nacimiento")

    colegio_nombre = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nombre del colegio")
    colegio_lugar = models.CharField(max_length=100, blank=True, null=True, verbose_name="Lugar del colegio")
    colegio_grado = models.CharField(max_length=200, blank=True, null=True, verbose_name="Grado escolar")

    ocupacion_principal = models.CharField(max_length=150, blank=True, null=True, verbose_name="Ocupación principal")
    ultimo_trabajo = models.CharField(max_length=150, blank=True, null=True, verbose_name="Último trabajo")
    jubilacion = models.TextField(blank=True, null=True, verbose_name="Jubilación")

    # Repetición del nombre/dirección
    repeticion_juan = models.BooleanField(default=False, verbose_name="Repetición: Juan")
    repeticion_perez = models.BooleanField(default=False, verbose_name="Repetición: Pérez")
    repeticion_calle = models.BooleanField(default=False, verbose_name="Repetición: Calle")
    repeticion_avenida = models.BooleanField(default=False, verbose_name="Repetición: Avenida")
    repeticion_cali = models.BooleanField(default=False, verbose_name="Repetición: Cali")

    # ====================
    # Dominio: Orientación
    # ====================
    orientacion_p1 = models.CharField(
        max_length=15, blank=True, null=True, verbose_name="Orientación pregunta 1"
    )  # correcto/incorrecto
    orientacion_p2 = models.CharField(max_length=150, blank=True, null=True, verbose_name="Orientación pregunta 2")
    orientacion_p3 = models.CharField(max_length=150, blank=True, null=True, verbose_name="Orientación pregunta 3")
    orientacion_p4 = models.CharField(max_length=150, blank=True, null=True, verbose_name="Orientación pregunta 4")
    orientacion_p5 = models.CharField(max_length=500, blank=True, null=True, verbose_name="Orientación pregunta 5")
    orientacion_p6 = models.CharField(max_length=500, blank=True, null=True, verbose_name="Orientación pregunta 6")
    orientacion_p7 = models.CharField(max_length=150, blank=True, null=True, verbose_name="Orientación pregunta 7")
    orientacion_p8 = models.CharField(max_length=150, blank=True, null=True, verbose_name="Orientación pregunta 8")

    # ====================
    # Dominio: Juicio y resolución de problemas
    # ====================
    juicio_p1_respuesta = models.TextField(blank=True, null=True, verbose_name="Juicio P1 respuesta")
    juicio_p1_puntaje = models.IntegerField(blank=True, null=True, verbose_name="Juicio P1 puntaje")

    juicio_p2_respuesta = models.TextField(blank=True, null=True, verbose_name="Juicio P2 respuesta")
    juicio_p2_puntaje = models.IntegerField(blank=True, null=True, verbose_name="Juicio P2 puntaje")

    juicio_p3_respuesta = models.TextField(blank=True, null=True, verbose_name="Juicio P3 respuesta")
    juicio_p3_puntaje = models.IntegerField(blank=True, null=True, verbose_name="Juicio P3 puntaje")

    juicio_p4_respuesta = models.TextField(blank=True, null=True, verbose_name="Juicio P4 respuesta")
    juicio_p4_puntaje = models.IntegerField(blank=True, null=True, verbose_name="Juicio P4 puntaje")

    juicio_p5 = models.CharField(
        max_length=15,
        choices=[
            ("correcto", "Correcto"),
            ("incorrecto", "Incorrecto"),
        ],
        blank=True,
        null=True,
        verbose_name="Juicio pregunta 5",
    )

    juicio_p6 = models.CharField(
        max_length=15,
        choices=[
            ("correcto", "Correcto"),
            ("incorrecto", "Incorrecto"),
        ],
        blank=True,
        null=True,
        verbose_name="Juicio pregunta 6",
    )

    juicio_p7 = models.CharField(
        max_length=15,
        choices=[
            ("correcto", "Correcto"),
            ("incorrecto", "Incorrecto"),
        ],
        blank=True,
        null=True,
        verbose_name="Juicio pregunta 7",
    )

    juicio_p8_puntaje = models.IntegerField(blank=True, null=True, verbose_name="Juicio P8 puntaje")

    juicio_p9 = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Juicio P9 percepción"
    )  # Buena, parcial, poca percepción

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


# ...existing code...
