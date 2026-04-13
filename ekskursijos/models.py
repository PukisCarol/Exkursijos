from django.db import models

class Ekskursija(models.Model):
    pavadinimas = models.CharField(max_length=200)
    aprasymas   = models.TextField()
    vieta       = models.CharField(max_length=200)
    kaina       = models.DecimalField(max_digits=8, decimal_places=2)
    trukme_val  = models.PositiveIntegerField()
    nuotrauka   = models.ImageField(upload_to='ekskursijos/', blank=True, null=True)
    aktyvi      = models.BooleanField(default=True)

    def __str__(self):
        return self.pavadinimas

    class Meta:
        verbose_name_plural = "Ekskursijos"