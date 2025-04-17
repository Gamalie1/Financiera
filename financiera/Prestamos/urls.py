from django.urls import path
from . import views as Prestamos_views

urlpatterns = [  
    path('principalPrestamos/', Prestamos_views.principal, name='principalPrestamos'),
]