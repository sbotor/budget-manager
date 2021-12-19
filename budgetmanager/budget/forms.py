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
            self.instance.final_datetime = timezone.now()

        super().save(commit=commit)
        return self.instance


class AddPersonalLabelForm(forms.ModelForm):
    class Meta:
        model = Label
        fields = ['name']
        