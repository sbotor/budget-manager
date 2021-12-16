from django.test import TestCase
from django.utils import timezone
from django.db.utils import IntegrityError

# Create your tests here.
from django.test import TestCase
from .models import Home, Account, Label, Operation


class TestHome(TestCase):
    """This probably does not work. Do not use until fixed."""
    
    def test_create_home(self):
        """Checks if home and admin creation is correct."""

        # Given
        home = Home.create_home('home1', 'admin_home1')

        # When
        home.save()
        created_home = Home.objects.all().get()
        created_admin = created_home.admin
        created_user = Account.objects.all().get()

        # Then
        self.assertEqual(created_home, home, "Home objects are not equal.")
        self.assertEqual(created_admin, created_user, "The admin and user are not equal.")

    def test_add_account(self):
        """Checks if creating and adding a new non-duplicate account is correct."""

        # Given
        home = Home.create_home('home1', 'admin_home1')

        # When
        home.save()
        added_account = home.add_account('added_account')

        # Then
        expected_account = Account(id=2, name='added_account', home=home)
        self.assertEqual(expected_account, added_account, 'The accounts are not equal.')

    def test_add_duplicate_account(self):
        """Checks if creating and adding a new duplicate account is correct."""

        # Given
        home = Home.create_home('home1', 'admin_home1')

        # When
        home.save()
        home.add_account('added_account')

        # Then
        self.assertIsNone(home.add_account('added_account'))
