from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Ekskursija, Profile, EkskursijosDalyvavimas
from .forms import EkskursijaForma, PaskelbtiForma

def checkRole(user):
    # Matches checkRole() call in Valdyti sequence diagram
    try:
        return user.profile.role
    except Profile.DoesNotExist:
        return None

def checkIfEmptyList(ekskursijos):
    # Matches checkIfEmptyList() self-call in Peržiūrėti sequence diagram
    return not ekskursijos.exists()

def showAlert():
    # Matches showAlert() call in Peržiūrėti sequence diagram
    return "Neturite prieigos prie šio puslapio."

def getEnrolledPupils(ekskursija):
    # Matches getEnrolledPupils() call in Valdyti sequence diagram
    return EkskursijosDalyvavimas.objects.filter(
        ekskursija=ekskursija, statusas='dalyvauja'
    ).select_related('mokinys')

def checkDate(data):
    # Matches checkDate() self-call in Valdyti sequence diagram
    return data >= timezone.now().date()

@login_required
def getExcursionList(request):
    # Matches getExcursionList() call in Peržiūrėti sequence diagram
    role = checkRole(request.user)
    ekskursijos = Ekskursija.objects.all()  # matches all() call in diagram

    if request.method == 'POST' and role == 'mokytojas':
        # matches delete() call in diagram
        ids = request.POST.getlist('trinti_ids')
        Ekskursija.objects.filter(pk__in=ids).delete()
        return redirect('getExcursionList')

    empty = checkIfEmptyList(ekskursijos)  # matches checkIfEmptyList() in diagram
    alert = showAlert() if role not in ['mokytojas', 'mokinys'] else None  # matches showAlert()

    return render(request, 'ekskursijos/sarasas.html', {
        'ekskursijos': ekskursijos,
        'role': role,
        'empty': empty,
        'alert': alert,
    })

@login_required
def openExcursion(request, pk):
    # Matches open() call in Valdyti sequence diagram
    e = get_object_or_404(Ekskursija, pk=pk)  # matches get() call in diagram
    role = checkRole(request.user)             # matches checkRole() in diagram

    dalyviai = getEnrolledPupils(e)            # matches getEnrolledPupils() in diagram

    forma = PaskelbtiForma()

    if request.method == 'POST' and role == 'mokytojas':
        forma = PaskelbtiForma(request.POST)
        if forma.is_valid():
            data = forma.cleaned_data['ekskursijos_data']
            if not checkDate(data):            # matches checkDate() in diagram
                forma.add_error('ekskursijos_data', 'Data negali būti praeityje.')  # matches error reply
            else:
                e.ekskursijos_data = data
                e.statusas = 'paskelbta'
                e.save()                       # matches success message in diagram
                return redirect('openExcursion', pk=pk)

    return render(request, 'ekskursijos/detaliai.html', {
        'ekskursija': e,
        'role': role,
        'dalyviai': dalyviai,
        'forma': forma,
    })

@login_required
def prisijungti(request, pk):
    # Handles Prisijungti prie ekskursijų ref in Peržiūrėti diagram
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
    # Matches addExcursion() call in Peržiūrėti sequence diagram
    if checkRole(request.user) != 'mokytojas':
        return redirect('getExcursionList')
    forma = EkskursijaForma(request.POST or None)
    if forma.is_valid():
        forma.save()                           # matches create() call in diagram
        return redirect('getExcursionList')    # matches success message reply in diagram
    return render(request, 'ekskursijos/forma.html', {'forma': forma, 'veiksmas': 'Pridėti'})

@login_required
def redaguoti(request, pk):
    if checkRole(request.user) != 'mokytojas':
        return redirect('getExcursionList')
    e = get_object_or_404(Ekskursija, pk=pk)
    forma = EkskursijaForma(request.POST or None, instance=e)
    if forma.is_valid():
        forma.save()
        return redirect('getExcursionList')
    return render(request, 'ekskursijos/forma.html', {'forma': forma, 'veiksmas': 'Redaguoti'})

@login_required
def deleteExcursion(request, pk):
    # Matches delete() call in Peržiūrėti sequence diagram (single excursion)
    if checkRole(request.user) != 'mokytojas':
        return redirect('getExcursionList')
    e = get_object_or_404(Ekskursija, pk=pk)
    if request.method == 'POST':
        e.delete()                             # matches delete() on Excursion entity in diagram
        return redirect('getExcursionList')
    return render(request, 'ekskursijos/trinti.html', {'ekskursija': e})