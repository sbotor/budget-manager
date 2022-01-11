from abc import ABC
from django.http.request import HttpRequest
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views.generic.base import TemplateView
from django.contrib.auth.forms import UserCreationForm

from .models import *
from . import forms

from django.core import serializers


def index(request: HttpRequest):
    return render(request, 'budget/index.html')


class BaseTemplateView(TemplateView):
    """Base view for template rendering with context and convenient redirecting."""

    redirect_name = None
    """View redirect name."""

    def redirect(self):
        """Redirects to the specified view name."""

        return redirect(self.redirect_name)

    def update_context(self, context: dict = None, **kwargs):
        """Method adding passed keyword arguments to the view's extra_context."""

        if self.extra_context == None:
            self.extra_context = dict()

        if context:
            self.extra_context.update(context)
        if kwargs:
            self.extra_context.update(kwargs)


class AddHomeView(BaseTemplateView):

    template_name = 'registration/new_home.html'

    redirect_name = '/login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if context.get('form') is None:
            context['form'] = forms.HomeCreationForm()

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        form = forms.HomeCreationForm(request.POST)

        if form.is_valid():
            form.save()
            home_name = form.cleaned_data.get('home_name')
            messages.success(
                request, f'Home "{home_name}" was successfully created')

            return redirect(self.redirect_name)

        else:
            self.update_context(form=form)

            return render(request, self.template_name, self.get_context_data())


@method_decorator(login_required(login_url='/login'), name='setup')
class BaseUserView(ABC, BaseTemplateView):
    """Abstract class for user-specific view inheritance."""

    def setup(self, request: HttpRequest, *args, **kwargs):
        self.user = request.user
        super().setup(request, *args, **kwargs)


class UserView(BaseUserView):
    """Main user page view class."""

    template_name = 'budget/user/user.html'

    redirect_name = 'user_page'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['operations'] = Operation.objects.filter(
            account=self.user.account).order_by('-id')[:5]
        context['allOperations'] = Operation.objects.filter(
            account=self.user.account).order_by('-id')
        context['final_amount'] = self.user.account.final_amount
        context['current_amount'] = self.user.account.current_amount

        context['income'] = self.user.account.get_last_year_income()
        context['expenses'] = self.user.account.get_last_year_expenses()

        add_op_form = forms.AddOperationForm()
        add_op_form.update_label_choices(self.user)
        context['add_op_form'] = add_op_form

        trans_form = forms.TransDestinationForm()
        trans_form.update_destinations(self.user.account)
        context['transaction_form'] = trans_form

        context['make_transactions'] = self.user.has_perm(
            'budget.make_transactions')

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        """Modifies the user page and renders it."""

        post = request.POST

        #print(post.get('rm_id'))

        if post.get('rm_id') is not None:  # Remove an operation
            op_id = post.get('rm_id')
            Operation.objects.get(id=op_id).delete()

        elif post.get('fin_id') is not None:  # Finalize an operation
            op_id = post.get('fin_id')
            Operation.objects.get(id=op_id).finalize()

        elif post.get('add_operation') is not None:  # Add a new operation
            form = forms.AddOperationForm(post)
            if form.is_valid():
                op = form.save(commit=False)
                self.user.account.add_operation(operation=op)

        elif post.get('transaction') is not None:
            form = forms.TransDestinationForm(post)
            form.update_destinations(self.user.account)
            valid = False
            if form.is_valid():
                outcoming, incoming = form.make_transaction(
                    source=self.user.account)
                valid = outcoming and incoming
            if not valid:
                messages.error(request, 'Invalid transaction form.')

        return self.redirect()


class OpHistoryView(BaseUserView):
    """Full operation history view class."""

    template_name = 'budget/user/history.html'

    redirect_name = 'user_history'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['operations'] = Operation.objects.filter(
            account=self.user.account).order_by('-id')

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        if request.POST.get('rm_id') is not None:
            op_id = request.POST.get('rm_id')
            Operation.objects.get(id=op_id).delete()
        elif request.POST.get('fin_id') is not None:
            op_id = request.POST.get('fin_id')
            Operation.objects.get(id=op_id).finalize()

        return self.redirect()


class UserLabelsView(BaseUserView):
    """View for showing and editing user-specific labels."""

    template_name = 'budget/user/labels.html'

    redirect_name = 'user_labels'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['pers_labels'] = self.user.account.available_labels(
            include_home=False)
        context['home_labels'] = self.user.account.home.get_labels(
            home_only=True)

        context['add_label_form'] = forms.AddLabelForm()

        context['manage_home_labels'] = self.user.has_perm(
            'budget.manage_home_labels')

        return context

    # TODO
    def post(self, request: HttpRequest, *args, **kwargs):

        post = request.POST

        if post.get('add_pers_label') is not None:
            form = forms.AddLabelForm(post)
            if form.is_valid():
                label = form.save(commit=False)
                self.user.account.add_label(label=label)

        elif post.get('pers_rm_id') is not None:
            label_id = post.get('pers_rm_id')
            Label.objects.get(id=label_id).delete()

        elif post.get('pers_rename_id') is not None:
            form = forms.AddLabelForm(post)
            if form.is_valid():
                label_id = post.get('pers_rename_id')
                label = Label.objects.get(id=label_id)
                label.rename(new_name=form.cleaned_data.get('name'))

        elif post.get('add_home_label') is not None:
            form = forms.AddLabelForm(post)
            if form.is_valid():
                label = form.save(commit=False)
                self.user.account.home.add_label(label=label)

        elif post.get('home_rename_id') is not None:
            form = forms.AddLabelForm(post)
            if form.is_valid():
                label_id = post.get('home_rename_id')
                label = Label.objects.get(id=label_id)
                label.rename(new_name=form.cleaned_data.get('name'))

        elif post.get('home_rm_id') is not None:
            label_id = post.get('home_rm_id')
            Label.objects.get(id=label_id).delete()

        elif post.get('home_default') is not None:
            keep = post.get('home_default') == 'keep'
            self.user.account.home.create_predefined_labels(keep_custom=keep)

        return self.redirect()


