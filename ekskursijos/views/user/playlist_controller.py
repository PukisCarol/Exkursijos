import random
import math
import traceback
import logging
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.db.models import Max
from django.contrib.auth.decorators import login_required
from ...services.music_api import search_songs, get_track_details
from ...models.models import (
    Playlist, Excursion, ListOfPlaces, ObjectAddressProgress,
    Genre, PlaylistGenre, GenrePrice, Song, PlaylistItem, Place, PlaceType
)

logger = logging.getLogger(__name__)


def _get_role(user):
    return user.profile.role if hasattr(user, 'profile') else None


class PlaylistController:
    PLACE_MISMATCH_PENALTY = 1000.0
    AVG_SONG_DURATION = 200

    def __init__(self, playlist):
        self.playlist = playlist
        self.excursion = playlist.excursion
        self.favorite_genre = None
        self.places = []
        self.place_types = []
        self.place_genres = []
        self.processed_places = set()
        self.songs = []
        self.N = 0
        self.unprocessed_places = []

        self.T = 1000.0
        self.Tmin = 0.1
        self.cooling_rate = 0.995
        self.max_iter = 1000
        self.iterations_at_min_temp = 50
        self.iteration = 0
        self.transition_cost = []
        self.price_dict = {}
        self.current_solution = []
        self.current_cost = 0.0
        self.best_solution = []
        self.best_cost = float('inf')

    # 5
    def checkGenreVotes(self, votes):
        return any(v.vote_count > 0 for v in votes)

    # 6/7
    def setMostVotedAsFavourite(self, votes):
        if not votes:
            return self.setHeavyMetalAsFavourite()
        best = max(votes, key=lambda v: v.vote_count)
        self.favorite_genre = best.genre
        return self.favorite_genre

    # 6/11
    def setHeavyMetalAsFavourite(self):
        genre = Genre.objects.filter(name__iexact='Heavy Metal').first()
        if not genre:
            genre = Genre.objects.first()
        self.favorite_genre = genre
        return self.favorite_genre

    # 12
    def getExcursionID(self):
        return self.excursion.id

    # 14
    def getExcursionPlaces(self):
        try:
            lop = ListOfPlaces.objects.get(excursion=self.excursion)
        except ListOfPlaces.DoesNotExist:
            self.places = []
            return self.places
        progresses = ObjectAddressProgress.objects.filter(list_of_places=lop).select_related('place').order_by('visit_number')
        self.places = [p.place for p in progresses]
        return self.places

    # 16
    def getExcursionPlaceTypes(self):
        if not self.places:
            self.place_types = []
            return self.place_types
        self.place_types = list(PlaceType.objects.filter(places__in=self.places).distinct())
        return self.place_types

    # 18
    def getAllGenrePrices(self):
        return list(GenrePrice.objects.all())

    # 20
    def getPlaceGenres(self, place):
        return set(Genre.objects.filter(place_types__places=place).distinct())

    # 21
    def markPlaceProcessed(self, place):
        self.processed_places.add(place.id)

    # 22
    def getExcursionStartAndEnd(self):
        progresses = ObjectAddressProgress.objects.filter(list_of_places__excursion=self.excursion)
        total_minutes = sum(p.duration_minutes for p in progresses)
        total_seconds = total_minutes * 60
        return (0, total_seconds)

    # 24
    def findRequiredSongsCount(self, start_seconds, end_seconds):
        total_duration = end_seconds - start_seconds
        if total_duration <= 0:
            raise ValueError("Excursion duration is zero or negative")
        count = math.ceil(total_duration / self.AVG_SONG_DURATION)
        return max(count, 1)

    # 25
    def getRandomSongs(self, count):
        seeds = []
        seen = set()
        queries = []

        if self.favorite_genre:
            queries.append(self.favorite_genre.name)
        other_genres = list(Genre.objects.exclude(id=self.favorite_genre.id)[:5]) if self.favorite_genre else list(Genre.objects.all()[:5])
        queries.extend([g.name for g in other_genres])
        queries.append('music')
        for q in queries:
            if len(seeds) >= count:
                break
            try:
                results = search_songs(q, limit=count)
                for track in results:
                    tid = track.get('track_id')
                    if tid and tid not in seen:
                        seeds.append(track)
                        seen.add(tid)
                        if len(seeds) >= count:
                            break
            except Exception as e:
                print(f"API search error for '{q}': {e}")
                continue

        letters = 'abcdefghijklmnopqrstuvwxyz'
        while len(seeds) < count:
            q = random.choice(letters)
            try:
                results = search_songs(q, limit=count)
                for track in results:
                    tid = track.get('track_id')
                    if tid and tid not in seen:
                        seeds.append(track)
                        seen.add(tid)
                        if len(seeds) >= count:
                            break
            except Exception:
                continue
        return seeds[:count]

    # 29
    def filterRequiredSongCount(self, raw_songs, count):
        filtered = []
        for track in raw_songs:
            genre_name = track.get('primary_genre_name', '').strip()
            if not genre_name:
                continue
            try:
                genre_obj = Genre.objects.get(name__iexact=genre_name)
                filtered.append({'track': track, 'genre': genre_obj})
            except Genre.DoesNotExist:
                continue
        if len(filtered) < count:
            raise ValueError(f"Not enough songs with known genres: found {len(filtered)}, required {count}")
        return random.sample(filtered, count)

    # 30
    def getRelevantSongPrices(self):
        selected_genres = set(item['genre'] for item in self.songs)
        self.relevant_prices = GenrePrice.objects.filter(
            first_genre__in=selected_genres,
            final_genre__in=selected_genres
        )
        self.price_dict = {
            (p.first_genre_id, p.final_genre_id): float(p.price)
            for p in self.relevant_prices
        }

    # 31
    def createRandomSolution(self):
        sol = list(range(self.N))
        random.shuffle(sol)
        return sol

    # 32
    def findSmallestPriceForEachSongCombination(self):
        n = self.N
        self.transition_cost = [[0] * n for _ in range(n)]
        for i in range(n):
            genre_i = self.songs[i]['genre'].id
            for j in range(n):
                if i == j:
                    self.transition_cost[i][j] = 0.0
                else:
                    genre_j = self.songs[j]['genre'].id
                    price = self.price_dict.get((genre_i, genre_j), 1000.0)
                    self.transition_cost[i][j] = price

    # 33
    def findStartingPrice(self, solution):
        return self.calculateCost(solution)

    # 34
    def setStartingSAParameters(self):
        self.T = 1000.0
        self.Tmin = 0.1
        self.cooling_rate = 0.995
        self.max_iter = max(1000, self.N * 100)
        self.iterations_at_min_temp = 50

    # 35
    def setCurrentSolution(self, solution, cost):
        self.current_solution = solution
        self.current_cost = cost

    # 36
    def generateNeighbor(self, solution):
        i, j = random.sample(range(len(solution)), 2)
        neighbor = solution.copy()
        neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
        return neighbor

    # 37
    def calculateCost(self, solution):
        total = 0.0
        n = len(solution)
        for i in range(n - 1):
            a = solution[i]
            b = solution[i + 1]
            total += self.transition_cost[a][b]
        for pos, idx in enumerate(solution):
            if pos < len(self.place_genres):
                song_genre = self.songs[idx]['genre']
                if song_genre not in self.place_genres[pos]:
                    total += self.PLACE_MISMATCH_PENALTY
        return total

    # 39
    def saveAsTempBest(self, solution, cost):
        if cost < self.best_cost:
            self.best_solution = solution.copy()
            self.best_cost = cost

    # 40
    def decideWhetherToTakeSolution(self, delta):
        if delta < 0:
            return True
        try:
            prob = math.exp(-delta / self.T)
        except (OverflowError, ZeroDivisionError):
            return False
        return random.random() < prob

    # 42
    def decreaseTemperature(self):
        self.T *= self.cooling_rate
        if self.T < self.Tmin:
            self.T = self.Tmin

    # 43
    def incrementCurrentIterations(self):
        self.iteration += 1

    # 44
    def deleteCurrentItems(self):
        PlaylistItem.objects.filter(playlist=self.playlist).delete()

    # 46,48
    def bulk_create_songs_and_items(self):
        ordered_data = [self.songs[i] for i in self.best_solution]
        song_objs = []
        for data in ordered_data:
            track = data['track']
            genre = data['genre']
            song = Song(
                author=track.get('artist_name', '')[:200],
                title=track.get('track_name', '')[:200],
                language=track.get('primary_genre_name', '')[:50],
                duration=track.get('duration_sec', 0)
            )
            song_objs.append(song)
        created_songs = Song.objects.bulk_create(song_objs)
        for song, data in zip(created_songs, ordered_data):
            song.genres.add(data['genre'])
        items = []
        accumulated = 0
        for order, song in enumerate(created_songs, start=1):
            item = PlaylistItem(
                playlist=self.playlist,
                song=song,
                order=order,
                start_time=accumulated
            )
            items.append(item)
            accumulated += song.duration
        PlaylistItem.objects.bulk_create(items)

    # 50
    def recountItemStartTimes(self):
        items = PlaylistItem.objects.filter(playlist=self.playlist).order_by('order')
        accumulated_time = 0
        items_to_update = []
        for item in items:
            item.start_time = accumulated_time
            items_to_update.append(item)
            accumulated_time += item.song.duration
        PlaylistItem.objects.bulk_update(items_to_update, ['start_time'])

    # 51
    def updateCreationDate(self):
        self.playlist.creation_date = timezone.now().date()
        self.playlist.save(update_fields=['creation_date'])

    def editSongOrder(self):
        max_order_result = PlaylistItem.objects.filter(playlist=self.playlist).aggregate(max_order=Max('order'))
        max_order = max_order_result['max_order'] if max_order_result['max_order'] is not None else 0
        return max_order + 1

    # votes resolver
    def getVotes(self):
        return list(PlaylistGenre.objects.filter(playlist=self.playlist).select_related('genre'))

    def getBestSongMatches(self, query):
        if not query:
            return []
        try:
            return search_songs(query, limit=10)
        except Exception as e:
            raise Exception(f'{str(e)}')

    def getSongDetails(self, track_id):
        if not track_id:
            raise ValueError('Neduotas track_id')
        try:
            return get_track_details(track_id)
        except Exception as e:
            raise Exception(f'Negauta dainų informacija: {str(e)}')

    def reorderItems(self, items, item_id, new_order):
        """
        Reorder playlist items by moving item_id to new_order position.
        Returns updated item_dict with correct order values.
        """
        for idx, item in enumerate(items):
            item.order = -(idx + 1)
        PlaylistItem.objects.bulk_update(items, ['order'])

        items = list(PlaylistItem.objects.filter(playlist=self.playlist).order_by('order'))
        item_dict = {item.id: item for item in items}
        position_ids = [item.id for item in items]
        position_ids.remove(item_id)
        position_ids.insert(new_order - 1, item_id)

        for idx, pid in enumerate(position_ids, start=1):
            item_dict[pid].order = idx

        PlaylistItem.objects.bulk_update(list(item_dict.values()), ['order'])
        return item_dict

    def processItem(self, item):
        start_time = item.start_time if item.start_time is not None else 0
        return {
            'id': item.id,
            'order': item.order,
            'start_time': start_time,
            'start_time_str': f"{start_time // 3600:02d}:{(start_time % 3600) // 60:02d}",
            'title': item.song.title,
            'author': item.song.author,
            'language': item.song.language,
            'duration_min': item.song.duration // 60 if item.song.duration else 0
        }



