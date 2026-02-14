from django.shortcuts import render, redirect, get_object_or_404
from .models import Cliente
from .forms import ClienteForm
from django.contrib import messages
from weasyprint import HTML
from django.http import HttpResponse
import tempfile
from django.template.loader import render_to_string
#Pagina principal
from django.contrib.auth.decorators import login_required

@login_required
def inicio_clientes(request):
     # Obtener todos los usuarios registrados
    Clientes = Cliente.objects.all()
    return render(request, 'clientes.html', {'Clientes': Clientes})

@login_required
def registronuevo(request):
    # Variables adicionales para el contexto
    context = {
        'dynamic_title': 'Registro nuevo',
    }

    if request.method == "POST":
        Cliente_Form = ClienteForm(request.POST)
        if Cliente_Form.is_valid():
            instancia = Cliente_Form.save(commit=False)  # No guarda todavía
            instancia.user = request.user  # Asigna el usuario autenticado
            instancia.save()  # Guarda con el usuario asignado
            messages.success(request, "Guardado exitosamente")
            return redirect('principalClientes')
    else:
        Cliente_Form = ClienteForm()

    # Añadir el formulario al contexto
    context['form'] = Cliente_Form  # Es más común usar 'form' como clave para el formulario

    # Renderizar la plantilla pasando todo el contexto
    return render(request, 'clienteNuevo.html', context)


@login_required
def editarcliente(request, cliente_id):
    # Obtener el cliente
    cliente = get_object_or_404(Cliente, id=cliente_id)

    if request.method == "POST":
        # Si el formulario se envía, crear una instancia de ClienteForm con los datos del cliente
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()  # Guarda los cambios en el cliente
            messages.success(request, "Cliente actualizado exitosamente")
            return redirect('principalClientes')  # Redirige a la vista de clientes
    else:
        # Si no se envía el formulario, crear una instancia vacía con los datos actuales del cliente
        form = ClienteForm(instance=cliente)

    # Contexto para la plantilla
    context = {
        'dynamic_title': 'Editar Cliente',
        'cliente': cliente,  # Pasamos el cliente actual para mostrar sus datos
        'form': form,  # Pasamos el formulario
    }

    # Renderizar la plantilla
    return render(request, 'clienteEditar.html', context)
@login_required
def eliminarcliente(request, id):
    cliente = Cliente.objects.get(id = id)
    cliente.delete()
    messages.success(request, "Cliente eliminado correctamente")
    return redirect ('principalClientes')



