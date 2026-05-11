from django.urls import path
from . import views as Pagos_views

urlpatterns = [  
    path('pagos/', Pagos_views.pagosPrincipal, name='pagos'),
    path('createPago/<int:id>/', Pagos_views.create_pago, name='createPago'),
    path('editar/<int:id>/', Pagos_views.editar_pago, name='editar'),
    path('eliminar/<int:pk>/', Pagos_views.eliminar_pago, name='eliminar'),
    path('detalle_pago/<int:prestamo_id>/', Pagos_views.detalle_pago, name='detalle_pago'),
    path('ticket/<int:id>/', Pagos_views.generar_ticket, name='generar_ticket'),
    path('ticket2/<int:id>/', Pagos_views.generar_ticke2, name='generar_ticket2'),
    path('ticket_generico/', Pagos_views.tiket_generico, name='ticket'),
    path('generar_ticket_generico/', Pagos_views.generar_ticket_generico, name='generar_ticket_generico'), 
    path('imprimir_ticket/', Pagos_views.imprimir_ticket, name='imprimir_ticket'), # Mapea la vista a la URL
    path('pago/<int:prestamo_id>/poner_al_corriente/', Pagos_views.poner_al_corriente, name='poner_al_corriente'),
    path('pago/reporte-diario/', Pagos_views.reporte_diario, name='reporte_diario'),
    path('liquidar-prestamo/<int:prestamo_id>/', Pagos_views.liquidar_prestamo, name='liquidar_prestamo'),
    path('pagar-cuota/<int:pago_id>/', Pagos_views.pagar_cuota_individual, name='pagar_cuota_individual'),

]