class CyclicOperationsView(BaseUserView):
    """TODO"""

    template_name = 'budget/user/planned_operations.html'

    redirect_name = 'planned_operations'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['operations'] = OperationPlan.objects.filter(
            account=self.user.account).order_by('-id')

        form = forms.PlanCyclicOperationForm()
        form.update_label_choices(self.user)
        context['add_cyclic_op_form'] = form

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        post = request.POST

        if post.get('rm_id') is not None:
            op_id = post.get('rm_id')
            OperationPlan.objects.get(id=op_id).delete()

        elif post.get('add_cyclic_op') is not None:
            form = forms.PlanCyclicOperationForm(post)
            if form.is_valid():
                plan = form.save(commit=False)
                self.user.account.add_operation_plan(plan=plan)

        return self.redirect()


class BaseHomeView(BaseUserView):
    """Abstract class serving as base for Home-oriented views."""

    def setup(self, request: HttpRequest, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.home = self.user.account.home


class HomeView(BaseHomeView):
    """Class for the user's Home view."""

    template_name = 'budget/home/home.html'

    redirect_name = 'user_home'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['new_user_form'] = UserCreationForm()
        context['transaction_form'] = forms.TransactionForm()
        context['accounts'] = Account.objects.filter(
            home=self.home).order_by('user__username')

        context['manage_users'] = self.user.has_perm('budget.manage_users')
        context['see_other_accounts'] = self.user.has_perm(
            'budget.see_other_accounts')
        context['make_transactions'] = self.user.has_perm(
            'budget.make_transactions')

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        post = request.POST

        if post.get('rm_id'):
            acc_id = post.get('rm_id')
            Account.objects.get(id=acc_id).delete()

        elif post.get('create') is not None:
            self._create_user()

        elif post.get('transaction') is not None:
            form = forms.TransactionForm(post)
            destination = Account.objects.get(id=post.get('transaction'))
            valid = False
            if form.is_valid():
                outcoming, incoming = form.make_transaction(
                    source=self.user.account, destination=destination)
                valid = outcoming and incoming
            if not valid:
                messages.error('Invalid transaction form.')

        return self.redirect()

    def _create_user(self):
        request = self.request
        form = UserCreationForm(request.POST)
        if form.is_valid():
            home = request.user.account.home
            account = Account(home=home)
            user = form.save()

            account.user = user
            account.save()

            messages.success(
                request, f'User "{user.username}" was successfully created')

            return account
        else:
            messages.error(request, 'Invalid user form.')
            return None


class ManageUserView(BaseHomeView):
    """TODO"""

    template_name = 'budget/home/manage_user.html'

    def setup(self, request: HttpRequest, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        try:
            self.managed_acc = User.objects.get(
                username=kwargs['username']).account
            self.update_context(managed_acc=self.managed_acc)

            self.redirect_name = f'/home/{self.managed_acc.user.username}'
        except User.DoesNotExist or Account.DoesNotExist:
            self.managed_acc = None

    def _check_account(self, account: Account):
        """TODO"""

        return self.managed_acc.home == account.home and self.user.has_perm('budget.manage_users') and self.managed_acc != account

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        if not self.managed_acc:
            return redirect('/')

        acc = request.user.account

        if self._check_account(acc):
            return super().dispatch(request, *args, **kwargs)
        else:
            return redirect('/')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['managed_acc'] = self.managed_acc

        context['is_mod'] = self.managed_acc.is_mod()
        form = forms.ChangeUserPermissionsForm()
        form.update_initial(self.managed_acc)
        context['perm_form'] = form

        #print(form.fields)

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        post = request.POST

        #print(post)

        if post.get('change') is not None:
            self._change_perms()

        elif post.get('make_mod') is not None:
            self.home.add_mod(self.managed_acc)

        elif post.get('remove_mod') is not None:
            self.home.remove_mod(self.managed_acc)

        elif post.get('remove') is not None:
            self.managed_acc.delete()
            return redirect(HomeView.redirect_name)

        return self.redirect()

    def _change_perms(self):
        """TODO"""

        form = forms.ChangeUserPermissionsForm(self.request.POST)
        form.update_choices(self.managed_acc)

        if form.is_valid():
            form.change_perms(self.managed_acc)
        else:
            messages.error(self.request, "Invalid user permissions form.")
            #print(form.errors.as_text())
