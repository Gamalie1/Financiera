from django.shortcuts import render, redirect
from django.contrib import messages
from Clientes.models import Cliente
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django import forms
from django.utils import timezone
from django.contrib import messages
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta  
from Prestamos.models import Prestamo,  InformacionCliente
from Pagos.models import Pago, Abono
from Grupos.models import Grupo, IntegranteGrupo
from Grupos.models import DetallePrestamoGrupal
from django.template.loader import render_to_string
from django.http import HttpResponse, FileResponse
from weasyprint import HTML
import tempfile
from django.core.files.storage import default_storage
from num2words import num2words
import calendar
import locale
from datetime import datetime
from django.contrib.auth.models import User  # Importar el modelo User de Django
from django.http import HttpResponseForbidden
from django.db.models import Q
from zoneinfo import ZoneInfo
from django.db.models import OuterRef, Subquery, DecimalField, Sum
from django.core.paginator import Paginator
from io import BytesIO
import zipfile
from django.http import FileResponse, HttpResponse, Http404

@login_required
def principal(request):
    es_grupal = request.GET.get('es_grupal')
    buscar = request.GET.get('buscar')
    estado = request.GET.get('estado')
    tipo = request.GET.get('tipo')
    page_number = request.GET.get('page', 1)

    # ==============================
    # FILTRO POR USUARIO (base)
    # ==============================
    if request.user.is_staff:
        prestamos = Prestamo.objects.all()
    else:
        # Antes solo veía sus préstamos ya APROBADOs; ahora ve todas sus propias
        # solicitudes para poder dar seguimiento a su estado.
        prestamos = Prestamo.objects.filter(promotor=request.user)

    prestamos = prestamos.select_related('cliente', 'grupo', 'promotor')

    if es_grupal == 'true':
        prestamos = prestamos.filter(es_grupal=True)

    if estado:
        prestamos = prestamos.filter(estado=estado)

    if tipo:
        prestamos = prestamos.filter(tipo=tipo)

    if buscar:
        prestamos = prestamos.filter(
            Q(cliente__nombre__icontains=buscar) |
            Q(folio__icontains=buscar) |
            Q(grupo__nombre__icontains=buscar) |
            Q(promotor__username__icontains=buscar)
        )

    prestamos = prestamos.order_by('-fecha_solicitud')

    # ==============================
    # TOTALES (sobre el conjunto filtrado completo, antes de paginar)
    # ==============================
    total_monto = prestamos.aggregate(total=Sum('monto'))['total'] or Decimal('0')
    aprobados_count = prestamos.filter(estado='APROBADO').count()
    # 'PENDIENTE' no es un estado real del modelo; el estado inicial es 'SOLICITADO'.
    pendientes_count = prestamos.filter(estado='SOLICITADO').count()
    total_count = prestamos.count()

    paginator = Paginator(prestamos, 15)
    page_obj = paginator.get_page(page_number)

    context = {
        'prestamos': page_obj,
        'page_obj': page_obj,
        'tipo_actual': es_grupal,
        'total_monto': total_monto,
        'aprobados_count': aprobados_count,
        'pendientes_count': pendientes_count,
        'total_count': total_count,
    }
    return render(request, 'prestamos.html', context)



