from django.db import models
from django.contrib.auth.models import User

class Cliente(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    nombre_completo = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(max_length=15)
    email = models.EmailField(max_length=255)
    fecha_nacimiento = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre_completo