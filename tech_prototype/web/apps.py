from django.apps import AppConfig


class WebConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'web'
    
    def ready(self):
        """
        Called when Django starts up.
        Note: Service wake-up is now handled on first request via wake_up_services()
        in facade.py with global state tracking. This ensures services are ready
        when the user first loads the homepage.
        """
        pass  # Wake-up handled in views.py on first request
