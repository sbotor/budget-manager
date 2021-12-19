from django.db import models, IntegrityError
from django.db.models import signals
from django.db.models.query import QuerySet
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.models import User


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
        queryset = Label.objects.filter(home=self)
        if home_only:
            queryset = queryset.filter(account=None)

        return queryset


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
            account=self).exclude(final_datetime=None)
        total = 0.0

        for op in operations:
            total += float(op.amount)

        return total

    def add_current(self, amount: float, commit: bool = True):
        """Used to add the specified value to the current account."""
        
        self.current_amount += amount
        if commit:
            self.save()

    def add_final(self, amount: float, commit: bool = True):
        """Used to add the specified value to the final account."""

        self.final_amount += amount
        if commit:
            self.save()

    def available_labels(self, include_home: bool = True):
        """Returns a QuerySet of all the available labels of this Account. 
        
        If `include_home` is set to False only personal labels are returned.
        """
    
        if include_home:
            return Label.objects.filter(home=self.home).filter(account=self)
        else:
            return Label.objects.filter(account=self)

        

# This can be done like this or two separate tables can be created (one for home and the other for personal labels).
# With separate tables there is a problem with relating labels to operations.


class Label(models.Model):
    """Label model. Home labels do not have a value in the account field and personal labels do."""

    name = models.CharField(max_length=10, verbose_name='Label name')
    """Label name."""

    home = models.ForeignKey(
        Home, on_delete=models.CASCADE, verbose_name='Home')
    """Home which the label belong to.
    It should be set even if the label is a personal label.
    """

    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, null=True, verbose_name='Account')
    """For a personal label this is the account that created it.
    It must be empty for a home label.
    """

    def __str__(self):
        return f'[H] {self.name}' if self.account is None else self.name


class Operation(models.Model):
    """Operation model. If the operation does not have a final_datetime than it is not finalized."""

    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, verbose_name='Account')
    """The account that the operation belongs to."""

    label = models.ForeignKey(
        Label, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Label')
    """An optional label attached to the operation.
    Can either be a personal or home label.
    """

    creation_datetime = models.DateTimeField(
        auto_now_add=True, verbose_name='Time created')
    """Creation date and time of the operation.
    It is automatically set during creation if not specified otherwise.
    """

    final_datetime = models.DateTimeField(
        null=True, verbose_name='Time finalized')
    """Finalization date and time of the operation. If present it means that the operation is finalized."""

    amount = models.DecimalField(
        decimal_places=2, max_digits=8, verbose_name='Operation amount')
    """The amount of money that the operation carried."""

    description = models.TextField(
        max_length=500, null=True, blank=True, verbose_name="Optional description")
    """Optional description of the operation."""

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        """Overriden save method to update account money during saving."""

        if self._state.adding:
            account = self.account
            if self.final_datetime is not None:
                account.add_current(self.amount, commit=False)
            
            account.add_final(self.amount)

        super().save(force_insert=force_insert, force_update=force_update,
                     using=using, update_fields=update_fields)

    def delete(self, using=None, keep_parents=False):
        """Overriden delete method to update account money during deleting."""

        account = self.account
        if self.final_datetime is not None:
            account.add_current(-self.amount, commit=False)
        
        account.add_final(-self.amount)

        super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return f'{self.amount}*' if self.final_datetime is None else self.amount

    def finalize(self, final_dt: timezone.datetime = None):
        """Finalizes the operation setting the finalization time according to the specified parameter.
        If no argument is passed it uses the current datetime.
        """

        if self.final_datetime is None:
            if final_dt is None:
                self.final_datetime = timezone.now()
            else:
                self.final_datetime = final_dt
            
            self.save()
            self.account.add_current(self.amount)
