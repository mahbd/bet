from datetime import datetime

import pytz
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.views.generic import View

from betting.forms import BetScopeForm, ClubForm
from betting.models import Deposit, DEPOSIT_WITHDRAW_CHOICES, Withdraw, Transfer, Match, GAME_CHOICES, BetScope, Bet, \
    DepositWithdrawMethod, ConfigModel, BET_CHOICES
from betting.views import generate_admin_dashboard_data, value_from_option, get_last_bet, sum_aggregate
from users.models import Club, User


def convert_time(time):
    tz = pytz.timezone('Asia/Dhaka')
    start_time = datetime.strptime(time, "%Y-%m-%d %I:%M %p")
    return tz.localize(start_time)


def success_message(message="action completed successfully"):
    return format_html('<div class="alert alert-danger">{}</div>', message)


@method_decorator(login_required, name='dispatch')
class Home(View):
    template_name = 'easy_admin/home.html'

    def get(self, request, *args, **kwargs):
        data = generate_admin_dashboard_data()
        table_header = (
            ('width-60p', 'Title'),
            ('width-40p', 'Value'),
        )
        table_body = [(key.replace('_', ' ').title(), value) for key, value in data.items()]
        table_data = {
            'table_header': table_header,
            'table_body': table_body,
        }
        buttons = (
            ('btn-primary', f"{reverse('ea:deposits')}#unverified", 'Unverified DepositsView'),
            ('btn-primary', f"{reverse('ea:withdraws')}#unverified", 'Unverified Withdraws'),
            ('btn-primary', f"{reverse('ea:transfers')}#unverified", 'Unverified Transactions'),
            ('btn-primary', f"{reverse('ea:matches')}#running", 'Running matches'),
            ('btn-primary', f"{reverse('ea:bet_options')}#running", 'Running bet options'),
        )
        return render(request, self.template_name, context={'data': data, 'table_data': table_data, 'buttons': buttons})


def deny_deposit(request, deposit_id, red=False):
    t = get_object_or_404(Deposit, pk=deposit_id)
    t.delete()
    if red:
        return redirect(red)
    return redirect('ea:deposits')


class DepositsView(View):
    model = Deposit
    template = 'easy_admin/deposit.html'
    name = 'deposit'

    def reverse_link(self):
        return reverse('ea:deposits')

    def get(self, request, *args, **kwargs):
        items = self.model.objects.exclude(verified=True)
        table_header = (
            ('', 'ID'),
            ('', 'User'),
            ('', 'Method'),
            ('', 'Amount'),
            ('', 'Transaction Id'),
            ('', 'Date'),
        )
        table_body = [(deposit.id, deposit.user.username, deposit.method, deposit.amount, deposit.transaction_id,
                       deposit.created_at) for deposit in self.model.objects.filter(verified=True)]
        table_data = {
            'table_header': table_header,
            'table_body': table_body,
        }

        return render(request, self.template, context={
            f'unverified_{self.name}s': items,
            'method_list': DEPOSIT_WITHDRAW_CHOICES,
            'table_data': table_data,
        })

    def post(self, request, *args, **kwargs):
        data = {}
        for key, value in request.POST.items():
            data[key] = value
        data.pop('csrfmiddlewaretoken')
        data['verified'] = True
        created_at = data.get('created_at')
        if created_at:
            data['created_at'] = convert_time(created_at)
        self.model.objects.filter(id=data['id']).update(**data)
        return redirect(self.reverse_link())


def deny_withdraw(request, withdraw_id, red=False):
    t = get_object_or_404(Withdraw, pk=withdraw_id)
    t.delete()
    if red:
        return redirect(red)
    return redirect('ea:withdraws')


class WithdrawsView(DepositsView):
    model = Withdraw
    template = 'easy_admin/withdraw.html'
    name = 'withdraw'

    def reverse_link(self):
        return reverse('ea:withdraws')


def verify_transfer(request, tra_id, red=False):
    t = get_object_or_404(Transfer, pk=tra_id)
    t.verified = True
    t.save()
    if red:
        return redirect(red)
    return redirect('ea:transfers')


def deny_transfer(request, tra_id, red=False):
    t = get_object_or_404(Transfer, pk=tra_id)
    t.delete()
    if red:
        return redirect(red)
    return redirect('ea:transfers')


