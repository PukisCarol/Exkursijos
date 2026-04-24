from django.urls import path
from .views.user.excursion import (
    addExcursion,
    deleteExcursion,
    editExcursion,
    open as getExcursionList,
    openExcursion,
)
from .views.user.login import authenticateLoginInfo

urlpatterns = [
    path('',                      getExcursionList,   name='getExcursionList'),
    path('<int:pk>/',             openExcursion,      name='openExcursion'),
    path('prideti/',              addExcursion,       name='addExcursion'),
    path('<int:pk>/redaguoti/',   editExcursion,      name='redaguoti'),
    path('<int:pk>/trinti/',      deleteExcursion,    name='deleteExcursion'),
    path('<int:pk>/prisijungti/', authenticateLoginInfo, name='prisijungti'),
]  