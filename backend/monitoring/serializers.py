from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import WatchTarget


class WatchTargetSerializer(serializers.ModelSerializer):
    # Convenience counts for the dashboard. Sourced from queryset annotations
    # when present (see WatchTargetViewSet.get_queryset); fall back to a live
    # count for freshly created/updated instances that lack the annotation.
    snapshots_count = serializers.SerializerMethodField()
    changes_count = serializers.SerializerMethodField()
    open_alerts_count = serializers.SerializerMethodField()

    class Meta:
        model = WatchTarget
        fields = [
            "id",
            "uuid",
            "name",
            "url",
            "description",
            "vertical",
            "watch_instructions",
            "extraction_schema",
            "fetch_strategy",
            "check_interval_minutes",
            "status",
            "status_note",
            "last_checked_at",
            "created_at",
            "updated_at",
            "snapshots_count",
            "changes_count",
            "open_alerts_count",
        ]
        # status/status_note are system-managed (see pause/resume actions and
        # the fetch pipeline); the rest are immutable metadata.
        read_only_fields = [
            "uuid",
            "status",
            "status_note",
            "last_checked_at",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(int)
    def get_snapshots_count(self, obj: WatchTarget) -> int:
        value = getattr(obj, "snapshots_count", None)
        return value if value is not None else obj.snapshots.count()

    @extend_schema_field(int)
    def get_changes_count(self, obj: WatchTarget) -> int:
        value = getattr(obj, "changes_count", None)
        return value if value is not None else obj.changes.count()

    @extend_schema_field(int)
    def get_open_alerts_count(self, obj: WatchTarget) -> int:
        value = getattr(obj, "open_alerts_count", None)
        return value if value is not None else obj.alerts.filter(status="new").count()

    def validate_check_interval_minutes(self, value: int) -> int:
        # Monitoring is naturally low-frequency; keep it polite (see fetch
        # doctrine). 5 minutes is the floor.
        if value < 5:
            raise serializers.ValidationError("Must be at least 5 minutes (be polite to targets).")
        return value

    def validate_extraction_schema(self, value: object) -> object:
        if not isinstance(value, dict):
            raise serializers.ValidationError('Must be a JSON object, e.g. {"price": "number"}.')
        return value
