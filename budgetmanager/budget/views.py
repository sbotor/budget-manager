from abc import ABC
from django import dispatch
from django.http.request import HttpRequest
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic.base import TemplateView
from django.contrib.auth.forms import UserCreationForm

from .models import *
from . import forms
from .decorators import home_required


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
    """TODO"""

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


@method_decorator(
    (login_required(), home_required()),
    name='dispatch')
class BaseUserView(ABC, BaseTemplateView):
    """Abstract class for user-specific view inheritance."""

    def setup(self, request: HttpRequest, *args, **kwargs):
        self.user = request.user

        super().setup(request, *args, **kwargs)

    def _add_operation(self):
        """Adds the operation from the POST data if valid. Returns True if successful."""

        form = forms.AddOperationForm(self.request.POST)
        if form.is_valid():
            op = form.save(commit=False)
            self.user.account.add_operation(operation=op)
            return True

        else:
            return False

    def _rm_op(self, op_id: int):
        """Removes an operation if it belongs to the user."""

        op = Operation.objects.get(id=op_id)
        if op.account == self.user.account:
            op.delete()
        # TODO: error message if wrong user

    def _fin_op(self, op_id: int):
        """Finalizes an operation if it belongs to the user."""

        op = Operation.objects.get(id=op_id)
        if op.account == self.user.account:
            op.finalize()
        # TODO: error

    def _make_transaction(self):
        """Makes a transaction based on the POST data."""

        form = forms.TransDestinationForm.from_post(self.user.account, self.request.POST)
        valid = False
        if form.is_valid():
            outcoming, incoming = form.make_transaction(
                source=self.user.account)
            valid = outcoming and incoming
        if not valid:
            messages.error(self.request, 'Invalid transaction form.')


class UserView(BaseUserView):
    """Main user page view class."""

    template_name = 'budget/user/user.html'

    redirect_name = 'user_page'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['operations'] = self.user.account.get_operations()[:5]
        context['allOperations'] = self.user.account.get_operations().order_by('-id')
        context['final_amount'] = self.user.account.final_amount
        context['current_amount'] = self.user.account.current_amount

        context['income'] = self.user.account.get_last_year_income()
        context['expenses'] = self.user.account.get_last_year_expenses()

        add_op_form = forms.AddOperationForm.from_account(self.user.account)
        context['add_op_form'] = add_op_form

        trans_form = forms.TransDestinationForm.from_account(self.user.account)
        context['transaction_form'] = trans_form

        context['make_transactions'] = self.user.has_perm(
            'budget.make_transactions')

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        """Modifies the user page and renders it."""

        post = request.POST

        if post.get('rm_id') is not None:  # Remove an operation
            op_id = post.get('rm_id')
            self._rm_op(op_id)

        elif post.get('fin_id') is not None:  # Finalize an operation
            op_id = post.get('fin_id')
            self._fin_op(op_id)

        elif post.get('add_operation') is not None:  # Add a new operation
            self._add_operation()

        elif post.get('transaction') is not None:
            self._make_transaction()

        return self.redirect()


