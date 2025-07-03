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