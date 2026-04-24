from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .excursion import checkRole
from ...models.models import Ekskursija, Profile, EkskursijosDalyvavimas
from ...forms import EkskursijaForma, PaskelbtiForma


@login_required
def authenticateLoginInfo(request, pk):
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