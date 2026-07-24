from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
# Create your models here.
class DocumentoGeneral(models.Model):
    nombre = models.CharField(max_length=200)
    archivo = models.FileField(upload_to='documentos_generales/%Y/%m/')
    fecha_subida = models.DateTimeField(auto_now_add=True)
    subido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.nombre