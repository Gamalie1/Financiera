from django.db import models
from django.utils import timezone
from Prestamos.models import Prestamo
from django.contrib.auth.models import User  # Importar el modelo User de Django

class Pago(models.Model):
    METODOS_PAGO = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta de crédito/débito'),
        ('TRANSFERENCIA', 'Transferencia bancaria'),
        ('CHEQUE', 'Cheque'),
        ('OTRO', 'Otro método'),
    ]
    
    ESTADO_PAGO = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
    ]
        
    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name='pagos') 
    monto_pago = models.DecimalField(max_digits=12, decimal_places=2)
    monto_pagado = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    fecha_programada = models.DateField(null=True, blank=True)
    fecha_pago = models.DateTimeField(default=timezone.now)
    dias_transcurridos = models.IntegerField(null=True, blank=True)
    saldo_restante = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pago_parcial = models.BooleanField(default=False)
    metodo_pago = models.CharField(max_length=50, choices=METODOS_PAGO)
    estado_pago = models.CharField(max_length=10, choices=[('pendiente', 'Pendiente'), ('pagado', 'Pagado'), ('parcial', 'Pago parcial')], default='pendiente')
    comentarios = models.TextField(null=True, blank=True, verbose_name="Comentarios")
    numero_pago = models.PositiveIntegerField(verbose_name="Número de pago", null=True, blank=True)
     # Relación con el usuario o empleado que hizo el cobro
    cobrador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pagos_realizados')
    cobrador_asignado = models.ForeignKey(User,on_delete=models.SET_NULL,null=True, blank=True, related_name='prestamos_asignados')
   
    
    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha_pago']
    
    def __str__(self):
        return f"Pago #{self.id} - {self.monto_pago} - {self.fecha_pago.strftime('%Y-%m-%d')}"

