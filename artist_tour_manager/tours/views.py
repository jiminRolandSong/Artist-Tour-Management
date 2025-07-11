from urllib import request, response
from django.http import HttpResponse
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
from rest_framework.response import Response
from .permissions import IsAdminOrReadOnly

# ViewSets are used to create views for models, allowing for CRUD operations.

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

'''
Filter by:
    artist: /api/tours/?artist=1

    venue: /api/tours/?venue=2

    date: /api/tours/?date=2025-09-01
'''

class TourDateViewSet(viewsets.ModelViewSet):
    queryset = TourDate.objects.all()
    serializer_class = TourDateSerializer
    
    # Check if Authenticated
    # Admins can read/write, others can only read
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    
    # Filter, Search, and Ordering
    # DjangoFilterBackend allows filtering by fields defined in filterset_fields
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['artist', 'venue', 'date']
    ordering_field = ['date', 'ticket_price']
    ordering = ['date']
    search_fields = ['artist__name', 'venue__name']
    
    # Automatically set the user who created the tour date
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)




# POST-only endpoint / automatically implements .create(), using the serializer
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    
    # public endpoint
    permission_classes = []

import csv
from rest_framework.views import APIView
# Export
class TourExportView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        
        print("Query params:", request.query_params)
        print("Format param:", request.query_params.get('format'))
        
        # Get the user and their tours
        # Assuming the user is authenticated and has a TourDate relationship
        user = request.user
        user_tours = TourDate.objects.filter(created_by=user)
        
        #csv format
        if request.query_params.get('type', '').lower() == 'csv':
            # Create a CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="my_tours.csv"'

            # Write CSV data
            writer = csv.writer(response)
            writer.writerow(['ID', 'Artist', 'Venue', 'Date', 'Ticket Price'])
            for tour in user_tours:
                writer.writerow([tour.id, tour.artist.name, tour.venue.name, tour.date, tour.ticket_price])
            return response

        serializer = TourDateSerializer(user_tours, many=True)
        return Response(serializer.data)