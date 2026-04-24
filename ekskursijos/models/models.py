from django.db import models
from django.contrib.auth.models import User

class Ekskursija(models.Model):
    STATUSAS = [
        ('sukurta', 'Sukurta ekskursija'),
        ('objektai', 'Sudarytas objektų sąrašas'),
        ('marsrutas', 'Sudarytas maršrutas'),
        ('paskelbta', 'Paskelbta ekskursija'),
    ]
    pavadinimas      = models.CharField(max_length=200)
    pradžios_laikas  = models.TimeField()
    pabaigos_laikas  = models.TimeField()
    ekskursijos_data = models.DateField(null=True, blank=True)
    statusas         = models.CharField(max_length=20, choices=STATUSAS, default='sukurta')

    def __str__(self):
        return self.pavadinimas

    class Meta:
        verbose_name_plural = "Ekskursijos"


class Profile(models.Model):
    ROLES = [
        ('mokytojas', 'Mokytojas'),
        ('mokinys', 'Mokinys'),
        
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLES)

    def __str__(self):
        return f"{self.user.username} ({self.role})"
    

class EkskursijosDalyvavimas(models.Model):
    STATUSAS = [
        ('dalyvauja', 'Dalyvauja'),
        ('nedalyvauja', 'Nedalyvauja'),
        ('nepasirinko', 'Nepasirinko'),
    ]
    mokinys = models.ForeignKey(User, on_delete=models.CASCADE)
    ekskursija = models.ForeignKey(Ekskursija, on_delete=models.CASCADE)
    statusas = models.CharField(max_length=20, choices=STATUSAS, default='nepasirinko')

    class Meta:
        unique_together = ('mokinys', 'ekskursija')