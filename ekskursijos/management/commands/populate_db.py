from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from ekskursijos.models.models import (
    Profile,
    Excursion,
    ExcursionEnrollment,
    Clothing,
    CollectionRoute,
    Collection,
    Genre,
    GenrePrice,
    TypesPrice,
    Song,
    PlaceType,
    Place,
    ListOfPlaces,
    ObjectAddressProgress,
    Playlist,
    PlaylistGenre,
    PlaylistItem,
    PupilBackpackItem,
    SharedBackpackItem,
    Item,
    GoogleAddress,
    Address,
)
import random

class Command(BaseCommand):
    help = 'Populates the database with test data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating test data...')
        
        # Create users (use get_or_create for idempotency)
        admin_user, _ = User.objects.get_or_create(username='admin', defaults={
            'email': 'admin@example.com', 'is_superuser': True, 'is_staff': True
        })
        admin_user.set_password('admin123')
        admin_user.save()
        
        teacher1, _ = User.objects.get_or_create(username='teacher1', defaults={
            'email': 'teacher1@example.com', 'is_staff': False
        })
        teacher1.set_password('pass123')
        teacher1.save()
        
        teacher2, _ = User.objects.get_or_create(username='teacher2', defaults={
            'email': 'teacher2@example.com', 'is_staff': False
        })
        teacher2.set_password('pass123')
        teacher2.save()
        
        pupils = []
        for i in range(1, 11):
            pupil, _ = User.objects.get_or_create(username=f'pupil{i}', defaults={
                'email': f'pupil{i}@example.com', 'is_staff': False
            })
            pupil.set_password('pass123')
            pupil.save()
            pupils.append(pupil)
        
        # Create profiles
        Profile.objects.get_or_create(user=admin_user, defaults={'role': 'administrator', 'home_address': 'Laisvės al. 1, Kaunas, Lietuva'})
        Profile.objects.get_or_create(user=teacher1, defaults={'role': 'teacher', 'home_address': 'Gedimino g. 5, Kaunas, Lietuva'})
        Profile.objects.get_or_create(user=teacher2, defaults={'role': 'teacher', 'home_address': 'Savanorių pr. 10, Kaunas, Lietuva'})

        kaunas_addresses = [
            'Žemaičių g. 3, Kaunas, Lietuva',
            'Taikos pr. 28, Kaunas, Lietuva',
            'Kalniečių g. 41, Kaunas, Lietuva',
            'Vilijampolės g. 15, Kaunas, Lietuva',
            'Partizanų g. 60, Kaunas, Lietuva',
            'Jonavos g. 7, Kaunas, Lietuva',
            'Draugystės g. 19, Kaunas, Lietuva',
            'Chemijos g. 5, Kaunas, Lietuva',
            'Semeliškių g. 12, Kaunas, Lietuva',
            'Ąžuolų g. 8, Kaunas, Lietuva',
        ]
        for i, pupil in enumerate(pupils):
            profile, _ = Profile.objects.get_or_create(user=pupil, defaults={'role': 'pupil', 'home_address': kaunas_addresses[i]})
            profile.home_address = kaunas_addresses[i]
            profile.save()
        
        # Clear existing data to avoid conflicts
        ExcursionEnrollment.objects.all().delete()
        PlaylistItem.objects.all().delete()
        PlaylistGenre.objects.all().delete()
        Playlist.objects.all().delete()
        PupilBackpackItem.objects.all().delete()
        SharedBackpackItem.objects.all().delete()
        Collection.objects.all().delete()
        CollectionRoute.objects.all().delete()
        ObjectAddressProgress.objects.all().delete()
        ListOfPlaces.objects.all().delete()
        Excursion.objects.all().delete()
        Song.objects.all().delete()
        GenrePrice.objects.all().delete()
        TypesPrice.objects.all().delete()
        Place.objects.all().delete()
        GoogleAddress.objects.all().delete()
        Address.objects.all().delete()
        Clothing.objects.all().delete()
        Item.objects.all().delete()
        Genre.objects.all().delete()
        PlaceType.objects.all().delete()
        
        # Create place types
        place_types = []
        for pt_name in ['Museum', 'Park', 'Monument', 'Gallery', 'Historic Site']:
            pt = PlaceType.objects.create(name=pt_name)
            place_types.append(pt)
        
        # Create genres - expanded list to match iTunes API genre names
        genre_names = [
            'Rock',
            'Pop',
            'Hip-Hop',
            'Rap',
            'R&B',
            'Soul',
            'Electronic',
            'Dance',
            'Classical',
            'Jazz',
            'Blues',
            'Country',
            'Folk',
            'Alternative',
            'Indie',
            'Metal',
            'Punk',
            'Reggae',
            'Latin',
            'World',
            'Soundtrack',
            'Musical',
            'Kid',
            'Gospel',
            'Christian',
            'Comedy',
            'Spoken Word',
            'Easy Listening',
            'New Age',
            'Ambient',
            'Chillout',
            'House',
            'Techno',
            'Trance',
            'Dubstep',
            'Disco',
            'Funk',
            'Gospel',
            'Ska',
            'Opera',
        ]
        genres = []
        for genre_name in genre_names:
            g = Genre.objects.create(name=genre_name)
            g.place_types.set(random.sample(place_types, k=random.randint(1, 3)))
            genres.append(g)
        
        # Create genre prices (sample random pairs to avoid massive table)
        for _ in range(200):  # create about 200 pricing rules
            g1 = random.choice(genres)
            g2 = random.choice(genres)
            if g1 != g2:
                GenrePrice.objects.get_or_create(
                    first_genre=g1,
                    final_genre=g2,
                    defaults={'price': round(random.uniform(5, 50), 2)}
                )
        
        # Create type prices
        for pt1 in place_types:
            for pt2 in place_types:
                if pt1 != pt2:
                    TypesPrice.objects.create(first_place_type=pt1, second_place_type=pt2, price=round(random.uniform(3, 30), 2))
        
        # Create clothing items
        clothing_items = []
        for name, temp_thresh, comp in [
            ('Winter Jacket', -5, 'above'),
            ('T-shirt', 20, 'below'),
            ('Raincoat', 10, 'above'),
            ('Sweater', 5, 'below'),
            ('Hat', 0, 'above'),
        ]:
            ci = Clothing.objects.create(name=name, temperature_threshold=temp_thresh, temperature_comparison=comp)
            clothing_items.append(ci)
        
        # Create excursions
        excursions = []
        for i in range(1, 6):
            exc = Excursion.objects.create(
                name=f'Excursion {i}',
                start_date=timezone.now().date() + timezone.timedelta(days=i*10),
                end_date=timezone.now().date() + timezone.timedelta(days=i*10 + 1),
                excursion_date=timezone.now().date() + timezone.timedelta(days=i*10 + 5),
                status='created',
                teacher=random.choice([teacher1, teacher2])
            )
            exc.clothing_items.set(random.sample(clothing_items, k=random.randint(1, 3)))
            excursions.append(exc)
        
        # Create excursion enrollments
        for pupil in pupils:
            for exc in excursions:
                if random.random() < 0.8:
                    ExcursionEnrollment.objects.create(
                        pupil=pupil,
                        excursion=exc,
                        status='participating'
                    )
        
        # Create items
        items = []
        for name in ['Water Bottle', 'Snacks', 'Map', 'Camera', 'Notebook', 'Pen', 'Hat', 'Sunscreen']:
            item = Item.objects.create(name=name, importance=random.randint(1, 10), weight=random.randint(100, 1000))
            items.append(item)
        
        # Create places
        places = []
        for i in range(1, 8):
            place = Place.objects.create(
                name=f'Place {i}',
                longitude=round(random.uniform(-180, 180), 6),
                latitude=round(random.uniform(-90, 90), 6)
            )
            place.place_types.set(random.sample(place_types, k=random.randint(1, 2)))
            places.append(place)
        
        # Create songs - more songs for richer selection
        songs = []
        for i in range(1, 51):
            song = Song.objects.create(
                author=f'Author {i}',
                title=f'Song {i}',
                language=random.choice(['English', 'Lithuanian', 'Spanish', 'French', 'German', 'Italian', 'Portuguese']),
                duration=random.randint(120, 300)
            )
            song.genres.set(random.sample(genres, k=random.randint(1, 2)))
            songs.append(song)
        
        # Create collection routes
        routes = []
        for i in range(1, 4):
            route = CollectionRoute.objects.create(
                name=f'Route {i}',
                start_date=timezone.now().date() + timezone.timedelta(days=i*20),
                end_date=timezone.now().date() + timezone.timedelta(days=i*20 + 7)
            )
            routes.append(route)
        
        # Create collections
        for route in routes:
            selected_pupils = random.sample(pupils, k=random.randint(3, 7))
            for idx, pupil in enumerate(selected_pupils):
                Collection.objects.create(route=route, pupil=pupil, sequence_number=idx + 1)
        
        # Create list of places
        lists_of_places = []
        for exc in excursions:
            lop = ListOfPlaces.objects.create(name=f'List for {exc.name}', teacher=random.choice([teacher1, teacher2]), excursion=exc)
            selected_places = random.sample(places, k=random.randint(2, 5))
            for idx, place in enumerate(selected_places, start=1):
                ObjectAddressProgress.objects.create(
                    list_of_places=lop,
                    place=place,
                    visit_number=idx,
                    duration_minutes=random.randint(15, 60)
                )
            lists_of_places.append(lop)
        
        # Create playlists
        playlists = []
        for exc in excursions:
            pl = Playlist.objects.create(excursion=exc)
            playlists.append(pl)
            
            # Create playlist genres
            for genre in random.sample(genres, k=random.randint(2, 4)):
                pg = PlaylistGenre.objects.create(playlist=pl, genre=genre, vote_count=random.randint(0, 10))
                pg.voted_pupils.set(random.sample(pupils, k=random.randint(1, 5)))
            
            # Create playlist items
            selected_songs = random.sample(songs, k=random.randint(3, 7))
            start_time = 0
            for order, song in enumerate(selected_songs, start=1):
                PlaylistItem.objects.create(playlist=pl, song=song, order=order, start_time=start_time)
                start_time += song.duration
        # Create pupil backpack items
        for pupil in pupils:
            for exc in random.sample(excursions, k=random.randint(1, 2)):
                for item in random.sample(items, k=random.randint(2, 4)):
                    PupilBackpackItem.objects.create(
                        pupil=pupil,
                        excursion=exc,
                        item=item,
                        importance=random.randint(1, 10),
                        weight=random.randint(100, 1000),
                        taken=random.choice([True, False])
                    )
        
        # Create shared backpack items
        for exc in excursions:
            for item in random.sample(items, k=random.randint(2, 4)):
                SharedBackpackItem.objects.create(
                    excursion=exc,
                    item=item,
                    importance=random.randint(1, 10),
                    weight=random.randint(100, 1000)
                )
        
        # Create GoogleAddresses
        for i in range(1, 6):
            GoogleAddress.objects.create()
        
        # Create Addresses
        for i in range(1, 6):
            Address.objects.create()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created test data!'))
        self.stdout.write(f'Users: {User.objects.count()} (1 admin, 2 teachers, 10 pupils)')
        self.stdout.write(f'Excursions: {Excursion.objects.count()}')
        self.stdout.write(f'Places: {Place.objects.count()}')
        self.stdout.write(f'Songs: {Song.objects.count()}')
        self.stdout.write(f'Playlists: {Playlist.objects.count()}')
        self.stdout.write('\nLogin credentials:')
        self.stdout.write('Admin: admin / admin123')
        self.stdout.write('Teacher: teacher1 / pass123')
        self.stdout.write('Pupils: pupil1-10 / pass123')