@login_required
def openExcursionPlaylist(request, pk):
    role = _get_role(request.user)
    if role not in ('teacher', 'pupil'):
        messages.error(request, 'You do not have access to this playlist.')
        return redirect('excursionListPage')

    playlist = get_object_or_404(Playlist, excursion__pk=pk)
    excursion = playlist.excursion
    controller = PlaylistController(playlist)

    playlist_items = PlaylistItem.objects.filter(playlist=playlist).select_related('song').order_by('order')
    songs_data = [controller.processItem(item) for item in playlist_items]

    return render(request, 'ekskursijos/user/playlistPage.html', {
        'excursion': excursion,
        'playlist': playlist,
        'songs': songs_data,
        'role': role,
    })


@login_required
def openPlaylistItemAddPage(request, pk):
    if request.method != 'GET':
        return redirect('PlaylistItemAddPage', pk=pk)

    playlist = get_object_or_404(Playlist, excursion__pk=pk)
    excursion = playlist.excursion
    role = _get_role(request.user)

    if role != 'teacher':
        messages.error(request, 'Only teachers can add songs to playlist.')
        return redirect('ExcursionPage', pk=pk)

    return render(request, 'ekskursijos/user/playlistItemAddPage.html', {
        'excursion': excursion,
        'playlist': playlist,
        'role': role,
    })


