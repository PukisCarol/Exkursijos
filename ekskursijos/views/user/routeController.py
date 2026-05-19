from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from ...models.models import Excursion, ListOfPlaces, ObjectAddressProgress
from ..user.excursion import checkRole
from ...services.routeToAPI import RouteToAPI


# ---------------------------------------------------------------------------
# Helper – validate time input
# ---------------------------------------------------------------------------

def validate_time(time_data):
    if not time_data:
        return False
    return True


# ---------------------------------------------------------------------------
# RouteController  (control class, matches sequence diagram)
# ---------------------------------------------------------------------------

class RouteController:

    def __init__(self):
        self.api = RouteToAPI()

    # -- Generate route helpers ---------------------------------------------------

    def all(self, excursion):
        """Returns the list of Place objects for this excursion (step 3 / 11 in diagram)."""
        try:
            list_of_places = ListOfPlaces.objects.get(excursion=excursion)
            return list(list_of_places.places.all())
        except ListOfPlaces.DoesNotExist:
            return []

    def showPlacesForReviewPage(self, request, excursion):
        """Fetches all places and renders the confirm-places page (step 2)."""
        places = self.all(excursion)
        return self.showPlacesToConfirm(request, excursion, places)

    def showPlacesToConfirm(self, request, excursion, places):
        """Renders the ConfirmPlacesPage (step 5)."""
        return render(request, 'ekskursijos/teacher/confirmPlacesPage.html', {
            'excursion': excursion,
            'places': places,
        })

    def getDistanceAndTime(self, excursion, places):
        """
        Delegates to RouteToAPI.getDistancesAndTimes and returns the distances/times
        dict keyed by (i, j) index pairs (steps 13-16 in diagram).
        """
        return self.api.getDistancesAndTimes(places)

    def generateAllSubsetsForTwoPlaces(self, places):
        """
        Generates initial subsets (pairs) used to seed the route-building loop
        (step 17 in diagram).  Returns a list of 2-place route candidates.
        """
        n = len(places)
        subsets = []
        for i in range(n):
            for j in range(n):
                if i != j:
                    subsets.append([i, j])
        return subsets

    def createSubsetsWithUnvisitedPlaces(self, current_route, all_indices, distances):
        """
        For the current partial route extend by every unvisited place (step 18).
        Returns a list of (cost, candidate_route) tuples.
        """
        visited = set(current_route)
        unvisited = [idx for idx in all_indices if idx not in visited]
        candidates = []
        for idx in unvisited:
            cost = self._route_cost(current_route + [idx], distances)
            candidates.append((cost, current_route + [idx]))
        return candidates

    def findShortestPathInSubset(self, candidates):
        """
        Picks the candidate route with the lowest cost (step 19).
        Returns the best route list.
        """
        if not candidates:
            return []
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    def addShortestPathPlaceToRoute(self, route):
        """
        Simply returns the route as-is; the mutation already happened in
        findShortestPathInSubset.  Exists to mirror the diagram method name (step 20).
        """
        return route

    def addLastPlaceDistance(self, route, distances):
        """
        Adds the final leg cost (last place back to first) so the total
        round-trip cost is available (step 21).
        """
        if len(route) < 2:
            return 0
        last_to_first = distances.get((route[-1], route[0]), {}).get('distance', 0)
        return last_to_first

    def getMap(self, places):
        """Delegates to RouteToAPI.getMap (step 22)."""
        return self.api.getMap(places)

    def calculateTime(self, route, distances, places, list_of_places=None):
        """
        Calculates the total travel duration (in minutes) for the ordered route
        plus the visit durations stored on each place (step 26).
        """
        total_seconds = 0
        n = len(route)
        for step in range(n - 1):
            pair = (route[step], route[step + 1])
            duration = distances.get(pair, {}).get('duration', 0)
            if duration is not None:
                total_seconds += duration

        # Add per-place visit durations from ObjectAddressProgress
        for idx in route:
            place = places[idx]
            try:
                if list_of_places is not None:
                    progress = ObjectAddressProgress.objects.filter(
                        list_of_places=list_of_places,
                        place=place,
                    ).first()
                else:
                    progress = place.address_progresses.first()
                if progress and progress.duration_minutes:
                    total_seconds += progress.duration_minutes * 60
            except Exception:
                pass

        minutes = total_seconds // 60
        return minutes if minutes > 0 else 0

    def generateRoute(self, excursion):
        """
        Full route-generation algorithm that wires together all sub-steps
        (steps 10-26 in diagram).  Returns (ordered_places, total_minutes, map_url).
        """
        places = self.all(excursion)
        if not places:
            return [], 0, ''

        n = len(places)
        all_indices = list(range(n))

        # Steps 13-16: get distances matrix
        distances = self.getDistanceAndTime(excursion, places)

        if n == 1:
            map_url = self.getMap(places)
            total_minutes = self.calculateTime([0], distances, places)
            return places, total_minutes, map_url

        # Step 17: seed with all 2-place subsets, pick shortest starting pair
        initial_subsets = self.generateAllSubsetsForTwoPlaces(places)
        best_pair = min(
            initial_subsets,
            key=lambda s: distances.get((s[0], s[1]), {}).get('distance', float('inf')),
        )
        current_route = best_pair

        # Steps 18-20 loop: extend until all places are included
        while len(current_route) < n:
            candidates = self.createSubsetsWithUnvisitedPlaces(current_route, all_indices, distances)
            current_route = self.findShortestPathInSubset(candidates)
            current_route = self.addShortestPathPlaceToRoute(current_route)

        # Step 21
        self.addLastPlaceDistance(current_route, distances)

        # Build ordered place list
        ordered_places = [places[i] for i in current_route]

        # Steps 22-25: get map
        map_url = self.getMap(ordered_places)

        # Step 26: calculate time
        total_minutes = self.calculateTime(current_route, distances, places)

        return ordered_places, total_minutes, map_url

    def save(self, excursion, ordered_places):
        """
        Persists the route order by updating visit_number on ObjectAddressProgress
        and setting excursion.status = 'route_ready' (step 34-35 in diagram).
        """
        try:
            list_of_places = ListOfPlaces.objects.get(excursion=excursion)
        except ListOfPlaces.DoesNotExist:
            return

        for order, place in enumerate(ordered_places, start=1):
            ObjectAddressProgress.objects.filter(
                list_of_places=list_of_places,
                place=place,
            ).update(visit_number=order)

        excursion.status = 'route_ready'
        excursion.save()

    def saveStartTime(self, excursion, start_date, end_date):
        """
        Persists the user-provided start date and the calculated end date
        (both as yyyy-mm-dd date objects) into excursion.start_date / end_date.
        """
        excursion.start_date = start_date
        excursion.end_date = end_date
        excursion.save()

    def sendSuccessMessage(self, request):
        """Adds a Django success message (step 36)."""
        messages.success(request, 'Maršrutas sėkmingai išsaugotas.')

    # -- Delete route helpers ------------------------------------------------

    def deleteRoute(self, request, excursion):
        """
        Called when teacher clicks 'delete route'.
        Renders the RoutePage with a show_delete_dialog flag so the
        confirmation dialog is visible (sequence diagram: step 1).
        """
        role = None
        if request.user.is_authenticated:
            try:
                role = request.user.profile.role
            except Exception:
                pass

        places = self.getRoute(excursion)
        total_minutes = 0
        map_url = ''
        if places:
            distances = self.getDistanceAndTime(excursion, places)
            route_indices = list(range(len(places)))
            total_minutes = self.calculateTime(route_indices, distances, places)
            map_url = self.getMap(places)

        return render(request, 'ekskursijos/user/routePage.html', {
            'excursion': excursion,
            'places': places,
            'total_minutes': total_minutes,
            'map_url': map_url,
            'show_delete_dialog': True,
            'role': role,
        })

    def delete(self, excursion):
        """
        Performs the actual deletion of the route.
        Clears visit_number on all ObjectAddressProgress records
        and resets excursion.status (sequence diagram: step ALT confirm).
        """
        try:
            list_of_places = ListOfPlaces.objects.get(excursion=excursion)
            list_of_places.address_progresses.all().update(visit_number=0)
        except ListOfPlaces.DoesNotExist:
            pass

        excursion.status = 'created'
        excursion.save()

    def sendDeleteSuccessMessage(self, request):
        """Adds a Django success message after route deletion (sequence diagram: final step)."""
        messages.success(request, 'Maršrutas sėkmingai ištrintas.')

    # -- View route diagram helpers ---------------------------------------------------

    def getRoute(self, excursion):
        """
        Returns the ordered list of Place objects sorted by visit_number (step 7-11).
        """
        try:
            list_of_places = ListOfPlaces.objects.get(excursion=excursion)
        except ListOfPlaces.DoesNotExist:
            return []

        progresses = (
            list_of_places.address_progresses
            .select_related('place')
            .order_by('visit_number')
        )
        return [p.place for p in progresses]

    def showRoute(self, request, excursion, places, total_minutes, map_url):
        """Renders the RoutePage (step 20)."""
        role = None
        if request.user.is_authenticated:
            try:
                role = request.user.profile.role
            except Exception:
                pass
        return render(request, 'ekskursijos/user/routePage.html', {
            'excursion': excursion,
            'places': places,
            'total_minutes': total_minutes,
            'map_url': map_url,
            'role': role,
        })

    # -- Internal helpers ----------------------------------------------------

    def _route_cost(self, route, distances):
        cost = 0
        for i in range(len(route) - 1):
            cost += distances.get((route[i], route[i + 1]), {}).get('distance', float('inf'))
        return cost


