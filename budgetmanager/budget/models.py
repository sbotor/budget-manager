from datetime import date, timedelta
from typing import Iterable
from django.db import models, IntegrityError
from django.db.models.query_utils import Q
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator


class Home(models.Model):
    """Home model used for account grouping."""

    name = models.CharField(max_length=50, verbose_name='Home name')
    """Home name."""

    admin = models.OneToOneField(
        'Account', null=True, on_delete=models.RESTRICT, related_name='+')
    """The Home's Administrator account.
    Null value is possible, but should only occur during home creation.
    It has no backward relation to the Home object as it can be obtained via the regular Account.home field.
    """

    def __str__(self):
        return self.name

    @staticmethod
    def create_home(home_name: str, user: User):
        """The method used to create a new home and add the administrator User passed as a parameter."""

        home = Home(name=home_name)
        admin = Account(user=user, home=home)
        try:
            home.save()
            admin.save()
            home.admin = admin
            
            home._create_predefined_labels()
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

        queryset = Label.objects.filter(home=self)
        if home_only:
            queryset = queryset.filter(account=None)

        return queryset

    # TODO
    def add_label(self, label: 'Label', commit: bool = True):
        """Add a new personal home to the database. Returns the newly added Label.

        If `commit` is False the label is not saved to the database.
        """

        label.account = None
        label.home = self
        if commit:
            label.save()

        return label

    def _create_predefined_labels(self):
        """TODO"""

        for name in Label.DEFAULT_LABELS:
            Label(name=name, home=self).save()


class Account(models.Model):
    """The model of the user account."""

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
            return Label.objects.filter(home=self.home).filter(account=self)
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

    def plan_operation(self, plan: 'OperationPlan', commit: bool = True):
        """TODO"""

        plan.account = self
        op = None
        now = timezone.now().date()

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


class Label(models.Model):
    """Label model. Home labels do not have a value in the account field and personal labels do. Global labels have neither."""

    name = models.CharField(max_length=10, verbose_name='Label name')
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

    # TODO
    DEFAULT_LABELS = ()
    """TODO"""

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
    def get_global(names: Iterable[str] = None):
        """TODO"""
        
        qset = Label.objects.filter(home=None)
        q = Q()

        if names:
            for name in names:
                q = q | Q(label__name=name)
            return qset.filter(q)
        else:
            return qset



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


class Operation(BaseOperation):
    """Operation model. If the operation does not have a `final_date` then it is not finalized."""

    creation_date = models.DateField(
        auto_now_add=True, verbose_name='Time created')
    """Creation date and time of the operation.
    It is automatically set during creation if not specified otherwise.
    """

    final_date = models.DateField(
        null=True, verbose_name='Time finalized')
    """Finalization date and time of the operation. If present it means that the operation is finalized."""

    plan = models.ForeignKey('OperationPlan', on_delete=models.SET_NULL,
                             null=True, blank=True, verbose_name='Planned')
    """Optional foreign key to the OperationPlan model. Present if the operation was created as a result of a plan."""

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
                self.final_date = timezone.now().date()
            else:
                self.final_date = final_datetime.date()

            self.save()
            self.account.add_to_current(self.amount)


class OperationPlan(BaseOperation):
    """Operation plan."""

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

    next_date = models.DateField(default=timezone.now, verbose_name='Next operation creation date')
    """Next day that the new operation should be created."""

    def save(self, force_insert: bool = False, force_update: bool = False, using = None, update_fields = None):
        """TODO"""
        
        if self.next_date == timezone.now().date():
            self.create_operation()
        
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

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
                       description=self.description,
                       plan=self)

        if commit:
            op.save()
            self.save()

        self.next_date = self.calculate_next()

        return op

    def is_due(self):
        """Checks if the plan's next date is today."""

        return self.next_date == timezone.now().date()
