from django.db import models


class LLMUsage(models.Model):
    """One LLM call's token + cost accounting (powers the cost panel/metrics)."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    operation = models.CharField(max_length=40)  # extract | assess | embed | ...
    model = models.CharField(max_length=120)

    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)

    target = models.ForeignKey(
        "monitoring.WatchTarget",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="llm_usage",
    )
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["operation", "-created_at"])]

    def __str__(self) -> str:
        return f"LLMUsage<{self.operation} {self.model} {self.total_tokens}tok ${self.cost_usd}>"
