from datetime import date, datetime, timedelta
from django.db import models, IntegrityError, transaction
from django.db.models.query_utils import Q
from django.contrib.auth.models import Permission, Group, User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator
import decimal

from .utils import today

ADMIN_GROUP = 'home_admin'
"""Home admin group name."""

MOD_GROUP = 'moderator'
"""Home moderator group name."""

BASE_MOD_PERMS = {
    ('manage_home_labels', 'Manage home labels'),
    ('make_transactions', 'Send money to another user'),
}
"""Base mod permissions codenames."""

MOD_PERMS = {
    ('plan_for_others', 'Plan operations for other users'),
    ('manage_users', 'Manage other users'),
}
"""Additional mod permissions codenames. Can be granted in addition to the base ones."""

BASE_ADMIN_PERMS = {
    *BASE_MOD_PERMS,
    *MOD_PERMS,

    ('manage_home', 'Manage the Home'),
    ('make_home_admin', 'Pass the admin role to another user'),
    ('make_mod', 'Grant Moderator permissions')
}
"""Base admin permissions codenames."""

USER_PERMS = {
    ('make_transactions', 'Send money to another user')
}
"""Additional regular user permissions."""


class ConvenienceModel(models.Model):
    """Class implementing convenience methods common to all models."""

    class Meta:
        abstract = True

    def is_saved(self):
        """Checks if the model exists in the database."""

        return not self._state.adding


class Home(ConvenienceModel):
    """Home model used for account grouping."""

    class Meta:
        permissions = {
            ('manage_home', 'Can manage the entire Home.'),
            ('make_home_admin', 'Can make a user a home admin.'),
            ('make_mod', 'Can make a user a moderator.'),
        }

    class Currency(models.TextChoices):
        """Enum class for the currency that the home uses."""

        USD = '$', 'USD'
        GBP = '£', 'GBP'
        EUR = '€', 'EUR'
        PLN = 'zł', 'PLN'

    name = models.CharField(max_length=50, verbose_name='Home name')
    """Home name."""

    admin = models.OneToOneField(
        'Account', null=True, on_delete=models.RESTRICT, related_name='+')
    """The Home's Administrator account.
    Null value is possible, but should only occur during home creation.
    It has no backward relation to the Home object as it can be obtained via the regular Account.home field.
    """

    currency = models.CharField(
        choices=Currency.choices, max_length=5, verbose_name='Home currency')
    """Home currency for all Accounts."""

    MAX_ACCOUNTS = 12
    """Maximum number of users in one Home."""

    MAX_LABELS = 10
    """Maximum number of non-default labels that can be created for a Home."""

    def __str__(self):
        return self.name

    @staticmethod
    def create_home(home_name: str, user: User, currency: str):
        """The method used to create a new home and add the administrator User passed as a parameter."""

        home = Home(name=home_name, currency=currency)
        admin = Account(user=user, home=home)
        home.save()
        home.change_admin(admin)

        home.create_predefined_labels()
        home.save()

        return home

    def remove(self):
        """Removes the entire home including all Operations and accounts."""

        accounts = Account.objects.filter(home=self)

        for acc in accounts:
            if acc != self.admin:
                acc.delete()
            else:
                self.admin = None
                self.save()
                acc.delete()
        
        self.delete()

    def get_labels(self, home_only: bool = False):
        """Return all the labels available to the Home excluding global labels.

        If `home_only` is False no personal labels are returned.
        """

        queryset = Label.objects.filter(home=self)
        if home_only:
            queryset = queryset.filter(account=None)

        return queryset

    def add_label(self, label: 'Label', commit: bool = True):
        """Add a new personal home to the database. Returns the newly added Label or None if unsuccessful.

        If `commit` is False the label is not saved to the database.
        """

        label.account = None
        label.home = self

        if not label._check_unique_name():
            return None

        if commit:
            label.save()

        return label

    def create_predefined_labels(self, keep_custom: bool = True):
        """Creates a set of predefined labels. If a default label exists it is not created again."""

        if not keep_custom:
            custom = self.get_labels(home_only=True)
            for label in custom:
                label.delete()

        for name in Label.DEFAULT_LABELS:
            Label.objects.get_or_create(name=name, home=self, is_default=True)

    def change_admin(self, account: 'Account'):
        """Changes the Home Admin removing the old one if present. Also grants Moderator permissions."""

        group, created = Group.objects.get_or_create(name=ADMIN_GROUP)
        if created:
            Home._setup_admin_group(group)

        prev_admin = self.admin
        if prev_admin:
            prev_admin.user.groups.remove(group)
            prev_admin.user.save()
            self.admin = None
            self.save()

        account.user.groups.add(group)
        self.add_mod(account, commit=False)
        account.user.save()
        account.save()

        self.admin = account
        self.save()

    def add_mod(self, account: 'Account', commit: bool = True):
        """Adds a Home moderator."""

        group, created = Group.objects.get_or_create(name=MOD_GROUP)
        if created:
            Home._setup_mod_group(group)

        account.user.groups.add(group)

        if commit:
            account.user.save()

    def remove_mod(self, account: 'Account', commit: bool = True):
        """Removes the Moderator role from the Account if exists. Clears additional permissions.
        Saves the Account instance if `commit` is True.
        """

        group = Group.objects.get(name=MOD_GROUP)

        if account.is_mod():
            account.user.groups.remove(group)

        account.user.user_permissions.clear()

        if commit:
            account.user.save()

    @staticmethod
    def _setup_admin_group(group: Group):
        """Sets up the Home Admin group permissions."""

        admin_perms = [Permission.objects.get_or_create(
            codename=perm[0])[0] for perm in BASE_ADMIN_PERMS]

        group.permissions.add(*admin_perms)
        group.save()

    @staticmethod
    def _setup_mod_group(group: Group):
        """Sets up the Home Moderator group permissions."""

        mod_perms = [Permission.objects.get_or_create(
            codename=perm[0])[0] for perm in BASE_MOD_PERMS]

        group.permissions.add(*mod_perms)
        group.save()


