from django.db import models
from Clientes.models import Cliente

class Grupo(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField(blank=True)
    responsable = models.ForeignKey(
        Cliente, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='grupos_responsables'
    )
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"Grupo {self.nombre}"

    class Meta:
        verbose_name = "Grupo de crédito"
        verbose_name_plural = "Grupos de crédito"


class IntegranteGrupo(models.Model):
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name='integrantes')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    es_representante = models.BooleanField(default=False)

    class Meta:
        unique_together = ('grupo', 'cliente') 

    def __str__(self):
        return f"{self.cliente.nombre} en {self.grupo.nombre}"


class DetallePrestamoGrupal(models.Model):
    prestamo = models.ForeignKey('Prestamos.Prestamo', on_delete=models.SET_NULL, null=True)
    integrante = models.ForeignKey(
        IntegranteGrupo,
        on_delete=models.CASCADE,
        related_name='prestamos'
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    tasa_interes = models.DecimalField(max_digits=5, decimal_places=2)
    plazo_pagos = models.IntegerField(verbose_name="Plazo en pagos")    

    def __str__(self):
        return f"Préstamo de ${self.monto} a {self.integrante.cliente.nombre}"

    class Meta:
        verbose_name = "Detalle de préstamo grupal"
