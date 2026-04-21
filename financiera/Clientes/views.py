from django.shortcuts import render, redirect, get_object_or_404
from .models import Cliente, Comunidad
from .forms import ClienteForm
from django.contrib import messages
from weasyprint import HTML
from django.http import HttpResponse
import tempfile
from django.template.loader import render_to_string
#Pagina principal
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q


@login_required
def inicio_clientes(request):

    busqueda = request.GET.get('q', '')

    clientes_lista = Cliente.objects.select_related('usuario').all()

    if busqueda:
        clientes_lista = clientes_lista.filter(
            Q(nombre__icontains=busqueda) |
            Q(telefono__icontains=busqueda) |
            Q(domicilio__icontains=busqueda) |
            Q(usuario__first_name__icontains=busqueda)
        )

    clientes_lista = clientes_lista.order_by('id')

    paginator = Paginator(clientes_lista, 10)
    page_number = request.GET.get('page')
    clientes = paginator.get_page(page_number)

    return render(request, 'clientes.html', {
        'Clientes': clientes,
        'busqueda': busqueda
    })


@login_required
def registronuevo(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            nueva_comunidad = form.cleaned_data.get('nueva_comunidad')
            comunidad_obj = None
            if nueva_comunidad:
                comunidad_obj, _ = Comunidad.objects.get_or_create(nombre=nueva_comunidad.strip())
            
            cliente = form.save(commit=False)
            cliente.usuario = request.user
            if comunidad_obj:
                cliente.comunidad = comunidad_obj
            cliente.save()
            messages.success(request, "Guardado exitosamente")
            return redirect('principalClientes')
    else:
        form = ClienteForm()
    return render(request, 'clienteNuevo.html', {'form': form})

@login_required
def editarcliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            # Obtener el nombre de la nueva comunidad (si se envió)
            nueva_comunidad_nombre = form.cleaned_data.get('nueva_comunidad')
            if nueva_comunidad_nombre:
                # Crear o recuperar la comunidad
                comunidad_obj, _ = Comunidad.objects.get_or_create(nombre=nueva_comunidad_nombre.strip())
                # Asignar la comunidad al cliente (sin guardar aún)
                cliente.comunidad = comunidad_obj
            else:
                # Si no se ingresó nueva comunidad, se respeta lo que venga en el select
                # El campo 'comunidad' ya se asigna automáticamente por el formulario
                pass

            # Guardar el cliente (el formulario ya tiene los demás datos)
            form.save()
            messages.success(request, "Cliente actualizado exitosamente")
            return redirect('principalClientes')
        else:
            messages.error(request, "Error en el formulario. Revisa los datos.")
    else:
        form = ClienteForm(instance=cliente)

    context = {
        'dynamic_title': 'Editar Cliente',
        'form': form,
        'cliente': cliente,
    }
    return render(request, 'clienteEditar.html', context)
@login_required
def eliminarcliente(request, id):
    cliente = Cliente.objects.get(id = id)
    cliente.delete()
    messages.success(request, "Cliente eliminado correctamente")
    return redirect ('principalClientes')



