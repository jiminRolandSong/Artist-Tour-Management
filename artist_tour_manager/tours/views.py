from django.shortcuts import render

# Create your views here.
# queryset = which database records to work with
# serializer_class = how to convert model data <-> JSON
# ViewSet = ALL the CRUD endpoints automatically from q. and s.

from rest_framework import viewsets
from .models import Artist, Venue, TourDate
from .serializers import ArtistSerializer, VenueSerializer, TourDateSerializer

class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer

class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer

class TourDateViewSet(viewsets.ModelViewSet):
    queryset = TourDate.objects.all()
    serializer_class = TourDateSerializer
