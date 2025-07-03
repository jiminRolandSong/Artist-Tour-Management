from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ArtistViewSet, VenueViewSet, TourDateViewSet, RegisterView

router = DefaultRouter()
router.register(r'artists', ArtistViewSet)
router.register(r'venues', VenueViewSet)
router.register(r'tours', TourDateViewSet)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('', include(router.urls)),
]