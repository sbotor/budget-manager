from django.apps import AppConfig

class BudgetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'budget'

    initialized = False

    def ready(self):
        from .jobs import OperationPlanner

        if not self.initialized:
            # TODO
            planner = OperationPlanner(thread_count=8)
            #planner.start()
            self.initialized = True