from django.db import models
from django.utils import timezone

class Home(models.Model):
    """Home model used for account grouping."""

    name = models.TextField(max_length=20, verbose_name='Home name')
    """Home name."""
    
    admin = models.OneToOneField('Account', null=True, on_delete=models.PROTECT, related_name='+')
    """The Home's Administrator account.
    Null value is possible, but should only occur during home creation.
    It has no backward relation to the Home object as it can be obtained via the regular Account.home field.
    """

    def __str__(self):
        return self.name

    @staticmethod
    def create_home(home_name: str, admin_name: str):
        """The method used to create a new home and the administrator account.
        This is a static method returning the newly created Home object.
        """

        home = Home(name=home_name)
        home.save()
        admin = Account(name=admin_name, home=home)
        admin.save()
        home.admin = admin
        home.save()

        return home
    
    def add_account(self, name: str):
        """Used to create a new user account, add it to the specified Home and return it."""

        account = Account(name=name, home=self)
        account.save()

        return account

class Account(models.Model):
    """The model of the user account."""

    name = models.TextField(max_length=20, verbose_name='Username', unique=True)
    """Account name, has to be unique. Eventually it should be removed and a User relation should be added."""

    home = models.ForeignKey(Home, on_delete=models.CASCADE, verbose_name='Home')
    """Home that the account belongs to."""

    def __str__(self):
        return f'User {self.name} (id: {self.pk}) from home {self.home} (id: {self.home.pk})'

    def get_final_amount(self):
        """Used to calculate the finalized amount of money in the account including finalized operations."""
        
        operations = Operation.objects.filter(account=self)
        total = 0.0

        for op in operations:
            total += float(op.amount)
        
        return total

    def get_current_amount(self):
        """Used to calculate the current amount of money excluding unfinalized operations."""
        
        operations = Operation.objects.filter(account=self).exclude(final_datetime=None)
        total = 0.0

        for op in operations:
            total += float(op.amount)
        
        return total

# This can be done like this or two separate tables can be created (one for home and the other for personal labels).
# With separate tables there is a problem with relating labels to operations.
class Label(models.Model):
    """Label model. Home labels do not have a value in the account field and personal labels do."""
    
    name = models.TextField(max_length=10, verbose_name='Label name')
    """Label name."""

    home = models.ForeignKey(Home, on_delete=models.CASCADE, verbose_name='Home')
    """Home which the label belong to.
    It should be set even if the label is a personal label.
    """

    account = models.ForeignKey(Account, on_delete = models.CASCADE, null=True, verbose_name='Account')
    """For a personal label this is the account that created it.
    It must be empty for a home label.
    """

    def __str__(self):
        return self.name

class Operation(models.Model):
    """Operation model. If the operation does not have a final_datetime than it is not finalized."""
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name='Account')
    """The account that the operation belongs to."""

    label = models.ForeignKey(Label, on_delete=models.SET_NULL, null=True, verbose_name='Label')
    """An optional label attached to the operation.
    Can either be a personal or home label.
    """

    creation_datetime = models.DateTimeField(auto_now_add=True, verbose_name='Time created')
    """Creation date and time of the operation.
    It is automatically set during creation if not specified otherwise.
    """
    
    final_datetime = models.DateTimeField(null=True, verbose_name='Time finalized')
    """Finalization date and time of the operation. If present it means that the operation is finalized."""
    
    amount = models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Operation amount')
    """The amount of money that the operation carried."""

    def __str__(self):
        retStr =  f'Operation id: {self.pk} amount: {self.amount} in account: {self.account.pk}. Created {self.creation_datetime}'
        return (retStr + f', finalized {self.final_datetime}.') if self.final_datetime else (retStr + '.')

    def finalize(self, final_dt: timezone.datetime = None):
        """Finalizes the operation setting the finalization time according to the specified parameter.
        If no argument is passed it uses the current datetime.
        """
        
        if (self.final_datetime is not None):
            if (final_dt is None):
                self.final_datetime = timezone.now()
            else:
                self.final_datetime = final_dt