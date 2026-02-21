from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission, User


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
