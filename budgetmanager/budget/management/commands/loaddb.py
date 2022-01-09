from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Convenience command for migrating the DB.'

    def add_arguments(self, parser):
        
        parser.add_argument(
            '-c', '--clear',
            action='store_true',
            help='Clear the previous database before migrating.'
        )

    def handle(self, *args, **options):
        
        if options['clear']:
            call_command('cleardb')

        call_command('makemigrations')
        call_command('migrate')
    