@login_required
def create_prestamo(request):
    clientes = Cliente.objects.all()
    promotores = User.objects.all()  # Trae todos los usuarios, o filtra los promotores
    grupos = Grupo.objects.all()  # Trae todos los grupos existentes
    
    
    if request.method == 'POST':
        form_data = request.POST.copy()
        try:
            # Conversión y validación 
            cliente_id = form_data.get('cliente')
            promotor_id = form_data.get('promotor')  # Obtener el ID del promotor
            grupo_id = form_data.get('grupo')  # Obtener el ID del grupo
            # Convertimos el valor de 'es_grupal' a booleano (True/False)
            es_grupal = request.POST.get('es_grupal') == 'True'  # Convertir "True"/"False" en booleano
            monto = Decimal(form_data.get('monto', '0').strip() or '0')
            tasa_interes = Decimal(form_data.get('tasa_interes', '0').strip() or '0')
            tipo = form_data.get('tipo')
            total_pagos = int(form_data.get('total_pagos', '0').strip() or 0)
            iva_sobre_intereses = Decimal(form_data.get('iva_sobre_intereses', '0').strip() or '0')
            garantia_liquida = Decimal(form_data.get('garantia_liquida', '0').strip() or '0')
            aportacion_social = Decimal(form_data.get('aportacion_social', '0').strip() or '0')
            ahorro = Decimal(form_data.get('ahorro', '0').strip() or '0')
            folio = form_data.get('solicitud_credito', '').strip()
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
                    'promotores': promotores,  # Asegúrate de pasar los promotores al template
                    'form_data': form_data
                })
          
            
            # Creación del préstamo
            Prestamo.objects.create(
                cliente_id=cliente_id,
                promotor_id=promotor_id,  # Asignar el promotor seleccionado
                monto=monto,
                tasa_interes=tasa_interes,
                tipo=tipo,
                total_pagos=total_pagos,
                estado='SOLICITADO',
                iva_sobre_intereses=iva_sobre_intereses,
                garantia_liquida=garantia_liquida,
                aportacion_social=aportacion_social,
                es_grupal=es_grupal,  # Asignar si es grupal o no
                ahorro=ahorro,   
                folio=folio,
            )
            
            messages.success(request, 'Préstamo creado exitosamente!')
            return redirect('principalPrestamos')
            
        except Exception as e:
            messages.error(request, f'Error al crear el préstamo: {str(e)}')
            return render(request, 'create_prestamo.html', {
                'clientes': clientes,
                'form_data': form_data
            })
    
    return render(request, 'create_prestamo.html', {'clientes': clientes,  "promotores": promotores,  "grupos": grupos})

