from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Max
import json
from .excursionEnrollment import getAllExcursionParticipants
from ...models.models import Excursion, Profile, ExcursionEnrollment, Playlist, PlaylistItem, Song
from ...forms import ExcursionForm, PublishExcursionForm
from ekskursijos.services.music_api import search_songs, get_track_details


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

    playlist_items = PlaylistItem.objects.filter(playlist=playlist).select_related('song').order_by('order')

    songs_data = []
    for item in playlist_items:
        song = item.song
        duration_min = song.duration // 60 if song.duration else 0
        start_seconds = item.start_time if item.start_time is not None else 0
        hours = start_seconds // 3600
        minutes = (start_seconds % 3600) // 60
        start_time_str = f"{hours:02d}:{minutes:02d}"
        
        songs_data.append({
            'order': item.order,
            'title': song.title,
            'author': song.author,
            'language': song.language,
            'duration': song.duration,
            'duration_min': duration_min,
            'start_time': item.start_time,
            'start_time_str': start_time_str,
            'item_id': item.id,
        })

    context = {
        'excursion': excursion,
        'playlist': playlist,
        'songs': songs_data,
        'role': role,
    }

    return render(request, 'ekskursijos/user/playlistPage.html', context)


@login_required
def openPlaylistItemAddPage(request, pk):
    excursion = get_object_or_404(Excursion, pk=pk)
    role = checkRole(request.user)

    if role != 'teacher':
        messages.error(request, 'Only teachers can add songs to playlist.')
        return redirect('ExcursionPage', pk=pk)

    playlist = get_object_or_404(Playlist, excursion=excursion)

    if request.method == 'GET':
        query = request.GET.get('q', '')
        search_results = []
        if query:
            try:
                raw_results = search_songs(query, limit=10)
                search_results = raw_results
            except Exception as e:
                messages.error(request, f'Search failed: {str(e)}')

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

        if track_data_str:
            try:
                track_data = json.loads(track_data_str)
            except json.JSONDecodeError:
                messages.error(request, 'Invalid song data.')
                return redirect('PlaylistItemAddPage', pk=pk)
        else:
            try:
                track_data = get_track_details(track_id)
            except Exception as e:
                messages.error(request, f'Failed to get song details: {str(e)}')
                return redirect('PlaylistItemAddPage', pk=pk)

        title = track_data.get('track_name', '')[:200]
        author = track_data.get('artist_name', '')[:200]
        language = track_data.get('primary_genre_name', '')[:50]
        duration_ms = track_data.get('duration_ms', 0)
        duration_sec = duration_ms // 1000 if duration_ms else 0

        song = Song.objects.create(
            title=title,
            author=author,
            language=language,
            duration=duration_sec
        )

        max_order_result = PlaylistItem.objects.filter(playlist=playlist).aggregate(
            max_order=Max('order')
        )
        max_order = max_order_result['max_order'] if max_order_result['max_order'] is not None else 0
        new_order = max_order + 1

        all_items = list(PlaylistItem.objects.filter(playlist=playlist).order_by('order'))
        accumulated_time = 0
        for item in all_items:
            item.start_time = accumulated_time
            item.save(update_fields=['start_time'])
            accumulated_time += item.song.duration

        new_start_time = accumulated_time
        PlaylistItem.objects.create(
            playlist=playlist,
            song=song,
            order=new_order,
            start_time=new_start_time
        )

        messages.success(request, f'Song "{title}" added to playlist.')

        return redirect('PlaylistPage', pk=pk)
