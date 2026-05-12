from django.shortcuts import get_object_or_404
from ...models.models import Excursion, ExcursionEnrollment


class ExcursionEnrollmentController:
    def getAllExcursionParticipants(self, excursion):
        return self.getParticipants(excursion)

    def getParticipants(self, excursion):
        return ExcursionEnrollment.objects.filter(
            excursion=excursion, status='participating'
        ).select_related('pupil', 'pupil__profile')


def getAllExcursionParticipants(ekskursija):
    return ExcursionEnrollment.objects.filter(
        excursion=ekskursija, status='participating'
    ).select_related('pupil')
