from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from ...models.models import Ekskursija, Profile, EkskursijosDalyvavimas
from ...forms import EkskursijaForma, PaskelbtiForma

def getAllExcursionParticipants(ekskursija):
    return EkskursijosDalyvavimas.objects.filter(
        ekskursija=ekskursija, statusas='dalyvauja'
    ).select_related('mokinys')