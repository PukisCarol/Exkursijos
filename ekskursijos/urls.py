from django.urls import path
from . import views

urlpatterns = [
    path('',                      views.getExcursionList, name='getExcursionList'),
    path('<int:pk>/',             views.openExcursion,    name='openExcursion'),
    path('prideti/',              views.addExcursion,     name='addExcursion'),
    path('<int:pk>/redaguoti/',   views.redaguoti,        name='redaguoti'),
    path('<int:pk>/trinti/',      views.deleteExcursion,  name='deleteExcursion'),
    path('<int:pk>/prisijungti/', views.prisijungti,      name='prisijungti'),
]  