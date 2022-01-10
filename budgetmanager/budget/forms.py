from django import forms
from django.contrib.auth.models import User
from django.forms import widgets
from .models import *
from django.contrib.auth.forms import UserCreationForm


class BaseLabelForm(forms.ModelForm):
    """TODO"""

    def update_label_choices(self, user: User):
        """TODO"""

        self.fields['label'] = forms.ModelChoiceField(
            queryset=user.account.available_labels(),
            empty_label='No label',
            required=False)


class AddOperationForm(BaseLabelForm):
    class Meta:
        model = Operation
        fields = ['finalized', 'amount', 'description', 'label']

    finalized = forms.BooleanField(required=False, label='Finalized')

    def save(self, commit: bool = True):
        """Overriden method to check if the operation should be finalized and update accordingly."""

        if self.cleaned_data.get('finalized'):
            self.instance.final_date = Operation.datetime_today()

        return super().save(commit=commit)


class PlanCyclicOperationForm(BaseLabelForm):
    """This form is used to plan a new cyclic operation."""

    class Meta:
        model = OperationPlan
        fields = ['amount', 'label', 'period',
                  'period_count', 'next_date', 'description']

    next_date = forms.DateField(required=False,
                                label="Starting day", widget=widgets.SelectDateWidget)

    def save(self, commit: bool = True):

        if self.cleaned_data.get('next_date') is None:
            self.instance.next_date = OperationPlan.datetime_today()

        return super().save(commit=commit)


class AddLabelForm(forms.ModelForm):
    """Used to create a new label."""

    class Meta:
        model = Label
        fields = ['name']


class HomeCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'home_name', 'password1', 'password2']

    home_name = forms.CharField(
        max_length=50,
        label='Home name',
        help_text='Your home\'s name. Maximum length is 50 characters.')

    def save(self, commit: bool = True):
        user = super().save(commit=True)
        home = Home.create_home(self.cleaned_data.get('home_name'), user)

        if home is None:
            user.delete()

        return home


# TODO
class ChangeUserPermissionsForm(forms.Form):
    """TODO"""

    def change_perms(account: Account):
        """TODO"""

        pass

# TODO


class ChangeModPermissionsForm(forms.Form):
    """TODO"""

    def change_perms(account: Account):
        """TODO"""

        pass


class TransactionForm(forms.ModelForm):
    """TODO"""

    class Meta:
        model = Operation
        fields = ['amount', 'description']

    def make_transaction(self, source: Account, target: Account):
        if source == target:
            return None, None

        data = self.cleaned_data
        amount = abs(data.get('amount'))
        desc = data.get('description')
        label = Label.get_global(name=('Internal'))

        outcoming = Operation(account=source, amount=-amount,
                              description=desc, final_date=Operation.datetime_today(), label=label)
        incoming = Operation(account=target, amount=amount,
                             description=desc, final_date=Operation.datetime_today(), label=label)

        outcoming.save()
        incoming.save()

        return outcoming, incoming
