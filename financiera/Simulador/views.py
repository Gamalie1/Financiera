from django.shortcuts import render
from django.http import HttpResponse
from weasyprint import HTML
from datetime import datetime, timedelta
from django.templatetags.static import static
from dateutil.relativedelta import relativedelta
import locale
import platform
from django.contrib.auth.decorators import login_required
#Pagina principal
@login_required
def principal(request):
    return render(request, 'simulador.html')

@login_required
def generar_pdf(request):
    if platform.system() == 'Windows':
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
    else:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

    # Recibir los datos del simulador desde el formulario
    nombre_cliente = request.POST.get('nombreCliente', '')  # Por defecto cadena vacía si no viene el dato
    capital = int(request.POST.get('capital', 10000))  # Usamos 'POST' en lugar de 'GET'
    tasa = float(request.POST.get('tasa', 5.75)) / 100
    numPagos = int(request.POST.get('numPagos', 12))
    tipo_pago = request.POST.get('tipo-pago', 'mensual')  # Por defecto mensual
    fecha = request.POST.get('fecha', '2024-11-12')
    dias = int(request.POST.get('dias', 30))
    ivaPorc = float(request.POST.get('iva', 16)) / 100
    garantiaValor = float(request.POST.get('garantia', 10)) 
    garantia = (float(request.POST.get('garantia', 10)) / 100) * capital
    garantiaLiquida = float(request.POST.get('garantiaLiquida', 0))  # Garantía líquida corregida
    aportacion = float(request.POST.get('aportacion', 650))  # Aportación
    base_fecha = datetime.strptime(fecha, "%Y-%m-%d")
    diaPrestamo = base_fecha.weekday()
    ahorroActivo = request.POST.get('switchAhorro') == 'on'
    ahorro = float(request.POST.get('ahorro', 0)) if ahorroActivo else 0

    # Realizar los cálculos
    saldo = capital  # Mantener el saldo constante
    print(saldo)
    print(ahorro)
    abono = round(capital / numPagos, 2)  # Redondear el abono
    print(abono)
    interesPorPeriodo = capital * tasa  # Interés fijo por periodo
    print(interesPorPeriodo)
    ivaPorPeriodo = interesPorPeriodo * ivaPorc  # IVA sobre el interés
    print(ivaPorPeriodo)
    totalPago = abono + interesPorPeriodo + ivaPorPeriodo + ahorro  # Total del pago
    print(totalPago)

    """"
     # === Ajuste de la tasa para igualar el cálculo de tu amigo ===
    # Él aplica una tasa semanal “efectiva” con un factor 4.33 / 2.5 ≈ 1.732
    # Esto convierte 1.54% → 2.625% por semana (aprox.)
    factor_ajuste = 4.33 / 2.5
    tasa_ajustada = tasa * factor_ajuste  # 0.0154 * 1.732 = 0.02625 = 2.625%

    # === Cálculos base ===
    abono = round(capital / numPagos, 2)
    interesPorPeriodo = round(capital * tasa_ajustada, 2)      # ≈ 105.0
    ivaPorPeriodo = round(interesPorPeriodo * ivaPorc, 2)       # ≈ 16.79
    totalPago = round(abono + interesPorPeriodo + ivaPorPeriodo, 2)  # ≈ 388.46

    saldo = capital  """

    def obtener_fecha_pago(base, tipo, i, diaPrestamo, dias_pago):
        nueva_fecha = base

        if tipo == 'mensual':
        # Para pago "mensual", sumamos i veces el intervalo de días definido por el usuario (no necesariamente meses completos)
            nueva_fecha += timedelta(days=dias_pago * i)

        elif tipo == 'semanal':
        # Para pago semanal, sumamos i semanas completas
            nueva_fecha += timedelta(weeks=i)

    # Ajustar para que caiga exactamente en el mismo día de la semana que el préstamo original (sin cambios de sábado o domingo)
        dia_pago_actual = nueva_fecha.weekday()
        diferencia = diaPrestamo - dia_pago_actual

    # Ajustamos sumando o restando la diferencia para caer en el día correcto (asegurándonos de que siempre sea el mismo día de la semana)
        nueva_fecha += timedelta(days=diferencia)

        return nueva_fecha

    # Generar las filas de la tabla de pagos
    pagos = []
    for i in range(1, numPagos + 1):
        fecha_pago = obtener_fecha_pago(datetime.strptime(fecha, "%Y-%m-%d"), tipo_pago, i, diaPrestamo, dias)
        pagos.append({
            'numero_pago': i,
            'fecha': fecha_pago.strftime('%A, %d de %B de %Y'),
            'saldo_capital': round(saldo, 0),  # Saldo constante
            'abono_capital': round(abono, 0),
            'pago_interes': round(interesPorPeriodo, 0),
            'pago_iva_interes': round(ivaPorPeriodo,0),
            'total_pago': round(totalPago, 0),
            'ahorro': round(ahorro, 0),
        })
        saldo -= abono

    # Calcular los totales
    totalIntereses = round(interesPorPeriodo * numPagos, 0)  # Intereses totales
    print(totalIntereses)
    totalIva = round(ivaPorPeriodo * numPagos, 0)  # IVA total
    print(totalIva)
    totalPrestamo = round(capital + totalIntereses + totalIva, 0)  # Total préstamo
    print(totalPrestamo)
    costosExtra = round(garantiaLiquida + aportacion, 0)  # Costos extra (garantía líquida + aportación)

    # Renderizar el HTML con los datos calculados
    html_content = render(request, 'imprimir.html', {
    'nombre_cliente': nombre_cliente,
    'capital': round(capital, 0),  # Redondear capital a 2 decimales (o 0 si quieres entero)
    'tasa': round(tasa * 100, 2),  # Tasa en porcentaje con 2 decimales
    'numPagos': numPagos,  # Es entero, no redondear
    'fecha': fecha,  # Es string, no redondear
    'garantia': round(garantia, 0),
    'garantiaValor': round(garantiaValor, 0),
    'dias': dias,  # Es entero, no redondear
    'garantiaLiquida': round(garantiaLiquida, 0),
    'aportacion': round(aportacion, 0),
    'pagos': pagos,  # Lista con diccionarios que ya deberían tener valores redondeados
    'total_prestamo': round(totalPrestamo, 0),
    'costos_extra': round(costosExtra, 0),
    'total_general': round(totalPrestamo + costosExtra, 0),
    'ahorroActivo': ahorroActivo,
    'ahorro': round(ahorro, 0),
    }).content

    # Generar el PDF con WeasyPrint y pasando el base_url
    pdf = HTML(string=html_content, base_url=request.build_absolute_uri()).write_pdf()

    # Responder con el PDF
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="simulador_prestamo.pdf"'
    return response