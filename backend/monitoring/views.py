from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status as http_status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from llm.models import LLMUsage

from .models import Alert, AlertStatus, Change, TargetStatus, WatchTarget
from .serializers import AlertSerializer, ChangeSerializer, WatchTargetSerializer


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


@extend_schema(tags=["alerts"])
class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only alerts feed with acknowledge/resolve actions."""

    serializer_class = AlertSerializer
    queryset = Alert.objects.select_related("target").all()
    filterset_fields = ["status", "level", "kind", "target__uuid"]
    search_fields = ["title", "body"]
    ordering_fields = ["created_at", "level"]
    ordering = ["-created_at"]

    def _set_status(self, new_status: str, *, acked: bool) -> Response:
        alert = self.get_object()
        alert.status = new_status
        if acked and alert.acknowledged_at is None:
            alert.acknowledged_at = timezone.now()
        alert.save(update_fields=["status", "acknowledged_at", "updated_at"])
        return Response(self.get_serializer(alert).data, status=http_status.HTTP_200_OK)

    @extend_schema(request=None, responses=AlertSerializer)
    @action(detail=True, methods=["post"])
    def acknowledge(self, request: Request, pk: str | None = None) -> Response:
        return self._set_status(AlertStatus.ACKNOWLEDGED, acked=True)

    @extend_schema(request=None, responses=AlertSerializer)
    @action(detail=True, methods=["post"])
    def resolve(self, request: Request, pk: str | None = None) -> Response:
        return self._set_status(AlertStatus.RESOLVED, acked=True)


@extend_schema(tags=["stats"], responses=OpenApiTypes.OBJECT)
class StatsView(APIView):
    """Aggregated dashboard stats: targets, change trend, alerts, and LLM cost."""

    def get(self, request: Request) -> Response:
        targets = WatchTarget.objects.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(status=TargetStatus.ACTIVE)),
            paused=Count("id", filter=Q(status=TargetStatus.PAUSED)),
            blocked=Count("id", filter=Q(status=TargetStatus.BLOCKED)),
            error=Count("id", filter=Q(status=TargetStatus.ERROR)),
        )

        changes_total = Change.objects.count()
        meaningful = Change.objects.filter(is_meaningful=True).count()

        since = timezone.now() - timedelta(days=7)
        trend_rows = (
            Change.objects.filter(detected_at__gte=since)
            .annotate(day=TruncDate("detected_at"))
            .values("day")
            .annotate(
                meaningful=Count("id", filter=Q(is_meaningful=True)),
                noise=Count("id", filter=Q(is_meaningful=False)),
            )
            .order_by("day")
        )
        trend = [
            {"date": str(r["day"]), "meaningful": r["meaningful"], "noise": r["noise"]}
            for r in trend_rows
        ]

        alerts_by_level = {
            r["level"]: r["n"] for r in Alert.objects.values("level").annotate(n=Count("id"))
        }

        llm_totals = LLMUsage.objects.aggregate(
            calls=Count("id"), tokens=Sum("total_tokens"), cost=Sum("cost_usd")
        )
        llm_by_op = [
            {
                "operation": r["operation"],
                "calls": r["n"],
                "tokens": r["t"] or 0,
                "cost_usd": float(r["c"] or 0),
            }
            for r in LLMUsage.objects.values("operation").annotate(
                n=Count("id"), t=Sum("total_tokens"), c=Sum("cost_usd")
            )
        ]

        return Response(
            {
                "targets": targets,
                "changes": {
                    "total": changes_total,
                    "meaningful": meaningful,
                    "noise": changes_total - meaningful,
                    "trend": trend,
                },
                "alerts": {
                    "total": Alert.objects.count(),
                    "open": Alert.objects.filter(status=AlertStatus.NEW).count(),
                    "by_level": alerts_by_level,
                },
                "llm": {
                    "calls": llm_totals["calls"] or 0,
                    "tokens": llm_totals["tokens"] or 0,
                    "cost_usd": float(llm_totals["cost"] or 0),
                    "by_operation": llm_by_op,
                },
            }
        )
