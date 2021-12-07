from django.db import models
from django.dispatch import receiver

# Create your models here.

class Home(models.Model):
    """Home model used for account grouping."""
    name = models.TextField(max_length=20, verbose_name='Home name')
    admin = models.OneToOneField('Account', null=True, on_delete=models.PROTECT)

    def __str__(self):
        return self.name

class Account(models.Model):
    """This is the model of the user account"""
    # Placeholder, eventually integrate the built in User model
    name = models.TextField(max_length=20, verbose_name='Username')
    #user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='User')
    bound_home = models.ForeignKey(Home, on_delete=models.CASCADE, verbose_name='Home')

    # class Meta:
    #     proxy = True

    def __str__(self):
        #return f'User {self.user} (id: {self.user.pk}) from home {self.home} (id: {self.home.pk})'
        return f'User {self.name} (id: {self.pk}) from home {self.bound_home} (id: {self.bound_home.pk})'

    def getFinalAmount(self):
        """This method is used to calculate the finalized amount of money in the account including finalized operations."""
        operations = Operation.objects.filter(account=self)
        total = 0.0

        for op in operations:
            total += float(op.amount)
        
        return total

    def getCurrentAmount(self):
        """This method is used to calculate the current amount of money excluding unfinalized operations."""
        operations = Operation.objects.filter(account=self).exclude(final_datetime=None)
        total = 0.0

        for op in operations:
            total += float(op.amount)
        
        return total

class Label(models.Model):
    """Label model."""
    name = models.TextField(max_length=10, verbose_name='Label name')
    home = models.ForeignKey(Home, on_delete=models.CASCADE, verbose_name='Home')
    account = models.ForeignKey(Account, on_delete = models.CASCADE, null=True, verbose_name='Account')

    def __str__(self):
        return self.name

class Operation(models.Model):
    """Operation model."""
    account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name='Account')
    label = models.ForeignKey(Label, on_delete=models.SET_NULL, null=True, verbose_name='Label')
    creation_datetime = models.DateTimeField(auto_now_add=True, verbose_name='Time created')
    final_datetime = models.DateTimeField(null=True, verbose_name='Time finalized')
    amount = models.DecimalField(decimal_places=2, max_digits=6, verbose_name='Operation amount')

    def __str__(self):
        retStr =  f'Operation id: {self.pk} amount: {self.amount} in account: {self.account.pk}. Created {self.creation_datetime}'
        return (retStr + f', finalized {self.final_datetime}.') if self.final_datetime else (retStr + '.')