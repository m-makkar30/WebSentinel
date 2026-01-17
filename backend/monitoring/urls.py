from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AlertViewSet,
    ChangeViewSet,
    CheckRunViewSet,
    StatsView,
    WatchTargetViewSet,
)

router = DefaultRouter()
router.register("targets", WatchTargetViewSet, basename="target")
router.register("changes", ChangeViewSet, basename="change")
router.register("alerts", AlertViewSet, basename="alert")
router.register("runs", CheckRunViewSet, basename="run")

urlpatterns = [*router.urls, path("stats/", StatsView.as_view(), name="stats")]
