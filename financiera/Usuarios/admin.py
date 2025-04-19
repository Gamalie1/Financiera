from django.contrib import admin
from django.contrib import admin
from Clientes.models import Cliente  # Importar desde la app correcta
from Prestamos.models import Prestamo  # Importar desde la app correcta

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'email', 'telefono', 'fecha_nacimiento')
    search_fields = ('nombre_completo', 'email')
    list_filter = ('fecha_nacimiento',)

@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'monto', 'estado', 'fecha_solicitud', 'fecha_aprobacion')
    list_filter = ('estado', 'fecha_solicitud')
    search_fields = ('cliente__nombre_completo',)
    raw_id_fields = ('cliente',)
# Register your models here.
