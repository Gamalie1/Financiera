from django.urls import path
from . import views as Documentos_views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [  
    path('documentos/', Documentos_views.lista_documentos, name='documentos'),
    path('documentos/subir/', Documentos_views.subir_documento_general, name='subir_documento_general'),
    path('documentos/<int:pk>/editar/', Documentos_views.editar_documento_general, name='editar_documento_general'),
    path('documentos/<int:pk>/eliminar/', Documentos_views.eliminar_documento_general, name='eliminar_documento_general'),
    path('documentos/<int:pk>/descargar/', Documentos_views.descargar_documento_general, name='descargar_documento_general'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)