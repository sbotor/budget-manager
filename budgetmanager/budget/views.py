from abc import ABC
from django.http.request import HttpRequest
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic.base import TemplateView, View
from django.contrib.auth.forms import UserCreationForm
import json

from .models import *
from . import forms
from .decorators import home_required


def index(request: HttpRequest):
    return render(request, 'budget/index.html')


@method_decorator(
    (login_required(), home_required(),
     permission_required('budget.plan_for_others')),
    name='dispatch')
class ViewAsView(View):
    """View for managin operations as another user. It serves mostly as a session-changing redirect."""

    def post(self, request: HttpRequest, *args, **kwargs):

        post = request.POST
        if post.get('begin') is not None:
            return self._begin()
        elif post.get('end') is not None:
            return self._end()

        return redirect('/')

    def _begin(self):
        "Starts a new view as session."

        request = self.request
        username = request.POST.get('begin')

        try:
            view_account = User.objects.filter(username=username).get().account
            if not request.user.has_perm('budget.plan_for_others') or request.user.account.home != view_account.home:
                messages.error(request, 'Cannot perform view as.')

            request.session['view_as'] = view_account.user.username

            return redirect(UserView.redirect_name)

        except User.DoesNotExist or Account.DoesNotExist or AttributeError:
            messages.error(request, 'Problem performing view as.')
            return redirect('/')

    def _end(self):
        """Ends the view as session."""

        request = self.request
        if request.session.get('view_as'):
            del request.session['view_as']

        return redirect('/home')


class BaseTemplateView(TemplateView):
    """Base view for template rendering with context and convenient redirecting."""

    redirect_name = None
    """View redirect name."""

    def redirect(self):
        """Redirects to the specified view name."""

        return redirect(self.redirect_name)

    def render(self):
        """Renders the page with appropriate context."""

        return render(self.request, self.template_name, self.get_context_data())

    def update_context(self, context: dict = None, **kwargs):
        """Method adding passed keyword arguments to the view's extra_context."""

        if self.extra_context == None:
            self.extra_context = dict()

        if context:
            self.extra_context.update(context)
        if kwargs:
            self.extra_context.update(kwargs)


class AddHomeView(BaseTemplateView):
    """View for adding a new Home and Administrator."""

    template_name = 'registration/new_home.html'

    redirect_name = '/login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form = context.get('form')
        context['form'] = form or forms.HomeCreationForm()

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        form = forms.HomeCreationForm(request.POST)

        if form.is_valid():
            form.save()
            home_name = form.cleaned_data.get('home_name')
            messages.success(request, f'Home "{home_name}" was successfully created')

            return redirect(self.redirect_name)

        else:
            self.update_context(form=form)

            return self.render()


@method_decorator(
    (login_required(), home_required()),
    name='dispatch')
