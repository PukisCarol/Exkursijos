from django.shortcuts import get_object_or_404
from ...models.models import Playlist, Genre, PlaylistGenre


class VotingController:
    """Controller for genre voting functionality (sequence diagram messages 2-20)."""

    def __init__(self, playlist, pupil):
        self.playlist = playlist
        self.pupil = pupil

    # Messages 3-4: get playlist ID
    def getPlaylistID(self):
        return self.playlist.id

    # Messages 5-6: get all existing genres (Genre.all())
    def getAllGenres(self):
        return list(Genre.objects.all())

    # Messages 7-8: get current voted genres for this playlist (PlaylistGenre.all())
    def getVotedGenres(self):
        return list(PlaylistGenre.objects.filter(playlist=self.playlist).select_related('genre'))

    # Messages 9-10: get pupil's ID
    def getPupilID(self):
        return self.pupil.id

    # Message 14: check if pupil has already voted for this playlist
    def checkIfPupilVotedAlreadyForThePlaylist(self):
        return PlaylistGenre.objects.filter(playlist=self.playlist, voted_pupils=self.pupil).exists()

    # Helper: check if pupil has voted for a specific PlaylistGenre instance
    def hasPupilVotedForGenre(self, playlist_genre):
        return playlist_genre.voted_pupils.filter(id=self.pupil.id).exists()

    # Messages 15-16: increment vote count on a PlaylistGenre
    def incrementVoteCount(self, playlist_genre):
        playlist_genre.vote_count += 1
        playlist_genre.save(update_fields=['vote_count'])
        return playlist_genre.vote_count

    # Message 13: main voteForGenre operation (handles alt: 15-18 or 19-20)
    def voteForGenre(self, genre_id):
        try:
            genre = Genre.objects.get(id=genre_id)
        except Genre.DoesNotExist:
            return {'status': 'error', 'message': 'Genre not found.'}

        playlist_genre, created = PlaylistGenre.objects.get_or_create(
            playlist=self.playlist,
            genre=genre,
            defaults={'vote_count': 0}
        )

        # Message 14: check before voting
        if self.checkIfPupilVotedAlreadyForThePlaylist():
            # ALT: 19-20 - already voted warning
            return {'status': 'already_voted', 'message': 'You have already voted for this playlist.'}

        # ALT: 15-18 - success path
        updated_count = self.incrementVoteCount(playlist_genre)
        playlist_genre.voted_pupils.add(self.pupil)

        return {
            'status': 'success',
            'message': 'Vote successfully cast!',
            'vote_count': updated_count,
            'genre_name': genre.name
        }
