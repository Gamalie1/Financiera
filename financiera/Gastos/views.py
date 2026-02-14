from django.shortcuts import render,redirect, get_object_or_404
from .forms import GastoForm
from django.contrib import messages
from .models import Gasto
from django.contrib.auth.decorators import login_required

# Create your views here.
#Pagina principal
@login_required
def gastosPrincipal(request):
    if request.user.is_staff:
        # Administrador ve todos los gastos
        gastos = Gasto.objects.all().order_by('-fecha_registro')
    else:
        # Empleado ve solo sus gastos
        gastos = Gasto.objects.filter(
            usuario=request.user
        ).order_by('-fecha_registro')

    context = {'gastos': gastos}
    return render(request, 'gastos.html', context)

@login_required
def registrar_nuevo_gasto(request):
    if request.method == "POST":
        # Crear una instancia del formulario con los datos del POST
        Gasto_Form = GastoForm(request.POST)
        
        if Gasto_Form.is_valid():
            # Guardar el gasto pero no guardarlo aún en la base de datos
            instancia = Gasto_Form.save(commit=False)
            instancia.usuario = request.user  # Asigna el usuario autenticado automáticamente
            instancia.save()  # Guarda la instancia en la base de datos

            messages.success(request, "Gasto registrado exitosamente")
            return redirect('Gastos')  # Redirige al detalle del gasto
        else:
            # Si el formulario no es válido, mostrar el mensaje de error
            messages.error(request, "Hubo un error al registrar el gasto. Por favor revisa los datos.")
    else:
        # Si es un GET, crear un formulario vacío
        Gasto_Form = GastoForm()

    # Renderizar la plantilla y pasar el formulario al contexto
    return render(request, 'crear_gastos.html', {'form': Gasto_Form})

@login_required
def editarGasto(request, gastos_id):
    # Obtener el cliente
    gastos = get_object_or_404(Gasto, id=gastos_id)

    if request.method == "POST":
        # Si el formulario se envía, crear una instancia de ClienteForm con los datos del cliente
        form = GastoForm(request.POST, instance=gastos)
        if form.is_valid():
            form.save()  # Guarda los cambios en el cliente
            messages.success(request, "Gasto actualizado exitosamente")
            return redirect('Gastos')  # Redirige a la vista de clientes
    else:
        # Si no se envía el formulario, crear una instancia vacía con los datos actuales del cliente
        form = GastoForm(instance=gastos)

    # Contexto para la plantilla
    context = {
        'gastos': gastos,  # Pasamos el cliente actual para mostrar sus datos
        'form': form,  # Pasamos el formulario
    }

    # Renderizar la plantilla
    return render(request, 'editar_gastos.html', context)

@login_required
def eliminarGasto(request, id):
    gasto = Gasto.objects.get(id = id)
    gasto.delete()
    messages.success(request, "Gasto eliminado correctamente")
    return redirect ('Gastos')