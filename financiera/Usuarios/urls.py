from django.urls import path
from . import views as Usuarios_views

urlpatterns = [  
    path('login/', Usuarios_views.signin, name='login'),
    path('principal/', Usuarios_views.principal, name='principal'),
    path('detalles_cobrador/<str:cobrador>/', Usuarios_views.detalles_cobrador, name='detalles_cobrador'),
    path('logout/', Usuarios_views.signout, name='logout'),
    path('signup/', Usuarios_views.signup, name='signup'),
    path('usuarios/', Usuarios_views.usuarios, name='usuarios'),
    path('editar_usuario/<int:user_id>/',  Usuarios_views.editar_usuario, name='editarUsuarios'),
    path('eliminaUsuarios/<int:id>/', Usuarios_views.eliminarUsuarios, name='eliminaUsuarios'),
]