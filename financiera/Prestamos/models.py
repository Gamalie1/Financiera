from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from Clientes.models import Cliente
from decimal import Decimal
from dateutil.relativedelta import relativedelta  
from datetime import timedelta
from django.contrib.auth.models import User  # Importar el modelo User de Django
from django.apps import apps

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

    ES_GRUPAL_CHOICES = [
        (False, 'Individual'),
        (True, 'Grupal')
    ]
    
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='prestamos', null=True, blank=True)
    grupo = models.ForeignKey('Grupos.Grupo', on_delete=models.CASCADE, related_name='prestamos', null=True, blank=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    tasa_interes = models.DecimalField(max_digits=5, decimal_places=2) 
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='SEMANAL', verbose_name="Tipo de pago")
    total_pagos = models.IntegerField(verbose_name="Total de pagos", help_text="Número total de pagos a realizar según el tipo seleccionado")
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='SOLICITADO')
    iva_sobre_intereses = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="IVA sobre intereses")
    garantia_liquida = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Garantía líquida")
    aportacion_social = models.DecimalField( max_digits=12, decimal_places=2, default=0, verbose_name="Aportación social")
    es_grupal = models.BooleanField( choices=ES_GRUPAL_CHOICES, default=False, verbose_name="Tipo de préstamo")
     # Campo para el archivo firmado
    archivo_firmado = models.FileField(upload_to='Prestamos/firmados/', null=True, blank=True, verbose_name="Archivo firmado")
    pagare = models.FileField(upload_to='Prestamos/pagares/', null=True, blank=True, verbose_name="Pagare")
    informacion = models.FileField(upload_to='Prestamos/informacions/', null=True, blank=True, verbose_name="informacion")
    promotor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='Promotor')
    ahorro = models.DecimalField(max_digits=10,decimal_places=2,default=0,verbose_name="Ahorro por periodo")
    folio = models.CharField(max_length=50,verbose_name="Folio de solicitud",null=True)
    pago_final = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)



    def __str__(self):
        return f"Préstamo #{self.id} - {self.cliente.nombre}"
    
    def clean(self):
        """Valida que el préstamo tenga cliente O grupo, pero no ambos"""
        if not self.cliente and not self.grupo:
            raise ValidationError("Debe especificar un cliente o un grupo.")
        if self.cliente and self.grupo:
            raise ValidationError("Un préstamo no puede ser individual y grupal simultáneamente.")
        self.es_grupal = bool(self.grupo) # Actualiza el campo es_grupal según la presencia del grupo
    @property
    def color_estado(self):
        pagos = self.pagos.all()

        if not pagos.exists():
            return ""

        # 🔴 Si hay algún pago con atraso
        for pago in pagos:
            if pago.dias_atraso > 0:
                return "table-danger"

        # 🟡 Si todos están pendientes
        if pagos.filter(estado_pago='pagado').count() == 0:
            return "table-warning"

        # 🟢 Caso contrario está al corriente
        return "table-success"

    
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
        """Maneja fechas de aprobación y genera los pagos"""
        if self.estado == 'APROBADO' and not self.fecha_aprobacion:
            # Si el estado es 'APROBADO' pero no se ha asignado fecha_aprobacion,
            # asignamos la fecha que el usuario ha proporcionado en el formulario
            if self.fecha_aprobacion is None:  # Aseguramos que no sobrescriba si ya tiene valor
                pass  # No hacemos nada si ya tiene una fecha de aprobación asignada
        elif self.estado != 'APROBADO':
            self.fecha_aprobacion = None  # Si no está aprobado, eliminamos la fecha de aprobación
        super().save(*args, **kwargs)


    @property
    def total_pagado(self):
        return sum(pago.monto_pago for pago in self.pagos.all())
    
    @property
    def saldo_pendiente(self):
        return self.total_pagar - self.total_pagado

    @property
    def proximo_pago(self):
        """
        Devuelve la fecha del próximo pago pendiente del préstamo.
        """
        Pago = apps.get_model('Pagos', 'Pago')

        pago_pendiente = (
            Pago.objects
            .filter(
                prestamo=self,
                estado_pago__in=['pendiente', 'parcial']
            )
            .order_by('fecha_programada')
            .first()
        )

        if pago_pendiente:
            return pago_pendiente.fecha_programada

        return None  # o self.fecha_aprobacion si prefieres
    
    @property
    def tasa_periodo(self):
        """Calcula la tasa de interés efectiva según el periodo"""
        tasa_anual = self.tasa_interes / Decimal(100)  # Convertir la tasa anual a decimal
        
        if self.tipo == 'SEMANAL':
            # Convertir tasa anual a semanal: (1 + tasa_anual)^(1/52) - 1
            return (Decimal(1) + tasa_anual)**(Decimal(1)/Decimal(52)) - Decimal(1)
        else:
            # Mantener tasa mensual directamente (tasa anual / 12)
            return tasa_anual / Decimal(12)

    def generar_pagos(self):
        from Pagos.models import Pago
        from decimal import Decimal
        from dateutil.relativedelta import relativedelta
        from datetime import timedelta

        print(f"IVA sobre intereses: {self.iva_sobre_intereses}")

        monto = Decimal(self.monto)
        tasa_interes = Decimal(self.tasa_interes) / Decimal('100')
        iva_porcentaje = Decimal(self.iva_sobre_intereses) / Decimal('100')

        total_pagos = self.total_pagos
        tipo_pago = self.tipo

        ahorro_por_pago = Decimal(self.ahorro or 0)
        pago_final_manual = Decimal(self.pago_final or 0)

        # ----- CALCULOS BASE -----

        abono_capital_base = monto / total_pagos
        interes_por_periodo = monto * tasa_interes
        iva_por_periodo = interes_por_periodo * iva_porcentaje

        cuota_base = abono_capital_base + interes_por_periodo + iva_por_periodo

        # ----- GENERAR FECHAS -----

        fechas_pagos = []

        if self.fecha_aprobacion:

            fecha_base = self.fecha_aprobacion.date()
            dia_prestamo = fecha_base.weekday()

            if tipo_pago == 'SEMANAL':
                fecha_pago = fecha_base + relativedelta(weeks=1)
            else:
                fecha_pago = fecha_base + timedelta(days=30)

            for _ in range(total_pagos):

                diferencia = dia_prestamo - fecha_pago.weekday()
                fecha_ajustada = fecha_pago + timedelta(days=diferencia)

                fechas_pagos.append(fecha_ajustada)

                if tipo_pago == 'SEMANAL':
                    fecha_pago += relativedelta(weeks=1)
                else:
                    fecha_pago += timedelta(days=30)

        responsable = self.promotor # aquí tomamos el responsable desde el préstamo

        # ----- CREAR CUOTAS -----

        for i, fecha_pago in enumerate(fechas_pagos):

            if pago_final_manual > 0:
                monto_total_pago = pago_final_manual
            else:
                cuota = cuota_base
                monto_total_pago = cuota + ahorro_por_pago

            Pago.objects.create(
                prestamo=self,
                fecha_programada=fecha_pago,   # ✅ CAMBIO IMPORTANTE
                monto_pago=round(monto_total_pago, 2),
                saldo_restante=round(monto_total_pago, 2),  # ✅ inicia igual
                estado_pago='pendiente',
                numero_pago=i + 1,
                cobrador_asignado=responsable
            )


    def save(self, *args, **kwargs):
        """Maneja fechas de aprobación y genera los pagos"""
        
        if self.estado == 'APROBADO' and not self.fecha_aprobacion:
            # Si el préstamo está aprobado y no tiene fecha de aprobación, asignamos la fecha actual
            self.fecha_aprobacion = timezone.now()

        if self.estado == 'APROBADO' and self.fecha_aprobacion:
            # Llamamos a generar_pagos si el préstamo está aprobado y tiene fecha de aprobación
            self.generar_pagos()

        elif self.estado != 'APROBADO':
            # Si el préstamo no está aprobado, eliminamos la fecha de aprobación
            self.fecha_aprobacion = None 

        # Guardamos el objeto Prestamo después de procesar la fecha y generar pagos
        super().save(*args, **kwargs)

    
    class Meta:
        verbose_name = "Préstamo"
        verbose_name_plural = "Préstamos"
        ordering = ['-fecha_solicitud']
        