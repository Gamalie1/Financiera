from django import forms
from .models import Prestamo

class ArchivoFirmadoForm(forms.ModelForm):
    class Meta:
        model = Prestamo
        fields = ['archivo_firmado', 'pagare']  # Solo el campo archivo_firmado