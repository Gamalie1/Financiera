from django.urls import path
from . import views as Prestamos_views

urlpatterns = [  
    path('principalPrestamos/', Prestamos_views.principal, name='principalPrestamos'),
    path('createPrestamo/', Prestamos_views.create_prestamo, name='createPrestamo'),
    path('editar/<int:pk>/', Prestamos_views.editar_prestamo, name='editar_prestamo'),
    path('eliminar/<int:pk>/', Prestamos_views.eliminar_prestamo, name='eliminar_prestamo'),
    path('detalle_prestamo/<int:pk>/', Prestamos_views.detalle_prestamo, name='detalle_prestamo'),
    
    
]