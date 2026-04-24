from django import forms
from .models.models import Ekskursija

class EkskursijaForma(forms.ModelForm):
    class Meta:
        model  = Ekskursija
        fields = ['pavadinimas', 'pradžios_laikas', 'pabaigos_laikas']
        widgets = {
            'pradžios_laikas': forms.DateInput(attrs={'type': 'date'}),
            'pabaigos_laikas': forms.DateInput(attrs={'type': 'date'}),
        }

class PaskelbtiForma(forms.Form):
    ekskursijos_data = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Ekskursijos data',
    )