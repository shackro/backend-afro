from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TeamCommissionViewSet, TeamStatsViewSet,
    TeamViewSet
)

router = DefaultRouter()
router.register(r'team/commissions', TeamCommissionViewSet, basename='team-commission')
router.register(r'team/stats', TeamStatsViewSet, basename='team-stats')
router.register(r'team', TeamViewSet, basename='team')

urlpatterns = [
    path('', include(router.urls)),
]