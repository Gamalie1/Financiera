# forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Cliente

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['usuario', 'nombre', 'aval', 'telefono', 'domicilio', 'trabajo', 'clave_elector', 'curp', 'clave_elector_aval', 'domicilio_aval', 'telefono_aval', 'aval2', 'clave_elector_aval2', 'domicilio_aval2', 'telefono_aval2','municipio', 'estado']

    # Asegúrate de que el campo de usuario esté configurado correctamente
    usuario = forms.ModelChoiceField(queryset=User.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}), required=True)