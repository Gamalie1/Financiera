from django.shortcuts import render, redirect, get_object_or_404
from .models import Pago, Prestamo
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal  
from django.db import transaction

def pagosPrincipal(request):
    pagos = Pago.objects.all().order_by('-fecha_pago')
    context = {'pagos': pagos}
    return render(request, 'pagos.html', context)

def create_pago(request):
    if request.method == 'POST':
        prestamo_id = request.POST.get('prestamo_id')
        try:
            with transaction.atomic():
                prestamo = Prestamo.objects.get(id=prestamo_id)
                monto_pago = Decimal(request.POST.get('monto_pago'))  # Conversión aquí
                
                pago = Pago(
                    prestamo=prestamo,
                    monto_pago=monto_pago,  # Usa la variable ya convertida
                    metodo_pago=request.POST.get('metodo_pago'),
                    fecha_pago=request.POST.get('fecha_pago'),
                )
                pago.save()
                
                messages.success(request, 'Pago registrado correctamente')
                return redirect('detalle_prestamo', pk=prestamo.id)
                
        except Prestamo.DoesNotExist:
            messages.error(request, 'Préstamo no encontrado')
            return redirect('create_pago')
    
    prestamos = Prestamo.objects.all()
    return render(request, 'create_pago.html', {'prestamos': prestamos})


def editar_pago(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    
    if request.method == 'POST':
        try:
            pago.prestamo_id = request.POST.get('prestamo_id')
            pago.monto_pago = request.POST.get('monto_pago')
            pago.fecha_pago = request.POST.get('fecha_pago')
            pago.metodo_pago = request.POST.get('metodo_pago')
            pago.save()
            
            messages.success(request, 'Pago actualizado exitosamente')
            return redirect('pagos')
        except Exception as e:
            messages.error(request, f'Error al actualizar pago: {str(e)}')
    
    prestamos = Prestamo.objects.all()
    context = {
        'pago': pago,
        'prestamos': prestamos
    }
    return render(request, 'editar_pago.html', context)


@require_POST
def eliminar_pago(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    try:
        pago.delete()
        messages.success(request, 'Pago eliminado correctamente')
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
