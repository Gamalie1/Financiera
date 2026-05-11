from django.shortcuts import render, redirect, get_object_or_404
from .models import Pago, Prestamo, Abono
from Clientes.models import Comunidad
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal , InvalidOperation
from django.db import transaction
from dateutil.relativedelta import relativedelta  
from django.utils import timezone
from django.db.models import Sum
from django.template.loader import get_template
from weasyprint import HTML
from django.http import HttpResponse
import calendar
from num2words import num2words
from django.utils.timezone import localtime
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
import qrcode
import base64
import platform
from django.http import HttpResponse
from weasyprint import HTML
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count



@login_required
def pagosPrincipal(request):
    buscar = request.GET.get('buscar')
    es_grupal = request.GET.get('es_grupal')
    estado = request.GET.get('estado')
    con_atrasos = request.GET.get('con_atrasos')

    # Base: préstamos según rol
    if request.user.is_staff:
        prestamos = Prestamo.objects.all()
    else:
        prestamos = Prestamo.objects.filter(promotor=request.user)

    # ========== NUEVO: Excluir préstamos ya pagados ==========
    prestamos = prestamos.exclude(estado='PAGADO')  # También podrías excluir 'LIQUIDADO' si existe

    prestamos = prestamos.select_related('cliente', 'grupo')

    # Filtro grupal
    if es_grupal == 'true':
        prestamos = prestamos.filter(es_grupal=True)

    # Filtro por estado del préstamo (solo los que aún están activos, ej. APROBADO, SOLICITADO)
    if estado:
        prestamos = prestamos.filter(estado=estado)

    # Búsqueda
    if buscar:
        prestamos = prestamos.filter(
            Q(cliente__nombre__icontains=buscar) |
            Q(folio__icontains=buscar) |
            Q(grupo__nombre__icontains=buscar)
        )

    # Anotar número de cuotas atrasadas por préstamo
    hoy = timezone.now().date()
    prestamos = prestamos.annotate(
        cuotas_atrasadas=Count(
            'pagos',
            filter=Q(pagos__estado_pago__in=['pendiente', 'parcial'],
                     pagos__fecha_programada__lt=hoy)
        )
    )

    # Filtro por préstamos con/sin cuotas atrasadas
    if con_atrasos == 'si':
        prestamos = prestamos.filter(cuotas_atrasadas__gt=0)
    elif con_atrasos == 'no':
        prestamos = prestamos.filter(cuotas_atrasadas=0)

    # Estadísticas (solo sobre los préstamos no pagados, que son los que se muestran)
    aprobados_count = prestamos.filter(estado='APROBADO').count()
    solicitados_count = prestamos.filter(estado='SOLICITADO').count()
    total_atrasadas = prestamos.aggregate(total=Sum('cuotas_atrasadas'))['total'] or 0

    context = {
        'prestamos': prestamos,
        'tipo_actual': es_grupal,
        'aprobados_count': aprobados_count,
        'solicitados_count': solicitados_count,
        'total_atrasadas': total_atrasadas,
    }
    return render(request, 'pagos.html', context)


@login_required
def tiket_generico(request):
    return render(request, 'tiket_generico.html')

def parse_decimal(value, default=Decimal('0')):
    """Convierte un valor a Decimal, devolviendo default si falla."""
    if not value or str(value).strip() == '':
        return default
    try:
        # Reemplazar coma por punto por si el usuario escribe "1,234.56"
        cleaned = str(value).replace(',', '')
        return Decimal(cleaned)
    except (InvalidOperation, ValueError, TypeError):
        return default

