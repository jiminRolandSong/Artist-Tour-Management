from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Artist(models.Model):
    name = models.CharField(max_length=100)
    genre = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class Venue(models.Model):
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()
    
    def __str__(self):
        return f"{self.name} ({self.city})"

class TourDate(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    date = models.DateField()
    ticket_price = models.DecimalField(max_digits=8, decimal_places=2)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_tours")

    def __str__(self):
        return f"{self.artist.name} @ {self.venue.name} on {self.date}"

