from django import forms
from . import models


class AddOperationForm(forms.Form):

    finalized = forms.BooleanField(
        required=False, label='Finalized')

    amount = forms.DecimalField(max_value=999999.0, label='Money amount')

    description = forms.CharField(
        max_length=500, widget=forms.Textarea, required=False, label='Optional description')
