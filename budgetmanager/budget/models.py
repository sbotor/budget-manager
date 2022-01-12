from datetime import date, datetime, timedelta
from django.db import models, IntegrityError
from django.db.models.query_utils import Q
from django.utils import timezone
from django.contrib.auth.models import Permission, Group, User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator


class Home(models.Model):
    """Home model used for account grouping."""

    class Meta:
        permissions = {
            ('manage_home', 'Can manage the entire Home.'),
            ('make_home_admin', 'Can make a user a home admin.'),
            ('make_mod', 'Can make a user a moderator.'),
        }

    name = models.CharField(max_length=50, verbose_name='Home name')
    """Home name."""

    admin = models.OneToOneField(
        'Account', null=True, on_delete=models.RESTRICT, related_name='+')
    """The Home's Administrator account.
    Null value is possible, but should only occur during home creation.
    It has no backward relation to the Home object as it can be obtained via the regular Account.home field.
    """

    ADMIN_GROUP = 'home_admin'
    """Home admin group name."""

    MOD_GROUP = 'moderator'
    """Home moderator group name."""

    BASE_MOD_PERMS = {
        ('see_other_accounts', 'See other users\' accounts'),
        ('manage_home_labels', 'Manage home labels'),
        ('make_transactions', 'Send money to another user'),
    }
    """Base mod permissions codenames."""

    MOD_PERMS = {
        ('make_mod', 'Grant Moderator permissions'),
        ('plan_for_others', 'Plan operations for other users'),
        ('manage_users', 'Manage other users'),
        ('make_mod', 'Grant Moderator permissions')
    }
    """Additional mod permissions codenames. Can be granted in addition to the base ones."""

    BASE_ADMIN_PERMS = {
        ('manage_home', 'Manage the Home'),
        ('make_home_admin', 'Pass the admin role to another user'),
        ('manage_users', 'Manage other users'),
    }
    """Base admin permissions codenames."""

    USER_PERMS = {
        ('make_transactions', 'Send money to another user')
    }
    """Additional regular user permissions."""

    def __str__(self):
        return self.name

    @staticmethod
    def create_home(home_name: str, user: User):
        """The method used to create a new home and add the administrator User passed as a parameter."""

        home = Home(name=home_name)
        admin = Account(user=user, home=home)
        try:
            home.save()
            home.change_admin(admin)

            home.create_predefined_labels()
            home.save()

            return home
        except IntegrityError:
            # Clean up and return None
            if not admin._state.adding:
                admin.delete()
            if not home._state.adding:
                home.delete()
            return None

    def get_labels(self, home_only: bool = False):
        """Return all the labels available to the Home excluding global labels.

        If `home_only` is False no personal labels are returned.
        """

        queryset = Label.objects.filter(home=self).order_by('name')
        if home_only:
            queryset = queryset.filter(account=None).order_by('name')

        return queryset

    def add_label(self, label: 'Label', commit: bool = True):
        """Add a new personal home to the database. Returns the newly added Label.

        If `commit` is False the label is not saved to the database.
        """

        label.account = None
        label.home = self
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

        group, created = Group.objects.get_or_create(name=Home.ADMIN_GROUP)
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
        """TODO"""

        group, created = Group.objects.get_or_create(name=Home.MOD_GROUP)
        if created:
            Home._setup_mod_group(group)

        account.user.groups.add(group)

        if commit:
            account.user.save()

    def remove_mod(self, account: 'Account', commit: bool = True):
        """TODO"""

        group = Group.objects.get(name=Home.MOD_GROUP)

        if account.is_mod():
            account.user.groups.remove(group)

        account.user.user_permissions.clear()

        if commit:
            account.user.save()

    @staticmethod
    def _setup_admin_group(group: Group):
        """TODO"""

        admin_perms = [Permission.objects.get_or_create(codename=perm[0])[0] for perm in Home.BASE_ADMIN_PERMS]

        group.permissions.add(*admin_perms)
        group.save()

    @staticmethod
    def _setup_mod_group(group: Group):
        """TODO"""

        mod_perms = [Permission.objects.get_or_create(codename=perm[0])[0] for perm in Home.BASE_MOD_PERMS]

        group.permissions.add(*mod_perms)
        group.save()