@login_required
def editar_prestamo(request, pk):
    prestamo = get_object_or_404(Prestamo, pk=pk)
    clientes = Cliente.objects.all()
    promotores = User.objects.all()
     # Traer los integrantes del grupo si el préstamo es grupal
    integrantes = []
    if prestamo.es_grupal:
        detalles = DetallePrestamoGrupal.objects.filter(prestamo_id=prestamo.id)
    else:
        detalles = []
    print("DETALLES:", detalles)
    estado_anterior = prestamo.estado

    

    if request.method == 'POST':
        try:
            prestamo.promotor_id = request.POST.get('promotor')
            prestamo.folio = request.POST.get('folio', '').strip()
            cliente_id = request.POST.get('cliente')
            monto = Decimal(request.POST.get('monto', '0') or '0')
            tasa_interes = Decimal(request.POST.get('tasa_interes', '0') or '0')
            tipo = request.POST.get('tipo')
            total_pagos = int(request.POST.get('total_pagos', '0') or 0)
            estado = request.POST.get('estado')

            iva_sobre_intereses = Decimal(request.POST.get('iva_sobre_intereses', '0') or '0')
            garantia_liquida = Decimal(request.POST.get('garantia_liquida', '0') or '0')
            aportacion_social = Decimal(request.POST.get('aportacion_social', '0') or '0')

            fecha_aprobacion = request.POST.get('fecha_aprobacion')

            ahorro = Decimal(request.POST.get('ahorro', '0') or '0')
            pago_final = Decimal(request.POST.get('pago_final', '0') or '0')

            errores = []

            # VALIDACIONES
            if monto < 100:
                errores.append("El monto mínimo es $100.00")

            if tipo not in ['SEMANAL', 'MENSUAL']:
                errores.append("Tipo de préstamo inválido")

            if total_pagos < 1:
                errores.append("El número mínimo de pagos es 1")

            if tipo == 'SEMANAL' and total_pagos > 520:
                errores.append("Máximo 520 pagos semanales")

            if tipo == 'MENSUAL' and total_pagos > 120:
                errores.append("Máximo 120 pagos mensuales")

            if tasa_interes < Decimal('0.1') or tasa_interes > Decimal('30'):
                errores.append("La tasa debe estar entre 0.1% y 30%")



            # SI NO HAY ERRORES
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
                prestamo.ahorro = ahorro
                prestamo.pago_final = pago_final

                # FECHA APROBACION
                if estado == 'APROBADO':
                  if fecha_aprobacion:
                    prestamo.fecha_aprobacion = datetime.strptime(
                        fecha_aprobacion, "%Y-%m-%d"
                    ).date()
                else:
                    prestamo.fecha_aprobacion = None

                
                prestamo.save()
                if prestamo.es_grupal:
                    detalle_ids = request.POST.getlist('detalle_ids[]')  # existentes
                    integrantes_ids = request.POST.getlist('integrantes_ids[]')  # nuevos
                    montos = request.POST.getlist('montos[]')

                                    # 🚨 VALIDAR DUPLICADOS EN EL FORMULARIO
                    if len(integrantes_ids) != len(set(integrantes_ids)):
                        messages.error(request, "No puedes agregar el mismo integrante más de una vez.")
                        return redirect('editar_prestamo', pk=prestamo.id)

                    # 🚨 VALIDAR QUE NO YA EXISTA EN BD
                    existentes = DetallePrestamoGrupal.objects.filter(
                        prestamo=prestamo,
                        integrante_id__in=integrantes_ids
                    ).values_list('integrante_id', flat=True)

                    if existentes:
                        messages.error(request, "Uno de los integrantes ya existe en el préstamo.")
                        return redirect('editar_prestamo', pk=prestamo.id)

                    # 1️⃣ Eliminar los que ya no están
                    DetallePrestamoGrupal.objects.filter(prestamo=prestamo)\
                        .exclude(id__in=detalle_ids)\
                        .delete()

                    # 2️⃣ Actualizar existentes
                    for i in range(len(detalle_ids)):
                        detalle = DetallePrestamoGrupal.objects.get(id=detalle_ids[i])
                        detalle.monto = Decimal(montos[i] or '0')
                        detalle.save()

                            # 3️⃣ Crear nuevos
                    inicio_nuevos = len(detalle_ids)

                    for i in range(len(integrantes_ids)):
                        cliente_id = integrantes_ids[i]
                        monto_nuevo = Decimal(montos[inicio_nuevos + i] or '0')

                        # 🔎 Buscar el integrante correcto del grupo
                        integrante = IntegranteGrupo.objects.get(
                            grupo=prestamo.grupo,
                            cliente_id=cliente_id
                        )

                        DetallePrestamoGrupal.objects.create(
                            prestamo=prestamo,
                            integrante=integrante,
                            monto=monto_nuevo,
                            tasa_interes=prestamo.tasa_interes,
                            plazo_pagos=prestamo.total_pagos
                        )

                
                

                messages.success(request, "Préstamo actualizado correctamente")
                return redirect('principalPrestamos')

            for error in errores:
                messages.error(request, error)

        except Exception as e:
            messages.error(request, f"Error al procesar los datos: {str(e)}")

    context = {
        'prestamo': prestamo,
        'clientes': clientes,
        'estados': Prestamo.ESTADO_CHOICES,
        'cliente_seleccionado': prestamo.cliente_id,
        'promotores': promotores,
         'integrantes': integrantes,  # Pasar los integrantes y sus montos al template
          'detalles': detalles,  # Pasamos los detalles del préstamo grupal
    }

    return render(request, 'editar_prestamo.html', context)


@login_required
def eliminar_prestamo(request, pk):
    prestamo = get_object_or_404(Prestamo, pk=pk)
    prestamo.delete()
    messages.success(request, 'Préstamo eliminado correctamente')
    return redirect('principalPrestamos')

# Establecer el locale para español
locale.setlocale(locale.LC_TIME, 'es_ES.utf8')

def fecha_a_letras(fecha):
    locale.setlocale(locale.LC_TIME, 'es_ES.utf8')
    """Convierte una fecha en formato 'día de mes de año, día de la semana' en español."""
    # Convertir la fecha en formato 'día de mes de año'
    dia_semana = fecha.strftime("%A")  # Obtener el día de la semana
    fecha_letras = fecha.strftime("%d de %B de %Y")  # Fecha en formato "7 de junio de 2025"
    return f"{dia_semana}, {fecha_letras}"

