from django.urls import path
from . import views as Clientes_views

urlpatterns = [  
    path('principalClientes/', Clientes_views.inicio_clientes, name='principalClientes'),
    path('registronuevo/', Clientes_views.registronuevo, name='registronuevo'),
    path('eliminarcliente/<int:id>/', Clientes_views.eliminarcliente, name='eliminarcliente'),
    path('editarCliente/<int:cliente_id>/', Clientes_views.editarcliente, name='editarCliente'),
]