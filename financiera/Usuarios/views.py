from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.contrib import messages



#Index
def inicio(request):
    return render(request, 'index.html')

#Login para iniciar sesion
def signin(request):
    if request.method == 'GET':
        return render(request, 'signin.html', {"form": AuthenticationForm})
    else:
        user = authenticate(
            request, username=request.POST['username'], password=request.POST['password'])
        if user is None:
            return render(request, 'signin.html', {"form": AuthenticationForm, "error": "Usuario o la contraseña es incorrecta."})

        login(request, user)
        return redirect('principal')
    
#Pagina principal
def principal(request):
    return render(request, 'principal.html')

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
        username = request.POST['username']
        first_name = request.POST['first_name']  # Asegúrate de que el nombre del campo sea el correcto
        last_name = request.POST['last_name']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        ocupacion = request.POST['ocupacion']

        # Comprobar si las contraseñas coinciden
        if password1 != password2:
            messages.error(request, "Las contraseñas no coinciden")
            return render(request, 'signup.html')

        try:
            # Crear un nuevo usuario
            user = User.objects.create_user(username=username, 
                                            first_name=first_name,  # Guardar el primer nombre
                                            last_name=last_name,  # Guardar el apellido
                                            email=email,  # Guardar el correo
                                            password=password1)  # Guardar la contraseña
            user.save()

            # Guardar el tipo de usuario (ocupación) si es necesario
            if ocupacion == "psicologa":
                # Asignar al grupo de Administradores
                user.is_staff = True  # Si quieres que sea un administrador
            user.save()

            # Redirigir al usuario a la página de login o dashboard
            messages.success(request, f'Cuenta creada exitosamente para {username}!')
            return redirect('login')  # Asegúrate de tener una URL llamada 'login'

        except IntegrityError:
            messages.error(request, "El nombre de usuario ya existe.")
            return render(request, 'signup.html')

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