class Account(ConvenienceModel):
    """The model of the user account."""

    class Meta:
        permissions = {
            ('manage_users', 'Can manage user accounts.'),
        }

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, verbose_name="User")
    """User model object bound to the account."""

    home = models.ForeignKey(
        Home, on_delete=models.CASCADE, verbose_name='Home')
    """Home that the account belongs to."""

    MAX_AMOUNT = decimal.Decimal('999999.99')
    """Maximum value for an Account's amount."""

    current_amount = models.DecimalField(
        decimal_places=2, max_digits=8, default=0.0, verbose_name='Current amount of money')
    """Current amount of money that the account has."""

    final_amount = models.DecimalField(
        decimal_places=2, max_digits=8, default=0.0, verbose_name='Final amount of money')
    """Amount of money after all the operations are finalized."""

    MAX_LABELS = 6
    """Maximum number of labels that can be created for a user."""

    def __str__(self):
        return self.user.username

    def save(self, force_insert: bool = False, force_update: bool = False, using=None, update_fields=None):
        self.user.save()

        try:
            with transaction.atomic():
                super().save(force_insert=force_insert, force_update=force_update,
                     using=using, update_fields=update_fields)
        except decimal.InvalidOperation:
            if self.final_amount > self.MAX_AMOUNT:
                self.final_amount = self.MAX_AMOUNT
            elif self.final_amount < -self.MAX_AMOUNT:
                self.final_amount = -self.MAX_AMOUNT

            if self.current_amount > self.MAX_AMOUNT:
                self.current_amount = self.MAX_AMOUNT
            elif self.current_amount < -self.MAX_AMOUNT:
                self.current_amount = -self.MAX_AMOUNT

            super().save(force_insert=force_insert, force_update=force_update,
                     using=using, update_fields=update_fields)

    def calculate_final(self):
        """Used to calculate the finalized amount of money in the account including finalized operations."""

        operations = Operation.objects.filter(account=self)
        total = 0.0

        for op in operations:
            total += float(op.amount)

        return total

    def get_username(self):
        """Shows the user's username or first name if exists."""

        ret_str = ""

        if self.user.first_name:
            ret_str = f'{self.user.first_name} ({self.user.username})'
        else:
            ret_str = self.user.username

        return ret_str

    def calculate_current(self):
        """Used to calculate the current amount of money excluding unfinalized operations."""

        operations = Operation.objects.filter(
            account=self).exclude(final_date=None)
        total = 0.0

        for op in operations:
            total += float(op.amount)

        return total

    def get_this_year_income(self):
        """Returns this year's income as a list."""

        td = today()
        start_date = date(year=td.year, month=1, day=1)

        operations = Operation.objects.filter(
            account=self).exclude(
                final_date=None).filter(
                    final_date__gte=start_date).filter(
                        final_date__lte=td).filter(
                            amount__gt=0)

        income = [0.0] * 12
        for op in operations:
            income[op.final_date.month - 1] += float(op.amount)

        return income

    def get_this_year_expenses(self):
        """Returns this year's expenses as a list."""

        td = today()
        start_date = date(year=td.year, month=1, day=1)

        operations = Operation.objects.filter(
            account=self).exclude(
                final_date=None).filter(
                    final_date__gte=start_date).filter(
                        final_date__lte=td).filter(
                            amount__lt=0)

        expenses = [0.0] * 12
        for op in operations:
            expenses[op.final_date.month - 1] -= float(op.amount)

        return expenses

    def get_this_month_operations(self):
        """Returns this month's operations."""

        td = today()
        start_date = date(year=td.year, month=td.month, day=1)
        return Operation.objects.filter(
            account=self).exclude(
                final_date=None).filter(
                    final_date__gte=start_date).filter(
                        final_date__lte=td)

    def finalize_operations(self):
        """Finalizes all operations for the account."""

        operations = Operation.objects.filter(
            account=self).filter(final_date=None)

        for op in operations:
            op.finalize()

    def add_to_current(self, amount: float, commit: bool = True):
        """Used to add the specified value to the current account. Return the new `current_amount`.

        If `commit` is False the Account is not saved to the database.
        """

        self.current_amount += amount
        if commit:
            self.save()

        return self.current_amount

    def add_to_final(self, amount: float, commit: bool = True):
        """Used to add the specified value to the final account. Return the new `final_amount`.

        If `commit` is False the Account is not saved to the database.
        """

        self.final_amount += amount
        if commit:
            self.save()

        return self.final_amount

    def available_labels(self, include_home: bool = True):
        """Returns a QuerySet of all the available labels of this Account. 

        If `include_home` is set to False only personal labels are returned.
        """

        if include_home:
            q = Q(home=self.home) & Q(account=None) | Q(account=self)
            return Label.objects.filter(q)
        else:
            return Label.objects.filter(account=self)

    def add_operation(self, operation: 'Operation', commit: bool = True):
        """Add an operation to the account. Returns the newly added Operation.

        If `commit` is False the Account is not saved to the database.
        """

        operation.account = self
        if commit:
            operation.save()

        return operation

    def add_operation_plan(self, plan: 'OperationPlan', commit: bool = True):
        """Adds an operation plan to the account and saves it if `commit` is True."""

        plan.account = self

        if commit:
            plan.save()

        return plan

    def recalculate_amounts(self, commit: bool = True):
        """Recalculates both amounts of money.
        
        If `commit` is False the Account is not saved to the database.
        """

        operations = Operation.objects.filter(account=self)
        final = 0.0
        current = 0.0

        for op in operations:
            amount = float(op.amount)
            if op.final_date:
                current += amount
            final += amount

        self.final_amount = final
        self.current_amount = current

        if commit:
            self.save()
    
    def _update_plans(self):
        """Checks if there are due operation plans for the account and creates operations.

        Returns a tuple of lists: `([plans], [operations])` consisting of the updated plans and created operations.
        The lists can be empty."""

        qset = OperationPlan.objects.filter(
            account=self).filter(next_date__lte=today())
        if not qset:
            return [], []

        plans = []
        ops = []

        for plan in qset:

            while plan.is_due():
                op = plan.create_operation()
                ops.append(op)

            plans.append(plan)

        return plans, ops

    def add_label(self, label: 'Label', commit: bool = True):
        """Add a new personal label to the database. Returns the newly added Label or None if unsuccessful.

        If `commit` is False the label is not saved to the database.
        """

        label.account = self
        label.home = self.home
        
        if not label._check_unique_name():
            return None
        
        if commit:
            label.save()

        return label

    def delete(self, using=None, keep_parents: bool = False):

        user = self.user
        ret_val = super().delete(using=using, keep_parents=keep_parents)
        user.delete()
        return ret_val

    def is_admin(self, home: Home = None):
        """Checks if the Account's User is the Home's Admin.
        If no Home is passed the method checks if the user belongs to the Admin permission group.
        """

        if home:
            return home.admin == self

        return self.user.groups.filter(name=ADMIN_GROUP).exists()

    def is_mod(self, home: Home = None):
        """Checks if the Account's User is the Home's Moderator.
        If no Home is passed the method checks if the user belongs to the Moderator permission group.
        """

        mod = self.user.groups.filter(name=MOD_GROUP).exists()

        if not mod:
            return False

        if Home:
            return Account.objects.filter(home=self.home).filter(id=self.id).exists()
        else:
            return True

    def make_transaction(self, destination: 'Account', amount: float, description: str = None):
        """Creates a transaction composed of two new operations with the specified description.

        The amount is subtracted from the account and added to the destination account.
        Returns a tuple of `(outcoming, incoming)` transactions"""

        label = Label.get_global(name=('Internal'))

        outcoming = Operation(account=self, amount=-amount,
                              description=description, final_date=today(), label=label)
        incoming = Operation(account=destination, amount=amount,
                             description=description, final_date=today(), label=label)

        outcoming.save()
        incoming.source = outcoming
        incoming.save()

        return outcoming, incoming

    def has_perm(self, perm: str):
        """Checks if the Account's user has a specified permission.
        Shortcut for `.user.has_perm()`."""

        return self.user.has_perm(perm)

    def clear_additional_perms(self):
        """Clear additional user permissions."""

        if self.is_admin():
            return
        elif self.is_mod():
            perms = MOD_PERMS
        else:
            perms = USER_PERMS

        for perm in perms:
            app_perm = f'budget.{perm[0]}'
            if self.has_perm(app_perm):
                perm = Permission.objects.get(codename=perm[0])
                self.user.user_permissions.remove(perm)

        self.save()

    def add_perm(self, codename: str, commit: bool = True):
        """Add user permission specified by the codename.
        Return True if the permission was added or the user already had it."""

        if self.has_perm(f'budget.{codename}'):
            return True

        try:
            perm = Permission.objects.get(codename=codename)
            self.user.user_permissions.add(perm)
            if commit:
                self.user.save()

            return True
        except Permission.DoesNotExist:
            return False

    def remove_perm(self, codename: str, commit: bool = True):
        """Remove user permission specified by the codename.
        Returns True if the permission was removed or the user did not have it."""

        if not self.has_perm(f'budget.{codename}'):
            return True

        try:
            perm = Permission.objects.get(codename=codename)
            self.user.user_permissions.remove(perm)
            if commit:
                self.user.save()

            return True
        except Permission.DoesNotExist:
            return False

    def get_operations(self):
        """Updates the operation plans and returns this Account's operations as a QuerySet."""

        self._update_plans()
        return Operation.objects.filter(account=self)

    def get_plans(self):
        """Updates the operation plans and returns this Account's operation plans as a QuerySet."""

        self._update_plans()
        return OperationPlan.objects.filter(account=self)

    def rename(self, new_name: str):
        """Changes the Account's User name (not username)."""

        new_name = new_name or ''

        self.user.first_name = new_name
        self.user.save()

    def get_title(self):
        """Returns the account title ([Administrator], [Moderator] or an empty string)."""

        if self.is_admin():
            return '[Administrator]'
        elif self.is_mod():
            return '[Moderator]'
        else:
            return ''

    def _fetch_perms(self, descriptions: bool = False):
        """Returns granted user permissions without the default ones.
        If `descriptions` is true it fetches all descriptions instead of codenames.
        """

        i = 1 if descriptions else 0

        if self.is_admin():
            return [perm[i] for perm in BASE_ADMIN_PERMS]

        elif self.is_mod():
            perms = [perm[i] for perm in BASE_MOD_PERMS]
            for perm in MOD_PERMS:
                if self.has_perm(f'budget.{perm[0]}'):
                    perms.append(perm[i])
            
            return perms

        else:
            perms = []
            for perm in USER_PERMS:
                if self.has_perm(f'budget.{perm[0]}'):
                    perms.append(perm[i])

            return perms
    
    def get_perms(self):
        """Returns all the granted permissions for this user excluding the default ones."""

        return self._fetch_perms(False)        

    def get_perm_descriptions(self):
        """Returns a list of the granted user permission descriptions (excluding default ones)."""

        return self._fetch_perms(True)

