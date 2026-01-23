from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User, Group
from django.db import IntegrityError
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from Pagos.models import Pago
from Gastos.models import Gasto
from Prestamos.models import Prestamo
from datetime import timedelta
from django.http import Http404


#Index
def inicio(request):
    return render(request, 'index.html')

#Login para iniciar sesion
def signin(request):
    if request.method == 'GET':
        return render(request, 'signin.html', {"form": AuthenticationForm})
    else:
        user = authenticate(
            request,
            username=request.POST['username'],
            password=request.POST['password']
        )

        if user is None:
            return render(
                request,
                'signin.html',
                {"form": AuthenticationForm, "error": "Usuario o la contraseña es incorrecta."}
            )

        login(request, user)

        # 🔥 Redirección según tipo de usuario
        if user.is_staff:
            return redirect('principal')       # Administrador
        else:
            return redirect('pagos')          # Empleado
    

def principal(request):
    hoy = timezone.now().date()

    # Obtener todos los usuarios (cobradores)
    users = User.objects.all()

    # Crear diccionarios para almacenar los totales
    totales_cobradores = {}
    totales_gastos = {}
    pagos_retrasados = {}
    prestamos_diarios = {}  # Diccionario para almacenar la información de los pagos pendientes

    # Iterar sobre los usuarios y obtener el total de lo que han recaudado, los gastos y pagos retrasados
    for user in users:
        # Total de pagos de hoy
        pagos_hoy = Pago.objects.filter(cobrador=user, fecha_pago__date=hoy)
        total_pagado = pagos_hoy.aggregate(Sum('monto_pago'))['monto_pago__sum'] or 0.00
        
        # Total de gastos de hoy (filtrado por el usuario)
        gastos_hoy = Gasto.objects.filter(usuario=user, fecha_registro=hoy)
        total_gasto = gastos_hoy.aggregate(Sum('monto'))['monto__sum'] or 0.00
        
        # Pagos PENDIENTES asignados al usuario para HOY (tomando del propio Pago)
        pagos_pendientes = Pago.objects.filter(
            cobrador_asignado=user,         # <<--- en Pago
            estado_pago='pendiente',
            fecha_pago__date=hoy
        )

        total_pagos_retrasados = pagos_pendientes.aggregate(
            Sum('monto_pago')
        )['monto_pago__sum'] or 0.00

        # Conteo de PRÉSTAMOS distintos con pagos pendientes hoy (sin ir a Prestamo)
        prestamos_pendientes_hoy_count = pagos_pendientes.values('prestamo').distinct().count()

        # Guardar en los diccionarios
        pagos_retrasados[user.username] = total_pagos_retrasados
        prestamos_diarios[user.username] = prestamos_pendientes_hoy_count
        
        
        # Guardar los totales en los diccionarios
        totales_cobradores[user.username] = total_pagado
        totales_gastos[user.username] = total_gasto
        pagos_retrasados[user.username] = total_pagos_retrasados
        
        # Número de préstamos con pagos pendientes de hoy
        prestamos_diarios[user.username] = prestamos_pendientes_hoy_count

    # Asegurarnos de que estamos pasando un valor por defecto
    context = {
        'totales_cobradores': totales_cobradores,
        'totales_gastos': totales_gastos,
        'pagos_retrasados': pagos_retrasados,
        'prestamos_diarios': prestamos_diarios,  # Añadimos los préstamos con pagos pendientes de hoy al contexto
        'default_value': 0.00  # Esto será el valor por defecto si no existe un valor
    }

    return render(request, 'principal.html', context)

