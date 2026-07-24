from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.templatetags.static import static
from .models import DocumentoGeneral
from django.contrib import messages
from django.http import FileResponse, Http404
# Create your views here.
import os

@login_required
def lista_documentos(request):
    documentos = []

    # Documentos estáticos (los que ya tenías en static/documentos/)
    static_docs = [
        {'nombre': 'Contrato individual', 'url': static('documentos/Contrato_Individual.pdf'), 'es_estatico': True},
        {'nombre': 'Pagare individual semanal', 'url': static('documentos/PAGARE_INDIVIDUAL_SEMANAL.pdf'), 'es_estatico': True},
        {'nombre': 'Pagare individual mensual', 'url': static('documentos/PAGARE_INDIVIDUAL_MENSUAL.pdf'), 'es_estatico': True},
        {'nombre': 'Documento de liquidacion', 'url': static('documentos/LIQUIDACION.pdf'), 'es_estatico': True},
        {'nombre': 'Documento de invitacion', 'url': static('documentos/INVITACION.pdf'), 'es_estatico': True},
        {'nombre': 'Invitacion de pago', 'url': static('documentos/invitacion_de_pago.pdf'), 'es_estatico': True},
        {'nombre': 'Lista de control grupal', 'url': static('documentos/Lista_control_pagos.pdf'), 'es_estatico': True},
        {'nombre': 'Garantia Individual', 'url': static('documentos/Garantia_Individual.pdf'), 'es_estatico': True},
        {'nombre': 'Invitacion de pago 2', 'url': static('documentos/invitacion_2.pdf'), 'es_estatico': True},
    ]
    documentos.extend(static_docs)

       # Documentos dinámicos
    for doc in DocumentoGeneral.objects.all().order_by('-fecha_subida'):
        extension = os.path.splitext(doc.archivo.name)[1].lower()
        if extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            tipo = 'imagen'
        elif extension == '.pdf':
            tipo = 'pdf'
        elif extension in ['.doc', '.docx']:
            tipo = 'word'
        elif extension in ['.xls', '.xlsx']:
            tipo = 'excel'
        elif extension in ['.txt', '.csv']:
            tipo = 'texto'
        else:
            tipo = 'otros'
        documentos.append({
            'nombre': doc.nombre,
            'url': doc.archivo.url,
            'id': doc.id,
            'es_estatico': False,
            'fecha': doc.fecha_subida,
            'subido_por': doc.subido_por,
            'tipo': tipo,
            'extension': extension,
        })

    return render(request, 'documentos.html', {'documentos': documentos})

def subir_documento_general(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        archivo = request.FILES.get('archivo')
        if nombre and archivo:
            DocumentoGeneral.objects.create(
                nombre=nombre,
                archivo=archivo,
                subido_por=request.user
            )
            messages.success(request, "Documento subido correctamente.")
            return redirect('documentos')
        else:
            messages.error(request, "Debes proporcionar nombre y archivo.")
    return render(request, 'subir_documento_general.html')


def editar_documento_general(request, pk):
    doc = get_object_or_404(DocumentoGeneral, pk=pk)
    if request.method == 'POST':
        nuevo_nombre = request.POST.get('nombre')
        nuevo_archivo = request.FILES.get('archivo')
        if nuevo_nombre:
            doc.nombre = nuevo_nombre
        if nuevo_archivo:
            doc.archivo.delete(save=False)  # elimina el anterior
            doc.archivo = nuevo_archivo
        doc.save()
        messages.success(request, "Documento actualizado.")
        return redirect('documentos')
    return render(request, 'editar_documento_general.html', {'documento': doc})


def eliminar_documento_general(request, pk):
    doc = get_object_or_404(DocumentoGeneral, pk=pk)
    if request.method == 'POST':
        doc.archivo.delete()
        doc.delete()
        messages.success(request, "Documento eliminado.")
        return redirect('documentos')
    # Si llega por GET, redirige a la lista (o muestra confirmación, pero ya usamos modal)
    return redirect('documentos')

@login_required
def descargar_documento_general(request, pk):
    doc = get_object_or_404(DocumentoGeneral, pk=pk)
    # Verificar si el archivo existe
    if not doc.archivo or not doc.archivo.storage.exists(doc.archivo.name):
        raise Http404("El archivo no existe.")
    response = FileResponse(doc.archivo.open('rb'), as_attachment=True, filename=doc.nombre or doc.archivo.name)
    return response
