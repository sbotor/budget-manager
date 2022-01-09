import os
from django.core.management.base import BaseCommand, CommandError
from budgetmanager.settings import BASE_DIR
from django.db import connection
import shutil
from os.path import isfile

class Command(BaseCommand):
    help = 'Command removing the database files including migrations.'

    def handle(self, *args, **options):
        
        empty = True
        self.stdout.write(self.style.NOTICE('Clearing database.'))
        
        try:
            db_path = BASE_DIR / connection.settings_dict['NAME']
            os.remove(db_path)
            self.stdout.write(f'Removed database {db_path}.')
            empty = False
        except FileNotFoundError:
            pass
        
        pth = BASE_DIR / 'budget' / 'migrations'
        file_list = [item for item in os.listdir(pth) if isfile(pth / item) and item != '__init__.py']

        for item in file_list:
            try:
                item_path = pth / item
                os.remove(item_path)
                self.stdout.write(f'Removed migration file {item_path}.')
                empty = False
            except FileNotFoundError:
                pass

        try:
            shutil.rmtree(pth / '__pycache__')
            self.stdout.write('Removed migration pycache.')
            empty = False
        except FileNotFoundError:
            pass

        if empty:
            self.stdout.write(self.style.SUCCESS('Nothing to clear.'))
        else:
            self.stdout.write(self.style.SUCCESS('DB cleared.'))
    