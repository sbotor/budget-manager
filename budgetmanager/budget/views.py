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
    """Renders the Home page."""

    if request.user.is_authenticated:
        context = {}
        redir = False

        if request.method == 'POST':
            op_id = request.POST.get('rm_id')
            fin_id = request.POST.get('fin_id')
            form = forms.AddOperationForm(request.POST)

            if op_id is not None:
                Operation.objects.get(id=op_id).delete()
                redir = True
            elif fin_id is not None:
                Operation.objects.get(id=fin_id).finalize()
                redir = True
            elif form.is_valid():
                data = form.cleaned_data
                final_datetime = timezone.now() if data.get('finalized') else None

                #Check if final or current amount isn't surpassing the limitations
                added_amount = data.get('amount')
                current_money = request.user.account.current_amount
                final_money = request.user.account.final_amount
                if(abs(current_money + added_amount) < 1000000 and abs(final_money + added_amount) < 1000000):
                    request.user.account.operation_set.create(amount=data.get('amount'),
                        final_datetime=final_datetime, description=data.get('description'))
                    redir = True
                else:
                    redir = False
                    #TODO: Add a message for the user that the min/max amont was surpassed

        context['operations'] = Operation.objects.filter(
            account=request.user.account)[:10:-1]
        context['final_amount'] = request.user.account.final_amount
        context['current_amount'] = request.user.account.current_amount
        context['add_op_form'] = forms.AddOperationForm()
        return redirect('/user') if redir else render(request, 'budget/user.html', context)

    else:
        messages.error(request, 'You are not authorized to view this page.')
        return render(request, 'budget/index.html')


@login_required(login_url='/login')
def history(request:HttpRequest):
    if request.user.is_authenticated:
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
    else:
        messages.error(request, 'You are not authorized to view this page.')
        return render(request, 'budget/index.html')