@login_required
def detalle_prestamo(request, pk):
    prestamo = get_object_or_404(Prestamo, pk=pk)
    
    # Obtener todos los pagos del préstamo (ordenados)
    pagos = Pago.objects.filter(prestamo=prestamo).order_by('numero_pago')

        # Inicializar variables
    detalles_grupales = None
    total_monto_grupal = Decimal('0')
    
    # Anotar cada pago con el total abonado (suma de montos de abonos)
    abono_subquery = Abono.objects.filter(pago=OuterRef('pk')).values('pago').annotate(total=Sum('monto')).values('total')
    ahorro_subquery = Abono.objects.filter(pago=OuterRef('pk')).values('pago').annotate(total=Sum('ahorro')).values('total')
    
    pagos = pagos.annotate(
        total_abonado_anotado=Subquery(abono_subquery, output_field=DecimalField(max_digits=12, decimal_places=2)),
        total_ahorro=Subquery(ahorro_subquery, output_field=DecimalField(max_digits=12, decimal_places=2))
    )
    
    # Si algún pago no tiene abonos, asignar 0
    for pago in pagos:
        if pago.total_abonado is None:
            pago.total_abonado = Decimal('0')
        if pago.total_ahorro is None:
            pago.total_ahorro = Decimal('0')
    
    # Calcular estadísticas generales
    total_pagado = sum(pago.total_abonado for pago in pagos)
    saldo_pendiente = prestamo.monto - total_pagado
    cuotas_pagadas = pagos.filter(estado_pago='pagado').count()
    
    hoy = timezone.now().date()
    cuotas_atrasadas = pagos.filter(
        estado_pago__in=['pendiente', 'parcial'],
        fecha_programada__lt=hoy
    ).count()
    
    total_ahorro_general = sum(pago.total_ahorro for pago in pagos)
    total_abonado_general = total_pagado
    total_saldo_general = sum(pago.saldo_restante for pago in pagos)
    
    # Para mantener compatibilidad con el template (si aún usas algunas variables de tu vista anterior)
    # Calculamos también los valores que usabas antes (por si acaso)
    monto = Decimal(prestamo.monto)
    tasa_interes = Decimal(prestamo.tasa_interes) / Decimal('100')
    iva_porcentaje = Decimal(prestamo.iva_sobre_intereses) / Decimal('100')
    total_pagos = prestamo.total_pagos
    tipo_pago = prestamo.tipo
    garantia_liquida = Decimal(prestamo.garantia_liquida) if prestamo.garantia_liquida else Decimal('0')
    
    # Si necesitas calcular fechas de pagos (por si no están generadas)
    # Esta parte es opcional, solo si tu lógica anterior las usaba para algo
    fechas_pagos = []
    if prestamo.fecha_aprobacion:
        fecha_base = prestamo.fecha_aprobacion.date()
        dia_prestamo = fecha_base.weekday()
        if tipo_pago == 'SEMANAL':
            fecha_pago = fecha_base + relativedelta(weeks=1)
        else:
            fecha_pago = fecha_base + timedelta(days=30)
        for _ in range(total_pagos):
            diferencia = dia_prestamo - fecha_pago.weekday()
            fecha_ajustada = fecha_pago + timedelta(days=diferencia)
            fechas_pagos.append(fecha_ajustada)
            if tipo_pago == 'SEMANAL':
                fecha_pago += relativedelta(weeks=1)
            else:
                fecha_pago += timedelta(days=30)
        # Si es grupal, obtener los detalles de los integrantes
        detalles_grupales = None
        if prestamo.es_grupal:
            detalles_grupales = DetallePrestamoGrupal.objects.filter(
                prestamo=prestamo
            ).select_related('integrante__cliente')
            total_monto_grupal = detalles_grupales.aggregate(total=Sum('monto'))['total'] or Decimal('0')
        else:
            detalles_grupales = None
            total_monto_grupal = Decimal('0')
    # Preparar contexto para el template mejorado
    context = {
        'prestamo': prestamo,
        'pagos': pagos,  # importante: ahora la tabla usa esta variable
        'total_pagado': total_pagado,
        'saldo_pendiente': saldo_pendiente,
        'cuotas_pagadas': cuotas_pagadas,
        'cuotas_atrasadas': cuotas_atrasadas,
        'total_ahorro_general': total_ahorro_general,
        'total_abonado_general': total_abonado_general,
        'total_saldo_general': total_saldo_general,
        # Variables adicionales que tu template anterior podría necesitar (opcional)
        'garantia_monto': garantia_liquida,
        'multa_total': Decimal('0'),  # si no la calculas, puedes poner 0
        'total_intereses': Decimal('0'),
        'total_iva': Decimal('0'),
        'total_a_pagar': prestamo.monto,
        'fecha_solicitud': prestamo.fecha_solicitud.strftime('%d/%m/%Y %H:%M') if prestamo.fecha_solicitud else '',
        'detalles_grupales': detalles_grupales,
        'total_monto_grupal': total_monto_grupal,
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


@login_required
def generar_contrato_pdf(request, prestamo_id):
    cliente = get_object_or_404(Prestamo, id=prestamo_id)

    # Validar si es mensual o semanal y calcular el periodo
    if cliente.tipo == 'MENSUAL':
        periodo = f"{cliente.total_pagos} meses"
    elif cliente.tipo == 'SEMANAL':
        periodo = f"{cliente.total_pagos} semanas"
    else:
        periodo = "Sin periodo definido"
    
     # Convertir el monto del crédito a letras en pesos mexicanos
    credito_en_letras = num2words(cliente.monto, to='currency', lang='es', currency='MXN')

    monto_formateado = f"{int(cliente.monto):,}"
    

    # Definir los meses en letras
    meses = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
        7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }

    # Obtener la fecha actual
    
    fecha_actual = datetime.now(ZoneInfo("America/Mexico_City"))

    # Extraer el día, mes y año de la fecha actual
    dia = fecha_actual.day
    mes = fecha_actual.month
    año = fecha_actual.year

    # Generar la fecha en letras
    fecha_en_letras = f"{dia} de {meses[mes]} de {año}"
      # ============================
    # DETECTAR TIPO CONTRATO
    # ============================

    es_grupal = cliente.es_grupal

    titulo_contrato = (
        "Contrato de Apertura de Crédito Grupal"
        if es_grupal else
        "Contrato de Apertura de Crédito Individual"
    )
    # ============================
    # OBTENER INTEGRANTES SI ES GRUPAL
    # ============================

    integrantes = []

    if cliente.es_grupal:

        grupo = cliente.grupo

        integrantes = IntegranteGrupo.objects.select_related(
            'cliente'
        ).filter(grupo=grupo)

        print("INTEGRANTES DEL GRUPO:")
        for i in integrantes:
            print(i.id, i.cliente.nombre)
        


    context = {
        "titulo_contrato": titulo_contrato,
        "nombre_acreditado": cliente.cliente.nombre,  # Ajusta según tus campos
        "credito": monto_formateado,
        "credito_en_letras": credito_en_letras,
        "numero_pagos": cliente.total_pagos,
        "interes": cliente.tasa_interes,
        "direccion": cliente.cliente.domicilio,
        "periodo": periodo, 
        "fecha_en_letras": fecha_en_letras,
        "folio": cliente.folio,
        "es_grupal": cliente.es_grupal,
        "integrantes": integrantes,
        # Agrega aquí más datos necesarios
    }

    # Renderizar el HTML
    html_string = render_to_string("contrato.html", context)

    # Generar el PDF directamente en memoria
    html = HTML(string=html_string)
    pdf = html.write_pdf()

    # Crear una respuesta HTTP con el PDF en memoria
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename=contrato_{cliente.cliente.nombre}.pdf'

    return response

