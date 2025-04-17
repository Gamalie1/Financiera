from django.shortcuts import render

#Pagina principal
def inicio_clientes(request):
    return render(request, 'clientes.html')
