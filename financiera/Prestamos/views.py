from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Prestamo
from Clientes.models import Cliente
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django import forms
from django.utils import timezone
from django.contrib import messages
from decimal import Decimal

def principal(request):
    prestamos = Prestamo.objects.all().select_related('cliente')
    return render(request, 'prestamos.html', {
        'prestamos': prestamos,
        'seccion': 'prestamos'  # Puedes usar esto para resaltar la sección activa
    })

@login_required
def create_prestamo(request):
    clientes = Cliente.objects.all()
    
    if request.method == 'POST':
        try:
            cliente_id = request.POST.get('cliente')
            monto = request.POST.get('monto')
            tasa_interes = request.POST.get('tasa_interes')
            plazo = request.POST.get('plazo')
            
            if not all([cliente_id, monto, tasa_interes, plazo]):
                messages.error(request, 'Todos los campos son obligatorios')
                return render(request, 'create_prestamo.html', {
                    'clientes': clientes,
                    'form_data': request.POST
                })
            
            prestamo = Prestamo(
                cliente_id=cliente_id,
                monto=monto,
                tasa_interes=tasa_interes,
                plazo=plazo,
            )
            prestamo.save()
            
            messages.success(request, 'Préstamo creado exitosamente!')
            return redirect('principalPrestamos')  # Coincide con el name de tu URL
            
        except Exception as e:
            messages.error(request, f'Error al crear el préstamo: {str(e)}')
            return render(request, 'create_prestamo.html', {
                'clientes': clientes,
                'form_data': request.POST
            })
    
    return render(request, 'create_prestamo.html', {'clientes': clientes})





@login_required
def eliminar_prestamo(request, pk):
    prestamo = get_object_or_404(Prestamo, pk=pk)
    prestamo.delete()
    messages.success(request, 'Préstamo eliminado correctamente')
    return redirect('principalPrestamos')

class PrestamoForm(forms.ModelForm):
    class Meta:
        model = Prestamo
        fields = '__all__'


@login_required
def editar_prestamo(request, pk):
    prestamo = get_object_or_404(Prestamo, pk=pk)
    puede_editar = prestamo.estado == 'SOLICITADO'
    clientes = Cliente.objects.all()
    
    if request.method == 'POST':
        # Procesar datos del formulario con validación robusta
        try:
            cliente_id = request.POST.get('cliente')
            monto = Decimal(request.POST.get('monto', '0').strip() or '0')
            tasa_interes = Decimal(request.POST.get('tasa_interes', '0').strip() or '0')
            plazo = int(request.POST.get('plazo', '0').strip() or '0')
            estado = request.POST.get('estado')
            
            # Validaciones
            errores = []
            if monto < 100:
                errores.append("El monto mínimo es $100.00")
            if plazo < 4:
                errores.append("El plazo mínimo es 4 semanas")
            if plazo > 520:
                errores.append("El plazo máximo es 520 semanas (10 años)")
            if tasa_interes < Decimal('0.1') or tasa_interes > Decimal('50'):
                errores.append("La tasa de interés debe estar entre 0.1% y 50%")
            
            if not errores:
                prestamo.cliente_id = cliente_id
                prestamo.monto = monto
                prestamo.tasa_interes = tasa_interes
                prestamo.plazo = plazo
                prestamo.estado = estado
                
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
    
    # Cálculos financieros (asegurarse de usar valores válidos)
    cuota_semanal = Decimal('0')
    total_intereses = Decimal('0')
    cronograma = []
    
    if prestamo.plazo > 0 and prestamo.monto > 0 and prestamo.tasa_interes > 0:
        try:
            tasa_interes_decimal = prestamo.tasa_interes / Decimal('100')
            tasa_semanal = (Decimal('1') + tasa_interes_decimal)**(Decimal('1')/Decimal('52')) - Decimal('1')
            factor = (Decimal('1') + tasa_semanal)**Decimal(str(prestamo.plazo))
            cuota_semanal = (prestamo.monto * tasa_semanal * factor) / (factor - Decimal('1'))
            total_intereses = (cuota_semanal * Decimal(str(prestamo.plazo))) - prestamo.monto
            
            # Generar cronograma si está aprobado
            if prestamo.estado == 'APROBADO' and prestamo.fecha_aprobacion:
                saldo = prestamo.monto
                for semana in range(1, prestamo.plazo + 1):
                    interes = saldo * tasa_semanal
                    capital = cuota_semanal - interes
                    saldo -= capital
                    
                    if semana <= 4 or semana >= prestamo.plazo - 2 or semana % 10 == 0:
                        cronograma.append({
                            'semana': semana,
                            'fecha': (prestamo.fecha_aprobacion + timezone.timedelta(weeks=semana)).strftime('%d/%m/%Y'),
                            'cuota': float(round(cuota_semanal, 2)),
                            'interes': float(round(interes, 2)),
                            'capital': float(round(capital, 2)),
                            'saldo': float(round(saldo, 2)) if saldo > 0 else 0
                        })
        except Exception as e:
            print(f"Error en cálculos financieros: {str(e)}")
            messages.error(request, "Error en cálculos financieros. Verifique los datos.")

    context = {
        'prestamo': prestamo,
        'clientes': clientes,
        'estados': Prestamo.ESTADO_CHOICES,
        'puede_editar': puede_editar,
        'cuota_semanal': "{:,.2f}".format(float(round(cuota_semanal, 2))),
        'total_intereses': "{:,.2f}".format(float(round(total_intereses, 2))),
        'cronograma': cronograma
    }
    
    return render(request, 'editar_prestamo.html', context)