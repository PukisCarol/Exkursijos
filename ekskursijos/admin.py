from django.contrib import admin
from .models import Ekskursija, Profile, EkskursijosDalyvavimas

# Register your models here
admin.site.register(Ekskursija)
admin.site.register(Profile)
admin.site.register(EkskursijosDalyvavimas)