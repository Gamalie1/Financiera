from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from .models import Grupo, IntegranteGrupo, DetallePrestamoGrupal
from Clientes.models import Cliente
from Prestamos.models import Prestamo
from django.contrib.auth.models import User
from django.contrib import messages
from decimal import Decimal
from Prestamos.models import Prestamo
from django.db import transaction
from django.http import JsonResponse

from django.contrib.auth.decorators import login_required

# CRUD para Grupo
@login_required
def listar_grupos(request):
    grupos = Grupo.objects.prefetch_related('integrantes__prestamos').all()

    # Construimos una lista con cada grupo y su primer préstamo si existe
    grupos_con_prestamo = []
    for grupo in grupos:
        prestamo = None
        # Buscar el primer préstamo de cualquier integrante
        for integrante in grupo.integrantes.all():
            detalle = integrante.prestamos.first()
            if detalle and detalle.prestamo:
                prestamo = detalle.prestamo
                break
        grupos_con_prestamo.append({
            'grupo': grupo,
            'prestamo': prestamo
        })

    return render(request, 'grupo_list.html', {'grupos_con_prestamo': grupos_con_prestamo})

@login_required
def crear_prestamo_grupal(request):

    grupos = Grupo.objects.all()
    clientes = Cliente.objects.all()
    promotores = User.objects.all()

    if request.method == 'POST':

        form_data = request.POST.copy()

        grupo_id = form_data.get('grupo')
        grupo = Grupo.objects.get(id=grupo_id)
        responsable = grupo.responsable

        promotor = User.objects.get(id=form_data.get('promotor'))

        es_grupal = form_data.get('es_grupal') == 'True'

        monto = Decimal(form_data.get('monto', '0').strip() or '0')
        tasa_interes = Decimal(form_data.get('tasa_interes', '0').strip() or '0')

        tipo = form_data.get('tipo')
        total_pagos = int(form_data.get('total_pagos', '0') or 0)

        iva_sobre_intereses = Decimal(form_data.get('iva_sobre_intereses', '0') or '0')
        garantia_liquida = Decimal(form_data.get('garantia_liquida', '0') or '0')
        aportacion_social = Decimal(form_data.get('aportacion_social', '0') or '0')
        ahorro = Decimal(form_data.get('ahorro', '0') or '0')
        pago_final = Decimal(form_data.get('pago_final', '0') or '0')

        folio = form_data.get('solicitud_credito', '').strip()

        # ==========================
        # INTEGRANTES
        # ==========================
        integrantes_ids = request.POST.getlist('integrantes_ids[]')
        montos = request.POST.getlist('montos[]')

        if not integrantes_ids:
            messages.error(request, "Debe agregar integrantes al préstamo grupal")
            return redirect('crear_prestamo_grupal')

        # TRANSACCIÓN SEGURA
        # ==========================

        with transaction.atomic():

            # ✅ Crear préstamo
            prestamo = Prestamo.objects.create(
                cliente_id=responsable.id,
                grupo=grupo,
                promotor=promotor,
                monto=monto,
                tasa_interes=tasa_interes,
                tipo=tipo,
                total_pagos=total_pagos,
                iva_sobre_intereses=iva_sobre_intereses,
                garantia_liquida=garantia_liquida,
                aportacion_social=aportacion_social,
                es_grupal=es_grupal,
                ahorro=ahorro,
                pago_final=pago_final,
                estado='SOLICITADO',
                folio=folio,
            )
            integrantes_ids = request.POST.getlist('integrantes_ids[]')
            montos = request.POST.getlist('montos[]')

            for cliente_id, monto_individual in zip(integrantes_ids, montos):
                integrante, created = IntegranteGrupo.objects.get_or_create(
                    grupo=grupo,
                    cliente_id=cliente_id,
                    defaults={'es_representante': False}
                )

                DetallePrestamoGrupal.objects.create(
                    prestamo=prestamo,
                    integrante=integrante,
                    monto=Decimal(monto_individual),
                    tasa_interes=tasa_interes,
                    plazo_pagos=total_pagos
                )

        messages.success(request, 'Préstamo grupal creado correctamente')

    return render(request, "grupo_form.html", {
        "grupos": grupos,
        "clientes": clientes,
        "promotores": promotores,
        "grupo_seleccionado": request.POST.get("grupo")
    })

