from django.urls import path
from . import views as Usuarios_views

urlpatterns = [  
    path('login/', Usuarios_views.signin, name='login'),
    path('principal/', Usuarios_views.principal, name='principal'),
    path('logout/', Usuarios_views.signout, name='logout'),
    path('signup/', Usuarios_views.signup, name='signup'),
    path('usuarios/', Usuarios_views.usuarios, name='usuarios'),
    #path('editarUsuarios/<int:nino_id>/<int:prueba_id>/',  Usuarios_views.editarUsuarios, name='editarUsuarios'),
    path('eliminaUsuarios/<int:id>/', Usuarios_views.eliminarUsuarios, name='eliminaUsuarios'),
]