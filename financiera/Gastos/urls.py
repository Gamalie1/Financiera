from django.urls import path
from . import views as Gastos_views

urlpatterns = [  
    path('Gastos/', Gastos_views.gastosPrincipal, name='Gastos'),
    path('createGasto/',  Gastos_views.registrar_nuevo_gasto, name='createGasto'),
    path('eliminarGasto/<int:id>/', Gastos_views.eliminarGasto, name='eliminarGasto'),
    path('editarGasto/<int:gastos_id>/', Gastos_views.editarGasto, name='editarGasto')


]