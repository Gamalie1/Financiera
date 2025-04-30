from django.db import models
from django.utils import timezone
from Prestamos.models import Prestamo

class Pago(models.Model):
    METODOS_PAGO = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta de crédito/débito'),
        ('TRANSFERENCIA', 'Transferencia bancaria'),
        ('CHEQUE', 'Cheque'),
        ('OTRO', 'Otro método'),
    ]
        
    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE)
    monto_pago = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_pago = models.DateTimeField(default=timezone.now)
    metodo_pago = models.CharField(max_length=50, choices=METODOS_PAGO)
    
    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha_pago']
    
    def __str__(self):
        return f"Pago #{self.id} - {self.monto_pago} - {self.fecha_pago.strftime('%Y-%m-%d')}"

