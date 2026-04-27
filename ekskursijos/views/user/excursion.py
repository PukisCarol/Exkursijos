from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .excursionEnrollment import getAllExcursionParticipants
from ...models.models import Ekskursija, Profile, EkskursijosDalyvavimas
from ...forms import EkskursijaForma, PaskelbtiForma

def checkRole(user):
    try:
        return user.profile.role
    except Profile.DoesNotExist:
        return None
    
def checkIfEmptyList(ekskursijos):
    return not ekskursijos.exists()


@login_required
def openExcursion(request, pk):
    e = get_object_or_404(Ekskursija, pk=pk)
    role = checkRole(request.user)

    dalyviai = getAllExcursionParticipants(e)

    initial_data = {'ekskursijos_data': e.ekskursijos_data} if e.ekskursijos_data else {}
    forma = PaskelbtiForma(initial=initial_data)

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
                messages.success(request, f'Ekskursijos data sėkmingai paskelbta: {data.strftime("%Y-%m-%d")}.')
                return redirect('ExcursionPage', pk=pk)

    return render(request, 'ekskursijos/user/excursionPage.html', {
        'ekskursija': e,
        'role': role,
        'dalyviai': dalyviai,
        'forma': forma,
    })

@login_required
def addExcursion(request):
    if checkRole(request.user) != 'mokytojas':
        return redirect('excursionListPage')
    forma = EkskursijaForma(request.POST or None)
    if request.method == 'POST':
        if forma.is_valid():
            forma.save()
            return redirect('excursionListPage')
    return render(request, 'ekskursijos/teacher/createExcursionPage.html', 
                {'forma': forma,
                'veiksmas': 'Pridėti'})

def checkDate(data):
    return data >= timezone.now().date()

@login_required
def deleteExcursion(request, pk):
    if checkRole(request.user) != 'mokytojas':
        return redirect('getExcursionList')
    e = get_object_or_404(Ekskursija, pk=pk)
    if request.method == 'POST':
        e.delete()
        return redirect('excursionListPage')
    return redirect('openExcursion', pk=pk)


@login_required
def open(request):
    role = checkRole(request.user)
    ekskursijos = Ekskursija.objects.all()

    if request.method == 'POST' and role == 'mokytojas':
        if 'confirm_delete' in request.POST:
            ids = request.POST.getlist('confirm_delete_ids')
            Ekskursija.objects.filter(pk__in=ids).delete()
            return redirect('excursionListPage')
        ids = request.POST.getlist('trinti_ids')
        if ids:
            excursions_to_delete = Ekskursija.objects.filter(pk__in=ids)
            return render(request, 'ekskursijos/user/deleteExcursionConfirm.html', {
                'excursions': excursions_to_delete
            })
        return redirect('excursionListPage')

    empty = checkIfEmptyList(ekskursijos)
    alert = "Neturite prieigos prie šio puslapio." if role not in ['mokytojas', 'mokinys'] else None

    return render(request, 'ekskursijos/user/excursionListPage.html', {
        'ekskursijos': ekskursijos,
        'role': role,
        'empty': empty,
        'alert': alert,
    })

@login_required
def pupilsListPage(request, pk):
    role = checkRole(request.user)
    if role != 'mokytojas':
        return redirect('openExcursion', pk=pk)
    e = get_object_or_404(Ekskursija, pk=pk)
    pupils = EkskursijosDalyvavimas.objects.filter(ekskursija=e, statusas='dalyvauja')
    return render(request, 'ekskursijos/user/pupilsListPage.html', {
        'pupils': pupils,
        'excursion': e
    })

@login_required
def joinExcursionPage(request):
    role = checkRole(request.user)
    if role != 'mokinys':
        return redirect('excursionListPage')
    excursions = Ekskursija.objects.all()
    current_statuses = {}
    for e in excursions:
        dalyvavimas = EkskursijosDalyvavimas.objects.filter(mokinys=request.user, ekskursija=e).first()
        if dalyvavimas:
            current_statuses[e.pk] = dalyvavimas.statusas
        else:
            current_statuses[e.pk] = ''
    success_message = error_message = ''
    if request.method == 'POST':
        updated = False
        for e in excursions:
            status = request.POST.get(f'status_{e.pk}')
            if status:
                dalyvavimas, _ = EkskursijosDalyvavimas.objects.get_or_create(mokinys=request.user, ekskursija=e)
                dalyvavimas.statusas = status
                dalyvavimas.save()
                updated = True
        # Refresh current_statuses after saving
        current_statuses = {}
        for e in excursions:
            dalyvavimas = EkskursijosDalyvavimas.objects.filter(mokinys=request.user, ekskursija=e).first()
            if dalyvavimas:
                current_statuses[e.pk] = dalyvavimas.statusas
            else:
                current_statuses[e.pk] = ''
        if updated:
            success_message = 'Statusai sėkmingai atnaujinti.'
        else:
            error_message = 'Nepasirinkote jokių statusų.'
    return render(request, 'ekskursijos/user/joinExcursionPage.html', {
        'excursions': excursions,
        'current_statuses': current_statuses,
        'success_message': success_message,
        'error_message': error_message,
    })

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def mainPage(request):
    return render(request, 'ekskursijos/user/mainPage.html')