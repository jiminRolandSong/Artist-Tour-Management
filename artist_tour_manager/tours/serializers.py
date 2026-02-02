# Convert complex data types into formats that can be sent to the internet (json)

from rest_framework import serializers
from datetime import date as dt_date
from .models import Artist, Venue, TourDate, FanDemand, Tour, TourPlan, OptimizationRun
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
    tour = serializers.StringRelatedField(read_only=True)
    tour_id_read = serializers.IntegerField(source='tour.id', read_only=True)
    tour_name = serializers.CharField(source='tour.name', read_only=True)
    
    # These fields are used to create or update the TourDate instance
    # They are write_only because we don't want to expose the IDs in the API response
    artist_id = serializers.PrimaryKeyRelatedField(queryset=Artist.objects.all(), write_only=True, source='artist')
    venue_id = serializers.PrimaryKeyRelatedField(queryset=Venue.objects.all(), write_only=True, source='venue')
    tour_id = serializers.PrimaryKeyRelatedField(queryset=Tour.objects.all(), write_only=True, source='tour')

    class Meta:
        model = TourDate
        fields = ['id', 'tour', 'tour_id_read', 'tour_name', 'tour_id', 'artist', 'artist_id', 'venue', 'venue_id', 'date', 'ticket_price', 'is_archived']
    
    # Automatically called whenever someone creates ot updates a TourDate by DRF
    # Avoid sameday booking    
    def validate(self, data):
        artist = data.get('artist')
        tour_date = data.get('date')
        tour = data.get('tour')

        if tour and artist and tour.artist_id != artist.id:
            raise serializers.ValidationError("Tour must belong to the selected artist.")
        if not self.instance and tour_date and tour_date <= dt_date.today():
            raise serializers.ValidationError("Tour date must be in the future.")
        
        #Excluding current instance
        tourdate_id = self.instance.id if self.instance else None
        
        if TourDate.objects.filter(artist=artist, date=tour_date).exclude(id = tourdate_id).exists():
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

class TourSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    venues = VenueSerializer(many=True, read_only=True)
    venue_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    def validate(self, data):
        start_date = data.get('start_date')
        if start_date and start_date <= dt_date.today():
            raise serializers.ValidationError("Tour start date must be in the future.")
        return data

    class Meta:
        model = Tour
        fields = ['id', 'artist', 'artist_name', 'name', 'start_date', 'end_date', 'description', 'venues', 'venue_ids', 'created_by', 'created_at']

class FanDemandSerializer(serializers.ModelSerializer):
    class Meta:
        model = FanDemand
        fields = '__all__'

class OptimizationRequestSerializer(serializers.Serializer):
    artist_id = serializers.IntegerField()
    venue_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    start_venue_id = serializers.IntegerField(required=False)
    start_city = serializers.CharField(required=False, allow_blank=False)
    use_ai = serializers.BooleanField(default=False)
    cost_per_km = serializers.DecimalField(max_digits=10, decimal_places=2, default=2.00)
    distance_weight = serializers.DecimalField(max_digits=6, decimal_places=3, default=1.000)
    revenue_weight = serializers.DecimalField(max_digits=6, decimal_places=3, default=1.000)
    min_gap_days = serializers.IntegerField(required=False, min_value=0)
    start_date = serializers.DateField(required=False)
    travel_speed_km_per_day = serializers.DecimalField(max_digits=7, decimal_places=2, required=False)

class OptimizationConfirmSerializer(serializers.Serializer):
    artist_id = serializers.IntegerField()
    tour_id = serializers.IntegerField()
    schedule = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    conflict_strategy = serializers.ChoiceField(choices=['skip', 'overwrite'], required=False)

class TourPlanSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source='artist.name', read_only=True)

    def validate(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if start_date and start_date <= dt_date.today():
            raise serializers.ValidationError("Plan start date must be in the future.")
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("Plan end date must be after start date.")
        return data

    class Meta:
        model = TourPlan
        fields = [
            'id', 'artist', 'artist_name', 'name', 'start_date', 'end_date', 'start_city',
            'venue_ids', 'region_filters', 'targets', 'constraints', 'created_by', 'created_at'
        ]


class OptimizationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationRun
        fields = ['id', 'plan', 'result', 'created_at']
