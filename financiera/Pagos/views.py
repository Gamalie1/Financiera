from django.shortcuts import render, redirect, get_object_or_404
from .models import Pago, Prestamo, Abono
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal  
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
from datetime import datetime 
from django.contrib.auth.decorators import login_required
from django.db.models import Q



@login_required
def pagosPrincipal(request):

    buscar = request.GET.get('buscar')
    es_grupal = request.GET.get('es_grupal')

    # ==============================
    # FILTRO POR USUARIO
    # ==============================
    if request.user.is_staff:
        prestamos = Prestamo.objects.all()
    else:
        prestamos = Prestamo.objects.filter(
            promotor=request.user
        )

    prestamos = prestamos.select_related('cliente')

    # ==============================
    # FILTRO GRUPAL
    # ==============================
    if es_grupal == 'true':
        prestamos = prestamos.filter(es_grupal=True)

    # ==============================
    # BUSCADOR
    # ==============================
    if buscar:
        prestamos = prestamos.filter(
            Q(cliente__nombre__icontains=buscar) |
            Q(folio__icontains=buscar)
        )

    context = {
        'prestamos': prestamos,
        'tipo_actual': es_grupal
    }

    return render(request, 'pagos.html', context)
@login_required
def tiket_generico(request):
    return render(request, 'tiket_generico.html')



@login_required
def create_pago(request, id):

    pago = get_object_or_404(Pago, id=id)

    if request.method == 'POST':

        monto_abono = Decimal(request.POST.get('monto_pagado'))

        if monto_abono <= 0:
            messages.error(request, "El monto debe ser mayor a 0")
            return redirect('create_pago', id=id)
          # 2️⃣ Validar que no exceda el saldo restante
        total_abonado = pago.abonos.aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0')

        saldo_restante = pago.monto_pago - total_abonado

        if monto_abono > saldo_restante:
            messages.error(request, f"No puedes abonar más de {saldo_restante}")
            return redirect('createPago', id=id)

        # Guardar ABONO
        Abono.objects.create(
            pago=pago,
            monto=monto_abono,
            metodo_pago=request.POST.get('metodo_pago'),
            cobrador=request.user
        )

        # ---- RECALCULAR TOTALES ----

        total_abonado = pago.abonos.aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0')

        saldo_restante = pago.monto_pago - total_abonado

        # ---- ESTADO ----

        if saldo_restante <= 0:
            pago.estado_pago = 'pagado'
            pago.pago_parcial = False
            saldo_restante = 0
        else:
            pago.estado_pago = 'parcial'
            pago.pago_parcial = True

        pago.saldo_restante = saldo_restante
        pago.save()

        messages.success(request, "Abono registrado correctamente")
        return redirect('detalle_pago', prestamo_id=pago.prestamo.id)

    return render(request, 'create_pago.html', {'pago': pago})

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


def detalle_pago(request, prestamo_id):

    prestamo = get_object_or_404(Prestamo, id=prestamo_id)

    pagos = Pago.objects.filter(
        prestamo=prestamo
    ).order_by('numero_pago')

    context = {
        'prestamo': prestamo,
        'pagos': pagos
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