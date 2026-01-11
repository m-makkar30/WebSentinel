from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Change, Snapshot, WatchTarget


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


class SnapshotMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Snapshot
        fields = [
            "id",
            "fetched_at",
            "fetch_method",
            "http_status",
            "screenshot_path",
            "content_hash",
        ]


class ChangeSerializer(serializers.ModelSerializer):
    target = serializers.UUIDField(source="target.uuid", read_only=True)
    target_name = serializers.CharField(source="target.name", read_only=True)
    previous_snapshot = SnapshotMiniSerializer(read_only=True)
    current_snapshot = SnapshotMiniSerializer(read_only=True)

    class Meta:
        model = Change
        fields = [
            "id",
            "target",
            "target_name",
            "detection_method",
            "change_type",
            "is_meaningful",
            "severity",
            "significance_score",
            "summary",
            "why_it_matters",
            "field_diffs",
            "text_diff",
            "detected_at",
            "previous_snapshot",
            "current_snapshot",
            "created_at",
        ]
