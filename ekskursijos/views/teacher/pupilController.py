from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ...models.models import ExcursionEnrollment, Excursion, Profile
from ..user.excursion import checkRole
from ..user.excursionEnrollment import ExcursionEnrollmentController
from .collectionRouteToAPI import CollectionRouteToAPI
from .excursionController import ExcursionController


class PupilController:
    def get(self, excursion):
        return ExcursionEnrollment.objects.filter(
            excursion=excursion, status='participating'
        ).select_related('pupil', 'pupil__profile')

    def openCreateCollectionRoutePage(self, request, pk):
        excursion_controller = ExcursionController()
        excursion = excursion_controller.openCreateCollectionRoutePage(pk)
        enrollments = self.get(excursion)
        return render(request, 'ekskursijos/teacher/createCollectionRoute.html', {
            'excursion': excursion,
            'enrollments': enrollments,
        })

    def openAdministratePickupAddressesPage(self, request, excursion):
        enrollments = self.get(excursion)
        return render(request, 'ekskursijos/teacher/administratePickupAddress.html', {
            'enrollments': enrollments,
            'excursion': excursion,
        })

    def openDeletePickupAddressesPage(self, request, excursion):
        enrollments = self.get(excursion)
        return self.openAddressDeletionPage(request, excursion, enrollments)

    def openAddressDeletionPage(self, request, excursion, enrollments,
                                selected_ids=None, show_confirmation=False):
        return render(request, 'ekskursijos/teacher/deletePickupAddresses.html', {
            'enrollments': enrollments,
            'excursion': excursion,
            'selected_ids': selected_ids or [],
            'show_confirmation': show_confirmation,
        })

    def deleteSelectedAddresses(self, request, excursion, selected_ids):
        self.delete(selected_ids)
        enrollments = self.get(excursion)
        messages.success(request, 'Paėmimo adresai sėkmingai panaikinti.')
        return self.openAddressDeletionPage(request, excursion, enrollments)

    def delete(self, pupil_ids):
        Profile.objects.filter(user__id__in=pupil_ids).update(home_address=None)

    def cancelDeletionOfAddresses(self, request, excursion):
        enrollments = self.get(excursion)
        messages.info(request, 'Naikinimas atšauktas.')
        return self.openAddressDeletionPage(request, excursion, enrollments)

    def checkIfAllParticipantsHaveAddress(self, excursion):
        enrollments = self.get(excursion)
        for enrollment in enrollments:
            if not enrollment.pupil.profile.home_address:
                return False
        return True

    def getCoordinates(self, excursion):
        api = CollectionRouteToAPI()
        enrollments = self.get(excursion)
        coords = []
        for enrollment in enrollments:
            address = enrollment.pupil.profile.home_address
            result = api.getCoordinates(address)
            if result:
                coords.append({
                    'pupil': enrollment.pupil,
                    'address': address,
                    'coordinates': result,
                })
        return self.saveCoordinates(coords)

    def saveCoordinates(self, coords):
        return coords

    def createListForCollectionRoute(self, excursion, pupils_with_coords):
        from .collectionRoute import CollectionRouteController
        controller = CollectionRouteController()
        return controller.createListForCollectionRoute(excursion, pupils_with_coords)

    def openPickupAddressPage(self, request, pk):
        excursion_controller = ExcursionController()
        excursion = excursion_controller.get(pk)
        pupil_profile = Profile.objects.get(user=request.user)
        return render(request, 'ekskursijos/user/pickupAddressPage.html', {
            'excursion': excursion,
            'pupil_profile': pupil_profile,
        })

    def isAddressValid(self, address):
        return bool(address and address.strip())

    def handleNewAddress(self, request, pk):
        excursion_controller = ExcursionController()
        excursion = excursion_controller.get(pk)
        new_address = request.POST.get('home_address', '').strip()
        pupil_profile = Profile.objects.get(user=request.user)
        if self.isAddressValid(new_address):
            pupil_profile.home_address = new_address
            pupil_profile.save()
            return render(request, 'ekskursijos/user/pickupAddressPage.html', {
                'excursion': excursion,
                'pupil_profile': pupil_profile,
                'success': True,
            })
        else:
            return render(request, 'ekskursijos/user/pickupAddressPage.html', {
                'excursion': excursion,
                'pupil_profile': pupil_profile,
                'error': 'Adresas yra neteisingas.',
            })


    def openEditPickupAddressPage(self, request, excursion, pupil_profile):
        return render(request, 'ekskursijos/teacher/editPickupAddress.html', {
            'excursion': excursion,
            'pupil_profile': pupil_profile,
        })

    def handleInvalidAddress(self, request, excursion, pupil_profile):
        return render(request, 'ekskursijos/teacher/editPickupAddress.html', {
            'excursion': excursion,
            'pupil_profile': pupil_profile,
            'error': 'Adresas yra neteisingas.',
        })


