from django.test import TestCase
from .models import Home, Account, Label, Operation

# Create your tests here.
class TestDB(TestCase):
    def setUp(self):
        home = Home(name='Home 1')
        home.save()

        account1 = Account(name='User 1', home=home)
        account1.save()
        Label.objects.create(name='Label H1', home=home)
        Label.objects.create(name='Label H2', home=home)
        Label.objects.create(name='Label A1.1 (account)', home=home, account=account1)
        
        account2 = Account(name='User 2', home=home)
        account2.save()
        Label.objects.create(name='Label H3', home=home)
        Label.objects.create(name='Label H4', home=home)
        Label.objects.create(name='Label A2.1', home=home, account=account2)
        
        account3 = Account(name='User 3', home=home)
        account3.save()
        Label.objects.create(name='Label H5', home=home)
        Label.objects.create(name='Label A3.1', home=home, account=account3)
        Label.objects.create(name='Label A2.2', home=home, account=account3)

        Operation.objects.create(account=account1,
                                    label=Label.objects.filter(home=home, name='Label H3').get(),
                                    amount = 10)
        

    def testSimpleCreation(self):
        try:
            print(Operation.objects.all())
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.fail()