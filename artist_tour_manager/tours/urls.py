from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ArtistViewSet, VenueViewSet, FanDemandViewSet, TourDateViewSet, RegisterView, TourExportView, TourOptimizationView, TourOptimizationConfirmView, TourViewSet, TourPlanViewSet, PlanOptimizationRunView, OptimizationRunConfirmView

router = DefaultRouter()
router.register(r'artists', ArtistViewSet)
router.register(r'venues', VenueViewSet)
router.register(r'fan-demand', FanDemandViewSet)
router.register(r'tour-groups', TourViewSet)
router.register(r'plans', TourPlanViewSet)
router.register(r'tours', TourDateViewSet)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('export/tours/', TourExportView.as_view(), name='tour-export'),
    path('optimize/', TourOptimizationView.as_view(), name='tour-optimize'),
    path('optimize/confirm/', TourOptimizationConfirmView.as_view(), name='tour-optimize-confirm'),
    path('plans/<int:plan_id>/run/', PlanOptimizationRunView.as_view(), name='plan-optimize-run'),
    path('runs/<int:run_id>/confirm/', OptimizationRunConfirmView.as_view(), name='run-optimize-confirm'),
    path('', include(router.urls)),
]
