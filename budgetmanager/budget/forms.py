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
    """TODO"""

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
    """TODO"""

    class Meta:
        model = User
        fields = ['home_name', 'currency', 'username', 'password1', 'password2']

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
    """TODO"""

    choices = forms.MultipleChoiceField(
        choices={}, widget=forms.widgets.CheckboxSelectMultiple, label='Permissions', required=False)
    """TODO"""

    def change_perms(self, account: Account):
        """TODO"""

        choices = self.cleaned_data.get('choices')
        print(choices)
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
            print(
                f'{perm}, {app_perm}, {account.has_perm(app_perm)}, {perm in choices}')
            if perm[0] in choices and not account.has_perm(app_perm):
                account.add_perm(codename=perm[0])
            elif perm[0] not in choices and account.has_perm(app_perm):
                account.remove_perm(codename=perm[0])

    def update_choices(self, account: Account):
        """Updates the label choices according to the specified user Account.
        Returns the sorted list of all available choices as a tuple (codename, description)."""

        if account.is_mod():
            choices = MOD_PERMS
        else:
            choices = USER_PERMS

        choice_list = list(choices)
        choice_list.sort()
        self.fields['choices'].choices = choice_list

        return choices

    def update_initial(self, account: Account):
        """Updates the initially selected permissions according to the specified user Account.
        Returns the list of granted user permission descritpions."""

        choices = self.update_choices(account)
        # print(choices)
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
        print(total_list)
        return total_list


class TransactionForm(forms.ModelForm):
    """TODO"""

    class Meta:
        model = Operation
        fields = ['amount', 'description']

    def make_transaction(self, source: Account, destination: Account):
        """TODO"""

        if not source or not destination or source == destination:
            return None, None

        data = self.cleaned_data
        amount = abs(data.get('amount'))
        desc = data.get('description')

        return source.make_transaction(destination, amount, desc)


class TransDestinationForm(forms.ModelForm):
    """TODO"""

    class Meta:
        model = Operation
        fields = ['amount', 'description', 'destination']

    destination = forms.ModelChoiceField(
        queryset=Account.objects.none(), label="Destination account")

    def make_transaction(self, source: Account):
        """TODO"""

        data = self.cleaned_data
        destination = data.get('destination')
        amount = abs(data.get('amount'))
        desc = data.get('description')

        return source.make_transaction(destination, amount, desc)

    def update_destinations(self, source: Account):
        """TODO"""

        self.fields['destination'].queryset = Account.objects.filter(
            home=source.home).exclude(id=source.id)