# ---------------------------------------------------------------------------
# View functions (URL entry points)
# ---------------------------------------------------------------------------

@login_required
def planRoute(request, pk):
    """
    Step 1 – Teacher clicks 'Plan route' on ExcursionPage.
    Shows the list of places for review (ConfirmPlacesPage).
    """
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)
    controller = RouteController()
    return controller.showPlacesForReviewPage(request, excursion)


@login_required
def confirmPlaces(request, pk):
    """
    Teacher confirms the place list and proceeds to set time per place.
    """
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    if request.method == 'POST':
        return redirect('TimePerPlace', pk=pk)

    return redirect('PlanRoute', pk=pk)


@login_required
def openTimePerPlacePage(request, pk):
    """
     Opens the TimePerPlacePage (sets duration per place + start time).
    Kept as its own view so it can also be accessed directly.
    """
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)

    if request.method == 'POST':
        raw_time = request.POST.get('start_time')
        place_data = request.POST.getlist('place_times')
        unit_data = request.POST.getlist('place_time_units')

        if not validate_time(raw_time):
            messages.error(request, 'Neteisingi laiko duomenys.')
            return redirect('TimePerPlace', pk=pk)

        # --- Check that start_time is not in the past ---
        try:
            start_dt = datetime.strptime(raw_time, '%Y-%m-%dT%H:%M')
            now = timezone.localtime(timezone.now()).replace(tzinfo=None)
            if start_dt < now:
                messages.error(request, 'Pradžios laikas negali būti praeityje.')
                return redirect('TimePerPlace', pk=pk)
        except (ValueError, TypeError):
            messages.error(request, 'Neteisingas pradžios laiko formatas.')
            return redirect('TimePerPlace', pk=pk)

        try:
            list_of_places = ListOfPlaces.objects.get(excursion=excursion)
            progresses = list(
                list_of_places.address_progresses.select_related('place').all()
            )
            for i, progress in enumerate(progresses):
                raw_value = place_data[i] if i < len(place_data) else ''
                unit = unit_data[i] if i < len(unit_data) else 'minutes'

                if not raw_value or not raw_value.strip():
                    messages.error(request, f'Laukelis "{progress.place.name}" negali būti tuščias.')
                    return redirect('TimePerPlace', pk=pk)

                try:
                    value = int(raw_value)
                except (ValueError, TypeError):
                    messages.error(request, f'Lauke "{progress.place.name}" turi būti sveikas skaičius.')
                    return redirect('TimePerPlace', pk=pk)

                if value <= 0:
                    messages.error(
                        request,
                        f'Lauke "{progress.place.name}" reikšmė turi būti didesnė už 0.',
                    )
                    return redirect('TimePerPlace', pk=pk)

                # --- Max 24 hours check ---
                if unit == 'hours' and value >= 24:
                    messages.error(
                        request,
                        f'Lauke "{progress.place.name}" valandomis reikšmė negali viršyti 24.',
                    )
                    return redirect('TimePerPlace', pk=pk)

                # Convert hours to minutes
                if unit == 'hours':
                    value = value * 60

                progress.duration_minutes = value
                progress.save()

            # Store start_time in session so GenerateRoute can calculate end_time
            request.session[f'route_start_time_{pk}'] = raw_time
            excursion.save()
            messages.success(request, 'Laikas sėkmingai išsaugotas.')
            return redirect('GenerateRoute', pk=pk)

        except Exception as e:
            messages.error(request, str(e))
            return redirect('TimePerPlace', pk=pk)

    try:
        list_of_places = ListOfPlaces.objects.get(excursion=excursion)
        places = list(list_of_places.address_progresses.select_related('place').all())
    except ListOfPlaces.DoesNotExist:
        places = []

    return render(request, 'ekskursijos/teacher/timePerPlacePage.html', {
        'excursion': excursion,
        'places': places,
        'role': role,
    })


