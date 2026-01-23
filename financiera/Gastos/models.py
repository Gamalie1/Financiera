from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# Validación para monto negativo
def validate_monto(value):
    if value <= 0:
        raise ValidationError('El monto debe ser mayor que cero.')

class Gasto(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name="promotores", verbose_name="Usuario que registró", blank=False, null=False)
    nombre_promotor = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=10, decimal_places=2, validators=[validate_monto])  # Para almacenar el monto con dos decimales
    fecha_registro = models.DateField(auto_now_add=True)  # Fecha de registro, se guarda automáticamente
    concepto = models.TextField()  # Descripción del concepto del gasto
    fecha_modificado = models.DateField(auto_now=True)  # Fecha de última modificación

    def __str__(self):
        return f'{self.nombre_promotor} - {self.monto} - {self.fecha_registro}'

    class Meta:
        indexes = [
            models.Index(fields=['usuario', 'fecha_registro']),
        ]