class TransferView(View):
    def get(self, *args, **kwargs):
        table_header = (
            ('', 'ID'),
            ('', 'User'),
            ('', 'Amount'),
            ('', 'To user'),
            ('', 'Date'),
        )
        table_body = [(transfer.id, transfer.user.username, transfer.amount, transfer.to.username,
                       transfer.created_at) for transfer in Transfer.objects.filter(verified=True)]
        table_data = {
            'table_header': table_header,
            'table_body': table_body,
        }
        context = {
            'unverified_transfers': Transfer.objects.exclude(verified=True),
            'table_data': table_data
        }
        return render(self.request, 'easy_admin/transfer.html', context)


def lock_match(request, match_id, red=False):
    match = get_object_or_404(Match, pk=match_id)
    match.locked = not match.locked
    match.save()
    if red:
        return redirect(red)
    return redirect('ea:matches')


def hide_match(request, match_id, red=False):
    match = get_object_or_404(Match, pk=match_id)
    match.hide = not match.hide
    match.save()
    if red:
        return redirect(red)
    return redirect('ea:matches')


class MatchView(View):
    def get(self, *args, **kwargs):
        table_header = (
            ('', 'ID'),
            ('', 'Game Name'),
            ('', 'Match Title'),
            ('', 'Start Time'),
            ('', 'End Time'),
        )
        table_body = [(match.id, match.game_name, match.title, match.start_time,
                       match.end_time) for match in Match.objects.filter(end_time__lt=timezone.now())]
        table_data = {
            'table_header': table_header,
            'table_body': table_body,
        }
        context = {
            'live_matches': Match.objects.filter(end_time__gte=timezone.now()),
            'game_list': GAME_CHOICES,
            'table_data': table_data
        }
        return render(self.request, 'easy_admin/match.html', context)

    def post(self, *args, **kwargs):
        data = {}
        for key, value in self.request.POST.items():
            data[key] = value
        data.pop('csrfmiddlewaretoken')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        if start_time:
            data['start_time'] = convert_time(start_time)
        if end_time:
            data['end_time'] = convert_time(end_time)
        if data.get('id'):
            Match.objects.filter(id=data['id']).update(**data)
        else:
            Match.objects.create(**data)
        return redirect('ea:matches')


def hide_scope(request, scope_id, red=False):
    scope = get_object_or_404(BetScope, pk=scope_id)
    scope.hide = not scope.hide
    scope.save()
    if red:
        return redirect(red)
    return redirect('ea:bet_option_detail', scope_id)


def lock_scope(request, scope_id, red=False):
    scope = get_object_or_404(BetScope, pk=scope_id)
    scope.locked = not scope.locked
    scope.save()
    if red:
        return redirect(red)
    return redirect('ea:bet_option_detail', scope_id)


class BetOptionView(View):
    def get(self, *args, **kwargs):
        if kwargs.get('scope_id'):
            try:
                bet_scope = BetScope.objects.prefetch_related('bet_set').get(pk=kwargs.get('scope_id'))
            except BetScope.DoesNotExist:
                raise Http404

            return render(self.request, 'easy_admin/bet_option_details.html', context={
                'bet_scope': bet_scope,
                'choice_list': BET_CHOICES,
            })
        context = {
            'bet_scope_list': BetScope.objects.filter(winner__isnull=True)
        }
        return render(self.request, 'easy_admin/bet_option_list.html', context)


