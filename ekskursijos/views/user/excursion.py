from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .excursionEnrollment import getAllExcursionParticipants
from ...models.models import Excursion, Profile, ExcursionEnrollment
from ...forms import ExcursionForm, PublishExcursionForm


def checkRole(user):
    try:
        return user.profile.role
    except Profile.DoesNotExist:
        return None


def checkIfEmptyList(ekskursijos):
    return not ekskursijos.exists()


@login_required
def openExcursion(request, pk):
    e = get_object_or_404(Excursion, pk=pk)
    role = checkRole(request.user)

    dalyviai = getAllExcursionParticipants(e)

    initial_data = {'excursion_date': e.excursion_date} if e.excursion_date else {}
    forma = PublishExcursionForm(initial=initial_data)

    if request.method == 'POST' and role == 'teacher':
        forma = PublishExcursionForm(request.POST)
        if forma.is_valid():
            data = forma.cleaned_data['excursion_date']

            if not checkDate(data):
                forma.add_error('excursion_date', 'Date cannot be in the past.')
            else:
                e.excursion_date = data
                e.status = 'published'
                e.save()
                messages.success(request, f'Excursion date successfully published: {data.strftime("%Y-%m-%d")}.')
                return redirect('ExcursionPage', pk=pk)

    return render(request, 'ekskursijos/user/excursionPage.html', {
        'ekskursija': e,
        'role': role,
        'dalyviai': dalyviai,
        'forma': forma,
    })


@login_required
def addExcursion(request):
    if checkRole(request.user) != 'teacher':
        return redirect('excursionListPage')
    forma = ExcursionForm(request.POST or None)
    if request.method == 'POST':
        if forma.is_valid():
            forma.save()
            return redirect('excursionListPage')
    return render(request, 'ekskursijos/teacher/createExcursionPage.html',
                {'forma': forma,
                 'veiksmas': 'Add'})


def checkDate(data):
    return data >= timezone.now().date()


@login_required
def deleteExcursion(request, pk):
    if checkRole(request.user) != 'teacher':
        return redirect('getExcursionList')
    e = get_object_or_404(Excursion, pk=pk)
    if request.method == 'POST':
        e.delete()
        return redirect('excursionListPage')
    return redirect('openExcursion', pk=pk)


@login_required
def getExcursionList(request):
    role = checkRole(request.user)
    ekskursijos = Excursion.objects.all()

    if request.method == 'POST' and role == 'teacher':
        if 'confirm_delete' in request.POST:
            ids = request.POST.getlist('confirm_delete_ids')
            Excursion.objects.filter(pk__in=ids).delete()
            return redirect('excursionListPage')
        ids = request.POST.getlist('trinti_ids')
        if ids:
            excursions_to_delete = Excursion.objects.filter(pk__in=ids)
            return render(request, 'ekskursijos/user/deleteExcursionConfirm.html', {
                'excursions': excursions_to_delete
            })
        return redirect('excursionListPage')

    empty = checkIfEmptyList(ekskursijos)
    alert = "You do not have access to this page." if role not in ['teacher', 'pupil'] else None

    return render(request, 'ekskursijos/user/excursionListPage.html', {
        'ekskursijos': ekskursijos,
        'role': role,
        'empty': empty,
        'alert': alert,
    })


@login_required
def pupilsListPage(request, pk):
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('openExcursion', pk=pk)
    e = get_object_or_404(Excursion, pk=pk)
    pupils = ExcursionEnrollment.objects.filter(excursion=e, status='participating')
    return render(request, 'ekskursijos/user/pupilsListPage.html', {
        'pupils': pupils,
        'excursion': e
    })


@login_required
def openJoinExcursionPage(request):
    role = checkRole(request.user)
    if role != 'pupil':
        return redirect('excursionListPage')
    excursions = Excursion.objects.all()
    current_statuses = {}
    for e in excursions:
        dalyvavimas = ExcursionEnrollment.objects.filter(pupil=request.user, excursion=e).first()
        if dalyvavimas:
            current_statuses[e.pk] = dalyvavimas.status
        else:
            current_statuses[e.pk] = ''
    success_message = error_message = ''
    if request.method == 'POST':
        updated = False
        for e in excursions:
            status = request.POST.get(f'status_{e.pk}')
            if status:
                dalyvavimas, _ = ExcursionEnrollment.objects.get_or_create(pupil=request.user, excursion=e)
                dalyvavimas.status = status
                dalyvavimas.save()
                updated = True
        # Refresh current_statuses after saving
        current_statuses = {}
        for e in excursions:
            dalyvavimas = ExcursionEnrollment.objects.filter(pupil=request.user, excursion=e).first()
            if dalyvavimas:
                current_statuses[e.pk] = dalyvavimas.status
            else:
                current_statuses[e.pk] = ''
        if updated:
            success_message = 'Statuses successfully updated.'
        else:
            error_message = 'No statuses selected.'
    return render(request, 'ekskursijos/user/joinExcursionPage.html', {
        'excursions': excursions,
        'current_statuses': current_statuses,
        'success_message': success_message,
        'error_message': error_message,
    })


def mainPage(request):
    return render(request, 'ekskursijos/user/mainPage.html')
