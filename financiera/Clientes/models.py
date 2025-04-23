from django.db import models
from django.contrib.auth.models import User  # Importar el modelo User de Django

class Cliente(models.Model):
    id = models.AutoField(primary_key=True)
    # Relación con el usuario que registra el cliente
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="clientes", verbose_name="Usuario que registró", blank=False, null=False)

    # Campos para el nombre y el aval de la persona
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la persona")
    aval = models.CharField(max_length=100, verbose_name="Aval")

    # Campo de teléfono (puede incluir validación adicional si lo deseas)
    telefono = models.CharField(max_length=15, verbose_name="Teléfono")

    # Campo de domicilio
    domicilio = models.TextField(verbose_name="Domicilio")

      # Campo para el trabajo
    trabajo = models.CharField(max_length=100, verbose_name="Trabajo")

    # Campo para la imagen de la INE
    ine = models.ImageField(upload_to='ine/', verbose_name="INE", null=True, blank=True)

   # Campo para el trabajo
    curp = models.CharField(max_length=100, verbose_name="CURP", default="No proporcionado")  # Valor predeterminado

    # Añadir fechas de creación y modificación
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de modificación")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"