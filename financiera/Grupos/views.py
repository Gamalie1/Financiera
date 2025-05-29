from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from .models import Grupo, IntegranteGrupo, DetallePrestamoGrupal
from Clientes.models import Cliente
from Prestamos.models import Prestamo

# CRUD para Grupo
def listar_grupos(request):
    grupos = Grupo.objects.all()
    return render(request, 'grupo_list.html', {'grupos': grupos})

def crear_grupo(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        responsable_id = request.POST.get('responsable')
        activo = 'activo' in request.POST
        
        responsable = get_object_or_404(Cliente, id=responsable_id) if responsable_id else None
        
        grupo = Grupo.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            responsable=responsable,
            activo=activo
        )
        return redirect('detalle-grupo', pk=grupo.pk)
    
    clientes = Cliente.objects.all()
    return render(request, 'grupo_form.html', {'clientes': clientes})

def detalle_grupo(request, pk):
    grupo = get_object_or_404(Grupo, pk=pk)
    integrantes = grupo.integrantes.all()
    return render(request, 'grupo_detail.html', {
        'grupo': grupo,
        'integrantes': integrantes
    })

def editar_grupo(request, pk):
    grupo = get_object_or_404(Grupo, pk=pk)
    
    if request.method == 'POST':
        grupo.nombre = request.POST.get('nombre')
        grupo.descripcion = request.POST.get('descripcion')
        responsable_id = request.POST.get('responsable')
        grupo.responsable = get_object_or_404(Cliente, id=responsable_id) if responsable_id else None
        grupo.activo = 'activo' in request.POST
        grupo.save()
        return redirect('detalle-grupo', pk=grupo.pk)
    
    clientes = Cliente.objects.all()
    return render(request, 'grupo_form.html', {
        'grupo': grupo,
        'clientes': clientes
    })

def eliminar_grupo(request, pk):
    grupo = get_object_or_404(Grupo, pk=pk)
    if request.method == 'POST':
        grupo.delete()
        return redirect('listar-grupos')
    return render(request, 'grupo_confirm_delete.html', {'grupo': grupo})

# CRUD para IntegranteGrupo
def agregar_integrante(request, grupo_id):
    grupo = get_object_or_404(Grupo, pk=grupo_id)
    
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente')
        es_representante = 'es_representante' in request.POST
        
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        
        IntegranteGrupo.objects.create(
            grupo=grupo,
            cliente=cliente,
            es_representante=es_representante
        )
        return redirect('detalle-grupo', pk=grupo_id)
    
    # Excluir clientes que ya están en el grupo
    clientes_existentes = grupo.integrantes.values_list('cliente__id', flat=True)
    clientes_disponibles = Cliente.objects.all().exclude(id__in=clientes_existentes)
    
    return render(request, 'integrante_form.html', {
        'grupo': grupo,
        'clientes': clientes_disponibles
    })

def editar_integrante(request, pk):
    integrante = get_object_or_404(IntegranteGrupo, pk=pk)
    
    if request.method == 'POST':
        integrante.es_representante = 'es_representante' in request.POST
        integrante.save()
        return redirect('detalle-grupo', pk=integrante.grupo.pk)
    
    return render(request, 'integrante_form.html', {'integrante': integrante})

def eliminar_integrante(request, pk):
    integrante = get_object_or_404(IntegranteGrupo, pk=pk)
    grupo_id = integrante.grupo.pk
    
    if request.method == 'POST':
        integrante.delete()
        return redirect('detalle-grupo', pk=grupo_id)
    
    return render(request, 'integrante_confirm_delete.html', {'integrante': integrante})

# CRUD para DetallePrestamoGrupal
def agregar_prestamo_grupal(request, integrante_id):
    integrante = get_object_or_404(IntegranteGrupo, pk=integrante_id)
    
    if request.method == 'POST':
        prestamo_id = request.POST.get('prestamo')
        monto = request.POST.get('monto')
        tasa_interes = request.POST.get('tasa_interes')
        plazo_pagos = request.POST.get('plazo_pagos')
        
        prestamo = get_object_or_404(Prestamo, pk=prestamo_id) if prestamo_id else None
        
        DetallePrestamoGrupal.objects.create(
            prestamo=prestamo,
            integrante=integrante,
            monto=monto,
            tasa_interes=tasa_interes,
            plazo_pagos=plazo_pagos
        )
        return redirect('detalle-grupo', pk=integrante.grupo.pk)
    
    prestamos = Prestamo.objects.all()
    return render(request, 'prestamo_grupal_form.html', {
        'integrante': integrante,
        'prestamos': prestamos
    })

def editar_prestamo_grupal(request, pk):
    prestamo_grupal = get_object_or_404(DetallePrestamoGrupal, pk=pk)
    
    if request.method == 'POST':
        prestamo_grupal.prestamo_id = request.POST.get('prestamo')
        prestamo_grupal.monto = request.POST.get('monto')
        prestamo_grupal.tasa_interes = request.POST.get('tasa_interes')
        prestamo_grupal.plazo_pagos = request.POST.get('plazo_pagos')
        prestamo_grupal.save()
        return redirect('detalle-grupo', pk=prestamo_grupal.integrante.grupo.pk)
    prestamos = Prestamo.objects.all()
    return render(request, 'prestamo_grupal_form.html', {
        'prestamo_grupal': prestamo_grupal,
        'prestamos': prestamos
    })

def eliminar_prestamo_grupal(request, pk):
    prestamo_grupal = get_object_or_404(DetallePrestamoGrupal, pk=pk)
    grupo_id = prestamo_grupal.integrante.grupo.pk
    
    if request.method == 'POST':
        prestamo_grupal.delete()
        return redirect('detalle-grupo', pk=grupo_id)
    
    return render(request, 'prestamo_grupal_confirm_delete.html', {
        'prestamo_grupal': prestamo_grupal
    })