from django.db import migrations


def create_default_tours(apps, schema_editor):
    Artist = apps.get_model('tours', 'Artist')
    Tour = apps.get_model('tours', 'Tour')
    TourDate = apps.get_model('tours', 'TourDate')

    for artist in Artist.objects.all():
        tour_dates = TourDate.objects.filter(artist=artist)
        if not tour_dates.exists():
            continue
        created_by = getattr(artist, 'owner', None)
        if created_by is None:
            created_by = tour_dates.first().created_by
        tour, _ = Tour.objects.get_or_create(
            artist=artist,
            name='Legacy Tour',
            defaults={
                'created_by': created_by,
            },
        )
        tour_dates.update(tour=tour)


def reverse_default_tours(apps, schema_editor):
    Tour = apps.get_model('tours', 'Tour')
    TourDate = apps.get_model('tours', 'TourDate')
    legacy_tours = Tour.objects.filter(name='Legacy Tour')
    TourDate.objects.filter(tour__in=legacy_tours).update(tour=None)


class Migration(migrations.Migration):

    dependencies = [
        ('tours', '0006_tour_model'),
    ]

    operations = [
        migrations.RunPython(create_default_tours, reverse_default_tours),
    ]
