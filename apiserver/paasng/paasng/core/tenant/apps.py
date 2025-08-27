from django.apps import AppConfig


class TenantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "paasng.core.tenant"

    def ready(self):
        # Register the Django check function
        from .sys_check import check_model_multi_tenancy_configured  # noqa: F401
