from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User, Group
from django.db import IntegrityError
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from Pagos.models import Pago, Abono
from Gastos.models import Gasto
from Prestamos.models import Prestamo
from datetime import timedelta
from django.http import Http404
from decimal import Decimal
from Clientes.models import Comunidad


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
    inicio_semana = hoy - timedelta(days=hoy.weekday())  # lunes de esta semana
    inicio_mes = hoy.replace(day=1)
    total_comunidades = Comunidad.objects.count()

    # Determinar usuarios según rol
    if request.user.is_staff:
        users = User.objects.all()
    else:
        users = User.objects.filter(id=request.user.id)

    # Diccionarios para cobradores
    totales_cobradores = {}
    totales_gastos = {}
    prestamos_diarios = {}

    # Listados de pagos para las tablas (sin filtrar por cobrador, o filtrando según necesidad)
    # Aquí asumimos que quieres mostrar todos los pagos (o solo los del usuario si no es staff)
    if request.user.is_staff:
        pagos_hoy = Pago.objects.filter(fecha_programada=hoy)
        pagos_semana = Pago.objects.filter(fecha_programada__gte=inicio_semana, fecha_programada__lte=hoy)
        pagos_mes = Pago.objects.filter(fecha_programada__gte=inicio_mes, fecha_programada__lte=hoy)
        pagos_total = Pago.objects.all()
    else:
        pagos_hoy = Pago.objects.filter(cobrador_asignado=request.user, fecha_programada=hoy)
        pagos_semana = Pago.objects.filter(cobrador_asignado=request.user, fecha_programada__gte=inicio_semana, fecha_programada__lte=hoy)
        pagos_mes = Pago.objects.filter(cobrador_asignado=request.user, fecha_programada__gte=inicio_mes, fecha_programada__lte=hoy)
        pagos_total = Pago.objects.filter(cobrador_asignado=request.user)

    # Totales para los pies de tabla
    total_hoy = pagos_hoy.aggregate(total=Sum('monto_pago'))['total'] or Decimal('0')
    total_semana = pagos_semana.aggregate(total=Sum('monto_pago'))['total'] or Decimal('0')
    total_mes = pagos_mes.aggregate(total=Sum('monto_pago'))['total'] or Decimal('0')
    total_general = pagos_total.aggregate(total=Sum('monto_pago'))['total'] or Decimal('0')

    # Estadísticas globales para tarjetas superiores
    total_recaudado = Abono.objects.aggregate(total=Sum('monto'))['total'] or Decimal('0')
    total_gastos_global = Gasto.objects.aggregate(total=Sum('monto'))['total'] or Decimal('0')
    total_prestamos_hoy = pagos_hoy.filter(estado_pago__in=['pendiente', 'parcial']).count()
    
    # Morosidad: porcentaje de pagos atrasados sobre el total de pagos pendientes
    pagos_atrasados = Pago.objects.filter(estado_pago__in=['pendiente', 'parcial'], fecha_programada__lt=hoy).count()
    total_pagos_pendientes = Pago.objects.filter(estado_pago__in=['pendiente', 'parcial']).count()
    morosidad = (pagos_atrasados / total_pagos_pendientes * 100) if total_pagos_pendientes > 0 else 0

    # Calcular datos por cada usuario (cobrador)
    for user in users:
        # Pagos de hoy para este cobrador
        abonos_hoy = Abono.objects.filter(cobrador=user, fecha__date=hoy)
        total_pagado = abonos_hoy.aggregate(Sum('monto'))['monto__sum'] or Decimal('0')
        
        gastos_hoy = Gasto.objects.filter(usuario=user, fecha_registro=hoy)
        total_gasto = gastos_hoy.aggregate(Sum('monto'))['monto__sum'] or Decimal('0')
        
        # Préstamos pendientes hoy
        pagos_pendientes_hoy = Pago.objects.filter(
            cobrador_asignado=user,
            estado_pago='pendiente',
            fecha_programada=hoy
        )
        prestamos_pendientes_hoy_count = pagos_pendientes_hoy.values('prestamo').distinct().count()
        
        totales_cobradores[user.username] = total_pagado - total_gasto
        totales_gastos[user.username] = total_gasto
        prestamos_diarios[user.username] = prestamos_pendientes_hoy_count

    context = {
        'totales_cobradores': totales_cobradores,
        'totales_gastos': totales_gastos,
        'prestamos_diarios': prestamos_diarios,
        # Variables para las tablas
        'pagos_hoy': pagos_hoy,
        'pagos_semana': pagos_semana,
        'pagos_mes': pagos_mes,
        'pagos_total': pagos_total,
        'total_hoy': total_hoy,
        'total_semana': total_semana,
        'total_mes': total_mes,
        'total_general': total_general,
        # Tarjetas globales
        'total_recaudado': total_recaudado,
        'total_gastos': total_gastos_global,
        'total_prestamos_hoy': total_prestamos_hoy,
        'morosidad': morosidad,
        'default_value': Decimal('0.00'),
         'total_comunidades': total_comunidades,
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
        
        abonos_hoy = Abono.objects.filter(
                cobrador=user,
                fecha__date=hoy
            )
        abonos_semana = Abono.objects.filter(
                cobrador=user,
                fecha__date__gte=inicio_semana,
                fecha__date__lte=fin_semana
            )
        abonos_mes = Abono.objects.filter(
                    cobrador=user,
                    fecha__year=hoy.year,
                    fecha__month=hoy.month
                )
        abonos_totales = Abono.objects.filter(
                    cobrador=user
                )
        
        total_pagado_hoy = abonos_hoy.aggregate(
                total=Sum('monto')
            )['total'] or 0
        total_pagado_semana = abonos_semana.aggregate(
                total=Sum('monto')
            )['total'] or 0
        total_pagado_mes = abonos_mes.aggregate(
                total=Sum('monto')
            )['total'] or 0
        total_pagado_general = abonos_totales.aggregate(
                    total=Sum('monto')
                )['total'] or 0
      
        

          # Traer los clientes relacionados con esos pagos
        abonos_hoy_detalles = abonos_hoy.select_related(
                    'pago__prestamo__cliente'
                ).values(
                    'pago__prestamo__cliente__nombre',
                    'pago__prestamo__tipo',
                    'monto',
                    'fecha',
                    'metodo_pago')
        abonos_semana_detalles = abonos_semana.select_related(
                    'pago__prestamo__cliente'
                ).values(
                    'pago__prestamo__cliente__nombre',
                    'pago__prestamo__tipo',
                    'fecha',              # fecha real del abono
                    'monto',              # monto real pagado
                    'metodo_pago'
                )
        abonos_mes_detalles = abonos_mes.select_related(
                        'pago__prestamo__cliente'
                    ).values(
                        'pago__prestamo__cliente__nombre',
                        'pago__prestamo__tipo',
                        'fecha',
                        'monto',
                        'metodo_pago'
                    )
        abonos_totales_detalles = abonos_totales.select_related(
                        'pago__prestamo__cliente'
                    ).values(
                        'pago__prestamo__cliente__nombre',
                        'pago__prestamo__tipo',
                        'fecha',
                        'monto',
                        'metodo_pago'
                    )
        
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
            'pagos_hoy_detalles': abonos_hoy_detalles,
            'pagos_semana_detalles': abonos_semana_detalles,
            'pagos_mes_detalles': abonos_mes_detalles,
            'pagos_totales_detalles': abonos_totales_detalles,
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
        pagos_pendientes_hoy = Pago.objects.filter( cobrador_asignado=user, estado_pago='pendiente', fecha_programada=hoy)
        pagos_pendientes_semana = Pago.objects.filter(cobrador_asignado=user,estado_pago='pendiente',fecha_programada__gte=inicio_semana,fecha_programada__lte=fin_semana)
        pagos_pendientes_mes = Pago.objects.filter( cobrador_asignado=user, estado_pago='pendiente', fecha_programada__month=hoy.month)
        pagos_pendientes_totales = Pago.objects.filter( cobrador_asignado=user, estado_pago='pendiente')

        # Contamos los pagos pendientes por día, semana, mes y total
        pagos_hoy = pagos_pendientes_hoy.count()
        pagos_semana = pagos_pendientes_semana.count()
        pagos_mes = pagos_pendientes_mes.count()
        pagos_totales = pagos_pendientes_totales.count()

        # Obtener detalles de los pagos pendientes (Nombre cliente, tipo de préstamo, fecha, monto, método de pago)
        pagos_hoy_detalles = pagos_pendientes_hoy.select_related('prestamo__cliente').values('prestamo__cliente__nombre', 'prestamo__tipo', 'fecha_programada', 'monto_pago')
        pagos_semana_detalles = pagos_pendientes_semana.select_related('prestamo__cliente').values('prestamo__cliente__nombre', 'prestamo__tipo', 'fecha_programada', 'monto_pago')
        pagos_mes_detalles = pagos_pendientes_mes.select_related('prestamo__cliente').values('prestamo__cliente__nombre', 'prestamo__tipo', 'fecha_programada', 'monto_pago')
        pagos_totales_detalles = pagos_pendientes_totales.select_related('prestamo__cliente').values('prestamo__cliente__nombre', 'prestamo__tipo', 'fecha_programada', 'monto_pago')
        
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
