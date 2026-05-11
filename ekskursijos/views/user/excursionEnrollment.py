from django.shortcuts import get_object_or_404
from ...models.models import Excursion, ExcursionEnrollment


def getAllExcursionParticipants(ekskursija):
    return ExcursionEnrollment.objects.filter(
        excursion=ekskursija, status='participating'
    ).select_related('pupil')