@login_required
def create_pago(request, id):
    pago = get_object_or_404(Pago, id=id)
    prestamo = pago.prestamo
    cliente = prestamo.cliente

    total_abonado = pago.abonos.aggregate(total=Sum('monto'))['total'] or Decimal('0')
    saldo_actual = pago.monto_pago - total_abonado

    if request.method == 'POST':
        es_pago_rapido = request.POST.get('pago_rapido') == '1'
        usar_ahorro = request.POST.get('usar_ahorro') == '1'
        # Conversión segura
        monto_ahorro_usar = parse_decimal(request.POST.get('monto_ahorro_usar', 0))

        if es_pago_rapido:
            monto_abono = saldo_actual
            metodo_pago = 'EFECTIVO'
            ahorro_depositado = Decimal('0')
            comentario = ''
            monto_ahorro_usar = Decimal('0')
            usar_ahorro = False
        else:
            monto_abono = parse_decimal(request.POST.get('monto_pagado', 0))
            ahorro_depositado = parse_decimal(request.POST.get('ahorro', 0))
            metodo_pago = request.POST.get('metodo_pago')
            comentario = request.POST.get('comentarios', '').strip()

        # Validaciones
        total_pagado = monto_abono + monto_ahorro_usar
        if total_pagado <= 0:
            messages.error(request, "Debe especificar un monto (en efectivo o usando ahorro).")
            return redirect(request.path)  # Cambiado para evitar NoReverseMatch

        if total_pagado > saldo_actual:
            messages.error(request, f"El total a pagar (${total_pagado}) supera el saldo de la cuota (${saldo_actual}).")
            return redirect(request.path)

        if not es_pago_rapido and not metodo_pago and monto_abono > 0:
            messages.error(request, "Debe seleccionar un método de pago para el abono en efectivo.")
            return redirect(request.path)

        if usar_ahorro and monto_ahorro_usar > 0:
            if monto_ahorro_usar > cliente.saldo_ahorro:
                messages.error(request, f"No tiene suficiente ahorro. Saldo disponible: ${cliente.saldo_ahorro:.2f}.")
                return redirect(request.path)

        with transaction.atomic():
            # 1) Abono en efectivo/tarjeta
            if monto_abono > 0:
                Abono.objects.create(
                    pago=pago,
                    monto=monto_abono,
                    ahorro=ahorro_depositado,
                    metodo_pago=metodo_pago,
                    cobrador=request.user,
                    comentario=comentario if comentario else None
                )
            # Depósito de ahorro (independiente del abono)
            if ahorro_depositado > 0:
                cliente.saldo_ahorro += ahorro_depositado
                cliente.save()
                # Si solo depositó ahorro y no hizo abono, crear un registro
                if monto_abono == 0:
                    Abono.objects.create(
                        pago=pago,
                        monto=0,
                        ahorro=ahorro_depositado,
                        metodo_pago=metodo_pago or 'EFECTIVO',
                        cobrador=request.user,
                        comentario="Depósito de ahorro"
                    )
            # 2) Uso de ahorro para pagar (abono aparte)
            if usar_ahorro and monto_ahorro_usar > 0:
                Abono.objects.create(
                    pago=pago,
                    monto=monto_ahorro_usar,
                    ahorro=Decimal('0'),
                    metodo_pago='AHORRO',
                    cobrador=request.user,
                    comentario=f"Pago con ahorro. Saldo anterior: ${cliente.saldo_ahorro:.2f}"
                )
                cliente.saldo_ahorro -= monto_ahorro_usar
                cliente.save()

        # Recalcular estado del pago
        nuevo_total_abonado = pago.abonos.aggregate(total=Sum('monto'))['total'] or Decimal('0')
        nuevo_saldo = pago.monto_pago - nuevo_total_abonado
        pago.saldo_restante = max(nuevo_saldo, 0)
        pago.estado_pago = 'pagado' if pago.saldo_restante == 0 else 'parcial'
        pago.save()
        prestamo.verificar_y_actualizar_estado()

        messages.success(request, "Abono registrado correctamente")
        return redirect('detalle_pago', prestamo_id=prestamo.id)

    # GET
    saldo_ahorro_cliente = cliente.saldo_ahorro if cliente.saldo_ahorro is not None else Decimal('0')
    return render(request, 'create_pago.html', {
        'pago': pago,
        'saldo_ahorro_cliente': saldo_ahorro_cliente,
    })
