from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
import json
from .excursionEnrollment import getAllExcursionParticipants
from ...models.models import Excursion, Profile, ExcursionEnrollment, Playlist, Genre
from ...forms import ExcursionForm, PublishExcursionForm
from .voting_controller import VotingController
from .playlist_controller import PlaylistController


def checkRole(user):
    try:
        return user.profile.role
    except Profile.DoesNotExist:
        return None


def checkIfEmptyList(ekskursijos):
    return not ekskursijos.exists()


@login_required
def openExcursion(request, pk):
    e = get_object_or_404(Excursion, pk=pk)
    role = checkRole(request.user)

    dalyviai = getAllExcursionParticipants(e)

    initial_data = {'excursion_date': e.excursion_date} if e.excursion_date else {}
    forma = PublishExcursionForm(initial=initial_data)

    if request.method == 'POST' and role == 'teacher':
        forma = PublishExcursionForm(request.POST)
        if forma.is_valid():
            data = forma.cleaned_data['excursion_date']

            if not checkDate(data):
                forma.add_error('excursion_date', 'Date cannot be in the past.')
            else:
                e.excursion_date = data
                e.status = 'published'
                e.save()
                messages.success(request, f'Excursion date successfully published: {data.strftime("%Y-%m-%d")}.')
                return redirect('ExcursionPage', pk=pk)
    
    return render(request, 'ekskursijos/user/excursionPage.html', {
        'ekskursija': e,
        'role': role,
        'dalyviai': dalyviai,
        'forma': forma,
    })


@login_required
def openGenreVotingPage(request, pk):
    excursion = get_object_or_404(Excursion, pk=pk)
    role = checkRole(request.user)
    if role != 'pupil':
        messages.error(request, 'Only pupils can vote.')
        return redirect('ExcursionPage', pk=pk)
    
    playlist = get_object_or_404(Playlist, excursion=excursion)
    controller = VotingController(playlist, request.user)
    
    all_genres = list(Genre.objects.all())
    voted_genres = controller.getVotedGenres()
    
    # Build list of genre data with vote count
    genres_data = []
    for genre in all_genres:
        pg = next((g for g in voted_genres if g.genre.id == genre.id), None)
        genres_data.append({
            'genre': genre,
            'vote_count': pg.vote_count if pg else 0,
        })
    
    return render(request, 'ekskursijos/user/GenreVotingPage.html', {
        'excursion': excursion,
        'playlist': playlist,
        'genres_data': genres_data,
        'role': role,
    })