class OpHistoryView(BaseUserView):
    """Full operation history view class."""

    template_name = 'budget/user/history.html'

    redirect_name = 'user_history'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(kwargs=kwargs)

        context['operations'] = self.user.account.get_operations()

        add_op_form = forms.AddOperationForm.from_account(self.user.account)
        context['add_op_form'] = add_op_form

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        if request.POST.get('rm_id') is not None:
            op_id = request.POST.get('rm_id')
            self._rm(op_id)

        elif request.POST.get('fin_id') is not None:
            op_id = request.POST.get('fin_id')
            self._fin_op(op_id)

        elif request.POST.get('fin_all') is not None:
            self.user.account.finalize_operations()

        elif request.POST.get('add_operation') is not None:  # Add a new operation
            self._add_operation()

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

    def post(self, request: HttpRequest, *args, **kwargs):

        post = request.POST

        if post.get('add_pers_label') is not None:
            self._add_pers_label()

        elif post.get('pers_rm_id') is not None:
            label_id = post.get('pers_rm_id')
            self._rm_pers_label(label_id)

        elif post.get('pers_rename_id') is not None:
            self._rename_pers_label()

        elif post.get('add_home_label') is not None:
            self._add_home_label()

        elif post.get('home_rename_id') is not None:
            self._rename_home_label()

        elif post.get('home_rm_id') is not None:
            label_id = post.get('home_rm_id')

        elif post.get('home_default') is not None:
            keep = post.get('home_default') == 'keep'
            self._restore_home_labels(keep=keep)

        return self.redirect()

    def _add_pers_label(self):
        """Adds a personal label to the user account."""

        form = forms.AddLabelForm(self.request.POST)
        if form.is_valid():
            label = form.save(commit=False)
            self.user.account.add_label(label=label)
        else:
            pass  # TODO

    def _rm_pers_label(self, label_id: str):
        """Removes a personal label if it belongs to the user account."""

        labl = Label.objects.get(id=label_id)
        if labl.account == self.user.account:
            labl.delete()
        else:
            pass  # TODO

    def _rename_pers_label(self):
        """Renames a personal label if it belongs to the user account."""

        post = self.request.POST
        form = forms.AddLabelForm(post)
        if form.is_valid():
            label_id = post.get('pers_rename_id')
            label = Label.objects.get(id=label_id)
            if label.account == self.user.account:
                label.rename(new_name=form.cleaned_data.get('name'))

    def _add_home_label(self):
        """Adds a new home label if the user has the permissions."""

        form = forms.AddLabelForm(self.request.POST)
        if form.is_valid():
            label = form.save(commit=False)
            if self.user.has_perm('budget.manage_home_labels'):
                self.user.account.home.add_label(label=label)
            else:
                pass  # TODO

    def _rename_home_label(self):
        """Renames the home label."""

        post = self.request.POST
        form = forms.AddLabelForm(post)
        if form.is_valid():
            label_id = post.get('home_rename_id')
            label = Label.objects.get(id=label_id)
            if self.user.has_perm('budget.manage_home_labels') and label.home == self.user.account.home:
                label.rename(new_name=form.cleaned_data.get('name'))

    def _rm_home_label(self, label_id: str):
        """Removes a new home label if the user has the permissions."""

        label = Label.objects.get(id=label_id)
        if self.user.has_perm('budget.manage_home_labels') and label.home == self.user.account.home:
            label.delete()
        else:
            pass  # TODO

    def _restore_home_labels(self, keep: bool):
        """Restores the default home labels."""

        if self.user.has_perm('budget.manage_home_labels'):
            self.user.account.home.create_predefined_labels(keep_custom=keep)


