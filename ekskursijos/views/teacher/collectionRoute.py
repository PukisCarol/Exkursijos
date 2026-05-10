from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from ...models.models import CollectionRoute, Excursion
from ..user.excursion import checkRole
from .pupilController import PupilController



@login_required
def openViewCollectionRoutePage(request, pk):
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)

    collection_routes = CollectionRoute.objects.filter(excursion=excursion)

    pupil_controller = PupilController()
    enrollments = pupil_controller.get(excursion)

    return render(request, 'ekskursijos/teacher/viewCollectionRoute.html', {
        'collection_routes': collection_routes,
        'enrollments': enrollments,
        'role': role,
        'excursion': excursion,
    })



