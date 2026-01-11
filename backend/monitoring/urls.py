from rest_framework.routers import DefaultRouter

from .views import ChangeViewSet, WatchTargetViewSet

router = DefaultRouter()
router.register("targets", WatchTargetViewSet, basename="target")
router.register("changes", ChangeViewSet, basename="change")

urlpatterns = router.urls
