from django import forms
from .models.models import Excursion


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
