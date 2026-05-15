from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from ...models.models import Playlist, Genre, PlaylistGenre, Excursion


def _get_role(user):
    return user.profile.role if hasattr(user, 'profile') else None


# ============================================================
#  VotingController — helpers only (no route-handler logic)
# ============================================================

class VotingController:

    def __init__(self, excursion, pupil):
        self.excursion = excursion
        self.pupil = pupil
        self.playlist = get_object_or_404(Playlist, excursion=excursion)

    # 3-4
    def getPlaylistID(self):
        return self.playlist.id

    # 9-10
    def getPupilID(self):
        return self.pupil.id

    def checkIfPupilHasVoted(self):
        return PlaylistGenre.objects.filter(playlist=self.playlist, voted_pupils=self.pupil).exists()

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


# routes
@login_required
def openGenreVotingPage(request, pk):
    excursion = get_object_or_404(Excursion, pk=pk)
    role = _get_role(request.user)
    if role != 'pupil':
        messages.error(request, 'Only pupils can vote.')
        return redirect('ExcursionPage', pk=pk)

    controller = VotingController(excursion, request.user)

    if request.method == 'POST':
        genre_id = request.POST.get('genre_id')
        if not genre_id:
            return JsonResponse({'status': 'error', 'message': 'Genre not provided.'}, status=400)

        try:
            genre_id = int(genre_id)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid genre ID.'}, status=400)

        result = controller.voteForGenre(genre_id)
        status_code = 200 if result['status'] == 'success' else 400
        return JsonResponse(result, status=status_code)

    # GET
    all_genres = list(Genre.objects.all())
    voted_genres = list(PlaylistGenre.objects.filter(playlist=controller.playlist).select_related('genre'))

    genres_data = []
    for genre in all_genres:
        pg = next((g for g in voted_genres if g.genre.id == genre.id), None)
        genres_data.append({
            'genre': genre,
            'vote_count': pg.vote_count if pg else 0,
        })

    return render(request, 'ekskursijos/user/GenreVotingPage.html', {
        'excursion': excursion,
        'playlist': controller.playlist,
        'genres_data': genres_data,
        'role': request.user.profile.role if hasattr(request.user, 'profile') else None,
    })


@login_required
def vote_for_genre(request, pk):
    excursion = get_object_or_404(Excursion, pk=pk)
    controller = VotingController(excursion, request.user)

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    if _get_role(request.user) != 'pupil':
        return JsonResponse({'status': 'error', 'message': 'Only pupils can vote.'}, status=403)

    genre_id = request.POST.get('genre_id')
    if not genre_id:
        return JsonResponse({'status': 'error', 'message': 'Genre not provided.'}, status=400)

    try:
        genre_id = int(genre_id)
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Invalid genre ID.'}, status=400)

    result = controller.voteForGenre(genre_id)
    status_code = 200 if result['status'] == 'success' else 400
    return JsonResponse(result, status=status_code)
