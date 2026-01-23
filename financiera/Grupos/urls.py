from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_grupos, name='listar-grupos'),
    path('crear/', views.crear_grupo, name='crear-grupo'),
    path('crear-prestamo/', views.crear_prestamo_grupal, name='crear-prestamo'),
    path('<int:pk>/', views.detalle_grupo, name='detalle-grupo'),
    path('<int:pk>/editar/', views.editar_grupo, name='editar-grupo'),
    path('<int:pk>/eliminar/', views.eliminar_grupo, name='eliminar-grupo'),
    
    # URLs para IntegranteGrupo
    path('<int:grupo_id>/agregar-integrante/', views.agregar_integrante, name='agregar-integrante'),
    path('integrante/<int:pk>/editar/', views.editar_integrante, name='editar-integrante'),
    path('integrante/<int:pk>/eliminar/', views.eliminar_integrante, name='eliminar-integrante'),
    
    # URLs para DetallePrestamoGrupal
    path('integrante/<int:integrante_id>/agregar-prestamo/', views.agregar_prestamo_grupal, name='agregar-prestamo-grupal'),
    path('prestamo-grupal/<int:pk>/editar/', views.editar_prestamo_grupal, name='editar-prestamo-grupal'),
    path('prestamo-grupal/<int:pk>/eliminar/', views.eliminar_prestamo_grupal, name='eliminar-prestamo-grupal'),
    path('<int:grupo_id>/integrantes/', views.obtener_integrantes_grupo, name='obtener_integrantes_grupo'),
]