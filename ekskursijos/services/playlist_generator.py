"""
Playlist Generator Service implementing the process described in the sequence diagram.
Generates an optimized playlist for an excursion using Simulated Annealing.
"""

import random
import math
from django.utils import timezone
from django.db import transaction
from .music_api import search_songs
from ..models.models import (
    Playlist, Excursion, ListOfPlaces, ObjectAddressProgress,
    Genre, PlaylistGenre, GenrePrice, Song, PlaylistItem, Place, PlaceType
)


class PlaylistController:
    """
    Controller that orchestrates playlist generation exactly as per sequence diagram.
    """

    PLACE_MISMATCH_PENALTY = 1000.0  # high penalty for song not matching place genres
    AVG_SONG_DURATION = 200  # average song length in seconds (approx 3:20)

    def __init__(self, playlist):
        """
        Initialize with a Playlist instance.
        """
        self.playlist = playlist
        self.excursion = playlist.excursion
        self.favorite_genre = None
        self.places = []            # list of Place objects in visit order
        self.place_types = []       # distinct PlaceType objects for these places
        self.place_genres = []      # list of sets of Genre objects per place
        self.processed_places = set()
        self.songs = []             # list of {'track': dict, 'genre': Genre}
        self.N = 0                  # number of songs required
        self.unprocessed_places = []  # used in processing loop

        # Simulated Annealing state
        self.T = 1000.0
        self.Tmin = 0.1
        self.cooling_rate = 0.995
        self.max_iter = 1000
        self.iterations_at_min_temp = 50
        self.iteration = 0
        self.transition_cost = []   # 2D list of costs between songs
        self.price_dict = {}        # dict mapping (genre1_id, genre2_id) -> price
        self.current_solution = []
        self.current_cost = 0.0
        self.best_solution = []
        self.best_cost = float('inf')

    # Step 1: getPlaylistID
    def getPlaylistID(self):
        return self.playlist.id

    # Step 2: (handled by caller)

    # Step 3: getVotes
    def getVotes(self):
        return list(PlaylistGenre.objects.filter(playlist=self.playlist).select_related('genre'))

    # Step 4: getAll (Genres)
    def getAllGenres(self):
        return list(Genre.objects.all())

    # Step 5: checkGenreVotes
    def checkGenreVotes(self, votes):
        return any(v.vote_count > 0 for v in votes)

    # Step 6/7: setMostVotedAsFavourite
    def setMostVotedAsFavourite(self, votes):
        if not votes:
            return self.setHeavyMetalAsFavourite()
        best = max(votes, key=lambda v: v.vote_count)
        self.favorite_genre = best.genre
        return self.favorite_genre

    # Step 6/11: setHeavyMetalAsFavourite
    def setHeavyMetalAsFavourite(self):
        genre = Genre.objects.filter(name__iexact='Heavy Metal').first()
        if not genre:
            # fallback to first genre
            genre = Genre.objects.first()
        self.favorite_genre = genre
        return self.favorite_genre

    # Step 12: getExcursionID
    def getExcursionID(self):
        return self.excursion.id

    # Step 14: getExcursionPlaces
    def getExcursionPlaces(self):
        # Find the ListOfPlaces for this excursion
        try:
            lop = ListOfPlaces.objects.get(excursion=self.excursion)
        except ListOfPlaces.DoesNotExist:
            self.places = []
            return self.places
        # Get ObjectAddressProgress entries ordered by visit_number
        progresses = ObjectAddressProgress.objects.filter(list_of_places=lop).select_related('place').order_by('visit_number')
        self.places = [p.place for p in progresses]
        return self.places

    # Step 16: getExcursionPlaceTypes
    def getExcursionPlaceTypes(self):
        # Get all distinct PlaceType objects attached to these places
        if not self.places:
            self.place_types = []
            return self.place_types
        self.place_types = list(PlaceType.objects.filter(places__in=self.places).distinct())
        return self.place_types

    # Step 18: all GenrePrice (getAllGenrePrices)
    def getAllGenrePrices(self):
        return list(GenrePrice.objects.all())

    # Step 20: getPlaceGenres
    def getPlaceGenres(self, place):
        return set(Genre.objects.filter(place_types__places=place).distinct())

    # Step 21: markPlaceProcessed
    def markPlaceProcessed(self, place):
        self.processed_places.add(place.id)

    # Step 22: getExcursionStartAndEnd
    def getExcursionStartAndEnd(self):
        """
        Returns a tuple (start_seconds, end_seconds) representing the total duration
        of the excursion based on the sum of place visit durations.
        """
        progresses = ObjectAddressProgress.objects.filter(list_of_places__excursion=self.excursion)
        total_minutes = sum(p.duration_minutes for p in progresses)
        total_seconds = total_minutes * 60
        # Start at 0 seconds, end at total_seconds
        return (0, total_seconds)

    # Step 24: findRequiredSongsCount
    def findRequiredSongsCount(self, start_seconds, end_seconds):
        total_duration = end_seconds - start_seconds
        if total_duration <= 0:
            raise ValueError("Excursion duration is zero or negative")
        count = math.ceil(total_duration / self.AVG_SONG_DURATION)
        return max(count, 1)

    # Step 25: getRandomSongs
    def getRandomSongs(self, count):
        """
        Fetches random songs from the Music API. Attempts to get a diverse pool
        using favorite genre first, then other genres, then generic queries.
        Returns list of raw track dicts.
        """
        seeds = []
        seen = set()
        queries = []

        if self.favorite_genre:
            queries.append(self.favorite_genre.name)
        other_genres = list(Genre.objects.exclude(id=self.favorite_genre.id)[:5]) if self.favorite_genre else list(Genre.objects.all()[:5])
        queries.extend([g.name for g in other_genres])
        queries.append('music')
        # Try each query
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

        # If still insufficient, use random letters
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

    # Step 29: filterRequiredSongCount
    def filterRequiredSongCount(self, raw_songs, count):
        """
        Converts raw track data to internal representation with linked Genre.
        Keeps only songs whose primary genre exists in our Genre DB.
        Returns exactly 'count' items by random sampling; raises if insufficient.
        """
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

    # Step 30: getRelevantSongPrices
    def getRelevantSongPrices(self):
        """
        Fetches all GenrePrice objects where both first_genre and final_genre
        belong to the set of genres of the selected songs.
        Stores in self.relevant_prices and self.price_dict.
        """
        selected_genres = set(item['genre'] for item in self.songs)
        self.relevant_prices = GenrePrice.objects.filter(
            first_genre__in=selected_genres,
            final_genre__in=selected_genres
        )
        self.price_dict = {
            (p.first_genre_id, p.final_genre_id): float(p.price)
            for p in self.relevant_prices
        }

    # Step 31: createRandomSolution
    def createRandomSolution(self):
        """Returns a random permutation of song indices [0..N-1]."""
        sol = list(range(self.N))
        random.shuffle(sol)
        return sol

    # Step 32: findSmallestPriceForEachSongCombination
    def findSmallestPriceForEachSongCombination(self):
        """
        Precomputes a transition cost matrix: cost[i][j] = smallest price from
        song i's genre to song j's genre based on self.price_dict.
        """
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

    # Step 33: findStartingPrice
    def findStartingPrice(self, solution):
        return self.calculateCost(solution)

    # Step 34: setStartingSAParameters
    def setStartingSAParameters(self):
        self.T = 1000.0
        self.Tmin = 0.1
        self.cooling_rate = 0.995
        self.max_iter = max(1000, self.N * 100)
        self.iterations_at_min_temp = 50

    # Step 35: setCurrentSolution
    def setCurrentSolution(self, solution, cost):
        self.current_solution = solution
        self.current_cost = cost

    # Step 36: generateNeighbor
    def generateNeighbor(self, solution):
        i, j = random.sample(range(len(solution)), 2)
        neighbor = solution.copy()
        neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
        return neighbor

    # Step 37: calculateCost
    def calculateCost(self, solution):
        total = 0.0
        n = len(solution)
        # Transition costs between consecutive songs
        for i in range(n - 1):
            a = solution[i]
            b = solution[i + 1]
            total += self.transition_cost[a][b]
        # Place mismatch penalties
        for pos, idx in enumerate(solution):
            if pos < len(self.place_genres):
                song_genre = self.songs[idx]['genre']
                if song_genre not in self.place_genres[pos]:
                    total += self.PLACE_MISMATCH_PENALTY
        return total

    # Step 39: saveAsTempBest
    def saveAsTempBest(self, solution, cost):
        if cost < self.best_cost:
            self.best_solution = solution.copy()
            self.best_cost = cost

    # Step 40: decideWhetherToTakeSolution
    def decideWhetherToTakeSolution(self, delta):
        if delta < 0:
            return True
        try:
            prob = math.exp(-delta / self.T)
        except (OverflowError, ZeroDivisionError):
            return False
        return random.random() < prob

    # Step 42: decreaseTemperature
    def decreaseTemperature(self):
        self.T *= self.cooling_rate
        if self.T < self.Tmin:
            self.T = self.Tmin

    # Step 43: incrementCurrentIterations
    def incrementCurrentIterations(self):
        self.iteration += 1

    # Step 44: deleteCurrentItems
    def deleteCurrentItems(self):
        PlaylistItem.objects.filter(playlist=self.playlist).delete()

    # Step 46: bulk_create Songs and step 48: playlist items combined
    def bulk_create_songs_and_items(self):
        # Create songs in final order
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
        # Assign M2M genres
        for song, data in zip(created_songs, ordered_data):
            song.genres.add(data['genre'])
        # Create playlist items
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

    # Step 50: recountItemStartTimes
    def recountItemStartTimes(self):
        # Import here to avoid circular
        from ekskursijos.views.user.excursion import recountItemStartTimes
        recountItemStartTimes(self.playlist)

    # Step 51: updateCreationDate
    def updateCreationDate(self):
        self.playlist.creation_date = timezone.now().date()
        self.playlist.save(update_fields=['creation_date'])

    # Main generate orchestration
    def generate(self):
        # Steps 1-9: get data and favorite genre
        self.getPlaylistID()
        votes = self.getVotes()
        all_genres = self.getAllGenres()
        if self.checkGenreVotes(votes):
            self.setMostVotedAsFavourite(votes)
        else:
            self.setHeavyMetalAsFavourite()
        self.getExcursionID()
        self.getExcursionPlaces()
        self.getExcursionPlaceTypes()
        self.getAllGenrePrices()

        # Steps 20-21: loop over places to collect genres
        self.unprocessed_places = self.places[:]  # copy
        while self.unprocessed_places:
            place = self.unprocessed_places.pop(0)
            genres = self.getPlaceGenres(place)
            self.place_genres.append(genres)  # maintain order of places
            self.markPlaceProcessed(place)

        # Steps 22-23: get excursion start and end times (relative)
        start_sec, end_sec = self.getExcursionStartAndEnd()

        # Step 24: required songs count
        self.N = self.findRequiredSongsCount(start_sec, end_sec)

        # Step 25-28: fetch songs and filter
        raw_songs = self.getRandomSongs(self.N * 3)  # ask for more to have pool
        self.songs = self.filterRequiredSongCount(raw_songs, self.N)

        # Step 30: get relevant genre prices
        self.getRelevantSongPrices()

        # Step 32: Precompute transition cost matrix
        self.findSmallestPriceForEachSongCombination()

        # Step 31 & 33: Create random solution and compute its cost
        initial_perm = self.createRandomSolution()
        start_cost = self.findStartingPrice(initial_perm)
        self.setCurrentSolution(initial_perm, start_cost)
        self.best_solution = initial_perm.copy()
        self.best_cost = start_cost

        # Steps 34-35: Set SA parameters and current solution already done
        self.setStartingSAParameters()

        # Step 6 - Simulated Annealing loop (only if more than 1 song)
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
                # Optionally decrease temperature every few iterations
                if self.iteration > 0 and self.iteration % self.iterations_at_min_temp == 0:
                    self.decreaseTemperature()
                self.incrementCurrentIterations()
        # For N == 1, best_solution is already the trivial solution

        # Finalization steps 44-52
        # Use a transaction to ensure atomic updates
        with transaction.atomic():
            self.deleteCurrentItems()                    # step 44
            self.bulk_create_songs_and_items()           # steps 46 & 48
            self.recountItemStartTimes()                 # step 50
            self.updateCreationDate()                    # step 51

        return self.playlist
