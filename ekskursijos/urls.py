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
from .views.teacher.teacherItem import (
    openTeacherItemList,
    itemSelected,
    editItem,
    newItemSelected,
    addItem,
    deleteItem,
    createNewLists,
)
from .views.pupil.pupilItem import (
    openPupilItemList,
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
    path('TeacherItemPage/<int:pk>/', openTeacherItemList, name='TeacherItemPage'),
    path('TeacherItemPage/<int:pk>/itemSelected/', itemSelected, name='itemSelected'),
    path('TeacherItemPage/<int:pk>/editItem/', editItem, name='editItem'),
    path('TeacherItemPage/<int:pk>/newItemSelected/', newItemSelected, name='newItemSelected'),
    path('TeacherItemPage/<int:pk>/addItem/', addItem, name='addItem'),
    path('TeacherItemPage/<int:pk>/deleteItem/', deleteItem, name='deleteItem'),
    path('TeacherItemPage/<int:pk>/createNewLists/', createNewLists, name='createNewLists'),
    path('PupilItemPage/<int:pk>/', openPupilItemList, name='openPupilItemList'),
    path('CreateExcursionPage/', addExcursion, name='CreateExcursionPage'),
    path('JoinExcursionPage/', openJoinExcursionPage, name='JoinExcursionPage'),
    path('<int:pk>/JoinExcursionPage/', authenticateLoginInfo, name='JoinExcursionPage'),
    path('<int:pk>/trinti/', deleteExcursion, name='deleteExcursion'),
]