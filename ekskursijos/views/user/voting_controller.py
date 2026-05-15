from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from ...models.models import Playlist, Genre, PlaylistGenre, Excursion


class VotingController:

    def __init__(self, excursion, pupil):
        self.excursion = excursion
        self.pupil = pupil
        self.playlist = get_object_or_404(Playlist, excursion=excursion)

    # mememe nekenciu puslapiu interneto
    def handle_request(self, request):
        """Route request to appropriate handler based on method."""
        if request.method == 'POST':
            return self.handle_vote(request)
        else:
            return self.handle_display(request)

    def handle_display(self, request):
        """Handle GET request to display voting page."""
        all_genres = list(Genre.objects.all())
        voted_genres = self.getVotedGenres()

        # nedarysiu sequence diagramoj for nes tingiu lmao
        genres_data = []
        for genre in all_genres:
            pg = next((g for g in voted_genres if g.genre.id == genre.id), None)
            genres_data.append({
                'genre': genre,
                'vote_count': pg.vote_count if pg else 0,
            })

        return render(request, 'ekskursijos/user/GenreVotingPage.html', {
            'excursion': self.excursion,
            'playlist': self.playlist,
            'genres_data': genres_data,
            'role': request.user.profile.role if hasattr(request.user, 'profile') else None,
        })

    def handle_vote(self, request):
        """Handle POST request for voting."""
        genre_id = request.POST.get('genre_id')
        if not genre_id:
            return JsonResponse({'status': 'error', 'message': 'Genre not provided.'}, status=400)

        try:
            genre_id = int(genre_id)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid genre ID.'}, status=400)

        result = self.voteForGenre(genre_id)
        status_code = 200 if result['status'] == 'success' else 400
        return JsonResponse(result, status=status_code)

    # 3-4
    def getPlaylistID(self):
        return self.playlist.id

    # 7-8
    def getVotedGenres(self):
        return list(PlaylistGenre.objects.filter(playlist=self.playlist).select_related('genre'))

    # 9-10
    def getPupilID(self):
        return self.pupil.id

    def checkIfPupilHasVoted(self):
        return PlaylistGenre.objects.filter(playlist=self.playlist, voted_pupils=self.pupil).exists()

    def hasPupilVotedForGenre(self, playlist_genre):
        return playlist_genre.voted_pupils.filter(id=self.pupil.id).exists()

    # 15-16
    def incrementVoteCount(self, playlist_genre):
        playlist_genre.vote_count += 1
        playlist_genre.save(update_fields=['vote_count'])
        return playlist_genre.vote_count

    # 13
    def voteForGenre(self, genre_id):
        try:
            genre = Genre.objects.get(id=genre_id)
        except Genre.DoesNotExist:
            return {'status': 'error', 'message': 'Žanras nerastas.'}

        playlist_genre, created = PlaylistGenre.objects.get_or_create(
            playlist=self.playlist,
            genre=genre,
            defaults={'vote_count': 0}
        )

        # 14:
        if self.checkIfPupilHasVoted():
            # 19-20
            return {'status': 'already_voted', 'message': 'Jau balsavote.'}

        # 15-18
        updated_count = self.incrementVoteCount(playlist_genre)
        playlist_genre.voted_pupils.add(self.pupil)

        return {
            'status': 'success',
            'message': 'Sėkmingas balsavimas!',
            'vote_count': updated_count,
            'genre_name': genre.name
        }


def _get_role(user):
    return user.profile.role if hasattr(user, 'profile') else None


@login_required
def openGenreVotingPage(request, pk):
    excursion = get_object_or_404(Excursion, pk=pk)
    role = _get_role(request.user)
    if role != 'pupil':
        messages.error(request, 'Only pupils can vote.')
        return redirect('ExcursionPage', pk=pk)

    controller = VotingController(excursion, request.user)
    return controller.handle_request(request)


@login_required
def vote_for_genre(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    excursion = get_object_or_404(Excursion, pk=pk)
    role = _get_role(request.user)
    if role != 'pupil':
        return JsonResponse({'status': 'error', 'message': 'Only pupils can vote.'}, status=403)

    controller = VotingController(excursion, request.user)
    return controller.handle_request(request)
