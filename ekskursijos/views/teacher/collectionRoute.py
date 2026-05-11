from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from ...models.models import CollectionRoute, Collection, Excursion
from ..user.excursion import checkRole
from .pupilController import PupilController
from .collectionRouteToAPI import CollectionRouteToAPI
import datetime


class CollectionRouteController:
    def __init__(self):
        self.api = CollectionRouteToAPI()

    def createListForCollectionRoute(self, excursion, pupils_with_coords):
        school_address = settings.SCHOOL_ADDRESS
        school_coords = self.api.getCoordinates(school_address)

        uncollected = list(pupils_with_coords)
        ordered_route = []

        current_stop = school_coords

        while uncollected:
            shortest_distance = self.initializeShortestDistance()
            closest_student = self.initializeClosestStudent()

            for entry in uncollected:
                pupil_coords = entry['coordinates']
                distance = self.getDistance(current_stop, pupil_coords)
                if distance < shortest_distance:
                    shortest_distance = self.saveShortestDistance(distance)
                    closest_student = self.saveClosestStudent(entry)

            ordered_route = self.SetNextStopClosestStudent(ordered_route, closest_student)
            current_stop = closest_student['coordinates']
            uncollected = self.removePupilFromUncollected(uncollected, closest_student)

        self.save(excursion, ordered_route)

    def initializeShortestDistance(self):
        return float('inf')

    def initializeClosestStudent(self):
        return None

    def getDistance(self, origin, destination):
        return self.api.getDistance(origin, destination)

    def saveShortestDistance(self, distance):
        return distance

    def saveClosestStudent(self, entry):
        return entry

    def SetNextStopClosestStudent(self, ordered_route, closest_student):
        ordered_route.append(closest_student)
        return ordered_route

    def removePupilFromUncollected(self, uncollected, closest_student):
        return [e for e in uncollected if e['pupil'].pk != closest_student['pupil'].pk]

    def save(self, excursion, ordered_route):
        # Delete any existing route for this excursion before saving the new one
        CollectionRoute.objects.filter(excursion=excursion).delete()

        today = datetime.date.today()
        route = CollectionRoute.objects.create(
            name=f'Surinkimo maršrutas — {excursion.name}',
            start_date=today,
            end_date=today,
            excursion=excursion,
        )
        for i, entry in enumerate(ordered_route, start=1):
            Collection.objects.create(
                route=route,
                pupil=entry['pupil'],
                sequence_number=i,
            )
        return route


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




