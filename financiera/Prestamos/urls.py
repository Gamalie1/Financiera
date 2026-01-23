from django.urls import path
from . import views as Prestamos_views

urlpatterns = [  
    path('principalPrestamos/', Prestamos_views.principal, name='principalPrestamos'),
    path('createPrestamo/', Prestamos_views.create_prestamo, name='createPrestamo'),
    path('editar/<int:pk>/', Prestamos_views.editar_prestamo, name='editar_prestamo'),
    path('eliminar/<int:pk>/', Prestamos_views.eliminar_prestamo, name='eliminar_prestamo'),
    path('detalle_prestamo/<int:pk>/', Prestamos_views.detalle_prestamo, name='detalle_prestamo'),
    path('contrato/<int:prestamo_id>/pdf/', Prestamos_views.generar_contrato_pdf, name='contrato_pdf'),
    path('pagare/<int:prestamo_id>/pdf/', Prestamos_views.generar_pagare, name='pagare_pdf'),
    path('subir-archivo/<int:prestamo_id>/', Prestamos_views.subir_archivo, name='subir_archivo'),
    path('eliminar-archivo/<int:prestamo_id>/', Prestamos_views.eliminar_archivo, name='eliminar_archivo'),
    path('descargar-archivo/<int:prestamo_id>/', Prestamos_views.descargar_archivo, name='descargar_archivo'),
    path('subir-pagare/<int:prestamo_id>/', Prestamos_views.subir_pagare, name='subir_pagare'),
    path('eliminar-pagare/<int:prestamo_id>/', Prestamos_views.eliminar_pagare, name='eliminar_pagare'),
    path('descargar-pagare/<int:prestamo_id>/', Prestamos_views.descargar_pagare, name='descargar_pagare'),
    path('lista/<int:prestamo_id>/', Prestamos_views.descargar_lista, name='descargar_lista'),
    path('subir-informacion/<int:prestamo_id>/', Prestamos_views.subir_informacion, name='subir_informacion'),
    path('eliminar-informacion/<int:prestamo_id>/', Prestamos_views.eliminar_informacion, name='eliminar_informacion'),
    path('descargar-informacion/<int:prestamo_id>/', Prestamos_views.descargar_informacion, name='descargar_informacion'),
    path('invitacion/<int:prestamo_id>/pdf/', Prestamos_views.generar_invitacion, name='invitacion_pdf'),
    path('liquidacion/<int:prestamo_id>/pdf/', Prestamos_views.generar_liquidacion, name='liquidacion_pdf'),


    
]