from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ArtistViewSet, VenueViewSet, TourDateViewSet

router = DefaultRouter()
router.register(r'artists', ArtistViewSet)
router.register(r'venues', VenueViewSet)
router.register(r'tours', TourDateViewSet)

urlpatterns = [
    path('', include(router.urls)),
]