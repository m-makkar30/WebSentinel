from django.contrib import admin

from .models import LLMUsage


@admin.register(LLMUsage)
class LLMUsageAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "operation",
        "model",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "cost_usd",
        "target",
    )
    list_filter = ("operation", "model")
    search_fields = ("model", "operation", "target__name")
    date_hierarchy = "created_at"
    readonly_fields = tuple(f.name for f in LLMUsage._meta.fields)
