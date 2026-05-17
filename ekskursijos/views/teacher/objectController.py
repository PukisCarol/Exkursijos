import math

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from ...models.models import Place, ListOfPlaces, ObjectAddressProgress, Excursion
from ..user.excursion import checkRole
from .collectionRouteToAPI import CollectionRouteToAPI
from ...services.googleApi import GoogleAPI
from ...forms import AddressFormSet, CriteriaForm, EditPlaceForm


class ObjectController:

    def redirect(self, request, pk):
        objects = self.findAll(pk)
        capacity = self.capacity(objects)
        return self.open(request, pk, objects, capacity)

    def findAll(self, pk):
        try:
            list_of_places = ListOfPlaces.objects.get(excursion__pk=pk)
            return list_of_places.places.all()
        except ListOfPlaces.DoesNotExist:
            return Place.objects.none()

    def capacity(self, objects):
        return objects.count()

    def open(self, request, pk, objects, capacity):
        excursion = get_object_or_404(Excursion, pk=pk)
        return render(request, 'ekskursijos/teacher/objectPage.html', {
            'excursion': excursion,
            'objects': objects,
            'capacity': capacity,
        })

    def delete(self, place_id):
        place = get_object_or_404(Place, pk=place_id)
        place.delete()
        return place

    def objectDeleted(self, request, pk):
        messages.success(request, 'vieta pašalinta')
        return redirect('ObjectPage', pk=pk)

    def save(self, place_id, form_data):
        place = get_object_or_404(Place, pk=place_id)
        place.name = form_data['name']
        place.longitude = form_data['longitude']
        place.latitude = form_data['latitude']
        place.save()
        return place

    def submitAddress(self, request, pk, addresses_data):
        excursion = get_object_or_404(Excursion, pk=pk)
        list_of_places, _ = ListOfPlaces.objects.get_or_create(
            excursion=excursion,
            defaults={'name': excursion.name, 'teacher': request.user},
        )
        try:
            api = CollectionRouteToAPI()
        except Exception:
            api = None
        objects_list = []
        for addr in addresses_data:
            coords = api.getCoordinates(addr['address_text']) if api else None
            lat, lng = coords if coords else (0.0, 0.0)
            place = Place.objects.create(
                name=addr['name'],
                latitude=lat,
                longitude=lng,
            )
            ObjectAddressProgress.objects.get_or_create(
                list_of_places=list_of_places,
                place=place,
                defaults={'visit_number': 1, 'duration_minutes': 60},
            )
            objects_list.append(place)
        return objects_list

    def saveCriteriaInfo(self, request, pk, criteria):
        request.session[f'criteria_{pk}'] = criteria

        if self.checkIfRecomendedListExists(request, pk):
            recommended_list = request.session[f'recommended_list_{pk}']
            element = self.takeElementFromRecomendedList(recommended_list, 0)
            self.checkIfFitsCriteria(element, criteria)
        else:
            try:
                list_of_places = ListOfPlaces.objects.get(excursion__pk=pk)
                addresses = [
                    (p.latitude, p.longitude)
                    for p in list_of_places.places.all()
                ]
            except ListOfPlaces.DoesNotExist:
                addresses = []
            recommended_list = self.requestrecomendedObjects(addresses, criteria)
            request.session[f'recommended_list_{pk}'] = recommended_list

        try:
            list_of_places = ListOfPlaces.objects.get(excursion__pk=pk)
            reference_coords = [
                (p.latitude, p.longitude)
                for p in list_of_places.places.all()
            ]
        except ListOfPlaces.DoesNotExist:
            reference_coords = []

        max_places = criteria.get('max_places', 10)
        final_list = []
        candidates = []

        for i in range(len(recommended_list)):
            element = self.takeElementFromRecomendedList(recommended_list, i)
            if element and self.checkIfFitsCriteria(element, criteria):
                candidates = self.takeObject(candidates, element)
                current = candidates[-1].copy()
                current = self.evaluateCoefficient(current, reference_coords)
                final_list = self.insertObjectInFinalList(final_list, current)
            if len(final_list) >= max_places:
                break

        excursion = get_object_or_404(Excursion, pk=pk)
        list_of_places, _ = ListOfPlaces.objects.get_or_create(
            excursion=excursion,
            defaults={'name': excursion.name, 'teacher': request.user},
        )
        saved_places = []
        for place_data in final_list:
            place, _ = Place.objects.get_or_create(
                name=place_data['name'],
                defaults={
                    'latitude': place_data['latitude'],
                    'longitude': place_data['longitude'],
                },
            )
            ObjectAddressProgress.objects.get_or_create(
                list_of_places=list_of_places,
                place=place,
                defaults={'visit_number': 1, 'duration_minutes': 60},
            )
            saved_places.append(place)
        return saved_places

    def checkIfRecomendedListExists(self, request, pk):
        return bool(request.session.get(f'recommended_list_{pk}'))

    def takeElementFromRecomendedList(self, recommended_list, index):
        if index < len(recommended_list):
            return recommended_list[index]
        return None

    def checkIfFitsCriteria(self, place_data, criteria):
        if not place_data:
            return False
        allowed_types = criteria.get('place_types', [])
        if not allowed_types:
            return True
        place_types = place_data.get('types', [])
        return any(
            allowed.lower() in [t.lower() for t in place_types]
            for allowed in allowed_types
        )

    def requestrecomendedObjects(self, addresses, criteria):
        try:
            google_api = GoogleAPI()
            return google_api.requestRecomendedObjects(addresses, criteria)
        except Exception:
            return []

    def takeObject(self, candidates, place_data):
        candidates.append(place_data)
        return candidates

    def evaluateCoefficient(self, place_data, reference_coords):
        if not reference_coords:
            place_data['coefficient'] = 0.0
            return place_data
        min_dist = float('inf')
        for ref_lat, ref_lng in reference_coords:
            dist = math.sqrt(
                (place_data['latitude'] - ref_lat) ** 2 +
                (place_data['longitude'] - ref_lng) ** 2
            )
            if dist < min_dist:
                min_dist = dist
        place_data['coefficient'] = min_dist
        return place_data

    def insertObjectInFinalList(self, final_list, place_data):
        final_list.append(place_data)
        final_list.sort(key=lambda x: x.get('coefficient', 0))
        return final_list

    def saveObligatoryInfo(self, request, pk, place_id, is_obligatory):
        try:
            list_of_places = ListOfPlaces.objects.get(excursion__pk=pk)
            progress = ObjectAddressProgress.objects.get(
                list_of_places=list_of_places,
                place_id=place_id,
            )
            progress.is_obligatory = is_obligatory
            progress.save()
            return progress
        except (ListOfPlaces.DoesNotExist, ObjectAddressProgress.DoesNotExist):
            return None


