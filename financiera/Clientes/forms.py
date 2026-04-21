# forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Cliente, Comunidad

# Formulario para crear comunidades (opcional, si lo necesitas en otro lado)
class ComunidadForm(forms.ModelForm):
    class Meta:
        model = Comunidad
        fields = ['nombre']

class ClienteForm(forms.ModelForm):
        # Campo extra (no pertenece al modelo) para capturar una nueva comunidad
    nueva_comunidad = forms.CharField(
        max_length=100,
        required=False,
        label="O registrar nueva comunidad",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Escribe el nombre de una nueva comunidad'
        })
    )
    class Meta:
        model = Cliente
        fields = ['usuario', 'nombre', 'aval', 'telefono', 'domicilio', 'trabajo', 'clave_elector', 'curp', 'clave_elector_aval', 'domicilio_aval', 'telefono_aval', 'aval2', 'clave_elector_aval2', 'domicilio_aval2', 'telefono_aval2','municipio', 'estado', 'comunidad']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar el campo 'comunidad' (relación FK)
        self.fields['comunidad'].queryset = Comunidad.objects.all().order_by('nombre')
        self.fields['comunidad'].empty_label = "Seleccione una comunidad"
        self.fields['comunidad'].required = False
        self.fields['comunidad'].widget.attrs.update({'class': 'form-control'})
        
        # Opcional: aplicar la clase 'form-control' a todos los campos del formulario
        for field_name, field in self.fields.items():
            if field_name != 'nueva_comunidad' and not isinstance(field.widget, forms.CheckboxInput):
                try:
                    field.widget.attrs.update({'class': 'form-control'})
                except AttributeError:
                    pass
    # Asegúrate de que el campo de usuario esté configurado correctamente
    usuario = forms.ModelChoiceField(queryset=User.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}), required=True)