def create_bet_option(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    if request.method != 'POST':
        form = BetScopeForm()
    else:
        data = {}
        for key, value in request.POST.items():
            data[key] = value
        if data.get('end_time'):
            data['end_time'] = convert_time(data.get('end_time'))
        form = BetScopeForm(data=data)
        if form.is_valid():
            scope = form.save(commit=False)
            scope.match = match
            scope.save()
            return redirect('ea:bet_option_detail', scope.id)
    return render(request, 'easy_admin/forms/bet_option_form.html', context={
        'form': form,
        'match': match,
    })


def update_bet_option(request, match_id, scope_id):
    match = get_object_or_404(Match, id=match_id)
    scope = get_object_or_404(BetScope, id=scope_id)
    if request.method != 'POST':
        form = BetScopeForm(instance=scope)
    else:
        data = {}
        for key, value in request.POST.items():
            data[key] = value
        if data.get('end_time'):
            data['end_time'] = convert_time(data.get('end_time'))
        form = BetScopeForm(instance=scope, data=data)
        if form.is_valid():
            form.save()
            return redirect('ea:bet_option_detail', scope_id)
    return render(request, 'easy_admin/forms/bet_option_form.html', context={
        'form': form,
        'match': match,
        'scope_id': scope_id
    })


def delete_club(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    club.delete()
    return redirect('ea:clubs')


class ClubView(View):
    def get(self, *args, **kwargs):
        messages = kwargs.get('messages') or []
        if kwargs.get('form'):
            errors = kwargs.get('form').errors.as_data()
            for error in errors:
                messages.append(format_html('<div class="alert alert-danger">{}: {}</div>', error, errors[error][0]))
        context = {
            'club_list': [(ClubForm(instance=club), club.total_user)
                          for club in Club.objects.prefetch_related('user_set', 'user_set__userclubinfo').annotate(
                    total_user=Count('user')).all()],
            'form': kwargs.get('form') or ClubForm(),
            'messages': messages or kwargs.get('messages')
        }
        return render(self.request, 'easy_admin/club.html', context)

    def post(self, *args, **kwargs):
        if kwargs.get('club_id'):
            club = get_object_or_404(Club, id=kwargs.get('club_id'))
            form = ClubForm(instance=club, data=self.request.POST)
        else:
            form = ClubForm(data=self.request.POST)
        if form.is_valid():
            form.save()
            return self.get(args, kwargs, messages=success_message("Club added/edited successfully"))
        return self.get(args, kwargs, form=form)


class UserView(View):
    def get(self, *args, **kwargs):
        table_header = (
            ('', 'ID'),
            ('', 'Joining Date'),
            ('', 'Last Bet'),
            ('', 'Name'),
            ('', 'Username'),
            ('', 'Email'),
            ('', 'Phone'),
            ('', 'Club'),
            ('', 'Total Bet'),
            ('', 'Balance'),
        )
        table_body = [
            (user.id, user.userclubinfo.date_joined, get_last_bet(user) and get_last_bet(user).created_at, user.get_full_name(),
             user.username, user.email, user.phone, user.user_club.name, sum_aggregate(user.bet_set.all()),
             user.balance)
            for user in User.objects.select_related('user_club').prefetch_related('bet_set').all()]
        table_data = {
            'table_header': table_header,
            'table_body': table_body,
        }
        context = {
            'table_data': table_data
        }
        return render(self.request, 'easy_admin/users.html', context)


class BetView(View):
    def get(self, *args, **kwargs):
        table_header = (
            ('', 'ID'),
            ('', 'Username'),
            ('', 'Amount'),
            ('', 'Question'),
            ('', 'Answer'),
            ('', 'User Answer'),
            ('', 'Return Rate'),
            ('', 'Win Amount(p)'),
            ('', 'Winner'),
        )
        unpaid_body = [(bet.id, bet.user.username, bet.amount, bet.bet_scope.question, bet.answer,
                        value_from_option(bet.choice, bet.bet_scope), bet.return_rate, bet.winning, bet.is_winner
                        ) for bet in Bet.objects.filter(paid=False)]
        paid_body = [(bet.id, bet.user.username, bet.amount, bet.bet_scope.question, bet.answer,
                      value_from_option(bet.choice, bet.bet_scope), bet.return_rate, bet.winning, bet.is_winner
                      ) for bet in Bet.objects.filter(paid=True)]
        unpaid_bet = {
            'table_header': table_header,
            'table_body': unpaid_body,
        }
        paid_bet = {
            'table_header': table_header,
            'table_body': paid_body,
        }
        return render(self.request, 'easy_admin/bets.html', context={
            'unpaid_bet': unpaid_bet,
            'paid_bet': paid_bet
        })


class MethodView(View):
    def get(self, *args, **kwargs):
        context = {
            'available_methods': DepositWithdrawMethod.objects.all(),
            'method_choices': DEPOSIT_WITHDRAW_CHOICES,
        }
        return render(self.request, 'easy_admin/method_list.html', context)


class ConfigureView(View):
    def get(self, *args, **kwargs):
        return render(self.request, 'easy_admin/configurations.html', context={
            'configurations': ConfigModel.objects.all()
        })
