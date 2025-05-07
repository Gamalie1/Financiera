from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from Clientes.models import Cliente
from decimal import Decimal
from dateutil.relativedelta import relativedelta  

class Prestamo(models.Model):

    ESTADO_CHOICES = [
        ('SOLICITADO', 'Solicitado'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
        ('PAGADO', 'Pagado'),
    ]
    
    TIPO_CHOICES = [  
        ('SEMANAL', 'Semanal'),
        ('MENSUAL', 'Mensual'),
    ]
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='prestamos')
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    tasa_interes = models.DecimalField(max_digits=5, decimal_places=2) 
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        default='SEMANAL',
        verbose_name="Tipo de pago"
    )
    total_pagos = models.IntegerField(
        verbose_name="Total de pagos",
        help_text="Número total de pagos a realizar según el tipo seleccionado"
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='SOLICITADO')
    iva_sobre_intereses = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0, 
        verbose_name="IVA sobre intereses"
    )
    garantia_liquida = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Garantía líquida"
    )
    aportacion_social = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Aportación social"
    )

    def __str__(self):
        return f"Préstamo #{self.id} - {self.cliente.nombre}"
    
    @property
    def tasa_periodo(self):
        """Calcula la tasa de interés efectiva según el periodo"""
        if self.tipo == 'SEMANAL':
            # Tasa semanal efectiva: (1 + tasa_anual)^(1/52) - 1
            return (Decimal(1) + self.tasa_interes/Decimal(100))**(Decimal(1)/Decimal(52)) - Decimal(1)
        else:
            # Tasa mensual efectiva: (1 + tasa_anual)^(1/12) - 1
            return (Decimal(1) + self.tasa_interes/Decimal(100))**(Decimal(1)/Decimal(12)) - Decimal(1)
    
    @property
    def cuota(self):
        """Calcula la cuota usando sistema francés con tasa mensual"""
        if self.total_pagos == 0 or self.monto == 0:
            return Decimal(0)
            
        tasa = self.tasa_periodo
        # Fórmula corregida para tasa mensual
        return (self.monto * tasa * (1 + tasa)**self.total_pagos) / \
               ((1 + tasa)**self.total_pagos - Decimal(1))
    
    @property
    def total_intereses(self):
        """Calcula el interés total a pagar"""
        return (self.cuota * self.total_pagos) - self.monto
    
    @property
    def total_pagar(self):
        """Calcula el total a pagar (capital + intereses)"""
        return self.cuota * self.total_pagos
    
    @property
    def fecha_finalizacion(self):
        if not self.fecha_aprobacion:
            return None
        
        if self.tipo == 'SEMANAL':
        # Para pagos semanales: total_pagos = número de semanas
            return self.fecha_aprobacion + timezone.timedelta(weeks=self.total_pagos)
        else:
        # Para pagos mensuales: total_pagos = número de meses
            return self.fecha_aprobacion + relativedelta(months=self.total_pagos)
    
    def save(self, *args, **kwargs):
        """Maneja fechas de aprobación"""
        if self.estado == 'APROBADO' and not self.fecha_aprobacion:
            self.fecha_aprobacion = timezone.now()
        elif self.estado != 'APROBADO':
            self.fecha_aprobacion = None
        super().save(*args, **kwargs)

    @property
    def total_pagado(self):
        return sum(pago.monto_pago for pago in self.pagos.all())
    
    @property
    def saldo_pendiente(self):
        return self.total_pagar - self.total_pagado

    @property
    def proximo_pago(self):
        """Calcula la fecha del próximo pago pendiente"""
        if not self.pagos.exists():
            return self.fecha_aprobacion
            
        ultimo_pago = self.pagos.latest('fecha_pago')
        if self.tipo == 'SEMANAL':
            return ultimo_pago.fecha_pago + timezone.timedelta(weeks=1)
        else:
            return ultimo_pago.fecha_pago + relativedelta(months=1)
 
    @property
    def tasa_periodo(self):
        """Convierte la tasa mensual a tasa periódica según el tipo de préstamo"""
        tasa_mensual = self.tasa_interes / Decimal(100)  # Convertir porcentaje a decimal
        
        if self.tipo == 'SEMANAL':
            # Convertir tasa mensual a semanal: (1 + tasa_mensual)^(1/4) - 1
            return (Decimal(1) + tasa_mensual)**(Decimal(1)/Decimal(4)) - Decimal(1)
        else:
            # Mantener tasa mensual directamente
            return tasa_mensual

    
  

    class Meta:
        verbose_name = "Préstamo"
        verbose_name_plural = "Préstamos"
        ordering = ['-fecha_solicitud']