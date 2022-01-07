from django.apps import AppConfig

class BudgetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'budget'

    initialized = False

    def ready(self):
        from .jobs import register_jobs

        if not self.initialized:
            # TODO
            #register_jobs(8)
            self.initialized = True