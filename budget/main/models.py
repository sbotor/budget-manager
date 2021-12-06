from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Home(models.Model):
    name = models.TextField(max_length=20, verbose_name='Home name')

    def __str__(self):
        return self.name

class Account(models.Model):
    # Placeholder, eventually integrate the built in User model
    name = models.TextField(max_length=20, verbose_name='Username')
    #user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='User')

    home = models.ForeignKey(Home, on_delete=models.CASCADE, verbose_name='Home')

    def __str__(self):
        #return f'User {self.user} (id: {self.user.id}) from home {self.home} (id: {self.home.id})'
        return f'User {self.name} (id: {self.id}) from home {self.home} (id: {self.home.id})'

    # class Meta:
    #     proxy = True

class Label(models.Model):
    name = models.TextField(max_length=10, verbose_name='Label name')
    home = models.ForeignKey(Home, on_delete=models.CASCADE, verbose_name='Home')
    account = models.ForeignKey(Account, on_delete = models.CASCADE, null=True, verbose_name='Account')

    def __str__(self):
        return self.name

class Operation(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name='Account')
    label = models.ForeignKey(Label, on_delete=models.SET_NULL, null=True, verbose_name='Label')
    creation_datetime = models.DateTimeField(auto_now_add=True, verbose_name='Time created')
    final_datetime = models.DateTimeField(null=True, verbose_name='Time finalized')
    amount = models.DecimalField(decimal_places=2, max_digits=6, verbose_name='Operation amount')

    def __str__(self):
        retStr =  f'Operation id: {self.id} amount: {self.amount} in account: {self.account.id}. Created {self.creation_datetime}'
        return (retStr + f', finalized {self.final_datetime}.') if self.final_datetime else (retStr + '.')