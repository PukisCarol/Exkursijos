from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .excursion import checkRole
from ...models.models import Excursion, Profile, ExcursionEnrollment
from ...forms import ExcursionForm, PublishExcursionForm


@login_required
def authenticateLoginInfo(request, pk):
    e = get_object_or_404(Excursion, pk=pk)
    role = checkRole(request.user)

    if role != 'pupil':
        return redirect('excursionListPage')

    dalyvavimas, sukurta = ExcursionEnrollment.objects.get_or_create(
        pupil=request.user,
        excursion=e,
        defaults={'status': 'participating'}
    )
    if not sukurta:
        dalyvavimas.status = 'participating'
        dalyvavimas.save()

    return redirect('ExcursionPage', pk=pk)
