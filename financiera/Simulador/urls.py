from django.urls import path
from . import views as Simulador_views

urlpatterns = [  
   path('simulador/', Simulador_views.principal, name='simulador'),
]