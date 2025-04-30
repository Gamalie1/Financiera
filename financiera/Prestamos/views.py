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
            plazo = int(form_data.get('plazo', '0').strip() or 0)
            
            errores = []
            if not cliente_id:
                errores.append("Debe seleccionar un cliente")
            if monto < 100:
                errores.append("El monto mínimo es $100.00")
            if plazo < 4:
                errores.append("El plazo mínimo es 4 semanas")
            if plazo > 520:
                errores.append("El plazo máximo es 520 semanas")
            if tasa_interes < Decimal('0.1') or tasa_interes > Decimal('50'):
                errores.append("La tasa debe estar entre 0.1% y 50%")
            
            if errores:
                for error in errores:
                    messages.error(request, error)
                return render(request, 'create_prestamo.html', {
                    'clientes': clientes,
                    'form_data': form_data
                })
            
            # Creación 
            Prestamo.objects.create(
                cliente_id=cliente_id,
                monto=monto,
                tasa_interes=tasa_interes,
                plazo=plazo,
                estado='SOLICITADO'
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
        try:
            cliente_id = request.POST.get('cliente')
            monto = Decimal(request.POST.get('monto', '0').strip() or '0')
            tasa_interes = Decimal(request.POST.get('tasa_interes', '0').strip() or '0')
            plazo = int(request.POST.get('plazo', '0').strip() or '0')
            estado = request.POST.get('estado')
            
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
    
    context = {
        'prestamo': prestamo,
        'clientes': clientes,
        'estados': Prestamo.ESTADO_CHOICES,
        'puede_editar': puede_editar
    }
    
    return render(request, 'editar_prestamo.html', context)