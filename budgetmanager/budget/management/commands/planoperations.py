from django.core.management.base import BaseCommand, CommandError

from budget.models import OperationPlan
from budget.utils import today

class Command(BaseCommand):
    help = 'Creates all operations from plans that are due.'

    def handle(self, *args, **options):
        counter = 0
        qset = OperationPlan.objects.filter(next_date__lte=today())

        for plan in qset:
            try:
                while plan.is_due():
                    plan.create_operation()
                    counter += 1
            except:
                self.stderr.write(self.style.ERROR(
                    f'Error creating operation from plan id: {plan.id}.'))

        self.stdout.write(self.style.SUCCESS(
            f'Created {counter} operation(s) from {qset.count()} plans.'))
