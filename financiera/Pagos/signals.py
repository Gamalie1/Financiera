# Pagos/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Abono, Pago

def actualizar_pago(pago):
    """Actualiza saldo_restante y estado_pago del Pago en base a sus abonos"""
    total_abonado = pago.total_abonado  # propiedad que ya tienes
    pago.saldo_restante = pago.monto_pago - total_abonado
    if pago.saldo_restante <= 0:
        pago.estado_pago = 'pagado'
    elif total_abonado > 0:
        pago.estado_pago = 'parcial'
    else:
        pago.estado_pago = 'pendiente'
    pago.save(update_fields=['saldo_restante', 'estado_pago'])
    # Propaga al préstamo para que actualice su estado general
    pago.prestamo.verificar_y_actualizar_estado()

@receiver(post_save, sender=Abono)
def actualizar_pago_al_guardar_abono(sender, instance, **kwargs):
    actualizar_pago(instance.pago)

@receiver(post_delete, sender=Abono)
def actualizar_pago_al_borrar_abono(sender, instance, **kwargs):
    actualizar_pago(instance.pago)