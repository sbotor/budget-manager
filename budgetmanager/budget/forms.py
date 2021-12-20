from django import forms
from django.contrib.auth.models import User
from .models import *
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm


class AddOperationForm(forms.ModelForm):
    class Meta:
        model = Operation
        fields = ['finalized', 'amount', 'description', 'label']

    finalized = forms.BooleanField(required=False, label='Finalized')

    def update_label_choices(self, user: User):
        self.fields['label'] = forms.ModelChoiceField(
            queryset=user.account.available_labels(),
            empty_label='No label',
            required=False)

    def save(self, commit: bool = True):
        """Overriden method to check if the operation should be finalized and update accordingly."""

        if self.cleaned_data.get('finalized'):
            self.instance.final_date = timezone.now().date()

        return super().save(commit=commit)


class PlanCyclicOperationForm(forms.ModelForm):
    """This form is used to plan a new cyclic operation."""

    class Meta:
        model = OperationPlan
        fields = ['period', 'period_count', 'start_date']

    # TODO: add a validator against a past date
    start_date = forms.DateField(label="Starting day")

    def save(self, commit: bool = True):
        """Overriden method to calculate the next starting date."""

        data = self.cleaned_data
        if data.get('start_date') == timezone.now().date():
            if commit:
                self.instance.create_operation()
            
            self.instance.next_date = self.instance.calculate_next(
                base_date=timezone.now().date())
        else:
            self.instance.next_date = self.instance.calculate_next(
                data.get('start_date'))

        return super().save(commit=commit)


class AddPersonalLabelForm(forms.ModelForm):
    """Used to create a new personal label."""

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