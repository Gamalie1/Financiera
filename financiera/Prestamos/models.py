from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from Clientes.models import Cliente
from decimal import Decimal

class Prestamo(models.Model):
    ESTADO_CHOICES = [
        ('SOLICITADO', 'Solicitado'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
        ('PAGADO', 'Pagado'),
    ]
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    tasa_interes = models.DecimalField(max_digits=5, decimal_places=2)  # Tasa anual
    plazo = models.IntegerField()  # En semanas
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='SOLICITADO')

    def __str__(self):
        return f"Préstamo #{self.id} - {self.cliente.nombre_completo}"
    
    @property
    def tasa_semanal(self):
        """Convierte la tasa anual a tasa semanal efectiva"""
        return (Decimal(1) + self.tasa_interes/Decimal(100))**(Decimal(1)/Decimal(52)) - Decimal(1)
    
    @property
    def cuota_semanal(self):
        """Calcula la cuota semanal usando sistema francés"""
        if self.plazo == 0 or self.monto == 0:
            return Decimal(0)
            
        cuota = (self.monto * self.tasa_semanal * (1 + self.tasa_semanal)**self.plazo) / \
               ((1 + self.tasa_semanal)**self.plazo - 1)
        return cuota.quantize(Decimal('0.01'))
    
    @property
    def total_intereses(self):
        """Calcula el interés total a pagar"""
        return (self.cuota_semanal * self.plazo) - self.monto
    
    @property
    def total_pagar(self):
        """Calcula el total a pagar (capital + intereses)"""
        return self.cuota_semanal * self.plazo
    
    @property
    def fecha_finalizacion(self):
        """Calcula la fecha estimada de finalización"""
        fecha_inicio = self.fecha_aprobacion if self.fecha_aprobacion else self.fecha_solicitud
        return fecha_inicio + timezone.timedelta(weeks=self.plazo)
    
    def save(self, *args, **kwargs):
        """Sobrescribir save para manejar fechas de aprobación"""
        if self.estado == 'APROBADO' and not self.fecha_aprobacion:
            self.fecha_aprobacion = timezone.now()
        elif self.estado != 'APROBADO':
            self.fecha_aprobacion = None
        super().save(*args, **kwargs)