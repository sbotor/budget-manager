from django.http.request import HttpRequest, QueryDict
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic.base import TemplateView

from .models import *
from . import forms


def index(request: HttpRequest):
    return render(request, 'budget/index.html')


@method_decorator(login_required(login_url='/login'), name='dispatch')
class UserPageView(TemplateView):

    def setup(self, request: HttpRequest, *args, **kwargs):
        self.user = request.user
        return super().setup(request, *args, **kwargs)


class UserView(UserPageView):

    template_name = 'budget/user.html'

    redirect_name = 'user_page'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['operations'] = Operation.objects.filter(
            account=self.user.account).order_by('-id')[:5]
        context['final_amount'] = self.user.account.final_amount
        context['current_amount'] = self.user.account.current_amount

        add_op_form = forms.AddOperationForm()
        add_op_form.update_label_choices(self.user)
        context['add_op_form'] = add_op_form

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        """Modifies the user page and renders it."""

        post = request.POST

        if post.get('rm_id') is not None:  # Remove an operation
            op_id = post.get('rm_id')
            Operation.objects.get(id=op_id).delete()
        elif post.get('fin_id') is not None:  # Finalize an operation
            op_id = post.get('fin_id')
            Operation.objects.get(id=op_id).finalize()
        elif post.get('add_operation') is not None:  # Add a new operation
            self.add_operation(post)

        return redirect(self.redirect_name)

    def add_operation(self, post: QueryDict):
        """Adds a new operation to the user Account."""

        op = Operation(account=self.user.account)
        form = forms.AddOperationForm(post, instance=op)

        if form.is_valid():  # Create a new operation
            data = form.cleaned_data

            # Check if final or current amount isn't surpassing the limitations
            # Reply: Shouldn't the database take care of it? Raise an error for example.
            #   This can be put into an overriden form method
            added_amount = data.get('amount')
            final_money = self.user.account.final_amount
            if(abs(final_money + added_amount) < 1000000):
                form.save()
            else:
                messages.error('Too much $$$')
                # TODO: Add a message for the user that the min/max amont was surpassed


class OpHistoryView(UserPageView):

    template_name = 'budget/history.html'

    redirect_name = 'user_history'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['operations'] = Operation.objects.filter(
            account=self.user.account)
        
        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        if request.POST.get('rm_id') is not None:
            op_id = request.POST.get('rm_id')
            Operation.objects.get(id=op_id).delete()
        elif request.POST.get('fin_id') is not None:
            op_id = request.POST.get('fin_id')
            Operation.objects.get(id=op_id).finalize()

        return redirect(self.redirect_name)


class UserLabelsView(UserPageView):
    template_name = 'budget/user_labels.html'

    redirect_name = 'user_labels'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['pers_labels'] = self.user.account.available_labels(include_home=False)
        context['home_labels'] = self.user.account.home.get_labels(home_only=True)
        
        context['add_pers_label_form'] = forms.AddPersonalLabelForm()
        
        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        
        if request.POST.get('add_pers_label') is not None:
            self.add_personal_label(request.POST)
        
        elif request.POST.get('pers_rm_id') is not None:
            label_id = request.POST.get('pers_rm_id')
            Label.objects.get(id=label_id).delete()
        
        elif request.POST.get('pers_rename_id') is not None:
            self.rename_personal_label(request.POST)
        
        return redirect(self.redirect_name)

    def add_personal_label(self, post: QueryDict):
        """Adds a new personal label to the user Account."""

        label = Label(home=self.user.account.home,
                      account=self.user.account)
        form = forms.AddPersonalLabelForm(post, instance=label)

        if form.is_valid():
            form.save()

    def rename_personal_label(self, post: QueryDict):
        label_id = post.get('pers_rename_id')
        label = Label.objects.get(id=label_id)
        form = forms.AddPersonalLabelForm(post, instance=label)

        if form.is_valid():
            form.save() 

class UserHomemateView(UserPageView):

    template_name = 'budget/home.html'

    redirect_name = 'user_homemates'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        return redirect(self.redirect_name)
