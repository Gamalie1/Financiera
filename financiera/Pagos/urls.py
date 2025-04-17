from django.urls import path
from . import views as Pagos_views

urlpatterns = [  
    path('pagos/', Pagos_views.principal, name='pagos'),
]