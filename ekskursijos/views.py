from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Ekskursija, Profile, EkskursijosDalyvavimas
from .forms import EkskursijaForma, PaskelbtiForma

def checkRole(user):
    try:
        return user.profile.role
    except Profile.DoesNotExist:
        return None

def checkIfEmptyList(ekskursijos):
    return not ekskursijos.exists()

def showAlert():
    return "Neturite prieigos prie šio puslapio."

def getEnrolledPupils(ekskursija):
    return EkskursijosDalyvavimas.objects.filter(
        ekskursija=ekskursija, statusas='dalyvauja'
    ).select_related('mokinys')

def checkDate(data):
    return data >= timezone.now().date()

@login_required
def getExcursionList(request):
    role = checkRole(request.user)
    ekskursijos = Ekskursija.objects.all()

    if request.method == 'POST' and role == 'mokytojas':
        ids = request.POST.getlist('trinti_ids')
        Ekskursija.objects.filter(pk__in=ids).delete()
        return redirect('getExcursionList')

    empty = checkIfEmptyList(ekskursijos)
    alert = showAlert() if role not in ['mokytojas', 'mokinys'] else None

    return render(request, 'ekskursijos/sarasas.html', {
        'ekskursijos': ekskursijos,
        'role': role,
        'empty': empty,
        'alert': alert,
    })

@login_required
def openExcursion(request, pk):
    e = get_object_or_404(Ekskursija, pk=pk)
    role = checkRole(request.user)

    dalyviai = getEnrolledPupils(e)

    forma = PaskelbtiForma()

    if request.method == 'POST' and role == 'mokytojas':
        forma = PaskelbtiForma(request.POST)
        if forma.is_valid():
            data = forma.cleaned_data['ekskursijos_data']
            if not checkDate(data):
                forma.add_error('ekskursijos_data', 'Data negali būti praeityje.')
            else:
                e.ekskursijos_data = data
                e.statusas = 'paskelbta'
                e.save()
                return redirect('openExcursion', pk=pk)

    return render(request, 'ekskursijos/detaliai.html', {
        'ekskursija': e,
        'role': role,
        'dalyviai': dalyviai,
        'forma': forma,
    })

@login_required
def prisijungti(request, pk):
    e = get_object_or_404(Ekskursija, pk=pk)
    role = checkRole(request.user)

    if role != 'mokinys':
        return redirect('getExcursionList')

    dalyvavimas, sukurta = EkskursijosDalyvavimas.objects.get_or_create(
        mokinys=request.user,
        ekskursija=e,
        defaults={'statusas': 'dalyvauja'}
    )
    if not sukurta:
        dalyvavimas.statusas = 'dalyvauja'
        dalyvavimas.save()

    return redirect('openExcursion', pk=pk)

@login_required
def addExcursion(request):
    if checkRole(request.user) != 'mokytojas':
        return redirect('getExcursionList')
    forma = EkskursijaForma(request.POST or None)
    if forma.is_valid():
        forma.save()
        return redirect('getExcursionList')
    return render(request, 'ekskursijos/forma.html', 
                {'forma': forma,
                'veiksmas': 'Pridėti'})

@login_required
def redaguoti(request, pk):
    if checkRole(request.user) != 'mokytojas':
        return redirect('getExcursionList')
    e = get_object_or_404(Ekskursija, pk=pk)
    forma = EkskursijaForma(request.POST or None, instance=e)
    if forma.is_valid():
        forma.save()
        return redirect('getExcursionList')
    return render(request, 'ekskursijos/forma.html', 
                {'forma': forma, 
                'veiksmas': 'Redaguoti'})

@login_required
def deleteExcursion(request, pk):
    if checkRole(request.user) != 'mokytojas':
        return redirect('getExcursionList')
    e = get_object_or_404(Ekskursija, pk=pk)
    if request.method == 'POST':
        e.delete()
        return redirect('getExcursionList')
    return render(request, 'ekskursijos/trinti.html', 
                  {'ekskursija': e})