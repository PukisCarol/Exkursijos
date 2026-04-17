from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Ekskursija, Profile, EkskursijosDalyvavimas
from .forms import EkskursijaForma, PaskelbtiForma

def gauti_role(user):
    try:
        return user.profile.role
    except Profile.DoesNotExist:
        return None
    
@login_required
def sarasas(request):
    role = gauti_role(request.user)
    ekskursijos = Ekskursija.objects.all()

    if request.method == 'POST' and role == 'mokytojas':
        ids = request.POST.getlist('trinti_ids')
        Ekskursija.objects.filter(pk__in=ids).delete()
        return redirect('sarasas')

    return render(request, 'ekskursijos/sarasas.html', {
        'ekskursijos': ekskursijos,
        'role': role,
    })

@login_required
def detaliai(request, pk):
    e = get_object_or_404(Ekskursija, pk=pk)
    role = gauti_role(request.user)

    dalyviai = EkskursijosDalyvavimas.objects.filter(
        ekskursija=e, statusas='dalyvauja'
    ).select_related('mokinys')

    forma = PaskelbtiForma()

    if request.method == 'POST' and role == 'mokytojas':
        forma = PaskelbtiForma(request.POST)
        if forma.is_valid():
            data = forma.cleaned_data['ekskursijos_data']
            if data <timezone.now().date():
                forma.add_error('ekskursijos_data', 'Data negali būti praeityje')
            else: 
                e.ekskursijos_data = data
                e.statusas = 'paskelbta'
                e.save()
                return redirect('detaliai', pk=pk)

    return render(request, 'ekskursijos/detaliai.html', {
        'ekskursija': e,
        'role': role,
        'dalyviai': dalyviai,
        'forma': forma,
    })

@login_required
def prisijungti(request, pk):
    e = get_object_or_404(Ekskursija, pk=pk)
    role = gauti_role(request.user)

    if role != 'mokinys':
        return redirect('sarasas')
    
    dalyvavimas, sukurta = EkskursijosDalyvavimas.objects.get_or_create(
        mokinys=request.user,
        ekskursija=e,
        defaults={'statusas': 'dalyvauja'}
    )
    if not sukurta:
        dalyvavimas.statusas = 'dalyvauja'
        dalyvavimas.save()

    return redirect('detaliai', pk=pk)

@login_required
def prideti(request):
    if gauti_role(request.user) != 'mokytojas':
        return redirect('sarasas')
    forma = EkskursijaForma(request.POST or None, request.FILES or None)
    if forma.is_valid():
        forma.save()
        return redirect('sarasas')
    return render(request, 'ekskursijos/forma.html', {'forma': forma, 'veiksmas': 'Pridėti'})

@login_required
def redaguoti(request, pk):
    if gauti_role(request.user) != 'mokytojas':
        return redirect('sarasas')
    e = get_object_or_404(Ekskursija, pk=pk)
    forma = EkskursijaForma(request.POST or None, request.FILES or None, instance=e)
    if forma.is_valid():
        forma.save()
        return redirect('sarasas')
    return render(request, 'ekskursijos/forma.html', {'forma': forma, 'veiksmas': 'Redaguoti'})

@login_required
def trinti(request, pk):
    if gauti_role(request.user) != 'mokytojas':
        return redirect('sarasas')
    e = get_object_or_404(Ekskursija, pk=pk)
    if request.method == 'POST':
        e.delete()
        return redirect('sarasas')
    return render(request, 'ekskursijos/trinti.html', {'ekskursija': e})