@login_required
def openEditPickupAddressPage(request, pk, pupil_id):
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('AdministratePickupAddress', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)
    pupil_profile = get_object_or_404(Profile, user__id=pupil_id)
    controller = PupilController()

    if request.method == 'POST':
        new_address = request.POST.get('home_address', '').strip()
        if controller.isAddressValid(new_address):
            Profile.objects.filter(user__id=pupil_id).update(home_address=new_address)
            pupil_profile.refresh_from_db()
            return render(request, 'ekskursijos/teacher/editPickupAddress.html', {
                'excursion': excursion,
                'pupil_profile': pupil_profile,
                'success': True,
            })
        else:
            return controller.handleInvalidAddress(request, excursion, pupil_profile)

    return controller.openEditPickupAddressPage(request, excursion, pupil_profile)


@login_required
def openPickupAddressPage(request, pk):
    role = checkRole(request.user)
    if role != 'pupil':
        return redirect('ExcursionPage', pk=pk)

    controller = PupilController()
    if request.method == 'POST':
        return controller.handleNewAddress(request, pk)
    return controller.openPickupAddressPage(request, pk)


@login_required
def openCreateCollectionRoutePage(request, pk):
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ViewCollectionRoute', pk=pk)

    if request.method == 'POST':
        excursion_controller = ExcursionController()
        excursion = excursion_controller.get(pk)

        enrollment_controller = ExcursionEnrollmentController()
        enrollments = enrollment_controller.getAllExcursionParticipants(excursion)

        pupil_controller = PupilController()

        all_have_address = pupil_controller.checkIfAllParticipantsHaveAddress(excursion)
        if not all_have_address:
            messages.error(
                request,
                'Ne visi mokiniai turi nustatytus paėmimo adresus. '
                'Prašome juos įvesti prieš sudarant maršrutą.'
            )
            return render(request, 'ekskursijos/teacher/createCollectionRoute.html', {
                'excursion': excursion,
                'enrollments': enrollments,
                'missing_addresses': True,
            })

        pupils_with_coords = pupil_controller.getCoordinates(excursion)

        pupil_controller.createListForCollectionRoute(excursion, pupils_with_coords)

        messages.success(request, 'Surinkimo maršrutas sėkmingai sudarytas.')
        return redirect('ViewCollectionRoute', pk=pk)

    pupil_controller = PupilController()
    return pupil_controller.openCreateCollectionRoutePage(request, pk)


@login_required
def openAdministratePickupAddressesPage(request, pk):
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ViewCollectionRoute', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)
    pupil_controller = PupilController()
    return pupil_controller.openAdministratePickupAddressesPage(request, excursion)


@login_required
def openDeletePickupAddressesPage(request, pk):
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('AdministratePickupAddress', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)
    pupil_controller = PupilController()

    if request.method == 'POST':
        action = request.POST.get('action')
        enrollments = pupil_controller.get(excursion)

        if action == 'delete':
            selected_ids = request.POST.getlist('pupil_ids')
            return pupil_controller.openAddressDeletionPage(
                request, excursion, enrollments,
                selected_ids=selected_ids, show_confirmation=True
            )
        elif action == 'confirm_delete':
            selected_ids = request.POST.getlist('confirmed_ids')
            return pupil_controller.deleteSelectedAddresses(request, excursion, selected_ids)
        elif action == 'cancel_delete':
            return pupil_controller.cancelDeletionOfAddresses(request, excursion)

    return pupil_controller.openDeletePickupAddressesPage(request, excursion)