class Account(models.Model):
    """The model of the user account."""

    class Meta:
        permissions = {
            ('manage_users', 'Can manage user accounts.'),
            ('see_other_accounts', 'Can see other users\' accounts.'),
        }

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, verbose_name="User")
    """User model object bound to the account."""

    home = models.ForeignKey(
        Home, on_delete=models.CASCADE, verbose_name='Home')
    """Home that the account belongs to."""

    current_amount = models.DecimalField(
        decimal_places=2, max_digits=8, default=0.0, verbose_name='Current amount of money')
    """Current amount of money that the account has."""

    final_amount = models.DecimalField(
        decimal_places=2, max_digits=8, default=0.0, verbose_name='Final amount of money')
    """Amount of money after all the operations are finalized."""

    def __str__(self):
        return self.user.username

    def calculate_final(self):
        """Used to calculate the finalized amount of money in the account including finalized operations."""

        operations = Operation.objects.filter(account=self)
        total = 0.0

        for op in operations:
            total += float(op.amount)

        return total

    def calculate_current(self):
        """Used to calculate the current amount of money excluding unfinalized operations."""

        operations = Operation.objects.filter(
            account=self).exclude(final_date=None)
        total = 0.0

        for op in operations:
            total += float(op.amount)

        return total

    def get_last_year_income(self):
        operations = Operation.objects.filter(
            account=self).exclude(final_date=None)

        income = [0,0,0,0,0,0,0,0,0,0,0,0]        

        for op in operations:
            difference = timezone.now().today().year - op.final_date.year
            if difference <= 1:
                month = op.final_date.month
                if op.amount > 0:
                    income[month-1] += float(op.amount)

        return income

    def get_last_year_expenses(self):
        operations = Operation.objects.filter(
            account=self).exclude(final_date=None)

        expenses = [0,0,0,0,0,0,0,0,0,0,0,0]

        for op in operations:
            difference = timezone.now().today().year - op.final_date.year
            if timezone.now().today().year - op.final_date.year < 1 and timezone.now().today().month >= op.final_date.month:
                month = op.final_date.month
                if op.amount < 0:
                    expenses[month-1] += -1*float(op.amount)

        return expenses

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
            return Label.objects.filter(q).order_by('name')
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
        """TODO"""

        plan.account = self
        op = None
        now = OperationPlan.datetime_today()

        if plan.next_date == now:
            op = plan.create_operation(commit=False)
            plan.next_date = plan.calculate_next(base_date=now)

        if commit:
            plan.save()
            if op is not None:
                op.save()

        return (plan, op)

    def add_label(self, label: 'Label', commit: bool = True):
        """Add a new personal label to the database. Returns the newly added Label.

        If `commit` is False the label is not saved to the database.
        """

        label.account = self
        label.home = self.home
        if commit:
            label.save()

        return label

    def delete(self, using=None, keep_parents: bool = False):

        user = self.user
        ret_val = super().delete(using=using, keep_parents=keep_parents)
        user.delete()
        return ret_val

    def is_admin(self):
        """Checks if the Account's User is a home Admin."""

        return self.user.groups.filter(name=Home.ADMIN_GROUP).exists()

    def is_mod(self):
        """Checks if the Account's User is a home Moderator."""

        return self.user.groups.filter(name=Home.MOD_GROUP).exists()

    def make_transaction(self, destination: 'Account', amount: float, description: str = None):
        """TODO"""

        label = Label.get_global(name=('Internal'))

        outcoming = Operation(account=self, amount=-amount,
                              description=description, final_date=Operation.datetime_today(), label=label)
        incoming = Operation(account=destination, amount=amount,
                             description=description, final_date=Operation.datetime_today(), label=label)

        outcoming.save()
        incoming.source = outcoming
        incoming.save()

        return outcoming, incoming

    def has_perm(self, perm: str):
        """Checks if the Account's user has a specified permission.
        Shorthand for *.user.has_perm()"""

        usr = User()
        return self.user.has_perm(perm)

    def clear_additional_perms(self):
        """Clear additional user permissions."""

        if self.is_admin():
            return
        elif self.is_mod():
            perms = Home.MOD_PERMS
        else:
            perms = Home.USER_PERMS

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

