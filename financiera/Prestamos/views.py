from django.shortcuts import render, redirect
from django.contrib import messages
from Clientes.models import Cliente
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django import forms
from django.utils import timezone
from django.contrib import messages
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta  
from Prestamos.models import Prestamo



def principal(request):
    prestamos = Prestamo.objects.all().select_related('cliente')
    return render(request, 'prestamos.html', {
        'prestamos': prestamos,
        'seccion': 'prestamos'  
    })

@login_required
def create_prestamo(request):
    clientes = Cliente.objects.all()
    
    if request.method == 'POST':
        form_data = request.POST.copy()
        try:
            # Conversión y validación 
            cliente_id = form_data.get('cliente')
            monto = Decimal(form_data.get('monto', '0').strip() or '0')
            tasa_interes = Decimal(form_data.get('tasa_interes', '0').strip() or '0')
            tipo = form_data.get('tipo')
            total_pagos = int(form_data.get('total_pagos', '0').strip() or 0)
            iva_sobre_intereses = Decimal(form_data.get('iva_sobre_intereses', '0').strip() or '0')
            garantia_liquida = Decimal(form_data.get('garantia_liquida', '0').strip() or '0')
            aportacion_social = Decimal(form_data.get('aportacion_social', '0').strip() or '0')

            errores = []
            if not cliente_id:
                errores.append("Debe seleccionar un cliente")
            if monto < 100:
                errores.append("El monto mínimo es $100.00")
            if tipo not in ['SEMANAL', 'MENSUAL']:
                errores.append("Tipo de préstamo inválido")
            if total_pagos < 1:
                errores.append("El número mínimo de pagos es 1")
                
            # Validaciones específicas por tipo
            if tipo == 'SEMANAL' and total_pagos > 520:
                errores.append("El máximo de pagos semanales es 520 (10 años)")
            elif tipo == 'MENSUAL' and total_pagos > 120:
                errores.append("El máximo de pagos mensuales es 120 (10 años)")
                
            if tasa_interes < Decimal('0.1') or tasa_interes > Decimal('30'):
                errores.append("La tasa debe estar entre 0.1% y 30%")
            
            if errores:
                for error in errores:
                    messages.error(request, error)
                return render(request, 'create_prestamo.html', {
                    'clientes': clientes,
                    'form_data': form_data
                })
            
            # Creación del préstamo
            Prestamo.objects.create(
                cliente_id=cliente_id,
                monto=monto,
                tasa_interes=tasa_interes,
                tipo=tipo,
                total_pagos=total_pagos,
                estado='SOLICITADO',
                iva_sobre_intereses=iva_sobre_intereses,
                garantia_liquida=garantia_liquida,
                aportacion_social=aportacion_social
            )
            
            messages.success(request, 'Préstamo creado exitosamente!')
            return redirect('principalPrestamos')
            
        except Exception as e:
            messages.error(request, f'Error al crear el préstamo: {str(e)}')
            return render(request, 'create_prestamo.html', {
                'clientes': clientes,
                'form_data': form_data
            })
    
    return render(request, 'create_prestamo.html', {'clientes': clientes})

@login_required
def editar_prestamo(request, pk):
    prestamo = get_object_or_404(Prestamo, pk=pk)
    puede_editar = prestamo.estado == 'SOLICITADO'
    clientes = Cliente.objects.all()
    
    if request.method == 'POST':
        try:
            cliente_id = request.POST.get('cliente')
            monto = Decimal(request.POST.get('monto', '0').strip() or '0')
            tasa_interes = Decimal(request.POST.get('tasa_interes', '0').strip() or '0')
            tipo = request.POST.get('tipo')
            total_pagos = int(request.POST.get('total_pagos', '0').strip() or 0)
            estado = request.POST.get('estado')
            iva_sobre_intereses = Decimal(request.POST.get('iva_sobre_intereses', '0').strip() or '0')
            garantia_liquida = Decimal(request.POST.get('garantia_liquida', '0').strip() or '0')
            aportacion_social = Decimal(request.POST.get('aportacion_social', '0').strip() or '0')

            errores = []
            if monto < 100:
                errores.append("El monto mínimo es $100.00")
            if tipo not in ['SEMANAL', 'MENSUAL']:
                errores.append("Tipo de préstamo inválido")
            if total_pagos < 1:
                errores.append("El número mínimo de pagos es 1")
                
            # Validaciones específicas por tipo
            if tipo == 'SEMANAL' and total_pagos > 520:
                errores.append("El máximo de pagos semanales es 520 (10 años)")
            elif tipo == 'MENSUAL' and total_pagos > 120:
                errores.append("El máximo de pagos mensuales es 120 (10 años)")
                
            if tasa_interes < Decimal('0.1') or tasa_interes > Decimal('30'):
                errores.append("La tasa debe estar entre 0.1% y 30%")

            if not errores:
                prestamo.cliente_id = cliente_id
                prestamo.monto = monto
                prestamo.tasa_interes = tasa_interes
                prestamo.tipo = tipo
                prestamo.total_pagos = total_pagos
                prestamo.estado = estado
                prestamo.iva_sobre_intereses = iva_sobre_intereses
                prestamo.garantia_liquida = garantia_liquida
                prestamo.aportacion_social = aportacion_social
                
                if estado == 'APROBADO' and prestamo.estado != 'APROBADO':
                    prestamo.fecha_aprobacion = timezone.now()
                elif estado != 'APROBADO':
                    prestamo.fecha_aprobacion = None
                
                prestamo.save()
                messages.success(request, 'Préstamo actualizado correctamente')
                return redirect('principalPrestamos')
            
            for error in errores:
                messages.error(request, error)
                
        except Exception as e:
            messages.error(request, f"Error al procesar los datos: {str(e)}")
    
    context = {
        'prestamo': prestamo,
        'clientes': clientes,
        'estados': Prestamo.ESTADO_CHOICES,
        'puede_editar': puede_editar
    }
    
    return render(request, 'editar_prestamo.html', context)



