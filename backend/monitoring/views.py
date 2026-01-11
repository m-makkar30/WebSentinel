from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema
from rest_framework import status as http_status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from .models import AlertStatus, Change, TargetStatus, WatchTarget
from .serializers import ChangeSerializer, WatchTargetSerializer


@extend_schema(tags=["targets"])
class WatchTargetViewSet(viewsets.ModelViewSet):
    """CRUD for watch targets, plus pause/resume.

    Targets are addressed by their stable ``uuid`` rather than the numeric PK.
    """

    serializer_class = WatchTargetSerializer
    lookup_field = "uuid"
    lookup_value_regex = "[0-9a-f-]{36}"

    filterset_fields = ["status", "vertical", "fetch_strategy"]
    search_fields = ["name", "url", "description"]
    ordering_fields = [
        "name",
        "created_at",
        "updated_at",
        "last_checked_at",
        "check_interval_minutes",
    ]
    ordering = ["name"]

    def get_queryset(self):
        return WatchTarget.objects.annotate(
            snapshots_count=Count("snapshots", distinct=True),
            changes_count=Count("changes", distinct=True),
            open_alerts_count=Count(
                "alerts",
                filter=Q(alerts__status=AlertStatus.NEW),
                distinct=True,
            ),
        )

    def _set_status(self, request: Request, new_status: str) -> Response:
        target = self.get_object()
        target.status = new_status
        target.status_note = ""
        target.save(update_fields=["status", "status_note", "updated_at"])
        return Response(self.get_serializer(target).data, status=http_status.HTTP_200_OK)

    @extend_schema(request=None, responses=WatchTargetSerializer)
    @action(detail=True, methods=["post"])
    def pause(self, request: Request, uuid: str | None = None) -> Response:
        return self._set_status(request, TargetStatus.PAUSED)

    @extend_schema(request=None, responses=WatchTargetSerializer)
    @action(detail=True, methods=["post"])
    def resume(self, request: Request, uuid: str | None = None) -> Response:
        return self._set_status(request, TargetStatus.ACTIVE)


@extend_schema(tags=["changes"])
class ChangeViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to detected changes (powers the timeline + diff viewer)."""

    serializer_class = ChangeSerializer
    queryset = Change.objects.select_related(
        "target", "previous_snapshot", "current_snapshot"
    ).all()
    filterset_fields = [
        "target__uuid",
        "is_meaningful",
        "severity",
        "change_type",
        "detection_method",
    ]
    search_fields = ["summary", "why_it_matters"]
    ordering_fields = ["detected_at", "severity", "significance_score"]
    ordering = ["-detected_at"]