class BaseUserView(ABC, BaseTemplateView):
    """Abstract class for user-specific view inheritance."""

    def setup(self, request: HttpRequest, *args, **kwargs):

        view_as = request.session.get('view_as')
        if view_as:
            self.user = User.objects.filter(username=view_as).get()
            self.actual_user = request.user
        else:
            self.user = request.user
            self.actual_user = None

        super().setup(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['view_as'] = self.user.account if self.actual_user else None
        context['user'] = self.user

        return context

    def _add_operation(self):
        """Adds the operation from the POST data if valid. Returns True if successful."""

        form = forms.AddOperationForm(self.request.POST)
        if form.is_valid():
            op = form.save(commit=False)
            self.user.account.add_operation(operation=op)
            messages.success(self.request, 'Operation added.')
            return self.redirect()

        else:
            self.update_context(add_op_form=form)
            messages.error(self.request, 'Invalid operation form.')
            return self.render()

    def _rm_op(self, op_id: int):
        """Removes an operation if it belongs to the user."""

        op = Operation.objects.get(id=op_id)
        if op.account == self.user.account:
            op.delete()
            messages.success(self.request, 'Operation removed.')
            return self.redirect()
        else:
            messages.error(self.request, 'Cannot remove someone else\'s operation.')
            return self.redirect()

    def _fin_op(self, op_id: int):
        """Finalizes an operation if it belongs to the user."""

        op = Operation.objects.get(id=op_id)
        if op.account == self.user.account:
            op.finalize()
            messages.success(self.request, 'Operation finalized.')
            return self.redirect()
        else:
            messages.error(self.request, 'Cannot finalize someone else\'s operation.')
            return self.redirect()

    def _make_transaction(self):
        """Makes a transaction based on the POST data."""

        form = forms.TransDestinationForm.from_post(
            self.user.account, self.request.POST)
        valid = False
        if form.is_valid():
            outcoming, incoming = form.make_transaction(
                source=self.user.account)
            valid = outcoming and incoming

        if valid:
            messages.success(self.request, 'Transaction made.')
            return self.redirect()
        else:
            self.update_context(transaction_form=form)
            messages.error(self.request, 'Invalid transaction form.')
            return self.render()


class UserView(BaseUserView):
    """Main user page view class."""

    template_name = 'budget/user/user.html'

    redirect_name = 'user_page'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['operations'] = self.user.account.get_operations()[:5]
        context['final_amount'] = self.user.account.final_amount
        context['current_amount'] = self.user.account.current_amount

        add_op_form = context.get(
            'add_op_form') or forms.AddOperationForm.from_account(self.user.account)
        context['add_op_form'] = add_op_form

        trans_form = context.get(
            'transaction_form') or forms.TransDestinationForm.from_account(self.user.account)
        context['transaction_form'] = trans_form

        context['make_transactions'] = self.user.has_perm(
            'budget.make_transactions')

        self._update_chart_data(context)

        return context

    def _update_chart_data(self, context: dict):
        """Updates the chart data for the user."""

        context['allOperations'] = self.user.account.get_operations().order_by('-id')

        income_string = [str(el)
                         for el in self.user.account.get_this_year_income()]
        context['income'] = ','.join(income_string)

        expenses_string = [str(el)
                           for el in self.user.account.get_this_year_expenses()]
        context['expenses'] = ','.join(expenses_string)

        context['operation_data'] = self._get_operations_json()

    def _get_operations_json(self):
        """Creates a JSON of this month\'s operations."""

        operations = self.user.account.get_this_month_operations()
        op_list = []

        for op in operations:
            op_list.append(json.dumps({
                'amount': str(op.amount),
                'label': [str(op.label.id), str(op.label)] if op.label else ['0', 'No label'],
            }))

        return json.dumps(op_list)

    def post(self, request: HttpRequest, *args, **kwargs):
        """Modifies the user page and renders it."""

        post = request.POST

        if post.get('rm_id') is not None:  # Remove an operation
            op_id = post.get('rm_id')
            return self._rm_op(op_id)

        elif post.get('fin_id') is not None:  # Finalize an operation
            op_id = post.get('fin_id')
            return self._fin_op(op_id)

        elif post.get('add_operation') is not None:  # Add a new operation
            return self._add_operation()

        elif post.get('transaction') is not None:
            return self._make_transaction()

        elif post.get('refresh') is not None:
            self.user.account.recalculate_amounts()

        return self.redirect()


class OpHistoryView(BaseUserView):
    """Full operation history view class."""

    template_name = 'budget/user/history.html'

    redirect_name = 'user_history'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(kwargs=kwargs)

        context['operations'] = self.user.account.get_operations()

        add_op_form = context.get(
            'add_op_form') or forms.AddOperationForm.from_account(self.user.account)
        context['add_op_form'] = add_op_form

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        if request.POST.get('rm_id') is not None:
            op_id = request.POST.get('rm_id')
            return self._rm_op(op_id)

        elif request.POST.get('fin_id') is not None:
            op_id = request.POST.get('fin_id')
            return self._fin_op(op_id)

        elif request.POST.get('fin_all') is not None:
            self.user.account.finalize_operations()

        elif request.POST.get('add_operation') is not None:
            return self._add_operation()

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

        add_label_form = context.get('add_label_form') or forms.AddLabelForm()
        context['add_label_form'] = add_label_form

        context['manage_home_labels'] = self.user.has_perm(
            'budget.manage_home_labels')

        return context

    def post(self, request: HttpRequest, *args, **kwargs):

        post = request.POST

        if post.get('add_pers_label') is not None:
            return self._add_pers_label()

        elif post.get('pers_rm_id') is not None:
            label_id = post.get('pers_rm_id')
            return self._rm_pers_label(label_id)

        elif post.get('pers_rename_id') is not None:
            return self._rename_pers_label()

        elif post.get('add_home_label') is not None:
            return self._add_home_label()

        elif post.get('home_rename_id') is not None:
            return self._rename_home_label()

        elif post.get('home_rm_id') is not None:
            label_id = post.get('home_rm_id')
            return self._rm_home_label(label_id)

        elif post.get('home_default') is not None:
            keep = post.get('home_default') == 'keep'
            return self._restore_home_labels(keep=keep)

        return self.redirect()

    def _add_pers_label(self):
        """Adds a personal label to the user account."""

        label_count = Label.objects.filter(account=self.user.account).count()
        if label_count >= Account.MAX_LABELS:
            messages.error(self.request, f'Maximum number of personal labels reached ({Account.MAX_LABELS}).')
            return self.redirect()

        form = forms.AddLabelForm(self.request.POST)
        if form.is_valid():
            label = form.save(commit=False)
            added = self.user.account.add_label(label=label)
            if added:
                messages.success(self.request, 'Label added.')
            else:
                messages.error(self.request, f'Label "{label.name}" already exists.')

            return self.redirect()
        else:
            self.update_context(add_label_form=form)
            messages.error(self.request, "Invalid label form.")
            return self.render()

    def _rm_pers_label(self, label_id: str):
        """Removes a personal label if it belongs to the user account."""

        labl = Label.objects.get(id=label_id)
        if labl.account == self.user.account:
            labl.delete()
            messages.success(self.request, 'Label removed.')
        else:
            messages.error(self.request, 'Cannot delete someone else\'s label.')

        return self.redirect()

    def _rename_pers_label(self):
        """Renames a personal label if it belongs to the user account."""

        post = self.request.POST
        form = forms.AddLabelForm(post)
        if form.is_valid():
            label_id = post.get('pers_rename_id')
            label = Label.objects.get(id=label_id)
            new_name = form.cleaned_data.get('name')
            if label.account == self.user.account:
                if label.rename(new_name=new_name):
                    messages.success(self.request, 'Label renamed.')
                else:
                    messages.error(self.request, f'Label "{new_name}" already exists.')

            return self.redirect()
        else:
            self.update_context(add_label_form=form)
            messages.error(self.request, 'Invalid label form.')
            return self.render()

    def _add_home_label(self):
        """Adds a new home label if the user has the permissions."""

        label_count = self.user.account.home.get_labels(home_only=True).exclude(is_default=True).count()
        if label_count >= Home.MAX_LABELS:
            messages.error(self.request, f'Maximum number of non-default Home labels reached ({Home.MAX_LABELS}).')
            return self.redirect()
        
        form = forms.AddLabelForm(self.request.POST)
        if form.is_valid():
            label = form.save(commit=False)
            if self.user.has_perm('budget.manage_home_labels'):
                added = self.user.account.home.add_label(label=label)
                if added:
                    messages.success(self.request, 'Added a new home label.')
                else:
                    messages.error(self.request, f'Label "{label.name}" already exists.')
            else:
                messages.error(self.request, 'Cannot delete home label.')

            return self.redirect()
        else:
            self.update_context(add_label_form=form)
            messages.error(self.request, 'Invalid label form.')
            return self.render()

    def _rename_home_label(self):
        """Renames the home label."""

        post = self.request.POST
        form = forms.AddLabelForm(post)
        if form.is_valid():
            label_id = post.get('home_rename_id')
            label = Label.objects.get(id=label_id)
            new_name = form.cleaned_data.get('name')

            if self.user.has_perm('budget.manage_home_labels') and label.home == self.user.account.home:

                if label.rename(new_name=new_name):
                    messages.success(self.request, 'Label renamed.')
                else:
                    messages.error(self.request, f'Label "{new_name}" already exists.')
            else:
                messages.error(self.request, 'Cannot rename the home label.')

            return self.redirect()
        else:
            self.update_context(add_label_form=form)
            messages.error(self.request, 'Invalid label form.')
            return self.render()

    def _rm_home_label(self, label_id: str):
        """Removes a new home label if the user has the permissions."""

        label = Label.objects.get(id=label_id)
        if self.user.has_perm('budget.manage_home_labels') and label.home == self.user.account.home:
            label.delete()
            messages.success(self.request, 'Label removed.')
        else:
            messages.error(self.request, 'Cannot remove home label.')

        return self.redirect()

    def _restore_home_labels(self, keep: bool):
        """Restores the default home labels."""

        if self.user.has_perm('budget.manage_home_labels'):
            self.user.account.home.create_predefined_labels(keep_custom=keep)
            messages.success(self.request, 'Default labels restored.')
        else:
            messages.error(self.request, 'Cannot restore default labels.')

        return self.redirect()


class CyclicOperationsView(BaseUserView):
    """View for managing cyclic operations."""

    template_name = 'budget/user/planned_operations.html'

    redirect_name = 'planned_operations'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['operations'] = self.user.account.get_plans()

        form = context.get('add_cyclic_op_form') or forms.PlanCyclicOperationForm.from_account(
            self.user.account)
        context['add_cyclic_op_form'] = form

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        post = request.POST

        if post.get('rm_id') is not None:
            op_id = post.get('rm_id')
            return self._rm_plan(op_id)

        elif post.get('add_cyclic_op') is not None:
            return self._add_plan()

        return self.redirect()

    def _rm_plan(self, op_id: int):
        """Removes the operation plan."""

        op = OperationPlan.objects.get(id=op_id)
        if op.account == self.user.account:
            op.delete()
            messages.success(self.request, 'Cyclic operation plan removed.')
        else:
            messages.error(self.request, 'Cannot remove someone else\'s plan.')

        return self.redirect()

    def _add_plan(self):
        """Adds a new operation plan."""

        form = forms.PlanCyclicOperationForm(self.request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            self.user.account.add_operation_plan(plan=plan)
            messages.success(self.request, 'Cyclic operation plan added.')
            return self.redirect()
        else:
            self.update_context(form=form)
            messages.error(self.request, 'Invalid plan form.')
            return self.render()


class BaseHomeView(BaseUserView):
    """Abstract class serving as base for Home-oriented views."""

    def setup(self, request: HttpRequest, *args, **kwargs):
        if request.session.get('view_as'):
            del request.session['view_as']

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

        context['view_as'] = None

        new_user_form = context.get('new_user_form') or UserCreationForm()
        context['new_user_form'] = new_user_form

        transaction_form = context.get(
            'transaction_form') or forms.TransactionForm()
        context['transaction_form'] = transaction_form

        context['accounts'] = Account.objects.filter(
            home=self.home).order_by('user__username')

        context['manage_users'] = self.user.has_perm('budget.manage_users')
        context['make_transactions'] = self.user.has_perm(
            'budget.make_transactions')

        context['can_view_as'] = self.user.has_perm('budget.plan_for_others')

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        post = request.POST

        if post.get('rm_id'):
            acc_id = post.get('rm_id')
            return self._rm_account(acc_id)

        elif post.get('create') is not None:
            return self._create_user()

        elif post.get('transaction') is not None:
            return self._make_transaction()

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

            messages.success(self.request, 'Account removed.')
            return self.redirect()

        messages.error(self.request, 'Cannot remove the account.')
        return self.redirect()

    def _create_user(self):
        """Creates a user from the POST data. Returns the created Account or None."""

        acc_count = Account.objects.filter(home=self.home).count()
        if acc_count >= Home.MAX_ACCOUNTS:
            messages.error(self.request, f'Maximum number of Accounts reached ({Home.MAX_ACCOUNTS}).')
            return self.redirect()
        
        if not self.user.has_perm('budget.manage_users'):
            messages.error(self.request, 'Cannot create a new user.')
            return self.redirect()

        form = UserCreationForm(self.request.POST)
        if form.is_valid():
            home = self.home
            account = Account(home=home)
            user = form.save()

            account.user = user
            account.save()

            messages.success(self.request, f'User "{user.username}" was successfully created')
            return self.redirect()
        else:
            self.update_context(new_user_form=form)
            messages.error(self.request, 'Invalid user form.')
            return self.render()

    def _make_transaction(self):
        """Makes a transaction to the specified user."""

        if not self.user.has_perm('budget.make_transactions'):
            messages.error(self.request, 'Cannot make a transaction.')
            return self.redirect()

        post = self.request.POST
        form = forms.TransactionForm(post)
        destination = Account.objects.get(id=post.get('transaction'))
        valid = False
        if form.is_valid():
            outcoming, incoming = form.make_transaction(
                source=self.user.account, destination=destination)

            valid = outcoming and incoming

        if valid:
            messages.success(self.request, 'Transaction made.')
            return self.redirect()
        else:
            self.update_context(transaction_form=form)
            messages.error(self.request, 'Invalid transaction form.')
            return self.render()


@method_decorator(
    (login_required(), home_required()),
    name='dispatch')
class AccountView(BaseUserView):
    """View for managing one\'s own Account."""

    template_name = 'budget/home/profile_options.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        rename_form = context.get(
            'rename_form') or forms.RenameAccountForm.from_account(self.user.account)
        context['rename_form'] = rename_form

        context['permissions'] = self.user.account.get_perm_descriptions()

        return context

    def setup(self, request: HttpRequest, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        username = kwargs.get('username')
        if self.user.username == username:
            self.redirect_name = f'/home/{username}'
        else:
            self.redirect_name = None

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        if self.redirect_name:
            return super().dispatch(request, *args, **kwargs)

        return ManageUserView.as_view()(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args, **kwargs):

        post = request.POST

        if post.get('rename') is not None:
            return self._rename()

        if post.get('remove') is not None:
            return self._remove()

        return self.redirect()

    def _rename(self):
        """Renames the user account."""

        form = forms.RenameAccountForm(self.request.POST)
        if form.is_valid():
            self.user.account.rename(form.cleaned_data.get('first_name'))
            messages.success(self.request, 'Account renamed.')
            return self.redirect()
        else:
            self.update_context(rename_form=form)
            messages.error(self.request, 'Invalid rename form.')
            return self.render()

    def _remove(self):
        """Removes the user account or the entire Home."""

        if self.user.account.is_admin():
            self.user.account.home.remove()
            messages.success(self.request, 'Home removed.')
            return redirect('/')

        self.user.account.delete()
        messages.success(self.request, 'Account deleted.')
        return redirect('/')


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

        return redirect('/home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['managed_acc'] = self.managed_acc

        context['is_mod'] = self.managed_acc.is_mod()
        context['make_mod'] = self.user.has_perm('budget.make_mod')

        form = context.get(
            'perm_form') or forms.ChangeUserPermissionsForm.from_account(self.managed_acc)
        context['granted_perms'] = form.all_perms
        context['perm_form'] = form

        rename_form = context.get(
            'rename_form') or forms.RenameAccountForm.from_account(self.managed_acc)
        context['rename_form'] = rename_form

        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        post = request.POST

        if post.get('change') is not None:
            return self._change_perms()

        elif post.get('make_mod') is not None:
            return self._add_mod()

        elif post.get('remove_mod') is not None:
            return self._rm_mod()

        elif post.get('remove') is not None:
            return self._rm_user()

        elif post.get('pass_admin') is not None:
            return self._pass_admin()

        elif post.get('rename') is not None:
            return self._rename()

        return self.redirect()

    def _change_perms(self):
        """Changes the user permissions"""

        if not self._check_account_and_perm():
            messages.error(self.request, 'Cannot change user permissions.')
            return self.redirect()

        if self.managed_acc.is_mod() and not self.user.account.is_admin():
            messages.error(self.request, 'Cannot change moderator permissions.')
            return self.redirect()

        form = forms.ChangeUserPermissionsForm.from_post(
            self.managed_acc, self.request.POST)
        if form.is_valid():
            form.change_perms(self.managed_acc)
            messages.success(self.request, 'Permissions changed.')
            return self.redirect()
        else:
            self.update_context(perm_form=form)
            messages.error(self.request, "Invalid user permissions form.")
            return self.render()

    def _pass_admin(self):
        """Gives the admin role to another user."""

        if not self._check_account():
            messages.error(self.request, 'Error passing Admin to the specified user.')
            return redirect('/')

        if self.user.account.is_admin():
            self.home.change_admin(self.managed_acc)
            for perm in MOD_PERMS:
                self.user.account.add_perm(perm[0])

            messages.success(self.request, 'Admin role passed successfully.')
            return redirect('/home')
        else:
            messages.error(self.request, 'You are not an Administrator.')
            return redirect('/')

    def _add_mod(self):
        """Adds a new home moderator."""

        if self._check_account() and self.user.has_perm('budget.make_mod') and not self.managed_acc.is_mod():
            self.home.add_mod(self.managed_acc)
            messages.success(self.request, 'Moderator added.')
        else:
            messages.error(self.request, 'Cannot add a Moderator.')

        return self.redirect()

    def _rm_mod(self):
        """Removes a home mod."""

        if self._check_account() and self.user.has_perm('budget.make_mod') and self.managed_acc.is_mod():
            self.home.remove_mod(self.managed_acc)
            messages.success(self.request, 'Moderator removed.')
        else:
            messages.error(self.request, 'Cannot remove a Moderator.')

        return self.redirect()

    def _rm_user(self):
        """Removes a user."""

        if self._check_account_and_perm():
            can_remove = False
            if self.managed_acc.is_mod():
                can_remove = self.user.account.is_admin()
            else:
                can_remove = True

            if can_remove:
                self.managed_acc.delete()
                messages.success(self.request, 'User removed.')
                return redirect(HomeView.redirect_name)

        messages.error(self.request, 'Cannot remove the user.')
        return redirect(HomeView.redirect_name)

    def _rename(self):
        """Renames the user account."""

        if not self._check_account_and_perm():
            messages.error(self.request, 'Cannot rename the user.')

        form = forms.RenameAccountForm(self.request.POST)
        if form.is_valid():
            self.managed_acc.rename(form.cleaned_data.get('first_name'))
            messages.success(self.request, 'Account renamed.')
            return self.redirect()
        else:
            self.update_context(rename_form=form)
            messages.error(self.request, 'Invalid rename form.')
            return self.render()
