from django.shortcuts import get_object_or_404
from ...models.models import Playlist, Genre, PlaylistGenre


class VotingController:

    def __init__(self, playlist, pupil):
        self.playlist = playlist
        self.pupil = pupil

    # 3-4
    def getPlaylistID(self):
        return self.playlist.id


    # 7-8
    def getVotedGenres(self):
        return list(PlaylistGenre.objects.filter(playlist=self.playlist).select_related('genre'))

    # 9-10
    def getPupilID(self):
        return self.pupil.id

    def checkIfPupilVotedAlreadyForThePlaylist(self):
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
        if self.checkIfPupilVotedAlreadyForThePlaylist():
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