@login_required
def generar_invitacion(request, prestamo_id):
    # Obtener el préstamo correspondiente, incluyendo el cliente relacionado
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    cliente = prestamo.cliente  # Obtener el cliente relacionado con el préstamo

    # Generar el contexto con los datos del cliente
    contexto = {
        'cliente_nombre': cliente.nombre.upper,
        'fecha_actual': datetime.now().strftime('%d de %B de %Y').upper,
    }

    # Renderizar la plantilla HTML con el contexto
    html_content = render_to_string('invitacion.html', contexto)

    # Usamos WeasyPrint para generar el PDF
    html = HTML(string=html_content)
    pdf = html.write_pdf()

    # Devolver el PDF como respuesta
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="invitacion_extrajudicial.pdf"'

    return response

@login_required
def generar_liquidacion(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)

     # Datos para la liquidación
    fecha_pago = prestamo.fecha_solicitud.strftime('%d de %B de %Y')  # Formato de fecha (ejemplo: 20 de julio de 2025)
    monto_credito = "{:,.2f}".format(prestamo.monto)  # Monto formateado (ejemplo: 10,000.00)
    nombre_deudor = prestamo.cliente.nombre
    pagare = prestamo.id  # Este es un ejemplo de cómo podría almacenar el número del pagaré

    # Generar el contexto para la plantilla
    contexto = {
        'fecha_pago': fecha_pago.upper,
        'monto_credito': monto_credito,
        'nombre_deudor': nombre_deudor.upper,
        'pagare': pagare,
        'fecha_actual': datetime.now().strftime('%d de %B de %Y').upper,
    }

    # Renderizamos la plantilla HTML
    html_content = render_to_string('liquidacion.html', contexto)

    # Usamos WeasyPrint para generar el PDF
    html = HTML(string=html_content)
    pdf = html.write_pdf()

    # Devolver el PDF como respuesta
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="liquidacion_credito.pdf"'

    return response
    
    
