from django.shortcuts import render

#Pagina principal
def principal(request):
    return render(request, 'prestamos.html')
