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

    # 5 - SELF-MESSAGE
    def checkGenreVotes(self, votes):
        return any(v.vote_count > 0 for v in votes)

    # 6/7 - SELF-MESSAGE
    def setMostVotedAsFavourite(self, votes):
        if not votes:
            return self.setHeavyMetalAsFavourite()
        best = max(votes, key=lambda v: v.vote_count)
        self.favorite_genre = best.genre
        return self.favorite_genre

    # 6/11 - SELF-MESSAGE
    def setHeavyMetalAsFavourite(self):
        genre = Genre.objects.filter(name__iexact='Heavy Metal').first()
        if not genre:
            genre = Genre.objects.first()
        self.favorite_genre = genre
        return self.favorite_genre

    # generavimas
    def generate(self):
        # 1-9 - Entity calls (not self-messages in diagram, but values needed)
        votes = self.playlist.getVotes()
        all_genres = list(Genre.objects.all())
        if self.checkGenreVotes(votes):
            self.setMostVotedAsFavourite(votes)
        else:
            self.setHeavyMetalAsFavourite()
        excursion_id = self.excursion.getID()
        # getExcursionPlaces() - entity call, inline
        try:
            lop = ListOfPlaces.objects.get(excursion=self.excursion)
            progresses = ObjectAddressProgress.objects.filter(list_of_places=lop).select_related('place').order_by('visit_number')
            self.places = [p.place for p in progresses]
        except ListOfPlaces.DoesNotExist:
            self.places = []
        # getExcursionPlaceTypes() - entity call, inline
        if not self.places:
            self.place_types = []
        else:
            self.place_types = list(PlaceType.objects.filter(places__in=self.places).distinct())
        # getAllGenrePrices() - entity call, inline
        all_prices = list(GenrePrice.objects.all())

        # 20-21 - loop with self-messages
        self.unprocessed_places = self.places[:]
        while self.unprocessed_places:
            place = self.unprocessed_places.pop(0)
            genres = self.getPlaceGenres(place)
            self.place_genres.append(genres)
            self.markPlaceProcessed(place)

        # 22-23 - getPlacesProgress() is entity call, inline
        progresses = ObjectAddressProgress.objects.filter(list_of_places__excursion=self.excursion)
        total_minutes = sum(p.duration_minutes for p in progresses)
        start_sec, end_sec = (0, total_minutes * 60)

        # 24
        self.N = self.findRequiredSongsCount(start_sec, end_sec)

        # 25-28 - getRandomSongs() call to MusicAPIIntermediary (entity), so inline
        seeds = []
        seen = set()
        queries = []
        if self.favorite_genre:
            queries.append(self.favorite_genre.name)
        other_genres = list(Genre.objects.exclude(id=self.favorite_genre.id)[:5]) if self.favorite_genre else list(Genre.objects.all()[:5])
        queries.extend([g.name for g in other_genres])
        queries.append('music')
        for q in queries:
            if len(seeds) >= self.N * 10:
                break
            try:
                results = search_songs(q, limit=self.N * 10)
                for track in results:
                    tid = track.get('track_id')
                    if tid and tid not in seen:
                        seeds.append(track)
                        seen.add(tid)
                        if len(seeds) >= self.N * 10:
                            break
            except Exception as e:
                print(f"API search error for '{q}': {e}")
                continue
        letters = 'abcdefghijklmnopqrstuvwxyz'
        while len(seeds) < self.N * 10:
            q = random.choice(letters)
            try:
                results = search_songs(q, limit=self.N * 10)
                for track in results:
                    tid = track.get('track_id')
                    if tid and tid not in seen:
                        seeds.append(track)
                        seen.add(tid)
                        if len(seeds) >= self.N * 10:
                            break
            except Exception:
                continue
        raw_songs = seeds[:self.N * 10]
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
            # 44 - deleteCurrentItems() is entity call, inline
            PlaylistItem.objects.filter(playlist=self.playlist).delete()
            # bulk_create songs and items - entity calls, inline
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
            self.recountItemStartTimes()
            # 51 - updateCreationDate() is entity call, inline
            self.playlist.updateCreationDate()

        return self.playlist

    # 2
    def getPlaylistData(self):
        items = self.getPlaylistItems()  # Step 3
        songs_data = []
        for item in items:
            songs_data.append(self.processItem(item))  # Step 5
        return {
            'excursion': self.excursion,
            'playlist': self.playlist,
            'songs': songs_data,
        }

    # 3
    def getPlaylistItems(self):
        return list(PlaylistItem.objects.filter(playlist=self.playlist).order_by('order'))

    # 5
    def processItem(self, item):
        song = item.song
        duration_min = song.duration // 60 if song.duration else 0
        start_seconds = item.start_time if item.start_time is not None else 0
        hours = start_seconds // 3600
        minutes = (start_seconds % 3600) // 60
        start_time_str = f"{hours:02d}:{minutes:02d}"
        return {
            'order': item.order,
            'title': song.title,
            'author': song.author,
            'language': song.language,
            'duration': song.duration,
            'duration_min': duration_min,
            'start_time': item.start_time,
            'start_time_str': start_time_str,
            'item_id': item.id,
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
