from django import forms
from .models import Ekskursija

class EkskursijaForma(forms.ModelForm):
    class Meta:
        model  = Ekskursija
        fields = ['pavadinimas', 'aprasymas', 'vieta', 'kaina', 'trukme_val', 'nuotrauka', 'aktyvi']
        widgets = {
            'aprasymas': forms.Textarea(attrs={'rows': 4}),
        }