class Label(models.Model):
    """Label model. Home labels do not have a value in the account field and personal labels do. Global labels have neither."""

    class Meta:
        permissions = {
            ('manage_home_labels', 'Can create or delete home labels.')
        }

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
            if self.home is not None:
                prefix = '[H] '
            else:
                prefix = '[G] '

        return prefix + self.name

    def rename(self, new_name: str, commit: bool = True):
        """Renames the label.

        If `commit` is False the Label is not saved to the database.
        """

        self.name = new_name
        if commit:
            self.save()

    @staticmethod
    def get_global(name: str):
        """TODO"""

        if not Label._global_initialized:
            Label._init_global()

        qset = Label.objects.filter(home=None)

        if name:
            return qset.get(name=name)
        else:
            return qset

    def _init_global():
        """Initializes global labels."""

        for name in Label.GLOBAL_LABELS:
            Label.objects.get_or_create(name=name, home=None, is_default=True)


class BaseOperation(models.Model):
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

    @staticmethod
    def datetime_today():
        """Returns timezone-aware present date."""

        return timezone.now().date()


class Operation(BaseOperation):
    """Operation model. If the operation does not have a `final_date` then it is not finalized."""

    class Meta:
        permissions = {
            ('make_transactions', 'Can make an internal transaction to another user.')
        }

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

    source = models.ForeignKey('self', on_delete=models.SET_NULL, null=True,
                               verbose_name='Optional transaction source operation.', related_name='destination')

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        """Overriden save method to update account money during saving."""

        if self._state.adding:
            account = self.account
            if self.final_date is not None:
                account.add_to_current(self.amount, commit=False)

            account.add_to_final(self.amount)

        super().save(force_insert=force_insert, force_update=force_update,
                     using=using, update_fields=update_fields)

    def delete(self, using=None, keep_parents=False):
        """Overriden delete method to update account money during deleting."""

        account = self.account
        if self.final_date is not None:
            account.add_to_current(-self.amount, commit=False)

        account.add_to_final(-self.amount)

        super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return f'{self.amount}*' if self.final_date is None else str(self.amount)

    def finalize(self, final_datetime: timezone.datetime = None):
        """Finalizes the operation setting the finalization time according to the specified parameter.
        If no argument is passed it uses the current date.
        """

        if self.final_date is None:
            if final_datetime is None:
                self.final_date = Operation.datetime_today()
            else:
                self.final_date = final_datetime.date()

            self.save()
            self.account.add_to_current(self.amount)


class OperationPlan(BaseOperation):
    """Operation plan."""

    class Meta:
        permissions = {
            ('plan_for_others', 'Can make plans for another user.')
        }

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
        default='datetime_today', verbose_name='Next operation creation date')
    """Next day that the new operation should be created."""

    def save(self, force_insert: bool = False, force_update: bool = False, using=None, update_fields=None):
        """TODO"""

        if isinstance(self.next_date, timezone.datetime):
            self.next_date = self.next_date.date()

        op = None
        while self.is_due():
            op = self.create_operation(commit=False)

            super().save()
            if op is not None:
                op.save()

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

    def create_operation(self, commit: bool = True):
        """Creates a new Operation object in the database according to this plan. Returns the created Operation."""

        op = Operation(account=self.account,
                       label=self.label,
                       amount=self.amount,
                       description=self.description)

        #print(f'Operation {op} created.')

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
        """TODO"""

        return self.next_date <= OperationPlan.datetime_today()