class Label(ConvenienceModel):
    """Label model. Home labels do not have a value in the account field and personal labels do. Global labels have neither."""

    class Meta:
        permissions = {
            ('manage_home_labels', 'Can create or delete home labels.')
        }
        ordering = ('name', 'id')

    name = models.CharField(max_length=32, verbose_name='Label name')
    """Label name."""

    home = models.ForeignKey(
        Home, on_delete=models.CASCADE, null=True, verbose_name='Home')
    """Home which the label belong to.
    It should be set even if the label is a personal label. If None then the label is global.
    """

    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, null=True, verbose_name='Account')
    """For a personal label this is the account that created it.
    It must be empty for a home label.
    """

    is_default = models.BooleanField(
        default=False, blank=True, verbose_name='If the label is a default label.')
    """If the label is a default label."""

    _global_initialized = False
    """TODO"""

    DEFAULT_LABELS = {
        'Food',
        'Transport',
        'Entertainment',
        'Health',
        'Clothes',
        'Accomodation',
        'Education',
        'Savings',
        'Other'
    }
    """Default home labels."""

    GLOBAL_LABELS = {
        'Internal'
    }

    def __str__(self):
        prefix = ''
        if self.account is None:
            prefix = '[Home] ' if self.home else '[Special] '

        return prefix + self.name

    def rename(self, new_name: str, commit: bool = True):
        """Renames the label. Returns True if renaming was successful.

        If `commit` is False the Label is not saved to the database.
        """

        if not self._check_unique_name(new_name):
            return False

        self.name = new_name
        if commit:
            self.save()

        return True

    def _check_unique_name(self, new_name: str | None = None):
        """Checks if the label is unique for the user and for the Home."""

        new_name = new_name or self.name
        
        if not self.home:
            return not Label.get_global().filter(name=new_name).exists()

        if not self.account: # Check if unique in Home
            return not Label.objects.filter(home=self.home).filter(account=None).filter(name=new_name).exists()

        # Check if unique for the user
        return not Label.objects.filter(account=self.account).filter(name=new_name).exists()

    @staticmethod
    def get_global(name: str | None = None):
        """Returns a global label with the specified name or all if no name is specified."""

        if not Label._global_initialized:
            Label._init_global()

        qset = Label.objects.filter(home=None)

        return qset.get(name=name) if name else qset

    def _init_global():
        """Initializes global labels."""

        for name in Label.GLOBAL_LABELS:
            Label.objects.get_or_create(name=name, home=None, is_default=True)


