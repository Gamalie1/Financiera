from django.db import models
from django.utils import timezone
from Prestamos.models import Prestamo
from django.contrib.auth.models import User  # Importar el modelo User de Django
from django.db.models import Sum


class Pago(models.Model):

    ESTADO_PAGO = [
        ('pendiente', 'Pendiente'),
        ('parcial', 'Parcial'),
        ('pagado', 'Pagado'),
    ]

    prestamo = models.ForeignKey(
        Prestamo,
        on_delete=models.CASCADE,
        related_name='pagos'
    )

    monto_pago = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto de la cuota"
    )

    fecha_programada = models.DateField(
        verbose_name="Fecha programada de pago"
    )

    saldo_restante = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    estado_pago = models.CharField(
        max_length=10,
        choices=ESTADO_PAGO,
        default='pendiente'
    )

    numero_pago = models.PositiveIntegerField(
        verbose_name="Número de cuota"
    )
    cobrador_asignado = models.ForeignKey(User,on_delete=models.SET_NULL,null=True, blank=True, related_name='prestamos_asignados')


    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Pago #{self.numero_pago} - {self.prestamo}"
    @property
    def dias_atraso(self):
        if self.estado_pago == 'pagado':
            return 0

        hoy = timezone.now().date()

        if self.fecha_programada < hoy:
            return (hoy - self.fecha_programada).days

        return 0
    @property
    def total_abonado(self):
        return self.abonos.aggregate(total=Sum('monto'))['total'] or 0

    
    
class Abono(models.Model):

    METODOS_PAGO = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta'),
        ('TRANSFERENCIA', 'Transferencia'),
        ('CHEQUE', 'Cheque'),
    ]

    pago = models.ForeignKey(
        Pago,
        on_delete=models.CASCADE,
        related_name='abonos'
    )

    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    fecha = models.DateTimeField(
        default=timezone.now
    )

    metodo_pago = models.CharField(
        max_length=20,
        choices=METODOS_PAGO
    )

    cobrador = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    comentario = models.TextField(
        blank=True,
        null=True
    )
    ahorro = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True  )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Abono ${self.monto} - Pago #{self.pago.numero_pago}"    
 

    