@login_required
def eliminar_prestamo(request, pk):
    prestamo = get_object_or_404(Prestamo, pk=pk)
    prestamo.delete()
    messages.success(request, 'Préstamo eliminado correctamente')
    return redirect('principalPrestamos')


@login_required
def detalle_prestamo(request, pk):
    prestamo = get_object_or_404(Prestamo, pk=pk)

    
    
    if not request.user.is_staff and prestamo.cliente.usuario != request.user:
        return HttpResponseForbidden("No tienes permiso para ver este préstamo")

    # Calcular tasa periódica ajustada (mensual o semanal)
    if prestamo.tipo == 'SEMANAL':
        tasa_periodo = (prestamo.tasa_interes / Decimal('100')) * (Decimal('7') / Decimal('30'))  # Tasa semanal
    else:
        tasa_periodo = prestamo.tasa_interes / Decimal('100')  # Tasa mensual

    garantia_monto = prestamo.monto * (prestamo.garantia_liquida / 100)
    iva_porc = prestamo.iva_sobre_intereses / Decimal('100')
    monto = prestamo.monto
    total_pagos = prestamo.total_pagos
    

    # Componentes fijos de cada pago
    abono_capital_base = monto / total_pagos
    interes_base = monto * tasa_periodo
    iva_base = interes_base * iva_porc
    cuota_base = abono_capital_base + interes_base + iva_base
    


    # Generar fechas de pagos
    fechas_pagos = []
    if prestamo.fecha_aprobacion:
        fecha_base = prestamo.fecha_aprobacion.date()
        
        if prestamo.tipo == 'SEMANAL':
            fecha_pago = fecha_base + relativedelta(weeks=1)
        else:
            fecha_pago = fecha_base + relativedelta(months=1)
                
                
        for _ in range(total_pagos):
            fechas_pagos.append(fecha_pago)
        
                # Calcular siguiente fecha
            if prestamo.tipo == 'SEMANAL':
                fecha_pago += relativedelta(weeks=1)
            else:
                fecha_pago += relativedelta(months=1)

    # Calcular detalle de pagos
    detalle_pagos = []
    saldo_restante = monto
    total_intereses = Decimal('0')
    total_iva = Decimal('0')
    multa_total = Decimal('0')

    for i, fecha_programada in enumerate(fechas_pagos):
        # Lógica de pagos realizados y multas (igual que antes)
        # Ordenar pagos por fecha y obtener por índice
        pagos_ordenados = list(prestamo.pagos.all().order_by('fecha_pago'))
        pago_realizado = pagos_ordenados[i] if i < len(pagos_ordenados) else None
        
        # Ajustar último pago para evitar decimales
        if i == total_pagos - 1:
            abono_capital = saldo_restante
            interes = interes_base
            iva = iva_base
            cuota = abono_capital + interes + iva
        else:
            abono_capital = abono_capital_base
            interes = interes_base
            iva = iva_base
            cuota = cuota_base

        # Calcular multas y actualizar saldos
        multa = Decimal('0')
        dias_atraso = 0
        if pago_realizado:
            if pago_realizado.fecha_pago.date() > fecha_programada:
                dias_atraso = (pago_realizado.fecha_pago.date() - fecha_programada).days
                multa = Decimal(dias_atraso) * Decimal('15')
        else:
            if timezone.now().date() > fecha_programada:
                dias_atraso = (timezone.now().date() - fecha_programada).days
                multa = Decimal(dias_atraso) * Decimal('15')
        
        multa_total += multa
        saldo_restante -= abono_capital
        total_intereses += interes
        total_iva += iva

        detalle_pagos.append({
            'numero': i + 1,
            'fecha_programada': fecha_programada,
            'abono_capital': float(abono_capital.quantize(Decimal('0.01'))),
            'interes': float(interes.quantize(Decimal('0.01'))),
            'iva': float(iva.quantize(Decimal('0.01'))),
            'total': float(cuota.quantize(Decimal('0.01'))),
            'realizado': pago_realizado is not None,
            'pago': pago_realizado,
            'dias_atraso': dias_atraso,
            'multa': float(multa)
        })

    context = {
        'prestamo': prestamo,
        'garantia_monto': garantia_monto, 
        'detalle_pagos': detalle_pagos,
        'multa_total': float(multa_total.quantize(Decimal('0.01'))),
        'total_pagado': float(prestamo.total_pagado),
        'saldo_pendiente': float(saldo_restante.quantize(Decimal('0.01'))),
        'total_intereses': float(total_intereses.quantize(Decimal('0.01'))),
        'total_iva': float(total_iva.quantize(Decimal('0.01'))),
        'total_a_pagar': float((monto + total_intereses + total_iva).quantize(Decimal('0.01')))
    }
    
    return render(request, 'detalle_prestamo.html', context)

    def actualizar_estado_pagos(self):
        """Actualiza el estado de las cuotas relacionadas"""
        pagos = self.pagos.all().order_by('fecha_pago')
        
        for pago in pagos:
            cuota = self.cuotas_plan.filter(
                estado__in=['PENDIENTE', 'PARCIAL']
            ).order_by('fecha_vencimiento').first()
            
            if cuota:
                cuota.monto_pagado += pago.monto_pago
                cuota.saldo_pendiente = cuota.total_cuota - cuota.monto_pagado
                cuota.estado = 'PAGADO' if cuota.saldo_pendiente == 0 else 'PARCIAL'
                cuota.save()