@login_required
def generar_pagare(request, prestamo_id):
    cliente = get_object_or_404(Prestamo, id=prestamo_id)
     # Traer el monto de pago del primer registro en la tabla Pago relacionado con este préstamo
    pago = cliente.pagos.first()  # Esto obtiene el primer pago asociado al préstamo
    monto_pago = pago.monto_pago if pago else 0  # Si no hay pagos, asigna 0
    es_grupal = cliente.es_grupal


    # Establecer la configuración regional en español de México
    locale.setlocale(locale.LC_TIME, 'es_MX.UTF-8')  # Establece el locale para español

   
    # Definir los meses en letras
    meses = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
        7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }

    # Usar la fecha de aprobación
    fecha_aprobacion = cliente.fecha_aprobacion

    # Asegurarnos que tenga zona horaria (opcional pero recomendable)
    if fecha_aprobacion.tzinfo is None:
        fecha_aprobacion = fecha_aprobacion.replace(tzinfo=ZoneInfo("America/Mexico_City"))

    dia = fecha_aprobacion.day
    mes = fecha_aprobacion.month
    año = fecha_aprobacion.year

    # Generar la fecha en letras
    fecha_en_letras = f"a los {dia} días del mes de {meses[mes]} de {año}"

     # Convertir el monto del crédito a letras en pesos mexicanos
    credito_en_letras = num2words(cliente.monto, to='currency', lang='es', currency='MXN')
      
    # Convertir el monto de pago a letras en pesos mexicanos
    monto_pago_en_letras = num2words(round(monto_pago, 0), to='currency', lang='es', currency='MXN')
        # Validar si es mensual o semanal y calcular el periodo
    if cliente.tipo == 'MENSUAL':
        periodo = f"{cliente.total_pagos} pagos mensuales"
    elif cliente.tipo == 'SEMANAL':
        periodo = f"{cliente.total_pagos} pagos semanales"
    else:
        periodo = "Sin periodo definido"

    if cliente.tipo == 'MENSUAL':
        periodo2 = f"mensual"
    elif cliente.tipo == 'SEMANAL':
        periodo2 = f"semanal"
    else:
        periodo2 = "Sin periodo definido"

    if cliente.tipo == 'MENSUAL':
        periodo3 = f"{cliente.total_pagos} MESES"
    elif cliente.tipo == 'SEMANAL':
        periodo3 = f"{cliente.total_pagos} SEMANAS"
    else:
        periodo3 = "Sin periodo definido"

        # Obtener solo la fecha (sin la hora)
        # Traer el primer pago relacionado con el préstamo, ordenado por fecha
    primer_pago = cliente.pagos.order_by('fecha_programada').first()  # Ordena ascendentemente por la fecha del pago

    # Si existe un primer pago, toma su fecha; si no, usa la fecha de aprobación por defecto
    fecha_inicial = primer_pago.fecha_programada if primer_pago else cliente.fecha_aprobacion
    
    monto_formateado = f"{int(cliente.monto):,}"
    monto_pago_redondeado = round(monto_pago)  # Redondea al número entero más cercano
    monto_pago_formateado = f"{int(monto_pago_redondeado):,}"

    integrantes = []

    if cliente.es_grupal:

        grupo = cliente.grupo

        integrantes = IntegranteGrupo.objects.filter(
            grupo=grupo
    ).select_related('cliente').order_by('-es_representante')
    
    cambiar_a_oficio = False

    if cliente.es_grupal and len(integrantes) > 10:
     cambiar_a_oficio = True

    context = {
        "numero": cliente.id,  # Ajusta según tus campos
        "nombre_acreditado": cliente.cliente.nombre,  # Ajusta según tus campos
        "credito": monto_formateado,
        "credito_letras": credito_en_letras,  # Aquí se coloca el crédito en letras
        "numero_pagos": cliente.total_pagos,
        "interes": cliente.tasa_interes,
        "direccion": cliente.cliente.domicilio,
        "direccion_aval": cliente.cliente.domicilio_aval,
        "periodo": periodo, 
        "periodo2": periodo2, 
        "periodo3": periodo3,
        "fecha_inicial": fecha_inicial,
        "ciudad": cliente.cliente.municipio,
        "estado": cliente.cliente.estado,
        "nombre_aval": cliente.cliente.aval,  # Ajusta según tus campos
        "clave": cliente.cliente.clave_elector,
        "clave_aval": cliente.cliente.clave_elector_aval,
        "monto_pago": monto_pago_formateado,  # Agregar monto_pago aquí
        "monto_pago_en_letras":monto_pago_en_letras,
        "fecha_actual": fecha_en_letras,  # Fecha actual en formato deseado
        "telefono1": cliente.cliente.telefono,
        "telefono2": cliente.cliente.telefono_aval,
        "nombre_aval2": cliente.cliente.aval2,
        "direccion_aval2": cliente.cliente.domicilio_aval2,
        "telefono_aval2": cliente.cliente.telefono_aval2,
        "es_grupal": cliente.es_grupal,
        "integrantes": integrantes,
         "cambiar_a_oficio": cambiar_a_oficio,
  
        # Agrega aquí más datos necesarios
    }

    html_string = render_to_string("pagare.html", context)
    
    pdf = HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="pagare.pdf"'
    return response
    
