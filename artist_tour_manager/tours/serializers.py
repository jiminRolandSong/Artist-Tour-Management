# Convert complex data types into formats that can be sent to the internet (json)

from rest_framework import serializers
from .models import Artist, Venue, TourDate
# Serializers are used to convert complex data types, such as querysets and model instances, into native Python datatypes that can then be easily rendered into JSON or XML.
# They also handle deserialization, allowing parsed data to be converted back into complex types, after validating the incoming data.
# This allows us to create, read, update, and delete data in a consistent way.
# Serializers are similar to Django Forms, but they are specifically designed for working with complex data types and can handle nested relationships.

class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = '__all__'

class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = '__all__'

class TourDateSerializer(serializers.ModelSerializer):
    # Nested serializers to include related Artist and Venue data in the TourDate response
    # This allows us to get the full details of the artist and venue without needing to make additional queries
    # The 'read_only' attribute means these fields are for display purposes only and cannot be used to create or update the TourDate instance directly
    # If you want to create or update a TourDate instance, you will need to use the artist_id and venue_id fields instead
    # This is useful for API responses where you want to show the full details of the artist and venue
    
    artist = ArtistSerializer(read_only=True)
    venue = VenueSerializer(read_only=True)
    
    # These fields are used to create or update the TourDate instance
    # They are write_only because we don't want to expose the IDs in the API response
    artist_id = serializers.PrimaryKeyRelatedField(queryset=Artist.objects.all(), write_only=True, source='artist')
    venue_id = serializers.PrimaryKeyRelatedField(queryset=Venue.objects.all(), write_only=True, source='venue')

    class Meta:
        model = TourDate
        fields = ['id', 'artist', 'artist_id', 'venue', 'venue_id', 'date', 'ticket_price']
    
    # Automatically called whenever someone creates ot updates a TourDate by DRF
    # Avoid sameday booking    
    def validate(self, data):
        artist = data.get('artist')
        date = data.get('date')
        
        #Excluding current instance
        tourdate_id = self.instance.id if self.instance else None
        
        if TourDate.objects.filter(artist=artist, date=date).exclude(id = tourdate_id).exists():
            raise serializers.ValidationError("This artist already has a show on this date")
        
        return data

from django.contrib.auth.models import User

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only = True, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        
    def create(self, validated_data):
        user = User.objects.create_user(
            username = validated_data['username'],
            email = validated_data['email'],
            password=validated_data['password']
        )
        return user