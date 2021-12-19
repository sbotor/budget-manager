from django import forms
from . import models
from django.utils import timezone


class AddOperationForm(forms.ModelForm):
    class Meta:
        model = models.Operation
        fields = ['finalized', 'amount', 'description', 'label']

    finalized = forms.BooleanField(
        required=False, label='Finalized')

    def save(self, commit: bool = True):
        """Overriden method to check if the operation should be finalized and update accordingly."""

        if self.cleaned_data.get('finalized'):
            self.instance.final_datetime = timezone.now()

        super().save(commit=commit)
        return self.instance

    #TODO: Labels

class AddPersonalLabelForm(forms.ModelForm):
    class Meta:
        model = models.Label
        fields = ['name']