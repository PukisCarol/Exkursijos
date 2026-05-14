import random
import math
from django.utils import timezone
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404
from ...services.music_api import search_songs, get_track_details
from ...models.models import (
    Playlist, Excursion, ListOfPlaces, ObjectAddressProgress,
    Genre, PlaylistGenre, GenrePrice, Song, PlaylistItem, Place, PlaceType
)


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

    # 1
    def getPlaylistID(self):
        return self.playlist.id

    # 2



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

    def get_playlist_display_data(self):
        playlist_items = PlaylistItem.objects.filter(playlist=self.playlist).select_related('song').order_by('order')
        
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
        
        return {
            'excursion': self.excursion,
            'playlist': self.playlist,
            'songs': songs_data,
        }

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

    def addSong(self, track_data):
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

        max_order_result = PlaylistItem.objects.filter(playlist=self.playlist).aggregate(
            max_order=Max('order')
        )
        max_order = max_order_result['max_order'] if max_order_result['max_order'] is not None else 0
        new_order = max_order + 1

        PlaylistItem.objects.create(
            playlist=self.playlist,
            song=song,
            order=new_order,
            start_time=0
        )

        self.recountItemStartTimes()

        return song

    def deletePlaylistItem(self, item_id):
        playlist_item = get_object_or_404(PlaylistItem, pk=item_id, playlist=self.playlist)
        song = playlist_item.song
        playlist_item.delete()
        song.delete()
        remaining_items = list(PlaylistItem.objects.filter(playlist=self.playlist).order_by('order'))
        for idx, item in enumerate(remaining_items, start=1):
            item.order = idx
        PlaylistItem.objects.bulk_update(remaining_items, ['order'])
        self.recountItemStartTimes()

    def changePlaylistItemPlace(self, item_id, new_order):
        current_item = PlaylistItem.objects.get(pk=item_id, playlist=self.playlist)
        items = list(PlaylistItem.objects.filter(playlist=self.playlist).order_by('order'))
        total_items = len(items)
        
        if new_order < 1 or new_order > total_items:
            raise ValueError(f'Reikšmės turi būti tarp {total_items}.')
        
        old_order = current_item.order
        
        if old_order == new_order:
            all_items = PlaylistItem.objects.filter(playlist=self.playlist).order_by('order')
            updated_items = []
            for item in all_items:
                updated_items.append({
                    'id': item.id,
                    'order': item.order,
                    'start_time': item.start_time,
                    'start_time_str': f"{item.start_time // 3600:02d}:{(item.start_time % 3600) // 60:02d}",
                    'title': item.song.title,
                    'author': item.song.author,
                    'language': item.song.language,
                    'duration_min': item.song.duration // 60 if item.song.duration else 0
                })
            return updated_items
        
        for item in items:
            item.order = -item.order
        
        PlaylistItem.objects.bulk_update(items, ['order'])
        
        items = list(PlaylistItem.objects.filter(playlist=self.playlist).order_by('order'))
        
        for item in items:
            abs_order = abs(item.order)
            if item.id == current_item.id:
                item.order = new_order
            elif new_order > old_order:
                if old_order < abs_order <= new_order:
                    item.order = abs_order - 1
                else:
                    item.order = abs_order
            else:
                if new_order <= abs_order < old_order:
                    item.order = abs_order + 1
                else:
                    item.order = abs_order
        
        PlaylistItem.objects.bulk_update(items, ['order'])
        
        self.recountItemStartTimes()
        
        all_items = PlaylistItem.objects.filter(playlist=self.playlist).order_by('order')
        updated_items = []
        for item in all_items:
            updated_items.append({
                'id': item.id,
                'order': item.order,
                'start_time': item.start_time,
                'start_time_str': f"{item.start_time // 3600:02d}:{(item.start_time % 3600) // 60:02d}",
                'title': item.song.title,
                'author': item.song.author,
                'language': item.song.language,
                'duration_min': item.song.duration // 60 if item.song.duration else 0
            })
        
        return updated_items

    # generavimas
    def generate(self):
        # 1-9
        self.getPlaylistID()
        votes = self.getVotes()
        all_genres = list(Genre.objects.all())
        if self.checkGenreVotes(votes):
            self.setMostVotedAsFavourite(votes)
        else:
            self.setHeavyMetalAsFavourite()
        self.getExcursionID()
        self.getExcursionPlaces()
        self.getExcursionPlaceTypes()
        self.getAllGenrePrices()

        # 20-21
        self.unprocessed_places = self.places[:]
        while self.unprocessed_places:
            place = self.unprocessed_places.pop(0)
            genres = self.getPlaceGenres(place)
            self.place_genres.append(genres)
            self.markPlaceProcessed(place)

        # 22-23
        start_sec, end_sec = self.getExcursionStartAndEnd()

        # 24
        self.N = self.findRequiredSongsCount(start_sec, end_sec)

        # 25-28
        raw_songs = self.getRandomSongs(self.N * 10)
        self.songs = self.filterRequiredSongCount(raw_songs, self.N)

        # 30
        self.getRelevantSongPrices()

        # 32
        self.findSmallestPriceForEachSongCombination()

        # 31-33
        initial_perm = self.createRandomSolution()
        start_cost = self.findStartingPrice(initial_perm)
        self.setCurrentSolution(initial_perm, start_cost)
        self.best_solution = initial_perm.copy()
        self.best_cost = start_cost

        self.setStartingSAParameters()

        if self.N > 1:
            while self.T > self.Tmin and self.iteration < self.max_iter:
                neighbor = self.generateNeighbor(self.current_solution)
                cost = self.calculateCost(neighbor)
                delta = cost - self.current_cost
                if delta < 0:
                    self.setCurrentSolution(neighbor, cost)
                    self.saveAsTempBest(neighbor, cost)
                else:
                    if self.decideWhetherToTakeSolution(delta):
                        self.setCurrentSolution(neighbor, cost)
                if self.iteration > 0 and self.iteration % self.iterations_at_min_temp == 0:
                    self.decreaseTemperature()
                self.incrementCurrentIterations()

        with transaction.atomic():
            self.deleteCurrentItems()
            self.bulk_create_songs_and_items()
            self.recountItemStartTimes()
            self.updateCreationDate()

        return self.playlist