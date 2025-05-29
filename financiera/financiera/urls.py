"""
URL configuration for financiera project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from Usuarios import views as Usuarios_views


urlpatterns = [
    #Inicio
    path('', Usuarios_views.inicio, name='Inicio'),
    path('admin/', admin.site.urls),
    #Usuarios
    path('Usuarios/', include('Usuarios.urls')),
    #Clientes
    path('Clientes/', include('Clientes.urls')),
    #Prestamos
    path('Prestamos/', include('Prestamos.urls')),
    #Pagos
    path('Pagos/', include('Pagos.urls')),
    #Simulador
    path('Simulador/', include('Simulador.urls')),
    #Grupos
    path('Grupos/', include('Grupos.urls'))

]