@login_required
def editar_pago(request, id): 
    pago = get_object_or_404(Pago, id=id)
    prestamo = pago.prestamo  

    if request.method == 'POST':
        try:
            # ---- MONTO PAGADO ----
            monto_pagado = Decimal(request.POST.get('monto_pagado', 0))

            # ---- FECHA REAL QUE PAGÓ EL CLIENTE ----
            fecha_real = request.POST.get('fecha_pago')
            fecha_real = datetime.strptime(fecha_real, "%Y-%m-%d").date()

            # ---- FECHA PROGRAMADA DEL SISTEMA ----
            fecha_programada = request.POST.get('fecha_programada')
            fecha_programada = datetime.strptime(fecha_programada, "%Y-%m-%d").date()

            pago.metodo_pago = request.POST.get('metodo_pago')
            pago.comentarios = request.POST.get('comentarios', '').strip()

            # Asignar usuario
            pago.cobrador = request.user

            # ======================================================
            #            CALCULO — SALDO RESTANTE
            # ======================================================
            saldo_restante = pago.monto_pago - monto_pagado

            # Evitar saldo negativo por error del usuario
            if saldo_restante < 0:
                saldo_restante = Decimal('0.00')

            pago.saldo_restante = saldo_restante


            # ======================================================
            #            DIAS TRANSCURRIDOS
            # ======================================================
            dias = (fecha_programada - pago.fecha_pago.date()).days

            # Que nunca sea negativo
            if dias < 0:
                dias = 0

            


            # ======================================================
            #            ESTADO DEL PAGO
            # ======================================================
           # ----- ESTADO DEL PAGO -----
            if saldo_restante == 0:
                estado_pago = 'pagado'
                pago_parcial = False
            elif monto_pagado == 0:
                estado_pago = 'pendiente'
                pago_parcial = False
            else:
                pago.estado = 'Pago parcial'
                pago.pago_parcial = True


            # Guardar cambios
            pago.fecha_programada = fecha_programada
            pago.pago_parcial = pago_parcial
            pago.dias_transcurridos = dias
            pago.monto_pagado = monto_pagado
            pago.estado_pago = estado_pago
            pago.fecha_pago = fecha_real
            pago.save()

            messages.success(request, 'Pago actualizado exitosamente')
            return redirect('detalle_pago', prestamo_id=prestamo.id)

        except Exception as e:
            messages.error(request, f'Error al actualizar pago: {str(e)}')

    return render(request, 'editar_pago.html', {
        'pago': pago,
        'prestamo': prestamo,
        'fecha_programada': pago.fecha_programada  # <-- AÑADIR
    })


