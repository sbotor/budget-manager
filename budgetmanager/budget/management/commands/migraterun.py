from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.core.management import call_command

from budget.models import OperationPlan

class Command(BaseCommand):
    help = 'Creates all operations from plans that are due.'

    def handle(self, *args, **options):
        call_command('makemigrations')
        call_command('migrate')
        call_command('runserver')
    