from django.urls import path
from . import views as Pagos_views

urlpatterns = [  
    path('pagos/', Pagos_views.pagosPrincipal, name='pagos'),
    path('createPago/', Pagos_views.create_pago, name='createPago'),
    path('editar/<int:pk>/', Pagos_views.editar_pago, name='editar'),
    path('eliminar/<int:pk>/', Pagos_views.eliminar_pago, name='eliminar'),
]