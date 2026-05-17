from django.urls import path
from .views.user.excursion import (
    addExcursion,
    deleteExcursion,
    getExcursionList,
    openExcursion,
    mainPage,
    openJoinExcursionPage,
    pupilsListPage,
)
from .views.user.playlistController import (
    openExcursionPlaylist,
    openPlaylistItemAddPage,
    searchSongs,
    deletePlaylistItem,
    changePlaylistItemPlace,
    addSong,
    generatePlaylist,
)
from .views.user.votingController import (
    openGenreVotingPage,
    voteForGenre,
)
from .views.teacher.teacherItem import (
    openTeacherItemLists,
    itemSelected,
    editItem,
    newItemSelected,
    addItem,
    deleteItem,
    createNewLists,
)
from .views.pupil.pupilItem import (
    openPupilItemLists,
)
from .views.user.login import authenticateLoginInfo
from .views.teacher.collectionRoute import openViewCollectionRoutePage
from .views.teacher.pupilController import openAdministratePickupAddressesPage, openDeletePickupAddressesPage, openCreateCollectionRoutePage, openPickupAddressPage, openEditPickupAddressPage
from .views.teacher.objectController import (
    openObjectsList,
    openNewObjectPage,
    submitAddress,
    saveCriteria,
    saveObligatory,
)

urlpatterns = [
    path('', mainPage, name='mainPage'),
    path('excursionListPage/', getExcursionList, name='excursionListPage'),
    path('ExcursionPage/<int:pk>/', openExcursion, name='ExcursionPage'),
    path('ExcursionPage/<int:pk>/genreVoting/', openGenreVotingPage, name='genreVotingPage'),
    path('ExcursionPage/<int:pk>/genreVoting/vote/', voteForGenre, name='voteForGenre'),
    path('PlaylistPage/<int:pk>/', openExcursionPlaylist, name='PlaylistPage'),
    path('PlaylistPage/<int:pk>/changePlace/', changePlaylistItemPlace, name='changePlaylistItemPlace'),
    path('PlaylistItemAddPage/<int:pk>/', openPlaylistItemAddPage, name='PlaylistItemAddPage'),
    path('PlaylistItemAddPage/<int:pk>/search/', searchSongs, name='searchSongs'),
    path('PlaylistItemAddPage/<int:pk>/add/', addSong, name='addSong'),
    path('PlaylistItem/<int:pk>/<int:item_id>/delete/', deletePlaylistItem, name='deletePlaylistItem'),
    path('PupilsListPage/<int:pk>/', pupilsListPage, name='PupilsListPage'),
    path('TeacherItemPage/<int:pk>/', openTeacherItemLists, name='openTeacherItemLists'),
    path('TeacherItemPage/<int:pk>/itemSelected/', itemSelected, name='itemSelected'),
    path('TeacherItemPage/<int:pk>/editItem/', editItem, name='editItem'),
    path('TeacherItemPage/<int:pk>/newItemSelected/', newItemSelected, name='newItemSelected'),
    path('TeacherItemPage/<int:pk>/addItem/', addItem, name='addItem'),
    path('TeacherItemPage/<int:pk>/deleteItem/', deleteItem, name='deleteItem'),
    path('TeacherItemPage/<int:pk>/createNewLists/', createNewLists, name='createNewLists'),
    path('PupilItemPage/<int:pk>/', openPupilItemLists, name='openPupilItemLists'),
    path('CreateExcursionPage/', addExcursion, name='CreateExcursionPage'),
    path('JoinExcursionPage/', openJoinExcursionPage, name='JoinExcursionPage'),
    path('<int:pk>/JoinExcursionPage/', authenticateLoginInfo, name='JoinExcursionPage'),
    path('<int:pk>/trinti/', deleteExcursion, name='deleteExcursion'),
    path('PlaylistPage/<int:pk>/generate/', generatePlaylist, name='generatePlaylist'),
    path('ViewCollectionRoute/<int:pk>/', openViewCollectionRoutePage, name='ViewCollectionRoute'),
    path('AdministratePickupAddress/<int:pk>/', openAdministratePickupAddressesPage, name='AdministratePickupAddress'),
    path('DeletePickupAddresses/<int:pk>/', openDeletePickupAddressesPage, name='DeletePickupAddresses'),
    path('CreateCollectionRoute/<int:pk>/', openCreateCollectionRoutePage, name='CreateCollectionRoute'),
    path('PickupAddressPage/<int:pk>/', openPickupAddressPage, name='PickupAddressPage'),
    path('EditPickupAddress/<int:pk>/<int:pupil_id>/', openEditPickupAddressPage, name='EditPickupAddress'),
    path('ObjectPage/<int:pk>/', openObjectsList, name='ObjectPage'),
    path('NewObjectPage/<int:pk>/', openNewObjectPage, name='NewObjectPage'),
    path('NewObjectPage/<int:pk>/submitAddress/', submitAddress, name='submitAddress'),
    path('NewObjectPage/<int:pk>/saveCriteria/', saveCriteria, name='saveCriteria'),
    path('NewObjectPage/<int:pk>/saveObligatory/', saveObligatory, name='saveObligatory'),
]