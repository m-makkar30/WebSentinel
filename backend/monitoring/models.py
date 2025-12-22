"""Core domain models for WebSentinel.

The pipeline these model:

    WatchTarget  -- a URL + "what to watch" the user registers
      └─ Snapshot   -- one fetch result (raw + extracted + content hash)
           └─ Change   -- a detected diff between two snapshots
                └─ Alert  -- a surfaced, plain-language notification

The pgvector embedding used by the semantic-diff layer is added to Snapshot in
a later commit, when that feature lands; these models are purely relational.
"""

from __future__ import annotations

import uuid

from django.db import models


# --- Enums --------------------------------------------------------------------
class Vertical(models.TextChoices):
    PRICING = "pricing", "Pricing / competitive"
    COMPLIANCE = "compliance", "Compliance / legal"
    REGULATORY = "regulatory", "Regulatory / government"
    STATUS = "status", "Status / uptime"
    DOCS = "docs", "Docs / changelog"
    GENERIC = "generic", "Generic"


class TargetStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    BLOCKED = "blocked", "Blocked"
    ERROR = "error", "Error"


class FetchStrategy(models.TextChoices):
    AUTO = "auto", "Auto (API/feed first, then browser)"
    API = "api", "API / feed only"
    BROWSER = "browser", "Browser render only"


class FetchMethod(models.TextChoices):
    API = "api", "API / feed"
    HTTP = "http", "Plain HTTP"
    BROWSER = "browser", "Browser render"


class Severity(models.TextChoices):
    INFO = "info", "Info"
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class DetectionMethod(models.TextChoices):
    NAIVE = "naive", "Naive (raw diff)"
    SEMANTIC = "semantic", "Semantic (field + embedding)"


class ChangeType(models.TextChoices):
    CONTENT = "content", "Content"
    PRICE = "price", "Price"
    AVAILABILITY = "availability", "Availability"
    CLAUSE = "clause", "Clause / policy"
    STATUS = "status", "Status"
    STRUCTURE = "structure", "Structure"
    OTHER = "other", "Other"


class AlertKind(models.TextChoices):
    CHANGE = "change", "Meaningful change"
    BLOCKED = "blocked", "Target blocked"
    ERROR = "error", "Fetch/processing error"
    INFO = "info", "Informational"


class AlertStatus(models.TextChoices):
    NEW = "new", "New"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    RESOLVED = "resolved", "Resolved"


# --- Abstract base ------------------------------------------------------------
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# --- Models -------------------------------------------------------------------
class WatchTarget(TimeStampedModel):
    """A page the user wants watched, plus what they care about on it."""

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=200)
    url = models.URLField(max_length=1000)
    description = models.TextField(blank=True)

    vertical = models.CharField(max_length=20, choices=Vertical.choices, default=Vertical.GENERIC)
    # Natural-language description of what to watch (drives LLM extraction).
    watch_instructions = models.TextField(blank=True)
    # Typed fields to extract, e.g. {"price": "number", "in_stock": "boolean"}.
    extraction_schema = models.JSONField(default=dict, blank=True)

    fetch_strategy = models.CharField(
        max_length=10, choices=FetchStrategy.choices, default=FetchStrategy.AUTO
    )
    check_interval_minutes = models.PositiveIntegerField(default=1440)  # daily

    status = models.CharField(
        max_length=10, choices=TargetStatus.choices, default=TargetStatus.ACTIVE
    )
    status_note = models.CharField(max_length=500, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.url})"


class Snapshot(models.Model):
    """One fetch of a target at a point in time. Immutable once written."""

    target = models.ForeignKey(WatchTarget, on_delete=models.CASCADE, related_name="snapshots")
    fetched_at = models.DateTimeField(db_index=True)

    fetch_method = models.CharField(
        max_length=10, choices=FetchMethod.choices, default=FetchMethod.HTTP
    )
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    ok = models.BooleanField(default=True)
    blocked = models.BooleanField(default=False)
    status_note = models.TextField(blank=True)

    # Raw fetched body, normalized readable text, and a hash for skip-unchanged.
    raw_content = models.TextField(blank=True)
    content_text = models.TextField(blank=True)
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)

    # Structured fields pulled out per the target's extraction schema.
    extracted = models.JSONField(default=dict, blank=True)

    screenshot_path = models.CharField(max_length=500, blank=True)
    fetch_duration_ms = models.PositiveIntegerField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-fetched_at"]
        indexes = [
            models.Index(fields=["target", "-fetched_at"]),
            models.Index(fields=["target", "content_hash"]),
        ]

    def __str__(self) -> str:
        return f"Snapshot<{self.target_id}@{self.fetched_at:%Y-%m-%d %H:%M}>"


class Change(TimeStampedModel):
    """A detected change between two snapshots of the same target."""

    target = models.ForeignKey(WatchTarget, on_delete=models.CASCADE, related_name="changes")
    previous_snapshot = models.ForeignKey(
        Snapshot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="changes_as_previous",
    )
    current_snapshot = models.ForeignKey(
        Snapshot, on_delete=models.CASCADE, related_name="changes_as_current"
    )
    detected_at = models.DateTimeField(db_index=True)

    detection_method = models.CharField(
        max_length=10, choices=DetectionMethod.choices, default=DetectionMethod.SEMANTIC
    )
    change_type = models.CharField(
        max_length=20, choices=ChangeType.choices, default=ChangeType.CONTENT
    )

    # Noise suppression + impact assessment.
    is_meaningful = models.BooleanField(default=False)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.INFO)
    significance_score = models.FloatField(null=True, blank=True)

    # Plain-language outputs (the assessment LLM fills these in a later commit).
    summary = models.TextField(blank=True)
    why_it_matters = models.TextField(blank=True)

    # Structured + textual diffs.
    field_diffs = models.JSONField(default=list, blank=True)
    text_diff = models.TextField(blank=True)

    # For collapsing repeated identical changes.
    dedup_hash = models.CharField(max_length=64, blank=True, db_index=True)

    class Meta:
        ordering = ["-detected_at"]
        indexes = [
            models.Index(fields=["target", "-detected_at"]),
            models.Index(fields=["is_meaningful", "severity"]),
        ]

    def __str__(self) -> str:
        return f"Change<{self.target_id} {self.change_type} {self.severity}>"


class Alert(TimeStampedModel):
    """A surfaced notification. Usually tied to a meaningful Change, but may be
    informational (e.g. a target became blocked)."""

    target = models.ForeignKey(WatchTarget, on_delete=models.CASCADE, related_name="alerts")
    change = models.ForeignKey(
        Change,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alerts",
    )

    kind = models.CharField(max_length=10, choices=AlertKind.choices, default=AlertKind.CHANGE)
    level = models.CharField(max_length=10, choices=Severity.choices, default=Severity.INFO)
    title = models.CharField(max_length=300)
    body = models.TextField(blank=True)

    status = models.CharField(max_length=12, choices=AlertStatus.choices, default=AlertStatus.NEW)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["target", "-created_at"]),
            models.Index(fields=["status", "level"]),
        ]

    def __str__(self) -> str:
        return f"Alert<{self.kind} {self.level}: {self.title}>"