class BaseOperation(ConvenienceModel):
    """Abstract base operation model."""

    class Meta:
        abstract = True

    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, verbose_name='Account')
    """The account that the operation belongs to."""

    label = models.ForeignKey(
        Label, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Label')
    """An optional label attached to the operation.
    Can either be a personal or home label.
    """

    amount = models.DecimalField(
        decimal_places=2, max_digits=8, verbose_name='Operation amount')
    """The amount of money that the operation carried."""

    description = models.TextField(
        max_length=500, null=True, blank=True, verbose_name="Optional description")
    """Optional description of the operation."""

    def currency_amount(self):
        return f'{self.amount} {self.account.home.currency}'


class Operation(BaseOperation):
    """Operation model. If the operation does not have a `final_date` then it is not finalized."""

    class Meta:
        permissions = {
            ('make_transactions', 'Can make an internal transaction to another user.')
        }
        ordering = ('-creation_date', '-id')

    creation_date = models.DateField(
        auto_now_add=True, verbose_name='Time created')
    """Creation date and time of the operation.
    It is automatically set during creation if not specified otherwise.
    """

    final_date = models.DateField(
        null=True, blank=True, verbose_name='Time finalized')
    """Finalization date and time of the operation. If present it means that the operation is finalized."""

    plan = models.ForeignKey('OperationPlan', on_delete=models.SET_NULL,
                             null=True, blank=True, verbose_name='Planned')
    """Optional foreign key to the OperationPlan model. Present if the operation was created as a result of a plan."""

    source = models.OneToOneField('self', on_delete=models.SET_NULL, null=True,
                                  verbose_name='Optional transaction source operation.', related_name='destination')

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        """Overriden save method to update account money during saving."""

        if not self.is_saved():
            account = self.account
            if self.final_date is not None:
                account.add_to_current(self.amount, commit=False)

            account.add_to_final(self.amount)

        super().save(force_insert=force_insert, force_update=force_update,
                     using=using, update_fields=update_fields)

    def delete(self, using=None, keep_parents=False):
        """Overriden delete method to update account money during deleting."""

        if self.is_transaction():
            if self.source:
                src = self.source
                self.source = None
                self.save()
                src.delete()
            else:
                dest = self.destination
                dest.source = None
                dest.save()
                dest.delete()

        account = self.account
        if self.final_date is not None:
            account.add_to_current(-self.amount, commit=False)

        account.add_to_final(-self.amount)

        return super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return f'{self.amount}*' if self.final_date is None else str(self.amount)

    def finalize(self, final_datetime: datetime | date = None):
        """Finalizes the operation setting the finalization time according to the specified parameter.
        If no argument is passed it uses the current date.
        """

        if self.final_date:
            return

        if isinstance(final_datetime, datetime):
            final_datetime = final_datetime.date()

        self.final_date = final_datetime or today()

        self.account.add_to_current(self.amount)
        self.save()

    def is_transaction(self) -> bool:
        """Checks if the Operation is an internal transaction."""

        try:
            return bool(self.source or self.destination) or False
        except self.DoesNotExist:
            return False

    def get_destination(self):
        """Returns the operation destination if the operation is a transaction.
        If not it does not throw an Error but returns None."""

        return self.destination if self.is_transaction() else None


class OperationPlan(BaseOperation):
    """Operation plan."""

    class Meta:
        permissions = {
            ('plan_for_others', 'Can make plans for another user.')
        }
        ordering = ('next_date', 'id')

    class TimePeriod(models.TextChoices):
        """Enum class for the time period."""

        DAY = 'D', _('Day')
        WEEK = 'W', _('Week')
        MONTH = 'M', _('Month')
        YEAR = 'Y', _('Year')

    period = models.CharField(
        max_length=1, choices=TimePeriod.choices, default=TimePeriod.WEEK, verbose_name='Time period')
    """Time period between the operations. A new operation is created every `period_count` * period."""

    period_count = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(20)],
                                               verbose_name='Period count')
    """How many periods (days, weeks, months, years) should pass between a new operation."""

    next_date = models.DateField(
        default='today', verbose_name='Next operation creation date')
    """Next day that the new operation should be created."""

    def save(self, force_insert: bool = False, force_update: bool = False, using=None, update_fields=None):
        """TODO"""

        if isinstance(self.next_date, datetime):
            self.next_date = self.next_date.date()

        super().save(force_insert=force_insert, force_update=force_update,
                     using=using, update_fields=update_fields)

    def calculate_next(self, base_date: date = None):
        """Calculates the next date of the operation creation.

        If no `base_date` is specified the next planned date is used.
        """

        if self.period == self.TimePeriod.DAY:
            delta = timedelta(days=self.period_count)

        elif self.period == self.TimePeriod.WEEK:
            delta = timedelta(weeks=self.period_count)

        elif self.period == self.TimePeriod.MONTH:
            delta = timedelta(days=30 * self.period_count)

        elif self.period == self.TimePeriod.YEAR:
            delta = timedelta(days=365 * self.period_count)

        else:
            delta = timedelta()

        if base_date is None:
            base_date = self.next_date

        next_date = base_date + delta
        return next_date

    def create_operation(self, commit: bool = True, recalculate: bool = True):
        """Creates a new Operation object in the database according to this plan. Returns the created Operation.
        If `recalculate` is True a new `next_date` is calculated from today."""

        op = Operation(account=self.account,
                       label=self.label,
                       amount=self.amount,
                       description=self.description)

        if recalculate:
            self.next_date = self.calculate_next()

        if commit:
            op.save()
            self.save()
            op.plan = self
            op.save()
        else:
            op.plan = self

        return op

    def is_due(self):
        """Chekcs if the plan is due for a new Operation."""

        return self.next_date <= today()

    def get_frequency(self):
        """"""

        plural = self.period_count != 1
        time_label = self.TimePeriod(self.period).label.lower()

        return f'Every {self.period_count} {time_label}s' if plural else f'Every {time_label}'
