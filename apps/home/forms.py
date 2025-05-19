from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from .models import  Proyecto
from django import forms
from .models import DatosDemograficos

class RegistroDemograficoForm(forms.ModelForm):
    class Meta:
        model = DatosDemograficos
        fields = '__all__'  # Incluir todos los campos del modelo
        widgets = {
            # Campos obligatorios
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'edad': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),  # Solo lectura
            'numero_documento': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),  # Evita edición accidental
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
            'celular': forms.TextInput(attrs={'class': 'form-control'}),

            # Datos personales
            'primer_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'segundo_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'primer_apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'segundo_apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_documento': forms.Select(attrs={'class': 'form-control'}),
            'municipio_nacimiento': forms.TextInput(attrs={'class': 'form-control'}),
            'departamento_nacimiento': forms.TextInput(attrs={'class': 'form-control'}),
            'pais_nacimiento': forms.TextInput(attrs={'class': 'form-control'}),
            'genero': forms.Select(attrs={'class': 'form-control'}),
            'estado_civil': forms.Select(attrs={'class': 'form-control'}),
            'escolaridad': forms.Select(attrs={'class': 'form-control'}),
            'lateralidad': forms.Select(attrs={'class': 'form-control'}),
            'ocupacion': forms.TextInput(attrs={'class': 'form-control'}),
            'grupo_sanguineo': forms.Select(attrs={'class': 'form-control'}),
            'rh': forms.Select(attrs={'class': 'form-control'}),
            'religion': forms.TextInput(attrs={'class': 'form-control'}),
            'eps': forms.TextInput(attrs={'class': 'form-control'}),
            'regimen': forms.Select(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'municipio_residencia': forms.TextInput(attrs={'class': 'form-control'}),
            'departamento_residencia': forms.TextInput(attrs={'class': 'form-control'}),
            'pais_residencia': forms.TextInput(attrs={'class': 'form-control'}),

            # Datos del acompañante
            'nombre_acompanante': forms.TextInput(attrs={'class': 'form-control'}),
            'relacion_acompanante': forms.TextInput(attrs={'class': 'form-control'}),
            'correo_acompanante': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono_acompanante': forms.TextInput(attrs={'class': 'form-control'}),
        }


class AnamnesisForm(forms.Form):
    # Campos de texto abiertos
    motivo_consulta = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe el motivo de consulta'}),
        label="Motivo de consulta"
    )
    enfermedad_actual = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe la enfermedad actual'}),
        label="Enfermedad actual"
    )
    quejas_sueno = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe las quejas del sueño'}),
        label="Quejas de sueño"
    )

    # Preguntas de selección Sí/No
    OPCIONES_SI_NO = [('si', 'Sí'), ('no', 'No')]

    dificultad_conciliacion = forms.ChoiceField(
        choices=OPCIONES_SI_NO, widget=forms.RadioSelect, label="Dificultad de conciliación"
    )
    dificultad_mantenimiento = forms.ChoiceField(
        choices=OPCIONES_SI_NO, widget=forms.RadioSelect, label="Dificultad de mantenimiento"
    )
    apnea = forms.ChoiceField(
        choices=OPCIONES_SI_NO, widget=forms.RadioSelect, label="Apnea"
    )
    ronquido = forms.ChoiceField(
        choices=OPCIONES_SI_NO, widget=forms.RadioSelect, label="Ronquido"
    )
    somnolencia_diurna = forms.ChoiceField(
        choices=OPCIONES_SI_NO, widget=forms.RadioSelect, label="Somnolencia diurna"
    )
    hipersomnolencia = forms.ChoiceField(
        choices=OPCIONES_SI_NO, widget=forms.RadioSelect, label="Hipersomnolencia"
    )

    # Campos adicionales (se activan si hay síntomas)
    inicio = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Fecha de inicio'}), required=False, label="Inicio"
    )
    evolucion = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Describe la evolución'}),
        required=False, label="Evolución"
    )
    frecuencia_semana = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Frecuencia semanal'}),
        required=False, label="Frecuencia semanal"
    )
    gravedad = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Gravedad'}),
        required=False, label="Gravedad"
    )

    # Causa conocida
    causa_conocida = forms.ChoiceField(
        choices=OPCIONES_SI_NO, widget=forms.RadioSelect, label="¿Existe una causa conocida?"
    )
    causa_cual = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Si la respuesta es sí, describe la causa'}),
        required=False, label="¿Cuál?"
    )

class CustomLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo Electrónico'}),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
    )

    # Sobrecargamos el método 'confirm_login_allowed' para autenticar por email en lugar de username
    def confirm_login_allowed(self, user):
        if not user.email:
            raise forms.ValidationError("Este correo no está registrado.")
        return super().confirm_login_allowed(user)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("username")
        password = cleaned_data.get("password")
        
        # Verificamos si el usuario existe con el email
        user = authenticate(username=email, password=password)
        if user is None:
            raise forms.ValidationError("Correo o contraseña incorrectos.")
        
        return cleaned_data
      
class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['nombre', 'descripcion', 'investigador_principal', 'codigo_siu', 'fecha_inicio', 'fecha_financiacion']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_financiacion': forms.DateInput(attrs={'type': 'date'}),
        }