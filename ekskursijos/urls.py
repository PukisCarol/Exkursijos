from django.urls import path
from . import views

urlpatterns = [
    path('',                    views.sarasas,   name='sarasas'),
    path('<int:pk>/',           views.detaliai,  name='detaliai'),
    path('prideti/',            views.prideti,   name='prideti'),
    path('<int:pk>/redaguoti/', views.redaguoti, name='redaguoti'),
    path('<int:pk>/trinti/',    views.trinti,    name='trinti'),
]  