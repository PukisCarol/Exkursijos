from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ...models.models import ExcursionEnrollment, Excursion, Profile
from ..user.excursion import checkRole


class PupilController:
    def get(self, excursion):
        return ExcursionEnrollment.objects.filter(
            excursion=excursion, status='participating'
        ).select_related('pupil', 'pupil__profile')

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



@login_required
def openAdministratePickupAddressesPage(request, pk):
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ViewCollectionRoute', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)

    pupil_controller = PupilController()
    return pupil_controller.openAdministratePickupAddressesPage(request, excursion)
