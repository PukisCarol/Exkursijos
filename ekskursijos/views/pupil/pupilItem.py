from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from types import SimpleNamespace
from ...models.models import (
    Excursion, Profile, SharedBackpackItem, PupilBackpackItem
)


def checkRole(user):
    try:
        return user.profile.role
    except Profile.DoesNotExist:
        return None


def knapsackRecursive(unchecked_items, remaining_weight):
    if not unchecked_items or remaining_weight <= 0:
        return 0, 0, []

    current_item = max(unchecked_items, key=lambda item: item.importance)
    current_index = unchecked_items.index(current_item)
    next_items = unchecked_items[:current_index] + unchecked_items[current_index + 1:]

    skip_importance, skip_weight, skip_items = knapsackRecursive(next_items, remaining_weight)

    if current_item.weight > remaining_weight:
        return skip_importance, skip_weight, skip_items

    take_importance, take_weight, take_items = knapsackRecursive(
        next_items,
        remaining_weight - current_item.weight,
    )
    take_importance += current_item.importance
    take_weight += current_item.weight
    take_items = [current_item] + take_items

    if take_importance > skip_importance:
        return take_importance, take_weight, take_items

    if take_importance < skip_importance:
        return skip_importance, skip_weight, skip_items

    if take_weight < skip_weight:
        return take_importance, take_weight, take_items

    return skip_importance, skip_weight, skip_items


def buildCandidateItems(request, shared_items):
    candidate_items = []

    for shared_item in shared_items:
        importance_raw = request.POST.get(f'importance_{shared_item.id}', str(shared_item.importance)).strip()
        try:
            importance = int(importance_raw)
        except ValueError:
            return None

        candidate_items.append(SimpleNamespace(
            item=shared_item.item,
            importance=importance,
            weight=shared_item.weight,
        ))

    return candidate_items


def saveBestCombination(request, excursion, candidate_items, max_weight_grams):
    best_importance, best_weight, best_items = knapsackRecursive(candidate_items, max_weight_grams)

    if not best_items:
        return False, best_importance, best_weight

    PupilBackpackItem.objects.filter(
        pupil=request.user,
        excursion=excursion,
    ).delete()

    for candidate_item in best_items:
        PupilBackpackItem.objects.create(
            pupil=request.user,
            excursion=excursion,
            item=candidate_item.item,
            importance=candidate_item.importance,
            weight=candidate_item.weight,
            taken=True,
        )

    return True, best_importance, best_weight


def editItems(request, excursion, pupil_items, shared_items, pupil_has_list):
    return render(request, 'ekskursijos/pupil/pupilItemPage.html', {
        'excursion': excursion,
        'is_published': True,
        'items': pupil_items,
        'shared_items': shared_items,
        'show_create_form': False,
        'show_edit_form': True,
        'pupil_has_list': pupil_has_list,
    })


def saveItems(request, excursion, pupil_items):
    selected_ids = set()

    for pupil_item in pupil_items:
        if request.POST.get(f'taken_{pupil_item.id}') == 'on':
            selected_ids.add(pupil_item.id)

    PupilBackpackItem.objects.filter(
        pupil=request.user,
        excursion=excursion,
    ).update(taken=False)

    if selected_ids:
        PupilBackpackItem.objects.filter(
            pupil=request.user,
            excursion=excursion,
            id__in=selected_ids,
        ).update(taken=True)


@login_required
def openPupilItemLists(request, pk):
    """Open the pupil item list page for an excursion."""
    role = checkRole(request.user)
    if role != 'pupil':
        return redirect('ExcursionPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)

    # Check if excursion is published
    if excursion.status != 'published':
        return render(request, 'ekskursijos/pupil/pupilItemPage.html', {
            'excursion': excursion,
            'is_published': False,
            'items': [],
            'shared_items': [],
            'show_create_form': False,
            'pupil_has_list': False,
        })

    shared_items = SharedBackpackItem.objects.filter(
        excursion=excursion
    ).select_related('item').order_by('item__name')

    # Check if pupil has a list created
    pupil_items = PupilBackpackItem.objects.filter(
        pupil=request.user,
        excursion=excursion
    ).select_related('item').order_by('item__name')

    pupil_has_list = pupil_items.exists()

    if pupil_has_list:
        if request.GET.get('edit') == '1':
            return editItems(request, excursion, pupil_items, shared_items, pupil_has_list)

        if request.method == 'POST':
            action = request.POST.get('action', 'create')

            if action == 'edit':
                saveItems(request, excursion, pupil_items)
                messages.success(request, 'Pasirinkti daiktai išsaugoti.')
                return redirect('openPupilItemList', pk=pk)

            max_weight_raw = request.POST.get('max_weight', '').strip()
            candidate_items = buildCandidateItems(request, shared_items)
            if candidate_items is None:
                messages.error(request, 'Svarbos reikšmės turi būti sveikieji skaičiai.')
                return render(request, 'ekskursijos/pupil/pupilItemPage.html', {
                    'excursion': excursion,
                    'is_published': True,
                    'items': [],
                    'shared_items': shared_items,
                    'show_create_form': True,
                    'pupil_has_list': False,
                })

            try:
                max_weight_kg = float(max_weight_raw)
            except ValueError:
                messages.error(request, 'Įveskite galiojantį maksimalų svorį.')
                return render(request, 'ekskursijos/pupil/pupilItemPage.html', {
                    'excursion': excursion,
                    'is_published': True,
                    'items': [],
                    'shared_items': shared_items,
                    'show_create_form': True,
                    'pupil_has_list': False,
                })

            if max_weight_kg <= 0:
                messages.error(request, 'Maksimalus svoris turi būti didesnis už nulį.')
                return render(request, 'ekskursijos/pupil/pupilItemPage.html', {
                    'excursion': excursion,
                    'is_published': True,
                    'items': [],
                    'shared_items': shared_items,
                    'show_create_form': True,
                    'pupil_has_list': False,
                })

            max_weight_grams = int(max_weight_kg * 1000)
            created, best_importance, best_weight = saveBestCombination(
                request,
                excursion,
                candidate_items,
                max_weight_grams,
            )

            if created:
                messages.success(
                    request,
                    f'Sąrašas sukurtas. Geriausias derinys: svarba {best_importance}, svoris {best_weight} g.',
                )
            else:
                messages.info(request, 'Tinkamų daiktų derinių nerasta.')

            return redirect('openPupilItemList', pk=pk)

        show_create_form = request.GET.get('add') == '1'

    return render(request, 'ekskursijos/pupil/pupilItemPage.html', {
        'excursion': excursion,
        'is_published': True,
        'items': pupil_items,
        'shared_items': shared_items,
        'show_create_form': show_create_form,
        'show_edit_form': False,
        'pupil_has_list': pupil_has_list,
    })
