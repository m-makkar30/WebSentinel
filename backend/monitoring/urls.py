from rest_framework.routers import DefaultRouter

from .views import WatchTargetViewSet

router = DefaultRouter()
router.register("targets", WatchTargetViewSet, basename="target")

urlpatterns = router.urls
