from django.db import models
from django.contrib.auth.models import User

# This file defines the models for the Artist Tour Management application.
class Artist(models.Model):
    name = models.CharField(max_length=100, unique=True)
    genre = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="artists", null=True, blank=True)

    def __str__(self):
        return self.name

class Venue(models.Model):
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    operating_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = [['name', 'city']]

    def __str__(self):
        return f"{self.name} ({self.city})"

class Tour(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="tours")
    name = models.CharField(max_length=150)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    venues = models.ManyToManyField('Venue', through='TourGroupVenue', related_name='tour_groups', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_tour_groups")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['artist', 'name']]

    def __str__(self):
        return f"{self.artist.name} - {self.name}"

class TourGroupVenue(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)

    class Meta:
        unique_together = [['tour', 'venue']]

class TourDate(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, null=True, blank=True, related_name="dates")
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    date = models.DateField()
    ticket_price = models.DecimalField(max_digits=8, decimal_places=2)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_tours")
    is_archived = models.BooleanField(default=False)

    class Meta:
        unique_together = [['artist', 'date']]

    def __str__(self):
        return f"{self.artist.name} @ {self.venue.name} on {self.date}"

class FanDemand(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    fan_count = models.PositiveIntegerField()
    engagement_score = models.DecimalField(max_digits=5, decimal_places=4, default=0.1000)
    expected_ticket_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.artist.name} @ {self.venue.name} fans"

class TourPlan(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="plans")
    name = models.CharField(max_length=150)
    start_date = models.DateField()
    end_date = models.DateField()
    start_city = models.CharField(max_length=120, blank=True)
    venue_ids = models.JSONField(default=list, blank=True)
    region_filters = models.JSONField(default=dict, blank=True)
    targets = models.JSONField(default=dict, blank=True)
    constraints = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_plans")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['artist', 'name']]

    def __str__(self):
        return f"{self.artist.name} Plan - {self.name}"


class OptimizationRun(models.Model):
    plan = models.ForeignKey(TourPlan, on_delete=models.CASCADE, related_name="runs")
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
