from django.urls import path
from . import views as Clientes_views

urlpatterns = [  
    path('principalClientes/', Clientes_views.inicio_clientes, name='principalClientes'),
]