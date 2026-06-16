from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse, NoReverseMatch
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords

from .patient import DatosDemograficos


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
        'TipoVisita',
        on_delete=models.CASCADE,
        related_name="visitas",
        null=True,
        blank=True,
    )
    fecha = models.DateField(blank=True, null=True)
    evaluador = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="visitas_evaluador"
    )

    # Notas aclaratorias — editable even after visit signature
    notas_aclaratorias = models.TextField(
        blank=True, null=True,
        verbose_name="Notas aclaratorias",
        help_text="Notas de clarificación editables después de la firma.",
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

    # Audit trail — tracks all changes with user and timestamp
    history = HistoricalRecords()

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
        'Examen', on_delete=models.CASCADE, related_name="examenes_realizados"
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

    # Audit trail — tracks all changes with user and timestamp
    history = HistoricalRecords()

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

        # Form Builder: resultado = ExamenSubmission (incluye IDs legacy si tienen ``campos``)
        from ..exam_legacy import examen_has_builder_schema, is_legacy_examen

        if examen_has_builder_schema(self.examen.campos) or not is_legacy_examen(
            self.examen_id
        ):
            from .exam_builder import ExamenSubmission

            tiene = ExamenSubmission.objects.filter(visita_examen=self).exists()
            return estado_completado and tiene

        resultado = self.get_resultado_instance()
        tiene_resultado = resultado is not None

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
