from django.contrib import admin
from .models.models import Excursion, Profile, ExcursionEnrollment

admin.site.register(Excursion)
admin.site.register(Profile)
admin.site.register(ExcursionEnrollment)