def detalles_cobrador(request, cobrador):
    hoy = timezone.now().date()
    tipo = request.GET.get('tipo', 'pagos')  # Obtener el tipo de detalle que se solicita (pagos, gastos, prestamos)
        # Lunes (weekday = 0)
    inicio_semana = hoy - timedelta(days=hoy.weekday())

    # Domingo (lunes + 6 días)
    fin_semana = inicio_semana + timedelta(days=6)
    
    try:
        # Intentamos obtener el usuario con el username proporcionado
        user = User.objects.get(username=cobrador)
    except User.DoesNotExist:
        # Si no se encuentra, lanzar una excepción o redirigir a otro lugar
        raise Http404("Cobrador no encontrado")

    # Imprimir el username del cobrador
    print(f"Usuario encontrado: {user.username}")
    context = {'user': user, 'tipo': tipo}  # Empieza con la información base

    
    # Datos de los pagos
    if tipo == 'pagos':
        pagos_hoy = Pago.objects.filter(cobrador=user, fecha_pago__date=hoy)
        pagos_semana = Pago.objects.filter(cobrador=user, fecha_pago__gte=hoy - timedelta(days=7))
        pagos_mes = Pago.objects.filter(cobrador=user, fecha_pago__month=hoy.month)
        pagos_totales = Pago.objects.filter(cobrador=user)
        
        total_pagado_hoy = pagos_hoy.aggregate(Sum('monto_pago'))['monto_pago__sum'] or 0.00
        total_pagado_semana = pagos_semana.aggregate(Sum('monto_pago'))['monto_pago__sum'] or 0.00
        total_pagado_mes = pagos_mes.aggregate(Sum('monto_pago'))['monto_pago__sum'] or 0.00
        total_pagado_general = pagos_totales.aggregate(Sum('monto_pago'))['monto_pago__sum'] or 0.00

          # Traer los clientes relacionados con esos pagos
        pagos_hoy_detalles = pagos_hoy.select_related('prestamo__cliente').values('prestamo__cliente__nombre', 'prestamo__tipo', 'fecha_pago', 'monto_pago', 'metodo_pago')
        pagos_semana_detalles = pagos_semana.select_related('prestamo__cliente').values('prestamo__cliente__nombre', 'prestamo__tipo', 'fecha_pago', 'monto_pago', 'metodo_pago')
        pagos_mes_detalles = pagos_mes.select_related('prestamo__cliente').values('prestamo__cliente__nombre', 'prestamo__tipo', 'fecha_pago', 'monto_pago', 'metodo_pago')
        pagos_totales_detalles = pagos_totales.select_related('prestamo__cliente').values('prestamo__cliente__nombre', 'prestamo__tipo', 'fecha_pago', 'monto_pago', 'metodo_pago')
        
        # Imprimir los totales de pagos
        print(f"Pagos hoy: {total_pagado_hoy}")
        print(f"Pagos semana: {total_pagado_semana}")
        print(f"Pagos mes: {total_pagado_mes}")
        print(f"Pagos totales: {total_pagado_general}") 


        
        
            # Calcular los pagos
        context.update({
            'total_pagado_hoy': total_pagado_hoy,
            'total_pagado_semana': total_pagado_semana,
            'total_pagado_mes': total_pagado_mes,
            'total_pagado_general': total_pagado_general,
        })
        context.update({
            'pagos_hoy_detalles': pagos_hoy_detalles,
            'pagos_semana_detalles': pagos_semana_detalles,
            'pagos_mes_detalles': pagos_mes_detalles,
            'pagos_totales_detalles': pagos_totales_detalles,
        })

    
    
    # Datos de los gastos
    elif tipo == 'gastos':
        # Obtener los gastos por día, semana, mes, total
        gastos_hoy = Gasto.objects.filter(usuario=user, fecha_registro=hoy)
        gastos_semana = Gasto.objects.filter(usuario=user, fecha_registro__gte=hoy - timedelta(days=7))
        gastos_mes = Gasto.objects.filter(usuario=user, fecha_registro__month=hoy.month)
        gastos_totales = Gasto.objects.filter(usuario=user)
        
        # Obtener detalles de los gastos (Promotor, Monto, Fecha, Concepto)
        gastos_hoy_detalles = gastos_hoy.values('usuario__username', 'monto', 'fecha_registro', 'concepto')
        gastos_semana_detalles = gastos_semana.values('usuario__username', 'monto', 'fecha_registro', 'concepto')
        gastos_mes_detalles = gastos_mes.values('usuario__username', 'monto', 'fecha_registro', 'concepto')
        gastos_totales_detalles = gastos_totales.values('usuario__username', 'monto', 'fecha_registro', 'concepto')

        # Total de gastos por día, semana, mes, y total
        total_gasto_hoy = gastos_hoy.aggregate(Sum('monto'))['monto__sum'] or 0.00
        total_gasto_semana = gastos_semana.aggregate(Sum('monto'))['monto__sum'] or 0.00
        total_gasto_mes = gastos_mes.aggregate(Sum('monto'))['monto__sum'] or 0.00
        total_gasto_general = gastos_totales.aggregate(Sum('monto'))['monto__sum'] or 0.00

        context.update({
            'gastos_hoy_detalles': gastos_hoy_detalles,
            'gastos_semana_detalles': gastos_semana_detalles,
            'gastos_mes_detalles': gastos_mes_detalles,
            'gastos_totales_detalles': gastos_totales_detalles,
            'total_gasto_hoy': total_gasto_hoy,
            'total_gasto_semana': total_gasto_semana,
            'total_gasto_mes': total_gasto_mes,
            'total_gasto_general': total_gasto_general,
        })
    # Datos de los préstamos pendientes
    elif tipo == 'prestamos':
         # Obtener los pagos pendientes
        pagos_pendientes_hoy = Pago.objects.filter( cobrador_asignado=user, estado_pago='pendiente', fecha_pago__date=hoy)
        pagos_pendientes_semana = Pago.objects.filter(cobrador_asignado=user,estado_pago='pendiente',fecha_pago__date__gte=inicio_semana,fecha_pago__date__lte=fin_semana)
        pagos_pendientes_mes = Pago.objects.filter( cobrador_asignado=user, estado_pago='pendiente', fecha_pago__month=hoy.month)
        pagos_pendientes_totales = Pago.objects.filter( cobrador_asignado=user, estado_pago='pendiente')

        # Contamos los pagos pendientes por día, semana, mes y total
        pagos_hoy = pagos_pendientes_hoy.count()
        pagos_semana = pagos_pendientes_semana.count()
        pagos_mes = pagos_pendientes_mes.count()
        pagos_totales = pagos_pendientes_totales.count()

        # Obtener detalles de los pagos pendientes (Nombre cliente, tipo de préstamo, fecha, monto, método de pago)
        pagos_hoy_detalles = pagos_pendientes_hoy.select_related('prestamo__cliente').values('prestamo__cliente__nombre', 'prestamo__tipo', 'fecha_pago', 'monto_pago')
        pagos_semana_detalles = pagos_pendientes_semana.select_related('prestamo__cliente').values('prestamo__cliente__nombre', 'prestamo__tipo', 'fecha_pago', 'monto_pago')
        pagos_mes_detalles = pagos_pendientes_mes.select_related('prestamo__cliente').values('prestamo__cliente__nombre', 'prestamo__tipo', 'fecha_pago', 'monto_pago')
        pagos_totales_detalles = pagos_pendientes_totales.select_related('prestamo__cliente').values('prestamo__cliente__nombre', 'prestamo__tipo', 'fecha_pago', 'monto_pago')
        
        print("Pagos hoy:", pagos_pendientes_hoy)
        print("Pagos semana:", pagos_pendientes_semana)
        print("Pagos mes:", pagos_pendientes_mes)
        print("Pagos totales:", pagos_pendientes_totales)

        context.update({
            'pagos_hoy': pagos_hoy,
            'pagos_semana': pagos_semana,
            'pagos_mes': pagos_mes,
            'pagos_totales': pagos_totales,
            'pagos_hoy_detalles': pagos_hoy_detalles,
            'pagos_semana_detalles': pagos_semana_detalles,
            'pagos_mes_detalles': pagos_mes_detalles,
            'pagos_totales_detalles': pagos_totales_detalles,
        })
    
    return render(request, 'detalles_cobros.html', context)