@require_POST
def eliminar_pago(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    try:
        pago.delete()
        messages.success(request, 'Pago eliminado correctamente')
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def detalle_pago(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    pagos = Pago.objects.filter(prestamo=prestamo).order_by('numero_pago')
    
    # Total pagado sumando todos los abonos del préstamo
    total_pagado = Abono.objects.filter(pago__prestamo=prestamo).aggregate(total=Sum('monto'))['total'] or Decimal('0')
    
    # Saldo pendiente
    saldo_pendiente = prestamo.monto - total_pagado
    
    # Cuotas pagadas
    cuotas_pagadas = pagos.filter(estado_pago='pagado').count()
    
    # Cuotas atrasadas
    hoy = timezone.now().date()
    cuotas_atrasadas = pagos.filter(
        estado_pago__in=['pendiente', 'parcial'],
        fecha_programada__lt=hoy
    ).count()
    
    # Totales para el pie de tabla
    total_abonado_general = total_pagado
    total_saldo_general = pagos.aggregate(total=Sum('saldo_restante'))['total'] or Decimal('0')
    # ✅ Obtener el ahorro acumulado directamente del cliente
    cliente = prestamo.cliente
    saldo_ahorro = cliente.saldo_ahorro if cliente and cliente.saldo_ahorro is not None else Decimal('0')

    context = {
        'prestamo': prestamo,
        'pagos': pagos,
        'total_pagado': total_pagado,
        'saldo_pendiente': saldo_pendiente,
        'cuotas_pagadas': cuotas_pagadas,
        'cuotas_atrasadas': cuotas_atrasadas,
        'total_abonado_general': total_abonado_general,
        'total_saldo_general': total_saldo_general,
        'total_ahorro': saldo_ahorro,      # <-- aquí el campo saldo_ahorro
    }
    return render(request, 'detalle_pago.html', context)



def fecha_a_letras(fecha):
    """Convierte una fecha en formato 'día de mes de año, día de la semana' en español."""
    # Convertir la fecha en formato 'día de mes de año'
    dia_semana = fecha.strftime("%A")  # Obtener el día de la semana
    fecha_letras = fecha.strftime("%d de %B de %Y")  # Fecha en formato "7 de junio de 2025"
    return f"{dia_semana}, {fecha_letras}"


def generar_ticket(request, id):

    pago = get_object_or_404(Pago, id=id)

    # ✅ Obtener todos los abonos del pago
    abonos = pago.abonos.all()

    if not abonos.exists():
        return HttpResponse(
            "Este pago aún no tiene abonos registrados.",
            status=400
        )

    # ✅ Suma total de abonos
    total_abonado = abonos.aggregate(
        total=Sum('monto')
    )['total']

    # ✅ Último abono (para la fecha)
    ultimo_abono = abonos.order_by('-fecha').first()
    fecha_local = ultimo_abono.fecha

    meses = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
        5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
        9: 'septiembre', 10: 'octubre',
        11: 'noviembre', 12: 'diciembre'
    }

    fecha_en_letras = (
        f"{fecha_local.day} de {meses[fecha_local.month]} "
        f"de {fecha_local.year}"
    ).upper()

    # ✅ Convertir monto a letras
    monto_letras = num2words(total_abonado, lang='es').capitalize()
    monto_letras = f"{monto_letras} pesos 00/100 M.N."

    ticket_data = {
        'numero_ticket': pago.numero_pago,
        'fecha': fecha_en_letras,
        'cliente': pago.prestamo.cliente.nombre,
        'monto': total_abonado,
        'monto_letras': monto_letras,
    }

    template = get_template('ticket_template.html')
    html = template.render(ticket_data)

    pdf_file = HTML(
        string=html,
        base_url=request.build_absolute_uri()
    ).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="ticket_pago_{pago.id}.pdf"'
    )
    return response

