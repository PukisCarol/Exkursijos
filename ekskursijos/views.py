from django.shortcuts import render, get_object_or_404, redirect
from .models import Ekskursija
from .forms import EkskursijaForma

def sarasas(request):
    ekskursijos = Ekskursija.objects.all()
    return render(request, 'ekskursijos/sarasas.html', {'ekskursijos': ekskursijos})

def detaliai(request, pk):
    e = get_object_or_404(Ekskursija, pk=pk)
    return render(request, 'ekskursijos/detaliai.html', {'ekskursija': e})

def prideti(request):
    forma = EkskursijaForma(request.POST or None, request.FILES or None)
    if forma.is_valid():
        forma.save()
        return redirect('sarasas')
    return render(request, 'ekskursijos/forma.html', {'forma': forma, 'veiksmas': 'Pridėti'})

def redaguoti(request, pk):
    e = get_object_or_404(Ekskursija, pk=pk)
    forma = EkskursijaForma(request.POST or None, request.FILES or None, instance=e)
    if forma.is_valid():
        forma.save()
        return redirect('sarasas')
    return render(request, 'ekskursijos/forma.html', {'forma': forma, 'veiksmas': 'Redaguoti'})

def trinti(request, pk):
    e = get_object_or_404(Ekskursija, pk=pk)
    if request.method == 'POST':
        e.delete()
        return redirect('sarasas')
    return render(request, 'ekskursijos/trinti.html', {'ekskursija': e})