@login_required
def searchSongs(request, pk):
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Only GET allowed'}, status=405)

    playlist = get_object_or_404(Playlist, excursion__pk=pk)
    role = _get_role(request.user)

    if role != 'teacher':
        return JsonResponse({'success': False, 'error': 'Only teachers can search songs.'}, status=403)

    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'success': True, 'results': []})

    try:
        controller = PlaylistController(playlist)
        results = controller.getBestSongMatches(query)
        return JsonResponse({'success': True, 'results': results})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def addSong(request, pk):
    if request.method != 'POST':
        return redirect('PlaylistItemAddPage', pk=pk)

    playlist = get_object_or_404(Playlist, excursion__pk=pk)
    role = _get_role(request.user)

    if role != 'teacher':
        messages.error(request, 'Only teachers can add songs to playlist.')
        return redirect('ExcursionPage', pk=pk)

    track_id = request.POST.get('track_id')
    track_data_str = request.POST.get('track_data')

    if not track_id and not track_data_str:
        messages.error(request, 'No song selected.')
        return redirect('PlaylistItemAddPage', pk=pk)

    try:
        controller = PlaylistController(playlist)
        editSongOrder = controller.editSongOrder
        if track_data_str:
            track_data = json.loads(track_data_str)
        else:
            track_data = get_track_details(track_id)

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

        new_order = editSongOrder()

        PlaylistItem.objects.create(
            playlist=playlist,
            song=song,
            order=new_order,
            start_time=0
        )

        controller.recountItemStartTimes()
        messages.success(request, f'Song "{song.title}" added to playlist.')
    except Exception as e:
        messages.error(request, str(e))
        return redirect('PlaylistItemAddPage', pk=pk)

    return redirect('PlaylistPage', pk=pk)


