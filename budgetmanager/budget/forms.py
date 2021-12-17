from django import forms
from . import models


class AddOperationForm(forms.Form):

    finalized = forms.BooleanField(
        required=False, label='Should the operation be instantly finalized')

    amount = forms.DecimalField(max_value=999999.0, label='Money amount')

    description = forms.CharField(
        max_length=500, widget=forms.Textarea, required=False, label='Optional description')
