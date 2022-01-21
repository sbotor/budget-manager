import time
from django.test import TestCase
from django.utils import timezone
from django.db.utils import Error, IntegrityError
from django.contrib.auth.models import User
from django.core.management import call_command

# Create your tests here.
from django.test import TestCase
from .models import *
from .utils import today

from freezegun import freeze_time


class PlanCommandTest(TestCase):

    def setUp(self):
        self.initial_date = today()
        self.dates = {
            'D': self.initial_date + timedelta(days=1),
            'W': self.initial_date + timedelta(days=7),
            'M': self.initial_date + timedelta(days=30),
            'Y': self.initial_date + timedelta(days=365)
        }

        user1 = User(username='user1', password='asdfzxcv1234')
        user1.save()
        Home.create_home(home_name='home1', user=user1)
        plan1 = OperationPlan(account=user1.account, amount=1,
                              period='D', period_count=1, next_date=self.dates['D'])
        plan1.save()

        user2 = User(username='user2', password='asdfzxcv1234')
        user2.save()
        Home.create_home(home_name='home2', user=user2)
        plan2 = OperationPlan(account=user2.account, amount=2,
                              period='M', period_count=1, next_date=self.dates['M'])
        plan2.save()

    def test_plan_command_two_due(self):
        with freeze_time(self.dates['M']) as frozen_datetime:
            call_command('planoperations')

            acc1 = User.objects.get(username='user1').account
            plan1 = OperationPlan.objects.get(account=acc1)
            ops1 = Operation.objects.filter(account=acc1)

            self.assertEqual(ops1.count(), 30,
                             'Wrong operation count for user1.')
            self.assertEqual(ops1.first().amount, plan1.amount,
                             'Amounts for user1 not equal.')
            self.assertEqual(
                plan1.next_date, self.dates['M'] + timedelta(days=1), 'Wrong next_date for user1.')

            acc2 = User.objects.get(username='user2').account
            plan2 = OperationPlan.objects.get(account=acc2)
            ops2 = Operation.objects.filter(account=acc2)

            self.assertEqual(
                ops2.count(), 1, 'Wrong operation count for user2.')
            self.assertEqual(ops2.first().amount, plan2.amount,
                             'Amounts for user2 not equal.')
            self.assertEqual(
                plan2.next_date, self.dates['M'] + timedelta(days=30), 'Wrong next_date for user2.')

    def test_plan_command_one_due(self):
        with freeze_time(self.dates['D'] + timedelta(days=7)) as frozen_datetime:
            call_command('planoperations')

            acc1 = User.objects.get(username='user1').account
            plan1 = OperationPlan.objects.get(account=acc1)
            ops1 = Operation.objects.filter(account=acc1)

            self.assertEqual(
                ops1.count(), 8, 'Wrong operation count for user1.')
            self.assertEqual(ops1.first().amount, plan1.amount,
                             'Amounts for user1 not equal.')
            self.assertEqual(
                plan1.next_date, self.dates['D'] + timedelta(days=8), 'Wrong next_date for user1.')

            acc2 = User.objects.get(username='user2').account
            plan2 = OperationPlan.objects.get(account=acc2)
            ops2 = Operation.objects.filter(account=acc2)

            self.assertEqual(
                ops2.count(), 0, 'Wrong operation count for user2.')
            #self.assertEqual(ops2.first().amount, plan2.amount, 'Amounts for user2 not equal.')
            self.assertEqual(
                plan2.next_date, self.dates['M'], 'Wrong next_date for user2.')