def money_to_text_es(amount: Decimal) -> str:
    """
    Convierte un Decimal a texto en español con centavos.
    1234.50 -> 'Mil doscientos treinta y cuatro pesos 50/100 M.N.'
    """
    amount = (amount or Decimal('0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    entero = int(amount)
    centavos = int((amount - Decimal(entero)) * 100)
    entero_txt = num2words(entero, lang='es')
    return f"{entero_txt.capitalize()} pesos {centavos:02d}/100 M.N."

@login_required
def generar_ticke2(request, id):

    pago = get_object_or_404(Pago, id=id)

    # ✅ Obtener abonos del pago
    abonos = pago.abonos.all()

    if not abonos.exists():
        return HttpResponse(
            "Este pago aún no tiene abonos registrados.",
            status=400
        )

    # ✅ Suma total de abonos
    total_abonado = abonos.aggregate(
        total=Sum('monto')
    )['total']

    total_abonado = Decimal(total_abonado).quantize(
        Decimal('0.01'),
        rounding=ROUND_HALF_UP
    )

    # ✅ Último abono (para la fecha)
    ultimo_abono = abonos.order_by('-fecha').first()
    fecha_local = localtime(ultimo_abono.fecha)

    empresa = {
        "nombre": "UNIÓN DE SOCIEDADES CIVILES FINANCIERAS",
        "domicilio": "Calle 5 de febrero #414, Centro, Miahuatlan de Porfirio Diaz, Oaxaca",
        "telefono": "9512316895 Y 9515812486",
    }

    # ---------------------------
    # Fecha en letras
    # ---------------------------
    meses = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
        5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
        9: 'septiembre', 10: 'octubre',
        11: 'noviembre', 12: 'diciembre'
    }

    fecha_en_letras = (
        f"{fecha_local.day} de {meses[fecha_local.month]} "
        f"de {fecha_local.year}"
    ).upper()

    # ---------------------------
    # Monto en letras
    # ---------------------------
    monto_letras = money_to_text_es(total_abonado)

    # ---------------------------
    # Folio
    # ---------------------------
    folio = f"{pago.numero_pago or pago.id}".zfill(6)

    # ---------------------------
    # Cliente
    # ---------------------------
    cliente_nombre = getattr(
        pago.prestamo.cliente, "nombre", "CLIENTE"
    )
    cliente_clave = getattr(
        pago.prestamo.cliente, "clave", ""
    )

    cliente_linea = (
        f"{cliente_nombre}"
        + (f" ({cliente_clave})" if cliente_clave else "")
    )

    # ---------------------------
    # Cajero
    # ---------------------------
    cajero = (
        request.user.username
        if request.user.is_authenticated
        else "SISTEMA"
    )

    # ---------------------------
    # QR
    # ---------------------------
    qr_payload = (
        f"FOLIO:{folio}"
        f"|FECHA:{fecha_local.strftime('%Y-%m-%d %H:%M')}"
        f"|CLIENTE:{cliente_nombre}"
        f"|MONTO:{total_abonado}"
    )

    qr_img = qrcode.make(qr_payload)
    buffer = BytesIO()
    qr_img.save(buffer, format="PNG")

    qr_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    qr_data_uri = f"data:image/png;base64,{qr_b64}"

    context = {
        "empresa": empresa,
        "folio": folio,
        "fecha": fecha_en_letras,
        "fecha_corta": fecha_local.strftime("%d/%m/%Y"),
        "cliente": cliente_linea,
        "monto": f"{total_abonado:.2f}",
        "monto_letras": monto_letras,
        "concepto": f"TOTAL ABONADO {pago.numero_pago}",
        "lugar": "MIAHUATLÁN DE PORFIRIO DÍAZ, OAXACA",
        "cajero": cajero.upper(),
        "qr_data_uri": qr_data_uri,
    }

    template = get_template("ticket_58mm.html")
    html = template.render(context)

    pdf = HTML(
        string=html,
        base_url=request.build_absolute_uri()
    ).write_pdf()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp['Content-Disposition'] = (
        f'inline; filename="ticket_pago_{pago.id}.pdf"'
    )

    return resp
    
@login_required
def generar_ticket_generico(request):
    if request.method == 'POST':
        # Recibir los datos del formulario
        cliente = request.POST['cliente']
        monto = request.POST['monto']
        numero_ticket = request.POST['numero_ticket']
        fecha = request.POST['fecha']

        # Verificar que los datos están llegando correctamente
        print(f"Cliente: {cliente}, Monto: {monto}, Número de Ticket: {numero_ticket}, Fecha: {fecha}")

        # Convertir el monto a tipo float
        try:
            monto = float(monto)
        except ValueError:
            return HttpResponse("El monto no es un número válido.", status=400)

        # Convertir la fecha a un objeto datetime
        try:
            fecha_pago = timezone.datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            return HttpResponse("La fecha no tiene un formato válido.", status=400)

        # Generar la fecha en letras
        meses = {
            1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
            7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
        }
        dia = fecha_pago.day
        mes = fecha_pago.month
        año = fecha_pago.year
        fecha_en_letras = f"{dia} de {meses[mes]} de {año}".upper()

        # Convertir monto a letras en español
        monto_letras = num2words(monto, lang='es').capitalize()
        monto_letras = f"{monto_letras} pesos 00/100 M.N."

        # Preparar los datos para la plantilla del ticket
        ticket_data = {
            'numero_ticket': numero_ticket,
            'fecha': fecha_en_letras,
            'cliente': cliente,
            'monto': monto,
            'monto_letras': monto_letras,
        }

        # Renderizar la plantilla HTML del ticket
        template = get_template('ticket_template.html')
        html = template.render(ticket_data)

        # Generar el PDF con WeasyPrint
        html_content = HTML(string=html, base_url=request.build_absolute_uri())
        pdf_file = html_content.write_pdf()

        # Verifica que el PDF se está generando correctamente
        if pdf_file:
            print(f"PDF generado correctamente para el ticket {numero_ticket}")
        else:
            print("Error al generar el PDF.")

        # Devolver el PDF como respuesta HTTP
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="ticket_pago_{numero_ticket}.pdf"'

        return response
    
@login_required   
def imprimir_ticket(request):
    if request.method == "POST":
        # Recibir los datos del formulario
        cliente = request.POST.get('cliente')
        monto = request.POST.get('monto')
        numero_ticket = request.POST.get('numero_ticket')
        fecha = request.POST.get('fecha')

        # Validación de que la fecha no esté vacía
        if not fecha:  # Verifica si 'fecha' está vacío
            messages.error(request, "La fecha no puede estar vacía.")
            return redirect('ruta_del_formulario')  # Redirige a la página del formulario

        # Validar el formato de la fecha
        try:
            fecha_local = datetime.strptime(fecha, '%Y-%m-%d')  # Convertir a fecha
        except ValueError:
            messages.error(request, "El formato de la fecha es incorrecto. Usa el formato YYYY-MM-DD.")
            return redirect('ruta_del_formulario')  # Redirige a la página del formulario

        # Si la fecha es válida, el resto del procesamiento sigue igual
        empresa = {
            "nombre": "UNIÓN DE SOCIEDADES CIVILES FINANCIERAS",
            "domicilio": "Calle 5 de febrero #414, Centro, Miahuatlan de Porfirio Diaz, Oaxaca",
            "telefono": "9512316895 Y 9515812486",
        }

        # Convertir la fecha a texto
        meses = {
            1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
            7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
        }
        dia = fecha_local.day
        mes = meses[fecha_local.month]
        año = fecha_local.year
        fecha_en_letras = f"{dia} de {mes} de {año}".upper()

        # Monto
        monto_decimal = Decimal(monto).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        monto_letras = money_to_text_es(monto_decimal)

        # Cliente
        cliente_linea = f"{cliente}"

        # Cajero
        cajero = request.user.username if request.user.is_authenticated else "SISTEMA"

        # Generación del QR
        qr_payload = f"FOLIO:{numero_ticket}|FECHA:{fecha_local.strftime('%Y-%m-%d %H:%M')}|CLIENTE:{cliente}|MONTO:{monto_decimal}"
        qr_img = qrcode.make(qr_payload)
        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")
        qr_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        qr_data_uri = f"data:image/png;base64,{qr_b64}"

        # Datos para el contexto de la plantilla
        context = {
            "empresa": empresa,
            "folio": numero_ticket,
            "fecha": fecha_en_letras,
            "fecha_corta": fecha_local.strftime("%d/%m/%Y"),
            "cliente": cliente_linea,
            "monto": f"{monto_decimal:.2f}",
            "monto_letras": monto_letras,
            "concepto": f"ABONO {numero_ticket}",
            "lugar": "MIAHUATLÁN DE PORFIRIO DÍAZ, OAXACA",
            "cajero": cajero.upper(),
            "qr_data_uri": qr_data_uri,
        }

        # Renderizar la plantilla HTML
        template = get_template("ticket_58mm.html")
        html = template.render(context)

        # Generación del archivo PDF
        pdf = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf()

        # Retornar el archivo PDF como respuesta
        resp = HttpResponse(pdf, content_type="application/pdf")
        resp['Content-Disposition'] = f'inline; filename="ticket_pago_{numero_ticket}.pdf"'
        
        return resp
    

@login_required
def poner_al_corriente(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    hoy = timezone.now().date()
    
    # Obtener solo cuotas vencidas (fecha programada < hoy y estado pendiente o parcial)
    cuotas_atraso = prestamo.pagos.filter(
        fecha_programada__lt=hoy,
        estado_pago__in=['pendiente', 'parcial']
    ).order_by('fecha_programada')
    
    total_adeudado = cuotas_atraso.aggregate(total=Sum('saldo_restante'))['total'] or Decimal('0')
    
    if request.method == 'POST':
        # Validar método de pago
        metodo_pago = request.POST.get('metodo_pago')
        if not metodo_pago:
            messages.error(request, "Debes seleccionar un método de pago.")
            return redirect('poner_al_corriente', prestamo_id=prestamo.id)
        
        # Obtener monto total a pagar (del formulario oculto) con validación segura
        monto_total_str = request.POST.get('monto_total', '').strip()
        if not monto_total_str:
            messages.error(request, "No se pudo determinar el monto total a pagar.")
            return redirect('poner_al_corriente', prestamo_id=prestamo.id)
        
        try:
            monto_recibido = Decimal(monto_total_str)
        except InvalidOperation:
            messages.error(request, "El monto total no es válido. Por favor, intente de nuevo.")
            return redirect('poner_al_corriente', prestamo_id=prestamo.id)
        
        # Validar que el monto recibido sea al menos el total adeudado
        if monto_recibido < total_adeudado:
            messages.error(request, f"Debes pagar al menos ${total_adeudado:.2f} para cubrir todas las cuotas vencidas.")
            return redirect('poner_al_corriente', prestamo_id=prestamo.id)
        
        # Obtener ahorro y comentario
        ahorro_str = request.POST.get('ahorro', '0').strip()
        ahorro = Decimal(ahorro_str) if ahorro_str else Decimal('0')
        comentario = request.POST.get('comentarios', '').strip()
        
        # Crear abonos para cada cuota vencida (usar transacción atómica)
        from django.db import transaction
        with transaction.atomic():
            for pago in cuotas_atraso:
                # El monto a abonar es el saldo restante de la cuota
                monto_abono = pago.saldo_restante
                # Asignar ahorro solo a la primera cuota (la más antigua)
                ahorro_parcial = ahorro if pago == cuotas_atraso.first() else Decimal('0')
                Abono.objects.create(
                    pago=pago,
                    monto=monto_abono,
                    ahorro=ahorro_parcial,
                    metodo_pago=metodo_pago,
                    cobrador=request.user,
                    comentario=f"[Poner al corriente - vencidas] {comentario}" if comentario else "Poner al corriente (cuotas vencidas)"
                )
                # Actualizar el pago
                pago.saldo_restante = Decimal('0')
                pago.estado_pago = 'pagado'
                pago.save()
            # Actualizar estado del préstamo
            prestamo.verificar_y_actualizar_estado()
        
        messages.success(request, f"Se han pagado {len(cuotas_atraso)} cuotas vencidas. Total pagado: ${total_adeudado:.2f}")
        return redirect('detalle_pago',  prestamo_id=pago.prestamo.id)
    
    context = {
        'prestamo': prestamo,
        'total_adeudado': total_adeudado,
        'cuotas_atraso': cuotas_atraso,
        'today': hoy,   # ← AÑADE ESTA LÍNEA
    }
    return render(request, 'poner_al_corriente.html', context)

@login_required
def reporte_diario(request):
    # Obtener fecha del GET o usar hoy
    fecha_str = request.GET.get('fecha')
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else timezone.now().date()
    except ValueError:
        fecha = timezone.now().date()

    comunidad_id = request.GET.get('comunidad')

    # 1. Abonos realizados exactamente en esa fecha (sin importar la hora)
    abonos_dia = Abono.objects.filter(fecha__date=fecha).select_related(
        'pago__prestamo__cliente', 'cobrador'
    )

    # 2. Pagos (cuotas) programados para esa fecha que NO estén completamente pagados
    pagos_programados = Pago.objects.filter(
        fecha_programada=fecha,
        estado_pago__in=['pendiente', 'parcial']
    ).select_related('prestamo__cliente')

    # Filtro por comunidad (si se seleccionó)
    if comunidad_id:
        abonos_dia = abonos_dia.filter(pago__prestamo__cliente__comunidad_id=comunidad_id)
        pagos_programados = pagos_programados.filter(prestamo__cliente__comunidad_id=comunidad_id)

    total_abonado = abonos_dia.aggregate(total=Sum('monto'))['total'] or Decimal('0')
    total_pendiente = pagos_programados.aggregate(total=Sum('saldo_restante'))['total'] or Decimal('0')

    # Lista de comunidades para el filtro
    comunidades = Comunidad.objects.all().order_by('nombre')

    context = {
        'fecha': fecha,
        'abonos_dia': abonos_dia,
        'pagos_programados': pagos_programados,
        'total_abonado': total_abonado,
        'total_pendiente': total_pendiente,
        'comunidades': comunidades,
        'comunidad_seleccionada': comunidad_id,
    }
    return render(request, 'reporte_diario.html', context)


@login_required
def liquidar_prestamo(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    
    if request.method == 'POST':
        # Buscar todas las cuotas pendientes o parciales de este préstamo
        cuotas_pendientes = prestamo.pagos.filter(estado_pago__in=['pendiente', 'parcial'])
        
        if not cuotas_pendientes:
            messages.warning(request, 'Este préstamo no tiene cuotas pendientes.')
            return redirect(request.META.get('HTTP_REFERER', 'reporte_diario'))

        # Determinar método de pago (puedes dejar un valor fijo o permitir selección en un modal)
        metodo_pago = request.POST.get('metodo_pago', 'EFECTIVO')
        comentario = f"Liquidación total del préstamo el {timezone.now().date()}"
        
        from django.db import transaction
        with transaction.atomic():
            for pago in cuotas_pendientes:
                saldo = pago.saldo_restante
                if saldo > 0:
                    Abono.objects.create(
                        pago=pago,
                        monto=saldo,
                        fecha=timezone.now(),
                        metodo_pago=metodo_pago,
                        cobrador=request.user,
                        comentario=comentario
                    )
            # Mensaje de éxito
            messages.success(
                request, 
                f'Préstamo #{prestamo.id} liquidado. Se registraron abonos por ${prestamo.saldo_pendiente} con fecha {timezone.now().date()}.'
            )
        return redirect(request.META.get('HTTP_REFERER', 'reporte_diario'))
    
    return redirect('reporte_diario')

@login_required
def pagar_cuota_individual(request, pago_id):
    """
    Registra un abono por el saldo restante de una cuota específica.
    No afecta otras cuotas del mismo préstamo.
    """
    pago = get_object_or_404(Pago, id=pago_id)
    
    # Verificar que la cuota no esté ya pagada
    if pago.estado_pago == 'pagado':
        messages.warning(request, f'La cuota #{pago.numero_pago} ya está pagada.')
        return redirect(request.META.get('HTTP_REFERER', 'reporte_diario'))
    
    # Obtener el saldo restante (cuánto falta para completar esta cuota)
    saldo_pendiente_cuota = pago.saldo_restante
    
    if saldo_pendiente_cuota <= 0:
        messages.warning(request, f'La cuota #{pago.numero_pago} no tiene saldo pendiente.')
        return redirect(request.META.get('HTTP_REFERER', 'reporte_diario'))
    
    if request.method == 'POST':
        # Puedes permitir elegir método de pago o usar uno por defecto
        metodo_pago = request.POST.get('metodo_pago', 'EFECTIVO')
        comentario = f"Pago de cuota #{pago.numero_pago} el {timezone.now().date()}"
        
        from django.db import transaction
        with transaction.atomic():
            # Crear el abono por el monto exacto del saldo restante de esta cuota
            Abono.objects.create(
                pago=pago,
                monto=saldo_pendiente_cuota,
                fecha=timezone.now(),
                metodo_pago=metodo_pago,
                cobrador=request.user,
                comentario=comentario
            )
            # La señal actualizará automáticamente el estado del Pago (a 'pagado' si saldo_restante = 0)
            # Y también actualizará el estado general del préstamo (verificar_y_actualizar_estado)
        
        messages.success(
            request,
            f'Cuota #{pago.numero_pago} del préstamo #{pago.prestamo.id} pagada con éxito. Monto: ${saldo_pendiente_cuota}'
        )
        return redirect(request.META.get('HTTP_REFERER', 'reporte_diario'))
    
    # Si no es POST, redirigir (por seguridad)
    return redirect('reporte_diario')