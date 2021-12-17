from django.http.request import HttpRequest
from django.shortcuts import render, redirect
from django.utils import timezone
from .models import *
from . import forms


def index(request: HttpRequest):
    """Renders the homepage."""

    if request.user.is_authenticated:
        context = {}
        redir = False

        if request.method == 'POST':
            op_id = request.POST.get('rm_id')
            form = forms.AddOperationForm(request.POST)

            if op_id is not None:
                Operation.objects.get(id=op_id).delete()
                redir = True
            elif form.is_valid():
                data = form.cleaned_data
                final_datetime = timezone.now() if data.get('finalized') else None
                request.user.account.operation_set.create(amount=data.get('amount'),
                    final_datetime=final_datetime, description=data.get('description'))
                redir = True

        #request.user.account.operation_set.create(amount=10.0, description="Test")
        context['operations'] = Operation.objects.filter(
            account=request.user.account)[:10:-1]
        context['final_amount'] = request.user.account.final_amount
        context['current_amount'] = request.user.account.current_amount
        context['add_op_form'] = forms.AddOperationForm()

        return redirect('/') if redir else render(request, 'budget/index.html', context)

    else:
        return render(request, 'budget/index.html')