@login_required
def vote_for_genre(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    excursion = get_object_or_404(Excursion, pk=pk)
    role = checkRole(request.user)
    if role != 'pupil':
        return JsonResponse({'status': 'error', 'message': 'Only pupils can vote.'}, status=403)
    
    genre_id = request.POST.get('genre_id')
    if not genre_id:
        return JsonResponse({'status': 'error', 'message': 'Genre not provided.'}, status=400)
    
    try:
        genre_id = int(genre_id)
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Invalid genre ID.'}, status=400)
    
    playlist = get_object_or_404(Playlist, excursion=excursion)
    controller = VotingController(playlist, request.user)
    result = controller.voteForGenre(genre_id)
    
    status_code = 200 if result['status'] == 'success' else 400
    return JsonResponse(result, status=status_code)


@login_required
def addExcursion(request):
    if checkRole(request.user) != 'teacher':
        return redirect('excursionListPage')
    forma = ExcursionForm(request.POST or None)
    if request.method == 'POST':
        if forma.is_valid():
            forma.save()
            return redirect('excursionListPage')
    return render(request, 'ekskursijos/teacher/createExcursionPage.html',
                {'forma': forma,
                 'veiksmas': 'Add'})


def checkDate(data):
    return data >= timezone.now().date()


@login_required
def deleteExcursion(request, pk):
    if checkRole(request.user) != 'teacher':
        return redirect('getExcursionList')
    e = get_object_or_404(Excursion, pk=pk)
    if request.method == 'POST':
        e.delete()
        return redirect('excursionListPage')
    return redirect('openExcursion', pk=pk)


@login_required
def getExcursionList(request):
    role = checkRole(request.user)
    ekskursijos = Excursion.objects.all()

    if request.method == 'POST' and role == 'teacher':
        if 'confirm_delete' in request.POST:
            ids = request.POST.getlist('confirm_delete_ids')
            Excursion.objects.filter(pk__in=ids).delete()
            return redirect('excursionListPage')
        ids = request.POST.getlist('trinti_ids')
        if ids:
            excursions_to_delete = Excursion.objects.filter(pk__in=ids)
            return render(request, 'ekskursijos/user/deleteExcursionConfirm.html', {
                'excursions': excursions_to_delete
            })
        return redirect('excursionListPage')

    empty = checkIfEmptyList(ekskursijos)
    alert = "You do not have access to this page." if role not in ['teacher', 'pupil'] else None

    return render(request, 'ekskursijos/user/excursionListPage.html', {
        'ekskursijos': ekskursijos,
        'role': role,
        'empty': empty,
        'alert': alert,
    })


@login_required
def pupilsListPage(request, pk):
    role = checkRole(request.user)
    if role != 'teacher':
        return redirect('openExcursion', pk=pk)
    e = get_object_or_404(Excursion, pk=pk)
    pupils = ExcursionEnrollment.objects.filter(excursion=e, status='participating')
    return render(request, 'ekskursijos/user/pupilsListPage.html', {
        'pupils': pupils,
        'excursion': e
    })


@login_required
def openJoinExcursionPage(request):
    role = checkRole(request.user)
    if role != 'pupil':
        return redirect('excursionListPage')
    excursions = Excursion.objects.all()
    current_statuses = {}
    for e in excursions:
        dalyvavimas = ExcursionEnrollment.objects.filter(pupil=request.user, excursion=e).first()
        if dalyvavimas:
            current_statuses[e.pk] = dalyvavimas.status
        else:
            current_statuses[e.pk] = ''
    success_message = error_message = ''
    if request.method == 'POST':
        updated = False
        for e in excursions:
            status = request.POST.get(f'status_{e.pk}')
            if status:
                dalyvavimas, _ = ExcursionEnrollment.objects.get_or_create(pupil=request.user, excursion=e)
                dalyvavimas.status = status
                dalyvavimas.save()
                updated = True
        # Refresh current_statuses after saving
        current_statuses = {}
        for e in excursions:
            dalyvavimas = ExcursionEnrollment.objects.filter(pupil=request.user, excursion=e).first()
            if dalyvavimas:
                current_statuses[e.pk] = dalyvavimas.status
            else:
                current_statuses[e.pk] = ''
        if updated:
            success_message = 'Statuses successfully updated.'
        else:
            error_message = 'No statuses selected.'
    return render(request, 'ekskursijos/user/joinExcursionPage.html', {
        'excursions': excursions,
        'current_statuses': current_statuses,
        'success_message': success_message,
        'error_message': error_message,
    })


def mainPage(request):
    return render(request, 'ekskursijos/user/mainPage.html')


@login_required
def openExcursionPlaylist(request, pk):
    excursion = get_object_or_404(Excursion, pk=pk)
    role = checkRole(request.user)

    if role not in ['teacher', 'pupil']:
        messages.error(request, 'You do not have access to this playlist.')
        return redirect('excursionListPage')

    playlist = get_object_or_404(Playlist, excursion=excursion)
    
    controller = PlaylistController(playlist)
    context = controller.get_playlist_display_data()
    context['role'] = role

    return render(request, 'ekskursijos/user/playlistPage.html', context)


@login_required
def openPlaylistItemAddPage(request, pk):
    excursion = get_object_or_404(Excursion, pk=pk)
    role = checkRole(request.user)

    if role != 'teacher':
        messages.error(request, 'Only teachers can add songs to playlist.')
        return redirect('ExcursionPage', pk=pk)

    playlist = get_object_or_404(Playlist, excursion=excursion)
    controller = PlaylistController(playlist)

    if request.method == 'GET':
        query = request.GET.get('q', '')
        search_results = []
        if query:
            try:
                search_results = controller.getBestSongMatches(query)
            except Exception as e:
                messages.error(request, str(e))

        return render(request, 'ekskursijos/user/playlistItemAddPage.html', {
            'excursion': excursion,
            'playlist': playlist,
            'role': role,
            'search_results': search_results,
            'query': query,
        })

    elif request.method == 'POST':
        track_id = request.POST.get('track_id')
        track_data_str = request.POST.get('track_data')

        if not track_id and not track_data_str:
            messages.error(request, 'No song selected.')
            return redirect('PlaylistItemAddPage', pk=pk)

        try:
            if track_data_str:
                track_data = json.loads(track_data_str)
            else:
                track_data = controller.getSongDetails(track_id)
            
            song = controller.addSong(track_data)
            messages.success(request, f'Song "{song.title}" added to playlist.')
        except Exception as e:
            messages.error(request, str(e))
            return redirect('PlaylistItemAddPage', pk=pk)

        return redirect('PlaylistPage', pk=pk)


@login_required
def deletePlaylistItem(request, pk, item_id):
    if request.method != 'POST':
        return redirect('PlaylistPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)
    role = checkRole(request.user)

    if role != 'teacher':
        messages.error(request, 'Only teachers can delete playlist items.')
        return redirect('PlaylistPage', pk=pk)

    playlist = get_object_or_404(Playlist, excursion=excursion)
    controller = PlaylistController(playlist)
    
    try:
        controller.deletePlaylistItem(item_id)
    except Exception as e:
        messages.error(request, str(e))

    return redirect('PlaylistPage', pk=pk)


@login_required
def changePlaylistItemPlace(request, pk):
    if request.method != 'POST':
        return redirect('PlaylistPage', pk=pk)

    excursion = get_object_or_404(Excursion, pk=pk)
    role = checkRole(request.user)

    if role != 'teacher':
        return JsonResponse({'success': False, 'error': 'Only teachers can modify playlist order.'})

    item_id = request.POST.get('item_id')
    new_order = request.POST.get('new_order')

    if not item_id or not new_order:
        return JsonResponse({'success': False, 'error': 'Missing item_id or new_order.'})

    try:
        new_order = int(new_order)
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid order number.'})

    playlist = get_object_or_404(Playlist, excursion=excursion)
    controller = PlaylistController(playlist)
    
    try:
        updated_items = controller.changePlaylistItemPlace(item_id, new_order)
        return JsonResponse({'success': True, 'items': updated_items})
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def generate_playlist(request, pk):
    excursion = get_object_or_404(Excursion, pk=pk)
    role = checkRole(request.user)
    if role != 'teacher':
        messages.error(request, 'Tik mokytojai gali generuoti grojaraščius.')
        return redirect('ExcursionPage', pk=pk)
    playlist = get_object_or_404(Playlist, excursion=excursion)
    if request.method == 'POST':
        try:
            controller = PlaylistController(playlist)
            controller.generate()
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        return redirect('PlaylistPage', pk=pk)
    return redirect('ExcursionPage', pk=pk)
