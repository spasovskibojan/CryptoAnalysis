from django.apps import AppConfig
import threading


class WebConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'web'
    
    def ready(self):
        """
        Called when Django starts up.
        Wake TA/FA services in background thread so all services are ready together.
        """
        # Only run in main process, not in reloader process
        import os
        if os.environ.get('RUN_MAIN') != 'true':
            # This is the reloader process, skip
            return
            
        # Import here to avoid circular imports
        from .facade import wake_up_services
        
        def wake_services_async():
            print("DEBUG: Django startup - waking TA/FA services in background...")
            wake_up_services()
            print("DEBUG: Background service wake-up complete!")
        
        # Start wake-up in background thread (non-blocking)
        thread = threading.Thread(target=wake_services_async, daemon=True)
        thread.start()
        print("DEBUG: Django ready - service wake-up started in background")
