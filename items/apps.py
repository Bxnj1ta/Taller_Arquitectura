from django.apps import AppConfig


class ItemsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "items"

    def ready(self):
        from . import kernel, plugins
        if not hasattr(kernel, 'K'):
            kernel.K = kernel.Kernel()
            kernel.K.discover_and_load(plugins)
