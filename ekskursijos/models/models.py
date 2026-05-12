from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    ROLE_CHOICES = [
        ('administrator', 'Administrator'),
        ('teacher', 'Teacher'),
        ('pupil', 'Pupil'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    home_address = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class Excursion(models.Model):
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('itinerary_ready', 'Itinerary Ready'),
        ('route_ready', 'Route Ready'),
        ('published', 'Published'),
    ]
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    excursion_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='excursions')
    clothing_items = models.ManyToManyField('Clothing', blank=True, related_name='excursions')

    def __str__(self):
        return self.name


class ExcursionEnrollment(models.Model):
    STATUS_CHOICES = [
        ('participating', 'Participating'),
        ('not_participating', 'Not Participating'),
        ('not_chosen', 'Not Chosen'),
    ]
    pupil = models.ForeignKey(User, on_delete=models.CASCADE, related_name='excursion_enrollments')
    excursion = models.ForeignKey(Excursion, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_chosen')

    class Meta:
        unique_together = ('pupil', 'excursion')

    def __str__(self):
        return f"{self.pupil} in {self.excursion}"


class Clothing(models.Model):
    TEMPERATURE_COMPARISON_CHOICES = [
        ('above', 'Above'),
        ('below', 'Below'),
        ('equal', 'Equal'),
    ]
    name = models.CharField(max_length=200)
    temperature_threshold = models.IntegerField()
    temperature_comparison = models.CharField(max_length=20, choices=TEMPERATURE_COMPARISON_CHOICES)

    def __str__(self):
        return self.name


class CollectionRoute(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    excursion = models.ForeignKey('Excursion', on_delete=models.CASCADE, null=True, blank=True, related_name='collection_routes')
    pupils = models.ManyToManyField(User, through='Collection', related_name='collection_routes')

    def __str__(self):
        return self.name


class Collection(models.Model):
    route = models.ForeignKey(CollectionRoute, on_delete=models.CASCADE, related_name='collections')
    pupil = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collections')
    sequence_number = models.IntegerField()

    class Meta:
        unique_together = ('route', 'pupil')

    def __str__(self):
        return f"{self.pupil} in {self.route} #{self.sequence_number}"


class PlaceType(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(max_length=200)
    place_types = models.ManyToManyField(PlaceType, blank=True, related_name='genres')

    def __str__(self):
        return self.name


class GenrePrice(models.Model):
    price = models.DecimalField(decimal_places=2, max_digits=8)
    first_genre = models.ForeignKey(Genre, on_delete=models.CASCADE, related_name='first_genre_prices')
    final_genre = models.ForeignKey(Genre, on_delete=models.CASCADE, related_name='final_genre_prices')

    class Meta:
        unique_together = ('first_genre', 'final_genre')

    def __str__(self):
        return f"{self.first_genre} → {self.final_genre}: {self.price}"


class TypesPrice(models.Model):
    price = models.DecimalField(decimal_places=2, max_digits=8)
    first_place_type = models.ForeignKey(PlaceType, on_delete=models.CASCADE, related_name='first_type_prices')
    second_place_type = models.ForeignKey(PlaceType, on_delete=models.CASCADE, related_name='second_type_prices')

    class Meta:
        unique_together = ('first_place_type', 'second_place_type')

    def __str__(self):
        return f"{self.first_place_type} → {self.second_place_type}: {self.price}"


class Song(models.Model):
    author = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    language = models.CharField(max_length=50)
    duration = models.IntegerField()
    genres = models.ManyToManyField(Genre, blank=True, related_name='songs')

    def __str__(self):
        return self.title


class Place(models.Model):
    name = models.CharField(max_length=200)
    longitude = models.FloatField()
    latitude = models.FloatField()
    place_types = models.ManyToManyField(PlaceType, blank=True, related_name='places')

    def __str__(self):
        return self.name


class ListOfPlaces(models.Model):
    name = models.CharField(max_length=200)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_lists')
    excursion = models.OneToOneField(Excursion, on_delete=models.CASCADE, related_name='list_of_places')
    places = models.ManyToManyField(Place, through='ObjectAddressProgress', related_name='lists')

    def __str__(self):
        return self.name


class ObjectAddressProgress(models.Model):
    list_of_places = models.ForeignKey(ListOfPlaces, on_delete=models.CASCADE, related_name='address_progresses')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='address_progresses')
    visit_number = models.IntegerField()
    duration_minutes = models.IntegerField()

    class Meta:
        unique_together = ('list_of_places', 'place')

    def __str__(self):
        return f"{self.place} visit {self.visit_number}"


class Playlist(models.Model):
    excursion = models.OneToOneField(Excursion, on_delete=models.CASCADE, related_name='playlist')
    creation_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Playlist for {self.excursion}"


class PlaylistGenre(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='playlist_genres')
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE, related_name='playlist_genres')
    vote_count = models.IntegerField(default=0)
    voted_pupils = models.ManyToManyField(User, blank=True, related_name='voted_playlist_genres')

    def __str__(self):
        return f"{self.genre} in {self.playlist}"


class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='items')
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='playlist_items')
    order = models.IntegerField()
    start_time = models.IntegerField()

    class Meta:
        ordering = ['order']
        unique_together = ('playlist', 'order')

    def __str__(self):
        return f"{self.song} at {self.start_time}"


class PupilBackpackItem(models.Model):
    pupil = models.ForeignKey(User, on_delete=models.CASCADE, related_name='backpack_items')
    excursion = models.ForeignKey(Excursion, on_delete=models.CASCADE, related_name='pupil_backpack_items')
    item = models.ForeignKey('Item', on_delete=models.CASCADE, related_name='pupil_backpack_items')
    importance = models.IntegerField()
    weight = models.IntegerField()
    taken = models.BooleanField(default=False)

    class Meta:
        unique_together = ('pupil', 'excursion', 'item')

    def __str__(self):
        return f"{self.item} for {self.pupil}"


class SharedBackpackItem(models.Model):
    excursion = models.ForeignKey(Excursion, on_delete=models.CASCADE, related_name='shared_backpack_items')
    item = models.ForeignKey('Item', on_delete=models.CASCADE, related_name='shared_backpack_items')
    importance = models.IntegerField()
    weight = models.IntegerField()

    class Meta:
        unique_together = ('excursion', 'item')

    def __str__(self):
        return f"Shared {self.item} for {self.excursion}"


class Item(models.Model):
    name = models.CharField(max_length=200)
    importance = models.IntegerField()
    weight = models.IntegerField()

    def __str__(self):
        return self.name


class GoogleAddress(models.Model):
    def __str__(self):
        return "GoogleAddress"


class Address(models.Model):
    def __str__(self):
        return "Address"