@login_required
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
        # Guardar al responsable también como integrante del grupo
        if responsable:
            IntegranteGrupo.objects.create(
                grupo=grupo,
                cliente=responsable,
                es_representante=True
            )
        messages.success(request, 'Grupo creado correctamente')
        return redirect('crear-prestamo')
    clientes = Cliente.objects.all()
    return render(request, 'crear_grupo.html', {'clientes': clientes})

def detalle_grupo(request, pk):
    grupo = get_object_or_404(Grupo, pk=pk)
    integrantes = grupo.integrantes.all()
    return render(request, 'grupo_detail.html', {
        'grupo': grupo,
        'integrantes': integrantes
    })

@login_required
def editar_grupo(request, pk):
    # Obtener el grupo por pk
    grupo = get_object_or_404(Grupo, pk=pk)

    # Clientes disponibles para seleccionar
    clientes = Cliente.objects.all()

    # Detalles actuales del grupo (si existieran) o lista vacía
    integrantes = grupo.integrantes.select_related('cliente').all()

    if request.method == "POST":
        form_data = request.POST.copy()

        # Aquí puedes actualizar datos administrativos del grupo
        grupo.nombre = form_data.get("nombre", grupo.nombre)
        grupo.descripcion = form_data.get("descripcion", grupo.descripcion)

        responsable_id = form_data.get("responsable")
        if responsable_id:
            grupo.responsable = Cliente.objects.get(id=responsable_id)

        grupo.save()

        # Actualizar integrantes si se envían
        integrantes_ids = request.POST.getlist("integrantes_ids[]")
        montos = request.POST.getlist("montos[]")

        # Si quieres mantener un registro de préstamos grupales, podrías crear uno aquí
        # pero si solo quieres editar integrantes del grupo, basta con actualizar DetallePrestamoGrupal
        DetallePrestamoGrupal.objects.filter(prestamo__grupo=grupo).delete()  # Opcional, depende de tu modelo

        for cliente_id, monto_individual in zip(integrantes_ids, montos):
            integrante = IntegranteGrupo.objects.get(grupo=grupo, cliente_id=cliente_id)
            # Puedes guardar el detalle de monto si quieres
            DetallePrestamoGrupal.objects.create(
                prestamo=None,  # Sin préstamo asociado
                integrante=integrante,
                monto=Decimal(monto_individual)
            )

        messages.success(request, "Grupo actualizado correctamente")
        return redirect("principalPrestamos")

    return render(request, "grupo_form_edit.html", {
        "grupo": grupo,
        "integrantes": integrantes,
        "clientes": clientes
    })

@login_required
def eliminar_grupo(request, pk):
    grupo = get_object_or_404(Grupo, pk=pk)
    if request.method == 'POST':
        grupo.delete()
        messages.success(request, 'Préstamo grupal eliminado correctamente')
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

@login_required
def editar_integrante(request, pk):
    integrante = get_object_or_404(IntegranteGrupo, pk=pk)
    
    if request.method == 'POST':
        integrante.es_representante = 'es_representante' in request.POST
        integrante.save()
        return redirect('detalle-grupo', pk=integrante.grupo.pk)
    
    return render(request, 'integrante_form.html', {'integrante': integrante})

@login_required
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

@login_required
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

@login_required
def eliminar_prestamo_grupal(request, pk):
    prestamo_grupal = get_object_or_404(DetallePrestamoGrupal, pk=pk)
    grupo_id = prestamo_grupal.integrante.grupo.pk
    
    if request.method == 'POST':
        prestamo_grupal.delete()
        return redirect('detalle-grupo', pk=grupo_id)
    
    return render(request, 'prestamo_grupal_confirm_delete.html', {
        'prestamo_grupal': prestamo_grupal
    })

def obtener_integrantes_grupo(request, grupo_id):

    integrantes = IntegranteGrupo.objects.filter(
        grupo_id=grupo_id
    ).select_related('cliente')

    data = []

    for item in integrantes:
        data.append({
            'id': item.cliente.id,
            'nombre': item.cliente.nombre,
            'representante': item.es_representante
        })

    return JsonResponse(data, safe=False)