from django.shortcuts import render

# Create your views here.
# queryset = which database records to work with
# serializer_class = how to convert model data <-> JSON
# ViewSet = ALL the CRUD endpoints automatically from q. and s.

from rest_framework import viewsets, generics
from .models import Artist, Venue, TourDate
from django.contrib.auth.models import User
from .serializers import ArtistSerializer, VenueSerializer, TourDateSerializer, RegisterSerializer
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdminOrReadOnly

class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
    
    # Check if Authenticated
    permission_classes = [IsAuthenticated]
    
    #Search fields - case-insensitive
    filter_backends = [SearchFilter]
    search_fields = ['name', 'genre']

class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    
    permission_classes = [IsAuthenticated]
    
    filter_backends = [SearchFilter]
    search_fields = ['name', 'city']

from django_filters.rest_framework import DjangoFilterBackend

class TourDateViewSet(viewsets.ModelViewSet):
    queryset = TourDate.objects.all()
    serializer_class = TourDateSerializer
    
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    
    #filters
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['artist', 'venue', 'date']
    ordering_field = ['date', 'ticket_price']
    ordering = ['date']
    search_fields = ['artist__name', 'venue__name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

'''
This allows you to filter by:
    artist: /api/tours/?artist=1

    venue: /api/tours/?venue=2

    date: /api/tours/?date=2025-09-01
'''

# POST-only endpoint / automatically implements .create(), using the serializer
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    
    # public endpoint
    permission_classes = []
    