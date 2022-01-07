import time
from django.test import TestCase
from django.utils import timezone
from django.db.utils import Error, IntegrityError
from django.contrib.auth.models import User

# Create your tests here.
from django.test import TestCase
from .models import *
from .jobs import OperationPlanner

from freezegun import freeze_time

class OperationPlannerTest(TestCase):

    def setUp(self):
        user1 = User(username='user1', password='asdfzxcv1234')
        user1.save()
        Home.create_home(home_name='home1', user=user1)
        plan1 = OperationPlan(account=user1.account, amount=1, period='D', period_count=1)
        plan1.save()

        user1.account.plan_operation
        
        user2 = User(username='user2', password='asdfzxcv1234')
        user2.save()
        Home.create_home(home_name='home2', user=user2)
        plan2 = OperationPlan(account=user2.account, amount=2, period='M', period_count=1)
        plan2.save()

        self.initial_date = timezone.now().date()
        self.dates = {
            'D': self.initial_date + timedelta(days=1),
            'W': self.initial_date + timedelta(days=7),
            'M': self.initial_date + timedelta(days=30),
            'Y': self.initial_date + timedelta(days=365)
        }

    def test_operation_planning_once(self):
        with freeze_time(self.dates['M'], tick=True) as frozen_datetime:

            print(timezone.now())
            try:
                self.planner = OperationPlanner(thread_count=1,sleep_time=0.1, time_str='00:00:01')
                self.planner.start()

                time.sleep(3)

                acc1 = User.objects.get(username='user1').account
                op1 = Operation.objects.get(account=acc1)
                plan1 = OperationPlan.objects.get(account=acc1)

                #self.assertEqual(op1.amount, plan1.amount, 'Amounts for user1 not equal.')
                self.assertEqual(plan1.next_date, self.dates['D'].date(), 'Wrong next_date for user1.')

                acc2 = User.objects.get(username='user2').account
                #op2 = Operation.objects.get(account_id=acc2.id)
                plan2 = OperationPlan.objects.get(account=acc2)

                #self.assertEqual(op2.amount, plan2.amount, 'Amounts for user1 not equal.')
                self.assertEqual(plan2.next_date, self.dates['M'].date(), 'Wrong next_date for user2.')
            except Error as e:
                print(e)
            finally:
                self.planner.stop()