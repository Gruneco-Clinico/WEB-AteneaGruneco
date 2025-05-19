# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission

class CustomUser(AbstractUser):
    # Campos adicionales
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    
    # Sobrescribir las relaciones con related_name personalizado
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        related_name='custom_user_set',
        related_query_name='custom_user'
    )
    
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        related_name='custom_user_set',
        related_query_name='custom_user'
    )

    def __str__(self):
        return self.username

class DatosDemograficos(models.Model):
    # Información Personal
    primer_nombre = models.CharField(max_length=50)
    segundo_nombre = models.CharField(max_length=50, blank=True, null=True)
    primer_apellido = models.CharField(max_length=50)
    segundo_apellido = models.CharField(max_length=50, blank=True, null=True)
    tipo_documento = models.CharField(max_length=50, choices=[
        ('CC', 'Cédula de Ciudadanía'),
        ('TI', 'Tarjeta de Identidad'),
        ('NUIP', 'Número Único de Identificación Personal'),
        ('CE', 'Cédula de Extranjería'),
        ('PS', 'Pasaporte'),
    ],default='')
    numero_documento = models.CharField(max_length=20, unique=True)
    celular = models.CharField(max_length=20, unique=True,default='')
    fecha_nacimiento = models.DateField()
    edad = models.IntegerField()
    genero = models.CharField(max_length=10, choices=[
        ('F', 'Femenino'),
        ('M', 'Masculino'),
        ('O', 'Otro'),
    ],default='')
    municipio_nacimiento = models.CharField(max_length=100,default='')
    departamento_nacimiento = models.CharField(max_length=100,default='')
    pais_nacimiento = models.CharField(max_length=100,default='')
    estado_civil = models.CharField(max_length=20, choices=[
        ('Soltero', 'Soltero(a)'),
        ('Casado', 'Casado(a)'),
        ('UnionLibre', 'Unión libre'),
        ('Viudo', 'Viudo(a)'),
    ],default='')
    
    ESCOLARIDAD_CHOICES = [
        ('primario', 'Primario'),
        ('bachiller', 'Bachiller'),
        ('universidad', 'Universidad'),
        ('maestria', 'Maestría'),
        ('doctorado', 'Doctorado'),
        ('especializacion', 'Especialización'),
    ]

    # Campo escolaridad
    escolaridad = models.CharField(
        max_length=20,
        choices=ESCOLARIDAD_CHOICES,
        blank=True,
        null=True,
        verbose_name="Escolaridad"
    )

    ocupacion = models.CharField(max_length=100)
    lateralidad = models.CharField(max_length=20, choices=[
        ('Diestro', 'Diestro'),
        ('Zurdo', 'Zurdo'),
        ('Ambidiestro', 'Ambidiestro'),
    ],default='')
    GRUPO_SANGUINEO_CHOICES = [
        ('O+', 'O+'),
        ('O-', 'O-'),
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
    ]
    grupo_sanguineo = models.CharField(
        max_length=5,
        choices=GRUPO_SANGUINEO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Grupo Sanguíneo"
    )
    religion = models.CharField(max_length=100)
    eps = models.CharField(max_length=100)
    regimen = models.CharField(max_length=20, choices=[
        ('Contributivo', 'Contributivo'),
        ('Subsidiado', 'Subsidiado'),
        ('Vinculado', 'Vinculado'),
        ('Otro', 'Otro'),
    ],default='')
    direccion = models.CharField(max_length=200,default='')
    municipio_residencia = models.CharField(max_length=100,default='')
    departamento_residencia = models.CharField(max_length=100,default='')
    pais_residencia = models.CharField(max_length=100,default='')
    
    correo = models.EmailField(unique=True, verbose_name="Correo Electrónico", default="sincorreo@example.com") 

    def __str__(self):
        return f"{self.primer_nombre} {self.primer_apellido}"

class Proyecto(models.Model):
    nombre = models.CharField(max_length=255, unique=True, verbose_name="Nombre del Proyecto")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción del Proyecto")
    investigador_principal = models.CharField(max_length=255, blank=True, null=True, verbose_name="Investigador Principal")
    codigo_siu = models.CharField(max_length=50, blank=True, null=True, verbose_name="Código SIU")
    fecha_inicio = models.DateField(blank=True, null=True, verbose_name="Fecha de Inicio")
    fecha_financiacion = models.DateField(blank=True, null=True, verbose_name="Fecha de Financiación")
    pacientes = models.ManyToManyField('DatosDemograficos', related_name='proyectos', verbose_name="Pacientes")
    
    def __str__(self):
        return self.nombre
    
class Examen(models.Model):
    nombre = models.CharField(max_length=255, verbose_name="Nombre del Examen")
    descripcion = models.TextField(verbose_name="Descripción del Examen", blank=True, null=True)
    campos = models.JSONField(verbose_name="Campos del Examen", default=list)  # Estructura del formulario

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Examen"
        verbose_name_plural = "Exámenes"
        
class TipoVisita(models.Model):
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la Visita")
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='visitas', verbose_name="Proyecto")
    observaciones = models.TextField(verbose_name="Observaciones", blank=True, null=True)
    examenes = models.JSONField(default=dict, verbose_name="Exámenes",null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} - {self.proyecto.nombre}"
        
class Visita(models.Model):
    paciente = models.ForeignKey(DatosDemograficos, on_delete=models.CASCADE, related_name="visitas",null=True, blank=True)
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la Visita")
    Tipo_visita = models.ForeignKey(TipoVisita, on_delete=models.CASCADE, related_name='visitas',null=True, blank=True)
    fecha = models.DateField(blank=True, null=True)
    evaluador = models.CharField(max_length=50,null=True, blank=True)
    
    # Campos del acompañante
    acompanante_nombre = models.CharField(max_length=255, verbose_name="Nombre del Acompañante", blank=True, null=True)
    acompanante_relacion = models.CharField(max_length=100, verbose_name="Relación con el Paciente", blank=True, null=True)
    acompanante_correo = models.EmailField(verbose_name="Correo del Acompañante", blank=True, null=True)
    acompanante_telefono = models.CharField(max_length=20, verbose_name="Teléfono del Acompañante", blank=True, null=True)
    
    def __str__(self):
        return f"{self.nombre} - {self.proyecto.nombre}"

class VisitaExamen(models.Model):
    visita = models.ForeignKey(Visita, on_delete=models.CASCADE, related_name="visita_examenes")
    examen = models.ForeignKey(Examen, on_delete=models.CASCADE, related_name="examenes_realizados")
    resultado = models.JSONField(verbose_name="Respuestas del Examen",null=True, blank=True)
    
    def __str__(self):
        return f"{self.visita.nombre} - {self.examen.nombre}"
    

