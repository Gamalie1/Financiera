from django.urls import path
from . import views as Documentos_views

urlpatterns = [  
    path('documentos/',  Documentos_views.DocumentosPrincipal, name='documentos'),
]