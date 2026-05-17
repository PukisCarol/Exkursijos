from django import forms
from django.forms import formset_factory
from .models.models import Excursion, SharedBackpackItem, Item, Place, PlaceType

class ExcursionForm(forms.ModelForm):
    class Meta:
        model = Excursion
        fields = ['name', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }


class PublishExcursionForm(forms.Form):
    excursion_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Excursion date',
    )


class SharedBackpackItemForm(forms.ModelForm):
    class Meta:
        model = SharedBackpackItem
        fields = ['item', 'importance', 'weight']
        widgets = {
            'importance': forms.NumberInput(attrs={'min': '1', 'max': '10'}),
            'weight': forms.NumberInput(attrs={'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        excursion = kwargs.pop('excursion', None)
        super().__init__(*args, **kwargs)
        if excursion:
            # Only show items not already in the excursion
            existing_items = SharedBackpackItem.objects.filter(
                excursion=excursion
            ).values_list('item_id', flat=True)
            queryset = Item.objects.exclude(id__in=existing_items)
            if self.instance and self.instance.pk:
                queryset = queryset | Item.objects.filter(pk=self.instance.item_id)
            self.fields['item'].queryset = queryset.distinct()


class AddressForm(forms.Form):
    name = forms.CharField(max_length=200, label='Vietos pavadinimas')
    address_text = forms.CharField(max_length=500, label='Adresas')


AddressFormSet = formset_factory(AddressForm, extra=1, max_num=10)


class CriteriaForm(forms.Form):
    max_places = forms.IntegerField(min_value=1, max_value=50, label='Maks. naujų vietų skaičius')
    place_types = forms.ModelMultipleChoiceField(
        queryset=PlaceType.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label='Vietų tipai',
        required=False,
    )


class EditPlaceForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = ['name', 'longitude', 'latitude']
        widgets = {
            'longitude': forms.NumberInput(attrs={'step': 'any'}),
            'latitude': forms.NumberInput(attrs={'step': 'any'}),
        }