@login_required
def deletePlaylistItem(request, pk, item_id):
    role = _get_role(request.user)
    if role != 'teacher':
        messages.error(request, 'Only teachers can delete playlist items.')
        return redirect('PlaylistPage', pk=pk)

    if request.method != 'POST':
        return redirect('PlaylistPage', pk=pk)

    playlist = get_object_or_404(Playlist, excursion__pk=pk)
    controller = PlaylistController(playlist)
    try:
        playlist_item = get_object_or_404(PlaylistItem, pk=item_id, playlist=playlist)
        song = playlist_item.song
        playlist_item.delete()
        song.delete()
        remaining_items = list(PlaylistItem.objects.filter(playlist=playlist).order_by('order'))
        for idx, item in enumerate(remaining_items, start=1):
            item.order = idx
        PlaylistItem.objects.bulk_update(remaining_items, ['order'])
        controller.recountItemStartTimes()
    except Exception as e:
        messages.error(request, str(e))

    return redirect('PlaylistPage', pk=pk)


@login_required
def changePlaylistItemPlace(request, pk):
    role = _get_role(request.user)
    if role != 'teacher':
        return JsonResponse({'success': False, 'error': 'Only teachers can modify playlist order.'})

    playlist = get_object_or_404(Playlist, excursion__pk=pk)
    controller = PlaylistController(playlist)

    item_id = request.POST.get('item_id')
    new_order = request.POST.get('new_order')

    if not item_id or not new_order:
        return JsonResponse({'success': False, 'error': 'Missing item_id or new_order.'})

    try:
        item_id = int(item_id)
        new_order = int(new_order)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid item_id or new_order format'})

    try:
       # current_item = PlaylistItem.objects.get(pk=item_id, playlist=playlist)
        items = list(PlaylistItem.objects.filter(playlist=playlist).order_by('order'))
        total_items = len(items)

        if new_order < 1 or new_order > total_items:
            return JsonResponse({'success': False, 'error': f'Reikšmės turi būti tarp {total_items}.'})

        if item_id not in [item.id for item in items]:
            return JsonResponse({'success': False, 'error': f'Item {item_id} not found in playlist'})

        with transaction.atomic():
            item_dict = controller.reorderItems(items, item_id, new_order)

        controller.recountItemStartTimes()

        items = list(PlaylistItem.objects.filter(playlist=playlist).order_by('order'))
        item_dict = {item.id: item for item in items}
        position_ids = [item.id for item in items]
        updated = [controller.processItem(item_dict[pid]) for pid in position_ids]
        return JsonResponse({'success': True, 'items': updated})
    except ValueError as e:
        logger.error("[CHANGE_ORDER] ValueError: %s", str(e))
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        logger.error("[CHANGE_ORDER] Exception: %s\n%s", str(e), traceback.format_exc())
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'})