@login_required
def generateRoute(request, pk):
    """
    Step 9/10 – Teacher clicks 'Generate Route'.
    Runs the algorithm and shows result on GenerateRoutePage.
    """
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)
    controller = RouteController()

    ordered_places, total_minutes, map_url = controller.generateRoute(excursion)

    # Store generated order in session so saveRoute can use it
    request.session[f'generated_route_{pk}'] = [p.pk for p in ordered_places]

    # Calculate end date/time from start_time + total_minutes
    start_time_str = request.session.get(f'route_start_time_{pk}')
    formatted_start = None
    formatted_end = None
    if start_time_str and total_minutes is not None and total_minutes != 0:
        try:
            start_dt = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            from datetime import timedelta
            end_dt = start_dt + timedelta(minutes=total_minutes)
            from django.utils.dateformat import DateFormat
            formatted_start = DateFormat(start_dt).format('Y-m-d H:i')
            formatted_end = DateFormat(end_dt).format('Y-m-d H:i')
        except (ValueError, TypeError):
            pass

    return render(request, 'ekskursijos/teacher/generateRoutePage.html', {
        'excursion': excursion,
        'places': ordered_places,
        'total_minutes': total_minutes,
        'map_url': map_url,
        'role': role,
        'formatted_start': formatted_start,
        'formatted_end': formatted_end,
    })


