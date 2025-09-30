from django.apps import AppConfig


class RifaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rifa'
    
    def ready(self):
        import rifa.signals