#Cerrar sesion
def signout(request):
    logout(request)
    return redirect('login')


#Pagina de vista de usuarios
def usuarios(request):
     # Obtener todos los usuarios registrados
    usuarios = User.objects.all()
    return render(request, 'usuarios.html', {'usuarios': usuarios})

#Login crear usuarios nuevos
def signup(request):
    if request.method == 'POST':
        username     = request.POST.get('username')
        first_name   = request.POST.get('first_name')
        last_name    = request.POST.get('last_name')
        email        = request.POST.get('email')
        password1    = request.POST.get('password1')
        password2    = request.POST.get('password2')
        tipo_usuario = request.POST.get('tipo_usuario')  # "admin" o "empleado"

        # Contexto para regresar datos al template si hay error
        context = {
            "error": None,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "tipo_usuario": tipo_usuario,
        }

        # 1. Validar contraseñas
        if password1 != password2:
            context["error"] = "Las contraseñas no coinciden"
            return render(request, 'signup.html', context)

        try:
            # 2. Crear usuario
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password1
            )

            # 3. Asignar tipo de usuario (grupo y permisos)
            try:
                if tipo_usuario == "admin":
                    # Admin: acceso al admin y grupo Administrador
                    user.is_staff = True
                    grupo_admin = Group.objects.get(name='Administrador')
                    user.groups.add(grupo_admin)
                elif tipo_usuario == "empleado":
                    # Empleado: grupo Empleado (sin is_staff)
                    grupo_empleado = Group.objects.get(name='Empleado')
                    user.groups.add(grupo_empleado)
                else:
                    context["error"] = "Tipo de usuario no válido."
                    user.delete()
                    return render(request, 'signup.html', context)
            except Group.DoesNotExist:
                # Si aún no creas los grupos en el admin
                context["error"] = "No se encontraron los grupos 'Administrador' o 'Empleado'. Créelos en el admin de Django."
                user.delete()
                return render(request, 'signup.html', context)

            user.save()

            messages.success(request, f'Cuenta creada exitosamente para {username}!')
            return redirect('login')

        except IntegrityError:
            context["error"] = "El nombre de usuario ya existe."
            return render(request, 'signup.html', context)

    # Si es GET
    return render(request, 'signup.html')
