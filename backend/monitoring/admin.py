from django.contrib import admin

from .models import Alert, Change, Snapshot, WatchTarget


@admin.register(WatchTarget)
class WatchTargetAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "vertical", "fetch_strategy", "status", "last_checked_at")
    list_filter = ("status", "vertical", "fetch_strategy")
    search_fields = ("name", "url", "description")
    readonly_fields = ("uuid", "created_at", "updated_at", "last_checked_at")


@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "target", "fetched_at", "fetch_method", "http_status", "ok", "blocked")
    list_filter = ("fetch_method", "ok", "blocked")
    search_fields = ("target__name", "content_hash")
    date_hierarchy = "fetched_at"
    readonly_fields = ("content_hash",)
    autocomplete_fields = ("target",)


@admin.register(Change)
class ChangeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "target",
        "change_type",
        "detection_method",
        "is_meaningful",
        "severity",
        "significance_score",
        "detected_at",
    )
    list_filter = ("is_meaningful", "severity", "change_type", "detection_method")
    search_fields = ("target__name", "summary", "why_it_matters")
    date_hierarchy = "detected_at"
    autocomplete_fields = ("target", "previous_snapshot", "current_snapshot")


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("id", "target", "kind", "level", "title", "status", "created_at")
    list_filter = ("kind", "level", "status")
    search_fields = ("target__name", "title", "body")
    date_hierarchy = "created_at"
    autocomplete_fields = ("target", "change")