@login_required
def openRouteEditPage(request, pk):
    """
    Step 28 – Teacher opens the RouteEditPage to manually reorder the places.
    """
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)
    controller = RouteController()

    # Use previously generated order (from session) or fall back to saved order
    generated_ids = request.session.get(f'generated_route_{pk}')
    if generated_ids:
        from ...models.models import Place
        id_to_place = {p.pk: p for p in Place.objects.filter(pk__in=generated_ids)}
        places = [id_to_place[pid] for pid in generated_ids if pid in id_to_place]
    else:
        places = controller.getRoute(excursion)

    return render(request, 'ekskursijos/teacher/routeEditPage.html', {
        'excursion': excursion,
        'places': places,
        'role': role,
    })


@login_required
def saveRoute(request, pk):
    """
    Step 32/33 – Teacher saves the route (from GenerateRoutePage or RouteEditPage).
    Persists visit order, sets status=route_ready, sends success message.
    """
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)
    controller = RouteController()

    if request.method == 'POST':
        from ...models.models import Place

        # RouteEditPage submits ordered place IDs as 'place_order'
        ordered_ids = request.POST.getlist('place_order')
        if ordered_ids:
            id_to_place = {p.pk: p for p in Place.objects.filter(pk__in=ordered_ids)}
            ordered_places = [id_to_place[int(pid)] for pid in ordered_ids if int(pid) in id_to_place]
        else:
            # Fall back to session-stored generated order
            generated_ids = request.session.get(f'generated_route_{pk}', [])
            id_to_place = {p.pk: p for p in Place.objects.filter(pk__in=generated_ids)}
            ordered_places = [id_to_place[pid] for pid in generated_ids if pid in id_to_place]

        # Step 34-35: save()
        controller.save(excursion, ordered_places)

        # Save start_date and end_date (yyyy-mm-dd) from session start time + route duration
        start_time_str = request.session.get(f'route_start_time_{pk}')
        if start_time_str:
            try:
                from datetime import timedelta
                start_dt = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
                distances = controller.getDistanceAndTime(excursion, ordered_places)
                route_indices = list(range(len(ordered_places)))
                total_minutes = controller.calculateTime(route_indices, distances, ordered_places)
                end_dt = start_dt + timedelta(minutes=total_minutes)
                controller.saveStartTime(excursion, start_dt.date(), end_dt.date())
            except (ValueError, TypeError):
                pass

        # Step 36: sendSuccessMessage()
        controller.sendSuccessMessage(request)

        # Clear session
        request.session.pop(f'generated_route_{pk}', None)
        request.session.pop(f'route_start_time_{pk}', None)

        # Step 37: redirect back to ExcursionPage (success message shown there)
        return redirect('ExcursionPage', pk=pk)

    return redirect('GenerateRoute', pk=pk)


