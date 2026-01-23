from django.shortcuts import render, redirect, get_object_or_404
from .models import Pago, Prestamo
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



@login_required
def pagosPrincipal(request):
    if request.user.is_staff:
        # Admin ve todos los préstamos
        prestamos = Prestamo.objects.select_related('cliente').all()
    else:
        # Empleado solo ve los préstamos donde es cobrador asignado
        prestamos = Prestamo.objects.filter(
            promotor=request.user
        ).select_related('cliente')

    context = {'prestamos': prestamos}
    return render(request, 'pagos.html', context)
@login_required
def tiket_generico(request):
    return render(request, 'tiket_generico.html')



@login_required
def create_pago(request, id):
    pago = get_object_or_404(Pago, id=id)

    if request.method == 'POST':
        try:
            # Lo que pagó el cliente
            monto_pagado = Decimal(request.POST.get('monto_pagado'))

            # Validar que sea mayor a 0
            if monto_pagado <= 0:
                messages.error(request, "El monto pagado debe ser mayor a 0.")
                return redirect('create_pago', id=id)

            # Fecha real del cliente
            fecha_programada = request.POST.get('fecha_programada')
            fecha_programada_real = datetime.strptime(fecha_programada, "%Y-%m-%d").date()

            prestamo = pago.prestamo
            pago.cobrador = request.user

            # ----- CÁLCULO DEL SALDO RESTANTE -----
            saldo_restante = pago.monto_pago - monto_pagado


            # ----- DIAS TRANSCURRIDOS -----
            dias_transcurridos = (fecha_programada_real - pago.fecha_pago.date()).days

           
            # ----- ESTADO DEL PAGO -----
            if saldo_restante == 0:
                estado_pago = 'pagado'
                pago_parcial = False
            else:
                estado_pago = 'pendiente'
                pago_parcial = True

            # ----- GUARDAR DATOS -----
            pago.monto_pagado = monto_pagado
            pago.saldo_restante = saldo_restante
            pago.pago_parcial = pago_parcial
            pago.metodo_pago = request.POST.get('metodo_pago')
            pago.fecha_programada = fecha_programada_real
            pago.dias_transcurridos = dias_transcurridos
            pago.estado_pago = estado_pago
            pago.comentarios = request.POST.get('comentarios', '').strip()

            pago.save()

            messages.success(request, "Pago registrado correctamente.")
            return redirect('detalle_pago', prestamo_id=prestamo.id)

        except Exception as e:
            messages.error(request, f"Error al registrar el pago: {e}")
            return redirect('create_pago', id=id)

    context = {
        'pago': pago,
        'prestamo': pago.prestamo
    }

    return render(request, 'create_pago.html', context)

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
    # Obtener el préstamo correspondiente por el prestamo_id
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)

    # Obtener todos los pagos asociados a este préstamo, ordenados por fecha (ascendente)
    pagos = Pago.objects.filter(prestamo=prestamo).order_by('fecha_pago')

    # Pasar la lista de pagos y préstamo al contexto
    context = {
        'prestamo': prestamo,
        'pagos': pagos
    }
    return render(request, 'detalle_pago.html', context)



@login_required
def fecha_a_letras(fecha):
    """Convierte una fecha en formato 'día de mes de año, día de la semana' en español."""
    # Convertir la fecha en formato 'día de mes de año'
    dia_semana = fecha.strftime("%A")  # Obtener el día de la semana
    fecha_letras = fecha.strftime("%d de %B de %Y")  # Fecha en formato "7 de junio de 2025"
    return f"{dia_semana}, {fecha_letras}"


def generar_ticket(request, id):
    pago = get_object_or_404(Pago, id=id)

    meses = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
        7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }

    dia = pago.fecha_pago.day
    mes = pago.fecha_pago.month
    año = pago.fecha_pago.year

    fecha_en_letras = f"{dia} de {meses[mes]} de {año}".upper()

    # Convertir monto a letras en español
    monto_letras = num2words(pago.monto_pago, lang='es').capitalize()
    monto_letras = f"{monto_letras} pesos 00/100 M.N."

    ticket_data = {
        'numero_ticket': pago.numero_pago,
        'fecha': fecha_en_letras,
        'cliente': pago.prestamo.cliente.nombre,
        'monto': pago.monto_pago,
        'monto_letras': monto_letras,
    }

    template = get_template('ticket_template.html')
    html = template.render(ticket_data)

    html_content = HTML(string=html, base_url=request.build_absolute_uri())
    pdf_file = html_content.write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="ticket_pago_{pago.id}.pdf"'

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

    # --- Datos de empresa (pon los tuyos/rellena desde settings si prefieres) ---
    empresa = {
        "nombre": "UNIÓN DE SOCIEDADES CIVILES FINANCIERAS",
        "domicilio": "Calle 5 de febrero #414, Centro, Miahuatlan de Porfirio Diaz, Oaxaca",
        "telefono": "9512316895 Y 9515812486",
    }

    # Fecha local en MX
    fecha_local = localtime(pago.fecha_pago)
    meses = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
        7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }
    dia = fecha_local.day
    mes = meses[fecha_local.month]
    año = fecha_local.year
    fecha_en_letras = f"{dia} de {mes} de {año}".upper()

    # Monto
    monto = (Decimal(pago.monto_pago) if not isinstance(pago.monto_pago, Decimal)
             else pago.monto_pago).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    monto_letras = money_to_text_es(monto)

    # Folio (elige tu formato preferido)
    folio = f"{pago.numero_pago or pago.id}".zfill(6)

    # Cliente (ajusta campos reales)
    cliente_nombre = getattr(pago.prestamo.cliente, "nombre", "CLIENTE")
    cliente_clave = getattr(pago.prestamo.cliente, "clave", "")
    cliente_linea = f"{cliente_nombre}" + (f" ({cliente_clave})" if cliente_clave else "")

    # Cajero (si manejas usuario autenticado)
    cajero = getattr(getattr(request, "user", None), "username", "") or "SISTEMA"

    # Generación de QR (datos esenciales del comprobante)
    qr_payload = f"FOLIO:{folio}|FECHA:{fecha_local.strftime('%Y-%m-%d %H:%M')}|CLIENTE:{cliente_nombre}|MONTO:{monto}"
    qr_img = qrcode.make(qr_payload)
    buffer = BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    qr_data_uri = f"data:image/png;base64,{qr_b64}"

    # Datos para el contexto de la plantilla
    context = {
        "empresa": empresa,
        "folio": folio,
        "fecha": fecha_en_letras,
        "fecha_corta": fecha_local.strftime("%d/%m/%Y"),
        "cliente": cliente_linea,
        "monto": f"{monto:.2f}",
        "monto_letras": monto_letras,
        "concepto": f"ABONO {pago.numero_pago}",
        "lugar": "MIAHUATLÁN DE PORFIRIO DÍAZ, OAXACA",
        "cajero": cajero.upper,
        "qr_data_uri": qr_data_uri,
    }

    # Renderizar la plantilla HTML
    template = get_template("ticket_58mm.html")
    html = template.render(context)

    # Generación del archivo PDF
    pdf = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf()

    # Retornar el archivo PDF como respuesta
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp['Content-Disposition'] = f'inline; filename="ticket_pago_{pago.id}.pdf"'
    
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