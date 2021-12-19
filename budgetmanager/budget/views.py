from django.http.request import HttpRequest
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import *
from . import forms


def index(request: HttpRequest):
    return render(request, 'budget/index.html')


@login_required(login_url='/login')
def user(request: HttpRequest):
    """Renders the User page."""

    context = {}
    redir = False

    if request.method == 'POST':
        post = request.POST
        form = forms.AddOperationForm(
            request.POST, instance=Operation(account=request.user.account))

        if post.get('rm_id') is not None:  # Remove an operation
            Operation.objects.get(id=post.get('rm_id')).delete()
            redir = True
        elif post.get('fin_id') is not None:  # Finalize an operation
            Operation.objects.get(id=post.get('fin_id')).finalize()
            redir = True
        elif post.get('add_operation') is not None:
            op = Operation(account=request.user.account)
            form = forms.AddOperationForm(post, instance=op)
            
            if form.is_valid():  # Create a new operation
                data = form.cleaned_data

                # Check if final or current amount isn't surpassing the limitations
                # Reply: Shouldn't the database take care of it? Raise an error for example.
                #   This can be put into an overriden form method
                added_amount = data.get('amount')
                current_money = request.user.account.current_amount
                final_money = request.user.account.final_amount
                if(abs(current_money + added_amount) < 1000000 and abs(final_money + added_amount) < 1000000):
                    form.save()
                    redir = True
                else:
                    redir = False
                    messages.error('Too much $$$')
                    # TODO: Add a message for the user that the min/max amont was surpassed
        elif post.get('add_pers_label') is not None:
            label = Label(home=request.user.account.home, account=request.user.account)
            form = forms.AddPersonalLabelForm(post, instance=label)

            if form.is_valid():
                form.save()
                redir = True

    context['operations'] = Operation.objects.filter(
        account=request.user.account).order_by('-id')[:5]
    context['final_amount'] = request.user.account.final_amount
    context['current_amount'] = request.user.account.current_amount
    
    context['add_op_form'] = forms.AddOperationForm()
    context['add_pers_label_form'] = forms.AddPersonalLabelForm()
    return redirect('/user') if redir else render(request, 'budget/user.html', context)


@login_required(login_url='/login')
def history(request: HttpRequest):
    """Renders the detailed history page."""

    context = {}
    redir = False

    if request.method == 'POST':
        op_id = request.POST.get('rm_id')
        fin_id = request.POST.get('fin_id')
        if op_id is not None:
            Operation.objects.get(id=op_id).delete()
            redir = True
        elif fin_id is not None:
            Operation.objects.get(id=fin_id).finalize()
            redir = True

    context['operations'] = Operation.objects.filter(
        account=request.user.account)

    return redirect('/history') if redir else render(request, 'budget/history.html', context)