@login_required
def getRoute(request, pk):
    """
    Diagram 2 – Step 6/7 – User selects the RoutePage.
    Fetches the saved route, distances/times and map, then renders RoutePage.
    """
    excursion = get_object_or_404(Excursion, pk=pk)
    controller = RouteController()

    # Steps 8-11: get ordered places
    places = controller.getRoute(excursion)

    # Steps 12-15: getDistanceAndTime
    distances = controller.getDistanceAndTime(excursion, places)

    # Build sequential distance/time info for the template
    route_indices = list(range(len(places)))
    total_minutes = controller.calculateTime(route_indices, distances, places)

    # Steps 16-19: getMap
    map_url = controller.getMap(places)

    # Step 20: showRoute
    return controller.showRoute(request, excursion, places, total_minutes, map_url)


# ---------------------------------------------------------------------------
# Delete route views (sequence diagram: delete route flow)
# ---------------------------------------------------------------------------


@login_required
def deleteRouteView(request, pk):
    """
    Teacher clicks 'Delete Route' button.
    Shows the route page with the confirmation dialog visible.
    """
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)
    controller = RouteController()
    return controller.deleteRoute(request, excursion)


@login_required
def confirmDeletion(request, pk):
    """
    Teacher confirms deletion in the dialog.
    Performs the actual deletion and redirects to ExcursionPage.
    """
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    if request.method == 'POST':
        excursion = get_object_or_404(Excursion, pk=pk)
        controller = RouteController()
        controller.delete(excursion)
        controller.sendDeleteSuccessMessage(request)
        return redirect('ExcursionPage', pk=pk)

    return redirect('RoutePage', pk=pk)


@login_required
def cancelDeletion(request, pk):
    """
    Teacher cancels deletion in the dialog.
    Redirects back to the RoutePage without any changes.
    """
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    return redirect('RoutePage', pk=pk)
