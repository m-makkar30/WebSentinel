from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AlertViewSet, ChangeViewSet, StatsView, WatchTargetViewSet

router = DefaultRouter()
router.register("targets", WatchTargetViewSet, basename="target")
router.register("changes", ChangeViewSet, basename="change")
router.register("alerts", AlertViewSet, basename="alert")

urlpatterns = [*router.urls, path("stats/", StatsView.as_view(), name="stats")]
