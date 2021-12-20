from django import forms
from django.contrib.auth.models import User
from .models import *
from django.utils import timezone


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