class CyclicOperationsView(BaseUserView):
    """TODO"""

    template_name = 'budget/user/planned_operations.html'

    redirect_name = 'planned_operations'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['operations'] = self.user.account.get_plans()

        form = forms.PlanCyclicOperationForm.from_account(self.user.account)
        context['add_cyclic_op_form'] = form

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        post = request.POST

        if post.get('rm_id') is not None:
            op_id = post.get('rm_id')
            self._rm_plan(op_id)

        elif post.get('add_cyclic_op') is not None:
            self._add_plan()

        return self.redirect()

    def _rm_plan(self, op_id: int):
        """Removes the operation plan."""

        op = OperationPlan.objects.get(id=op_id)
        if op.account == self.user.account:
            op.delete()
        else:
            pass  # TODO

    def _add_plan(self):
        """Adds a new operation plan."""

        form = forms.PlanCyclicOperationForm(self.request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            self.user.account.add_operation_plan(plan=plan)


class BaseHomeView(BaseUserView):
    """Abstract class serving as base for Home-oriented views."""

    def setup(self, request: HttpRequest, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        usr = self.user
        if usr.is_authenticated and hasattr(usr, 'account') and hasattr(usr.account, 'home'):
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
            self._rm_account(acc_id)

        elif post.get('create') is not None:
            self._create_user()

        elif post.get('transaction') is not None:
            self._make_transaction()

        return self.redirect()

    def _rm_account(self, acc_id: int):
        """Removes a user account."""

        acc = Account.objects.get(id=acc_id)

        if self.user.has_perm('budget.manage_users') and self.home == acc.home:
            if self.user.account.is_admin():
                acc.delete()
            elif self.user.account.is_mod() and not acc.is_mod():
                acc.delete()
            elif not acc.is_mod():
                acc.delete()
        else:
            pass  # TODO

    def _create_user(self):
        request = self.request
        form = UserCreationForm(request.POST)
        if form.is_valid():
            home = self.home
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

    def _make_transaction(self):
        """Makes a transaction to the specified user."""

        if not self.user.has_perm('budget.make_transactions'):
            return  # TODO

        post = self.request.POST
        form = forms.TransactionForm(post)
        destination = Account.objects.get(id=post.get('transaction'))
        valid = False
        if form.is_valid():
            outcoming, incoming = form.make_transaction(
                source=self.user.account, destination=destination)
            valid = outcoming and incoming
        if not valid:
            messages.error('Invalid transaction form.')


@method_decorator(
    (login_required(), home_required()),
    name='dispatch')
class AccountView(BaseUserView):
    """View for managing one\'s own Account."""

    template_name = 'budget/home/profile_options.html'

    def setup(self, request: HttpRequest, *args, **kwargs):
        super().setup(request, args, kwargs)

        username = kwargs.get('username')
        if self.user.username == username:
            self.redirect_name = f'/home/{username}'
        else:
            self.redirect_name = None

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        if self.redirect_name:
            return super().dispatch(request, args, kwargs)

        return redirect('/home')

    def post(self, request: HttpRequest, *args, **kwargs):
        pass


@method_decorator(
    (login_required(), home_required(), permission_required('budget.manage_users')),
    name='dispatch')
class ManageUserView(BaseHomeView):
    """View for managing a specific user."""

    template_name = 'budget/home/manage_user.html'

    def setup(self, request: HttpRequest, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        try:
            self.managed_acc = User.objects.get(
                username=kwargs['username']).account
            self.update_context(managed_acc=self.managed_acc)

            self.redirect_name = f'/home/{self.managed_acc.user.username}'
        except User.DoesNotExist or Account.DoesNotExist or AttributeError:
            self.managed_acc = None
            self.redirect_name = '/home/'

    def _check_account(self, account: Account | None = None):
        """Checks if the account is in the same Home as the request's user and if both accounts are different."""

        account = account or self.managed_acc

        return self.user.account != account and self.home == account.home

    def _check_account_and_perm(self, account: Account | None = None):
        """Same as `_check_account()` but checks if the user has the `manage_users` permission."""

        return self.user.has_perm('budget.manage_users') and self._check_account(account)

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        if self.managed_acc and self._check_account_and_perm():
            return super().dispatch(request, *args, **kwargs)

        if self.user.account == self.managed_acc:
            return AccountView.as_view()(request, args, kwargs)

        return redirect('/home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['managed_acc'] = self.managed_acc

        context['is_mod'] = self.managed_acc.is_mod()
        context['make_mod'] = self.user.has_perm('budget.make_mod')

        form = forms.ChangeUserPermissionsForm.from_account(self.managed_acc)
        context['granted_perms'] = form.all_perms
        context['perm_form'] = form

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        post = request.POST

        if post.get('change') is not None:
            self._change_perms()

        elif post.get('make_mod') is not None:
            self._add_mod()

        elif post.get('remove_mod') is not None:
            self._rm_mod()

        elif post.get('remove') is not None:
            return self._rm_user()

        elif post.get('pass_admin') is not None:
            return self._pass_admin()

        return self.redirect()

    def _change_perms(self):
        """Changes the user permissions"""

        if not self._check_account_and_perm():
            return  # TODO

        if self.managed_acc.is_mod() and not self.user.account.is_admin():
            return  # TODO

        form = forms.ChangeUserPermissionsForm.from_post(self.managed_acc, self.request.POST)
        if form.is_valid():
            form.change_perms(self.managed_acc)
        else:
            messages.error(self.request, "Invalid user permissions form.")

    def _pass_admin(self):
        """Gives the admin role to another user."""

        if not self._check_account():
            return redirect('/')  # TODO

        if self.user.account.is_admin():
            self.home.change_admin(self.managed_acc)
            for perm in MOD_PERMS:
                self.user.account.add_perm(perm[0])
            return redirect('/home')
        else:
            return redirect('/')  # TODO

    def _add_mod(self):
        """Adds a new home moderator."""

        if self._check_account() and self.user.has_perm('budget.make_mod') and not self.managed_acc.is_mod():
            self.home.add_mod(self.managed_acc)
        else:
            pass  # TODO

    def _rm_mod(self):
        """Removes a home mod."""

        if self._check_account() and self.user.has_perm('budget.make_mod') and self.managed_acc.is_mod():
            self.home.remove_mod(self.managed_acc)
        else:
            pass  # TODO

    def _rm_user(self):
        """Removes a user."""

        if self._check_account_and_perm():
            if self.managed_acc.is_mod() and self.user.account.is_admin():
                self.managed_acc.delete()
        return redirect(HomeView.redirect_name)
