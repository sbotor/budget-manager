from xml.dom import ValidationErr
from django import forms
from django.contrib.auth.models import User
from django.forms import ValidationError, widgets
from django.contrib.auth.forms import UserCreationForm
from django.http import QueryDict
from django.core.validators import MinValueValidator

from .models import *
from .utils import today


class BaseLabelForm(forms.ModelForm):
    """Base class for all forms using labels. Should not be created."""

    def _update_label_choices(self, account: Account):
        """Updates label choices according to the passed Account."""

        self.fields['label'].queryset = account.available_labels()
        self.fields['label'].empty_label = 'No label'

    @classmethod
    def from_account(cls, account: Account):
        """Creates a form and updates the label choices according to the account.
        Returns the created form.
        """

        form = cls()
        form._update_label_choices(account)
        return form


class AddOperationForm(BaseLabelForm):
    """Form for adding a new operation."""

    class Meta:
        model = Operation
        fields = ['finalized', 'amount', 'description', 'label']

    finalized = forms.BooleanField(required=False, label='Finalized')

    def save(self, commit: bool = True):
        """Overriden method to check if the operation should be finalized and update accordingly."""

        if self.cleaned_data.get('finalized'):
            self.instance.final_date = today()

        return super().save(commit=commit)


class PlanCyclicOperationForm(BaseLabelForm):
    """This form is used to plan a new cyclic operation."""

    class Meta:
        model = OperationPlan
        fields = ['amount', 'label', 'period',
                  'period_count', 'next_date', 'description']

    next_date = forms.DateField(required=False,
                                label="Starting day", widget=widgets.SelectDateWidget,
                                help_text='Leave blank for today.')

    def save(self, commit: bool = True):

        if self.cleaned_data.get('next_date') is None:
            self.instance.next_date = today()

        return super().save(commit=commit)


class AddLabelForm(forms.ModelForm):
    """Used to create a new label."""

    class Meta:
        model = Label
        fields = ['name']


class HomeCreationForm(UserCreationForm):
    """Form for adding a new Home and an Administrator account."""

    class Meta:
        model = User
        fields = ['home_name', 'currency',
                  'username', 'password1', 'password2']

    home_name = forms.CharField(
        max_length=50,
        label='Home name',
        help_text='Your home\'s name. Maximum length is 50 characters.')

    currency = forms.ChoiceField(
        choices=Home.Currency.choices, label="Home currency")

    def save(self, commit: bool = True):
        data = self.cleaned_data

        user = super().save(commit=True)
        home = Home.create_home(home_name=data.get(
            'home_name'), user=user, currency=data.get('currency'))

        if home is None:
            user.delete()

        return home


class ChangeUserPermissionsForm(forms.Form):
    """Form for changing specific user permissions."""

    choices = forms.MultipleChoiceField(
        choices={}, widget=forms.widgets.CheckboxSelectMultiple, label='Permissions', required=False)

    def change_perms(self, account: Account):
        """Method changing the account's user permissions according to the data."""

        choices = self.cleaned_data.get('choices')
        if not choices:
            account.clear_additional_perms()
            return

        if account.is_admin():
            return
        elif account.is_mod():
            perms = MOD_PERMS
        else:
            perms = USER_PERMS

        for perm in perms:
            app_perm = f'budget.{perm[0]}'
            if perm[0] in choices and not account.has_perm(app_perm):
                account.add_perm(codename=perm[0])
            elif perm[0] not in choices and account.has_perm(app_perm):
                account.remove_perm(codename=perm[0])

    def _update_choices(self, account: Account):
        """Updates the label choices according to the specified user Account.
        Returns the sorted list of all available choices as a tuple (codename, description)."""

        choices = MOD_PERMS if account.is_mod() else USER_PERMS

        choice_list = list(choices)
        choice_list.sort()
        self.fields['choices'].choices = choice_list

        return choices

    def _update_initial(self, account: Account):
        """Updates the initially selected permissions according to the specified user Account.
        Returns the list of all granted user permission descriptions."""

        choices = self._update_choices(account)
        set_list = []
        total_list = []
        if account.is_mod():
            total_list.extend([desc[1] for desc in BASE_MOD_PERMS])

        for choice in choices:
            app_perm = f'budget.{choice[0]}'
            if account.has_perm(app_perm):
                set_list.append(choice[0])
                total_list.append(choice[1])

        self.fields['choices'].initial = set_list

        self.all_perms = total_list
        return total_list

    @classmethod
    def from_account(cls, account: Account):
        """Creates a new form with available choices updated according to the Account.
        Initial choices are also selected.
        """

        form = cls()
        form._update_initial(account)
        return form

    @classmethod
    def from_post(cls, account: Account, post: QueryDict):
        """Creates a new form from POST data without initial choices.
        Available choices are updated according to the Account.
        Returns the created form.
        """

        form = cls(post)
        form._update_choices(account)
        return form


class BaseTransactionForm(forms.ModelForm):
    """Base transaction form with custom validation."""

    class Meta:
        model = Operation
        fields = ['amount', 'description']

    def clean(self):

        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')

        if amount and amount <= 0:
            raise ValidationError("The amount cannot be negative.")

        return super().clean()

class TransactionForm(BaseTransactionForm):
    """Form for making transaction between accounts when the destination is known."""

    class Meta:
        model = Operation
        fields = ['amount', 'description']

    def make_transaction(self, source: Account, destination: Account):
        """Makes a transaction from the `source` Account to the `destination`.
        
        Returns a tuple of `(outcoming, incoming)` transactions.
        """

        if not source or not destination or source == destination:
            return None, None

        data = self.cleaned_data
        amount = data.get('amount')
        desc = data.get('description')

        return source.make_transaction(destination, amount, desc)


class TransDestinationForm(BaseTransactionForm):
    """Form for making transaction between accounts with the destination unknown (chosen in the form)."""

    class Meta:
        model = Operation
        fields = ['amount', 'description', 'destination']

    destination = forms.ModelChoiceField(
        queryset=Account.objects.none(), label="Destination account", required=True)

    def make_transaction(self, source: Account):
        """Makes a transaction from the `source` Account to the destination as chosen in the form.
        
        Returns a tuple of `(outcoming, incoming)` transactions.
        """

        data = self.cleaned_data
        destination = data.get('destination')
        amount = data.get('amount')
        desc = data.get('description')

        return source.make_transaction(destination, amount, desc)

    def _update_destinations(self, source: Account):
        """Updates the form with the destinations avaiable to the passed Account."""

        self.fields['destination'].queryset = Account.objects.filter(
            home=source.home).exclude(id=source.id)

    @classmethod
    def from_account(cls, source: Account):
        """Creates a new form with destinations updated according to the Account.
        Returns the form.
        """

        form = cls()
        form._update_destinations(source)
        return form

    @classmethod
    def from_post(cls, source: Account, post: QueryDict):
        """Creates a form from the POST data with the destinations updated according to the Account.
        Returns the created form.
        """

        form = cls(post)
        form._update_destinations(source)
        return form


class RenameAccountForm(forms.ModelForm):
    """Form for changing the user actual name (not username)."""

    class Meta:
        model = User
        fields = ['first_name']

    @classmethod
    def from_account(cls, account: Account):
        """Creates a form with the default name set to the account's name.
        Returns the created form.
        """

        name = account.user.first_name or account.user.username

        form = cls()
        form.fields['first_name'].label = 'Name'
        form.fields['first_name'].initial = name
        return form