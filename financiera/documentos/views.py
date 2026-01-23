from django.shortcuts import render

# Create your views here.
def DocumentosPrincipal(request):
    return render(request, 'documentos.html')