def subir_archivo(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)

    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo_firmado = request.FILES['archivo']
        prestamo.archivo_firmado = archivo_firmado
        messages.success(request, "Subido correctamente")
        prestamo.save()
    
    return redirect('detalle_prestamo', pk=prestamo.id)

def eliminar_archivo(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    default_storage.delete(prestamo.archivo_firmado.path)  # Elimina el archivo del almacenamiento
    prestamo.archivo_firmado = None
    messages.success(request, "Eliminado correctamente")
    prestamo.save()
    return redirect('detalle_prestamo', pk=prestamo.id)

def descargar_archivo(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)

    if prestamo.archivo_firmado:
        response = FileResponse(prestamo.archivo_firmado.open('rb'), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{prestamo.archivo_firmado.name}"'
        return response

    return HttpResponse("No hay archivo disponible", status=404)

def subir_pagare(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)

    if request.method == 'POST' and request.FILES.get('pagare'):
        pagare = request.FILES['pagare']
        prestamo.pagare = pagare
        messages.success(request, "Subido correctamente")
        prestamo.save()
    
    return redirect('detalle_prestamo', pk=prestamo.id)

def eliminar_pagare(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    default_storage.delete(prestamo.pagare.path)  # Elimina el archivo del almacenamiento
    prestamo.pagare = None
    messages.success(request, "Eliminado correctamente")
    prestamo.save()
    return redirect('detalle_prestamo', pk=prestamo.id)

def descargar_pagare(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)

    if prestamo.pagare:
        response = FileResponse(prestamo.pagare.open('rb'), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{prestamo.pagare.name}"'
        return response

    return HttpResponse("No hay archivo disponible", status=404)

def subir_informacion(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)

    if request.method == 'POST' and request.FILES.get('informacion'):
        informacion = request.FILES['informacion']
        prestamo.informacion = informacion
        messages.success(request, "Subido correctamente")
        prestamo.save()
    
    return redirect('detalle_prestamo', pk=prestamo.id)

def eliminar_informacion(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    default_storage.delete(prestamo.informacion.path)  # Elimina el archivo del almacenamiento
    prestamo.informacion = None
    messages.success(request, "Eliminado correctamente")
    prestamo.save()
    return redirect('detalle_prestamo', pk=prestamo.id)

def descargar_informacion(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)

    if prestamo.informacion:
        response = FileResponse(prestamo.informacion.open('rb'), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{prestamo.informacion.name}"'
        return response

    return HttpResponse("No hay archivo disponible", status=404)

def descargar_lista(request, prestamo_id):

    prestamo = get_object_or_404(Prestamo, id=prestamo_id)

    # Seguridad
    if not prestamo.es_grupal:
        return HttpResponse("Este préstamo no es grupal", status=403)

    grupo = prestamo.grupo
        # Total del préstamo grupal
    monto_prestamo = prestamo.monto
    # Número de integrantes reales (los que tienen préstamo)
    total_integrantes = DetallePrestamoGrupal.objects.filter(
        prestamo=prestamo
    ).count()

    # ✅ Calcular monto individual
    monto_individual = (
        monto_prestamo / Decimal(total_integrantes)
    ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Ahorro general del préstamo
    ahorro_prestamo = prestamo.ahorro or Decimal('0.00')

    # 🔥 AQUÍ está lo importante
    detalles = DetallePrestamoGrupal.objects.select_related(
        'integrante__cliente'
    ).filter(prestamo=prestamo).order_by(
        '-integrante__es_representante'
    )
    total_pago_general = Decimal('0.00')
    total_ahorro_general = Decimal('0.00')
    total_total_general = Decimal('0.00')
    total_monto_general = Decimal('0.00')

    integrantes = []

    for d in detalles:

        monto_pago = d.monto   # ✅ ESTE ES EL MONTO REAL

        total = monto_pago + ahorro_prestamo

        total_pago_general += monto_pago
        total_ahorro_general += ahorro_prestamo
        total_total_general += total
        total_monto_general += monto_individual

        integrantes.append({
            'cliente': d.integrante.cliente,
            'monto_pago': monto_pago,
            'ahorro': ahorro_prestamo,
            'total_pago': total,
            'monto_total': monto_individual,   # 👈 AQUÍ
        })

    context = {
        'prestamo': prestamo,
        'grupo': grupo,
        'integrantes': integrantes,
        'total_pago_general': total_pago_general,
        'total_ahorro_general': total_ahorro_general,
        'total_total_general': total_total_general,
        'total_monto_general': total_monto_general,
    }

    html_string = render_to_string('lista_miembros.html', context)

    pdf_file = HTML(
        string=html_string,
        base_url=request.build_absolute_uri()
    ).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="lista_miembros_{prestamo.id}.pdf"'

    return response


def subir_informacion(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    if request.method == 'POST':
        archivos = request.FILES.getlist('informacion')
        if archivos:
            for archivo in archivos:
                InformacionCliente.objects.create(
                    prestamo=prestamo,
                    archivo=archivo,
                    nombre=archivo.name,
                    subido_por=request.user
                )
            messages.success(request, f"Se subieron {len(archivos)} archivo(s) correctamente.")
        else:
            messages.warning(request, "No seleccionaste ningún archivo.")
    return redirect('detalle_prestamo', pk=prestamo.id)


def eliminar_informacion(request, info_id):
    info = get_object_or_404(InformacionCliente, id=info_id)
    prestamo_id = info.prestamo.id
    # Eliminar el archivo físico
    if info.archivo:
        default_storage.delete(info.archivo.path)
    info.delete()
    messages.success(request, "Archivo eliminado.")
    return redirect('detalle_prestamo', pk=prestamo_id)

# Descargar un archivo individual (cualquier usuario autenticado)
@login_required
def descargar_informacion(request, info_id):
    info = get_object_or_404(InformacionCliente, id=info_id)
    if not info.archivo or not default_storage.exists(info.archivo.name):
        raise Http404("El archivo no existe.")
    response = FileResponse(info.archivo.open('rb'), as_attachment=True, filename=info.filename())
    return response

# Descargar todos los archivos en un ZIP (cualquier usuario autenticado)
@login_required
def descargar_todas_informaciones(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    informaciones = prestamo.informaciones.all()
    if not informaciones:
        messages.warning(request, "No hay archivos para descargar.")
        return redirect('detalle_prestamo', pk=prestamo.id)

    # Crear ZIP en memoria
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for info in informaciones:
            # Leer archivo y agregarlo al ZIP
            with info.archivo.open('rb') as f:
                zip_file.writestr(info.filename(), f.read())

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="informacion_prestamo_{prestamo.id}.zip"'
    return response