@login_required
def generate_playlist(request, pk):
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('ExcursionPage', pk=pk)

    if _get_role(request.user) != 'teacher':
        messages.error(request, 'Tik mokytojai gali generuoti grojarastius.')
        return redirect('ExcursionPage', pk=pk)

    playlist = get_object_or_404(Playlist, excursion__pk=pk)
  #  excursion = playlist.excursion
    controller = PlaylistController(playlist)

    try:
        votes = controller.getVotes()
        #all_genres = list(Genre.objects.all())
        if controller.checkGenreVotes(votes):
            controller.setMostVotedAsFavourite(votes)
        else:
            controller.setHeavyMetalAsFavourite()
        controller.getExcursionPlaces()
        controller.getExcursionPlaceTypes()
        controller.getAllGenrePrices()

        controller.unprocessed_places = controller.places[:]
        while controller.unprocessed_places:
            place = controller.unprocessed_places.pop(0)
            genres = controller.getPlaceGenres(place)
            controller.place_genres.append(genres)
            controller.markPlaceProcessed(place)

        start_sec, end_sec = controller.getExcursionStartAndEnd()
        controller.N = controller.findRequiredSongsCount(start_sec, end_sec)
        raw_songs = controller.getRandomSongs(controller.N * 10)
        controller.songs = controller.filterRequiredSongCount(raw_songs, controller.N)
        controller.getRelevantSongPrices()
        controller.findSmallestPriceForEachSongCombination()

        initial_perm = controller.createRandomSolution()
        start_cost = controller.findStartingPrice(initial_perm)
        controller.setCurrentSolution(initial_perm, start_cost)
        controller.best_solution = initial_perm.copy()
        controller.best_cost = start_cost
        controller.setStartingSAParameters()

        if controller.N > 1:
            while controller.T > controller.Tmin and controller.iteration < controller.max_iter:
                neighbor = controller.generateNeighbor(controller.current_solution)
                cost = controller.calculateCost(neighbor)
                delta = cost - controller.current_cost
                if delta < 0:
                    controller.setCurrentSolution(neighbor, cost)
                    controller.saveAsTempBest(neighbor, cost)
                else:
                    if controller.decideWhetherToTakeSolution(delta):
                        controller.setCurrentSolution(neighbor, cost)
                if controller.iteration > 0 and controller.iteration % controller.iterations_at_min_temp == 0:
                    controller.decreaseTemperature()
                controller.incrementCurrentIterations()

        with transaction.atomic():
            controller.deleteCurrentItems()
            controller.bulk_create_songs_and_items()
            controller.recountItemStartTimes()
            controller.updateCreationDate()
    except Exception as e:
        logger.error("PlaylistController.generate() FAILED:\n%s", traceback.format_exc())
        messages.error(request, f'Error: {str(e)}')

    return redirect('PlaylistPage', pk=pk)
