from django.db import models
from django.contrib.auth.models import User  # Importar el modelo User de Django

class Comunidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la comunidad")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Comunidad"
        verbose_name_plural = "Comunidades"

class Cliente(models.Model):
    id = models.AutoField(primary_key=True)
    # Relación con el usuario que registra el cliente
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="clientes", verbose_name="Usuario que registró", blank=False, null=False)

    # Campos para el nombre y el aval de la persona
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la persona")

    aval = models.CharField(max_length=100, verbose_name="Aval")

    clave_elector_aval = models.CharField(max_length=100, verbose_name="Clave de electro aval", null=True, blank=True)

    domicilio_aval = models.TextField(verbose_name="Domicilio Aval", null=True, blank=True)

    telefono_aval = models.TextField(verbose_name="Telefono aval", null=True, blank=True)

    # Campo de teléfono (puede incluir validación adicional si lo deseas)
    telefono = models.CharField(max_length=15, verbose_name="Teléfono", null=True, blank=True)

    # Campo de domicilio
    domicilio = models.TextField(verbose_name="Domicilio", null=True, blank=True)

      # Campo para el trabajo
    trabajo = models.CharField(max_length=100, verbose_name="Trabajo", null=True, blank=True)

    # Campo para la imagen de la INE
    ine = models.ImageField(upload_to='ine/', verbose_name="INE", null=True, blank=True)

   # Campo para el trabajo
    curp = models.CharField(max_length=100, verbose_name="CURP", default="No proporcionado")  # Valor predeterminado

    clave_elector = models.CharField(max_length=100, verbose_name="Clave de elector", default="No proporcionado", null=True, blank=True)

    municipio = models.CharField(max_length=100, verbose_name="Municipio", default="No proporcionado", null=True, blank=True)

    estado = models.CharField(max_length=100, verbose_name="Estado", default="No proporcionado", null=True, blank=True)

    # Añadir fechas de creación y modificación
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de modificación")

    aval2 = models.CharField(max_length=100, verbose_name="Aval", null=True, blank=True)

    clave_elector_aval2 = models.CharField(max_length=100, verbose_name="Clave de electro aval", null=True, blank=True)

    domicilio_aval2 = models.TextField(verbose_name="Domicilio Aval", null=True, blank=True)

    telefono_aval2 = models.TextField(verbose_name="Telefono aval", null=True, blank=True)

    # Nueva relación con Comunidad
    comunidad = models.ForeignKey(
        Comunidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Comunidad"
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"