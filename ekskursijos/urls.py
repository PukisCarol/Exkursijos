from django.urls import path
from .views.user.excursion import (
    addExcursion,
    deleteExcursion,
    deletePlaylistItem,
    getExcursionList,
    openExcursion,
    mainPage,
    openJoinExcursionPage,
    pupilsListPage,
    openExcursionPlaylist,
    openPlaylistItemAddPage,
)
from .views.user.login import authenticateLoginInfo

urlpatterns = [
    path('', mainPage, name='mainPage'),
    path('excursionListPage/', getExcursionList, name='excursionListPage'),
    path('ExcursionPage/<int:pk>/', openExcursion, name='ExcursionPage'),
    path('PlaylistPage/<int:pk>/', openExcursionPlaylist, name='PlaylistPage'),
    path('PlaylistItemAddPage/<int:pk>/', openPlaylistItemAddPage, name='PlaylistItemAddPage'),
    path('PlaylistItem/<int:pk>/<int:item_id>/delete/', deletePlaylistItem, name='deletePlaylistItem'),
    path('PupilsListPage/<int:pk>/', pupilsListPage, name='PupilsListPage'),
    path('CreateExcursionPage/', addExcursion, name='CreateExcursionPage'),
    path('JoinExcursionPage/', openJoinExcursionPage, name='JoinExcursionPage'),
    path('<int:pk>/JoinExcursionPage/', authenticateLoginInfo, name='JoinExcursionPage'),
    path('<int:pk>/trinti/', deleteExcursion, name='deleteExcursion'),
]