@login_required
def openObjectsList(request, pk):
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)
    controller = ObjectController()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'confirm_delete':
            place_id = request.POST.get('place_id')
            controller.delete(place_id)
            return controller.objectDeleted(request, pk)
        elif action == 'decline_delete':
            messages.info(request, 'Atšaukta šalinti vietą')
            return redirect('ObjectPage', pk=pk)
        elif action == 'save_edit':
            place_id = request.POST.get('place_id')
            place = get_object_or_404(Place, pk=int(place_id))
            form = EditPlaceForm(request.POST, instance=place)
            if form.is_valid():
                form_data = {
                    'name': form.cleaned_data['name'],
                    'longitude': form.cleaned_data['longitude'],
                    'latitude': form.cleaned_data['latitude'],
                }
                controller.save(place_id, form_data)
                messages.success(request, 'ok')
                return redirect('ObjectPage', pk=pk)
            objects = controller.findAll(pk)
            capacity = controller.capacity(objects)
            excursion = get_object_or_404(Excursion, pk=pk)
            return render(request, 'ekskursijos/teacher/objectPage.html', {
                'excursion': excursion,
                'objects': objects,
                'capacity': capacity,
                'edit_place_id': int(place_id),
                'edit_form': form,
                'edit_place': place,
            })
        return redirect('ObjectPage', pk=pk)

    confirm_id = request.GET.get('confirm')
    edit_id = request.GET.get('edit')

    if confirm_id:
        objects = controller.findAll(pk)
        capacity = controller.capacity(objects)
        excursion = get_object_or_404(Excursion, pk=pk)
        return render(request, 'ekskursijos/teacher/objectPage.html', {
            'excursion': excursion,
            'objects': objects,
            'capacity': capacity,
            'confirm_delete_id': int(confirm_id),
            'place_to_delete': get_object_or_404(Place, pk=int(confirm_id)),
        })

    if edit_id:
        place = get_object_or_404(Place, pk=int(edit_id))
        objects = controller.findAll(pk)
        capacity = controller.capacity(objects)
        excursion = get_object_or_404(Excursion, pk=pk)
        return render(request, 'ekskursijos/teacher/objectPage.html', {
            'excursion': excursion,
            'objects': objects,
            'capacity': capacity,
            'edit_place_id': int(edit_id),
            'edit_form': EditPlaceForm(instance=place),
            'edit_place': place,
        })

    return controller.redirect(request, pk)