#Eliminar usuarios
def eliminarUsuarios(request, id):
    try:
        # Obtener el usuario con el ID proporcionado
        usuario = User.objects.get(id=id)
        
        # Eliminar el usuario
        usuario.delete()

        # Mensaje de éxito
        messages.success(request, f'El usuario {usuario.username} ha sido eliminado correctamente.')
    except User.DoesNotExist:
        # Si no se encuentra el usuario, muestra un error
        messages.error(request, 'El usuario no existe.')

    # Redirigir a la página de lista de usuarios o donde desees
    return redirect('usuarios')  # Asegúrate de tener una vista llamada 'usuarios' para redirigir


def editar_usuario(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        username     = request.POST.get('username')
        first_name   = request.POST.get('first_name')
        last_name    = request.POST.get('last_name')
        email        = request.POST.get('email')
        password1    = request.POST.get('password1')
        password2    = request.POST.get('password2')
        tipo_usuario = request.POST.get('tipo_usuario')

        # Contexto para mantener datos en caso de error
        context = {
            "error": None,
            "usuario": usuario,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "tipo_usuario": tipo_usuario,
        }

        # Validar contraseñas solo si intenta cambiarla
        if password1 or password2:
            if password1 != password2:
                context["error"] = "Las contraseñas no coinciden."
                return render(request, 'editar_usuario.html', context)
            else:
                usuario.set_password(password1)

        # Actualizar datos básicos
        usuario.username = username
        usuario.first_name = first_name
        usuario.last_name = last_name
        usuario.email = email

        # 🔥 Cambiar tipo de usuario (admin o empleado)
        try:
            # Limpiar grupos actuales
            usuario.groups.clear()

            if tipo_usuario == "admin":
                usuario.is_staff = True
                grupo_admin = Group.objects.get(name="Administrador")
                usuario.groups.add(grupo_admin)

            elif tipo_usuario == "empleado":
                usuario.is_staff = False
                grupo_empleado = Group.objects.get(name="Empleado")
                usuario.groups.add(grupo_empleado)

            else:
                context["error"] = "Tipo de usuario no válido."
                return render(request, 'editar_usuario.html', context)

        except Group.DoesNotExist:
            context["error"] = "Debes crear los grupos 'Administrador' y 'Empleado' en el admin."
            return render(request, 'editar_usuario.html', context)

        usuario.save()

        messages.success(request, "Usuario actualizado exitosamente.")
        return redirect('usuarios')  # o donde quieras redirigir

    # GET: cargar datos actuales
    context = {
        "usuario": usuario,
        "tipo_usuario": "admin" if usuario.is_staff else "empleado"
    }
    return render(request, 'editar_usuario.html', context)
