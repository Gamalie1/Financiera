from django import forms
from .models import Gasto

class GastoForm(forms.ModelForm):
    class Meta:
        model = Gasto
        fields = ['monto', 'concepto']  # Especificamos los campos del modelo que queremos en el formulario

        widgets = {
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': 'Ingrese el monto del gasto'}),
            'fecha_registro': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
        