@login_required
def openNewObjectPage(request, pk):
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ObjectPage', pk=pk)
    excursion = get_object_or_404(Excursion, pk=pk)
    address_formset = AddressFormSet(prefix='addresses')
    return render(request, 'ekskursijos/teacher/newObjectPage.html', {
        'excursion': excursion,
        'step': 'address',
        'address_formset': address_formset,
    })


@login_required
def submitAddress(request, pk):
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ObjectPage', pk=pk)
    excursion = get_object_or_404(Excursion, pk=pk)
    if request.method == 'POST':
        address_formset = AddressFormSet(request.POST, prefix='addresses')
        if address_formset.is_valid():
            controller = ObjectController()
            addresses_data = [
                {'name': f.cleaned_data['name'], 'address_text': f.cleaned_data['address_text']}
                for f in address_formset
                if f.cleaned_data.get('name')
            ]
            objects = controller.submitAddress(request, pk, addresses_data)
            criteria_form = CriteriaForm()
            return render(request, 'ekskursijos/teacher/newObjectPage.html', {
                'excursion': excursion,
                'step': 'criteria',
                'objects': objects,
                'criteria_form': criteria_form,
            })
        return render(request, 'ekskursijos/teacher/newObjectPage.html', {
            'excursion': excursion,
            'step': 'address',
            'address_formset': address_formset,
        })
    return redirect('NewObjectPage', pk=pk)


@login_required
def saveCriteria(request, pk):
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ObjectPage', pk=pk)
    excursion = get_object_or_404(Excursion, pk=pk)
    if request.method == 'POST':
        criteria_form = CriteriaForm(request.POST)
        if criteria_form.is_valid():
            controller = ObjectController()
            place_type_names = list(
                criteria_form.cleaned_data['place_types'].values_list('name', flat=True)
            )
            criteria = {
                'max_places': criteria_form.cleaned_data['max_places'],
                'place_types': place_type_names,
            }
            final_objects = controller.saveCriteriaInfo(request, pk, criteria)
            request.session[f'final_place_ids_{pk}'] = [p.pk for p in final_objects]
            try:
                list_of_places = ListOfPlaces.objects.get(excursion__pk=pk)
                obligatory_ids = set(
                    ObjectAddressProgress.objects.filter(
                        list_of_places=list_of_places,
                        is_obligatory=True,
                    ).values_list('place_id', flat=True)
                )
            except ListOfPlaces.DoesNotExist:
                obligatory_ids = set()
            return render(request, 'ekskursijos/teacher/newObjectPage.html', {
                'excursion': excursion,
                'step': 'result',
                'objects': final_objects,
                'obligatory_ids': obligatory_ids,
            })
        return render(request, 'ekskursijos/teacher/newObjectPage.html', {
            'excursion': excursion,
            'step': 'criteria',
            'criteria_form': criteria_form,
        })
    return redirect('NewObjectPage', pk=pk)


@login_required
def saveObligatory(request, pk):
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ObjectPage', pk=pk)
    if request.method == 'POST':
        place_id = request.POST.get('place_id')
        is_obligatory = request.POST.get('is_obligatory') == 'true'
        controller = ObjectController()
        controller.saveObligatoryInfo(request, pk, place_id, is_obligatory)
        excursion = get_object_or_404(Excursion, pk=pk)
        final_place_ids = request.session.get(f'final_place_ids_{pk}', [])
        final_objects = list(Place.objects.filter(pk__in=final_place_ids))
        try:
            list_of_places = ListOfPlaces.objects.get(excursion__pk=pk)
            obligatory_ids = set(
                ObjectAddressProgress.objects.filter(
                    list_of_places=list_of_places,
                    is_obligatory=True,
                ).values_list('place_id', flat=True)
            )
        except ListOfPlaces.DoesNotExist:
            obligatory_ids = set()
        return render(request, 'ekskursijos/teacher/newObjectPage.html', {
            'excursion': excursion,
            'step': 'result',
            'objects': final_objects,
            'obligatory_ids': obligatory_ids,
        })
    return redirect('NewObjectPage', pk=pk)
