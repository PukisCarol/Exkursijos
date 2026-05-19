from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ...models.models import (
    Excursion, Profile, SharedBackpackItem, Clothing, Item
)
from ...forms import SharedBackpackItemForm


def checkRole(user):
    try:
        return user.profile.role
    except Profile.DoesNotExist:
        return None


@login_required
def openTeacherItemLists(request, pk):
    """Open the teacher item list page for an excursion."""
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)

    items = SharedBackpackItem.objects.filter(
        excursion=excursion
    ).select_related('item').order_by('item__name')

    clothing_items = excursion.clothing_items.all().order_by('name')

    return render(request, 'ekskursijos/teacher/teacherItemPage.html', {
        'excursion': excursion,
        'items': items,
        'clothing_items': clothing_items,
        'edit_mode': False,
        'add_mode': False,
        'form': None,
        'edit_item_id': None,
    })


@login_required
def itemSelected(request, pk):
    """Show edit form for an item."""
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)
    edit_item_id = request.GET.get('edit')

    if not edit_item_id:
        return redirect('openTeacherItemLists', pk=pk)

    edit_item = get_object_or_404(SharedBackpackItem, id=edit_item_id, excursion=excursion)
    edit_form = SharedBackpackItemForm(instance=edit_item, excursion=excursion)

    items = SharedBackpackItem.objects.filter(
        excursion=excursion
    ).select_related('item').order_by('item__name')

    clothing_items = excursion.clothing_items.all().order_by('name')

    return render(request, 'ekskursijos/teacher/teacherItemPage.html', {
        'excursion': excursion,
        'items': items,
        'clothing_items': clothing_items,
        'edit_mode': True,
        'add_mode': False,
        'form': edit_form,
        'edit_item_id': edit_item_id,
    })


@login_required
def editItem(request, pk):
    """Save edited item changes."""
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)
    item_id = request.POST.get('item_id')

    if not item_id:
        return redirect('openTeacherItemLists', pk=pk)

    edit_item = get_object_or_404(SharedBackpackItem, id=item_id, excursion=excursion)
    edit_form = SharedBackpackItemForm(request.POST, instance=edit_item, excursion=excursion)

    if edit_form.is_valid():
        edit_form.save()
        messages.success(request, 'Item updated successfully.')
        return redirect('openTeacherItemLists', pk=pk)

    items = SharedBackpackItem.objects.filter(
        excursion=excursion
    ).select_related('item').order_by('item__name')

    clothing_items = excursion.clothing_items.all().order_by('name')

    return render(request, 'ekskursijos/teacher/teacherItemPage.html', {
        'excursion': excursion,
        'items': items,
        'clothing_items': clothing_items,
        'edit_mode': True,
        'add_mode': False,
        'form': edit_form,
        'edit_item_id': item_id,
    })


@login_required
def newItemSelected(request, pk):
    """Show form for adding a new item."""
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)
    create_form = SharedBackpackItemForm(excursion=excursion)

    items = SharedBackpackItem.objects.filter(
        excursion=excursion
    ).select_related('item').order_by('item__name')

    clothing_items = excursion.clothing_items.all().order_by('name')

    return render(request, 'ekskursijos/teacher/teacherItemPage.html', {
        'excursion': excursion,
        'items': items,
        'clothing_items': clothing_items,
        'edit_mode': False,
        'add_mode': True,
        'form': create_form,
        'edit_item_id': None,
    })


@login_required
def addItem(request, pk):
    """Save a new item to the list."""
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)
    create_form = SharedBackpackItemForm(request.POST, excursion=excursion)

    if create_form.is_valid():
        new_item = create_form.save(commit=False)
        new_item.excursion = excursion
        new_item.save()
        messages.success(request, 'Item added to list.')
        return redirect('openTeacherItemLists', pk=pk)

    items = SharedBackpackItem.objects.filter(
        excursion=excursion
    ).select_related('item').order_by('item__name')

    clothing_items = excursion.clothing_items.all().order_by('name')

    return render(request, 'ekskursijos/teacher/teacherItemPage.html', {
        'excursion': excursion,
        'items': items,
        'clothing_items': clothing_items,
        'edit_mode': False,
        'add_mode': True,
        'form': create_form,
        'edit_item_id': None,
    })


@login_required
def deleteItem(request, pk):
    """Delete an item from the list."""
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)
    item_id = request.POST.get('item_id')

    if item_id:
        SharedBackpackItem.objects.filter(id=item_id, excursion=excursion).delete()
        messages.success(request, 'Item removed from list.')

    return redirect('openTeacherItemLists', pk=pk)


@login_required
def createNewLists(request, pk):
    """Create default item and clothing lists for an excursion."""
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('ExcursionPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)

    linked_items = 0
    linked_clothing = 0

    # Link all existing items to the excursion
    for item in Item.objects.all():
        _, created = SharedBackpackItem.objects.get_or_create(
            excursion=excursion,
            item=item,
            defaults={
                'importance': item.importance,
                'weight': item.weight,
            },
        )
        if created:
            linked_items += 1

    for clothing_name in ['Marškinėliai', 'Kelnės']:
        clothing = Clothing.objects.filter(name__iexact=clothing_name).first()
        if clothing and not excursion.clothing_items.filter(pk=clothing.pk).exists():
            excursion.clothing_items.add(clothing)
            linked_clothing += 1

    if linked_items or linked_clothing:
        messages.success(request, 'Item and clothing lists created.')
    else:
        messages.warning(request, 'No existing items or clothing were found to link.')

    return redirect('openTeacherItemLists', pk=pk)
