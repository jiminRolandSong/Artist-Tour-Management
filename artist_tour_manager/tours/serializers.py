# Convert complex data types into formats that can be sent to the internet (json)

from rest_framework import serializers
from .models import Artist, Venue, TourDate

class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = '__all__'

class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = '__all__'

class TourDateSerializer(serializers.ModelSerializer):
    artist = ArtistSerializer(read_only=True)
    venue = VenueSerializer(read_only=True)
    artist_id = serializers.PrimaryKeyRelatedField(queryset=Artist.objects.all(), write_only=True, source='artist')
    venue_id = serializers.PrimaryKeyRelatedField(queryset=Venue.objects.all(), write_only=True, source='venue')

    class Meta:
        model = TourDate
        fields = ['id', 'artist', 'artist_id', 'venue', 'venue_id', 'date', 'ticket_price']