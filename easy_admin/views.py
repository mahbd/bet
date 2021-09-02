from datetime import datetime

import pytz
from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.views.generic import View

from betting.forms import BetScopeForm, ClubForm, MethodForm
from betting.models import Deposit, DEPOSIT_WITHDRAW_CHOICES, Withdraw, Transfer, Match, GAME_CHOICES, BetScope, Bet, \
    DepositWithdrawMethod, ConfigModel, BET_CHOICES, config, ClubTransfer, Commission, COMMISSION_REFER, COMMISSION_CLUB
from betting.views import generate_admin_dashboard_data, value_from_option, get_last_bet, sum_aggregate
from users.backends import superuser_only
from users.models import Club, User
from users.views import notify_user


def convert_time(time):
    tz = pytz.timezone('Asia/Dhaka')
    start_time = datetime.strptime(time, "%Y-%m-%d %I:%M %p")
    return tz.localize(start_time)


def success_message(message="action completed successfully"):
    return format_html('<div class="alert alert-success">{}</div>', message)


def failure_message(message="action completed successfully"):
    return format_html('<div class="alert alert-danger">{}</div>', message)


@method_decorator(superuser_only, name='dispatch')
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
            ('btn-primary', f"{reverse('ea:transfers')}#unverified", 'Unverified Transfers'),
            ('btn-primary', f"{reverse('ea:club_transfers')}#unverified", 'Unverified Club Transfers'),
            ('btn-primary', f"{reverse('ea:matches')}#running", 'Running matches'),
            ('btn-primary', f"{reverse('ea:bet_options')}#running", 'Running bet options'),
        )
        return render(request, self.template_name, context={'data': data, 'table_data': table_data, 'buttons': buttons})


@superuser_only
def deny_deposit(request, deposit_id, red=False):
    t = get_object_or_404(Deposit, pk=deposit_id)
    t.delete()
    if red:
        return redirect(red)
    return redirect('ea:deposits')


@method_decorator(superuser_only, name='dispatch')
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


@superuser_only
def deny_withdraw(request, withdraw_id, red=False):
    t = get_object_or_404(Withdraw, pk=withdraw_id)
    t.delete()
    if red:
        return redirect(red)
    return redirect('ea:withdraws')


@method_decorator(superuser_only, name='dispatch')
class WithdrawsView(DepositsView):
    model = Withdraw
    template = 'easy_admin/withdraw.html'
    name = 'withdraw'

    def reverse_link(self):
        return reverse('ea:withdraws')


@superuser_only
def verify_transfer(request, tra_id, red=False):
    t = get_object_or_404(Transfer, pk=tra_id)
    t.verified = True
    t.save()
    if red:
        return redirect(red)
    return redirect('ea:transfers')


@superuser_only
def deny_transfer(request, tra_id, red=False):
    t = get_object_or_404(Transfer, pk=tra_id)
    t.delete()
    if red:
        return redirect(red)
    return redirect('ea:transfers')


@method_decorator(superuser_only, name='dispatch')
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


@superuser_only
def verify_club_transfer(request, tra_id, red=False):
    t = get_object_or_404(ClubTransfer, pk=tra_id)
    t.verified = True
    t.save()
    if red:
        return redirect(red)
    return redirect('ea:club_transfers')


@superuser_only
def deny_club_transfer(request, tra_id, red=False):
    t = get_object_or_404(ClubTransfer, pk=tra_id)
    t.delete()
    if red:
        return redirect(red)
    return redirect('ea:club_transfers')


@method_decorator(superuser_only, name='dispatch')
class ClubTransferView(View):
    def get(self, *args, **kwargs):
        table_header = (
            ('', 'ID'),
            ('', 'Club'),
            ('', 'Amount'),
            ('', 'To user'),
            ('', 'Date'),
        )
        table_body = [(club_transfer.id, club_transfer.club.name, club_transfer.amount, club_transfer.to.username,
                       club_transfer.created_at) for club_transfer in ClubTransfer.objects.filter(verified=True)]
        table_data = {
            'table_header': table_header,
            'table_body': table_body,
        }
        context = {
            'unverified_club_transfers': ClubTransfer.objects.exclude(verified=True),
            'table_data': table_data
        }
        return render(self.request, 'easy_admin/club_transfer.html', context)


@superuser_only
def lock_match(request, match_id, red=False):
    match = get_object_or_404(Match, pk=match_id)
    match.locked = not match.locked
    match.save()
    if red:
        return redirect(red)
    return redirect('ea:matches')


@superuser_only
def hide_match(request, match_id, red=False):
    match = get_object_or_404(Match, pk=match_id)
    match.hide = not match.hide
    match.save()
    if red:
        return redirect(red)
    return redirect('ea:matches')


@method_decorator(superuser_only, name='dispatch')
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


@superuser_only
def hide_scope(request, scope_id, red=False):
    scope = get_object_or_404(BetScope, pk=scope_id)
    scope.hide = not scope.hide
    scope.save()
    if red:
        return redirect(red)
    return redirect('ea:bet_option_detail', scope_id)


@superuser_only
def lock_scope(request, scope_id, red=False):
    scope = get_object_or_404(BetScope, pk=scope_id)
    scope.locked = not scope.locked
    scope.save()
    if red:
        return redirect(red)
    return redirect('ea:bet_option_detail', scope_id)


@superuser_only
def pay_scope(request, scope_id, red=False):
    scope = get_object_or_404(BetScope, pk=scope_id)
    if scope.processed_internally or not scope.winner:
        return render(request, 'super_base.html', {
            'messages': [failure_message('Winner is not selected or already paid')]
        })
    with transaction.atomic():
        scope.processed_internally = True  # To avoid reprocessing the bet scope

        bet_winners = list(scope.bet_set.filter(choice=scope.winner))
        bet_losers = scope.bet_set.exclude(choice=scope.winner)
        club_commission = float(config.get_config_str('club_commission')) / 100
        refer_commission = float(config.get_config_str('refer_commission')) / 100

        for winner in bet_winners:
            final_win = winner.amount * winner.return_rate * (1 - club_commission - refer_commission)
            winner.user.balance += final_win
            winner.user.save()
            winner.winning = final_win
            winner.is_winner = True
            winner.answer = value_from_option(winner.choice, scope)
            winner.save()
            if winner.user.referred_by:
                winner.user.referred_by.balance += winner.winning * refer_commission
                winner.user.referred_by.earn_from_refer += winner.winning * refer_commission
                notify_user(winner.user.referred_by, f"You earned {winner.winning * refer_commission} from user "
                                                     f"{winner.user.username}. Keep referring and "
                                                     f"earn {refer_commission}% commission from each bet")
                winner.user.referred_by.save()
                Commission.objects.create(bet=winner, amount=winner.winning * refer_commission,
                                          type=COMMISSION_REFER, balance=winner.user.referred_by.balance)

            if winner.user.user_club:
                winner.user.user_club.balance += winner.winning * club_commission
                winner.user.user_club.save()
                notify_user(winner.user.user_club.admin, f"{winner.user.user_club.name} has "
                                                         f"earned {winner.winning * club_commission} from "
                                                         f"{winner.user.username}")
                Commission.objects.create(bet=winner, amount=winner.winning * club_commission,
                                          club=winner.user.user_club,
                                          type=COMMISSION_CLUB, balance=winner.user.user_club.balance)
        for loser in bet_losers:
            loser.is_winner = False
            loser.paid = True
            loser.winning = 0
            loser.answer = value_from_option(loser.choice, scope)
            loser.save()
        scope.save()  # To avoid reprocessing the bet scope
    if red:
        return redirect(red)
    return redirect('ea:bet_option_detail', scope_id)


def set_scope_winner(request, scope_id, winner, red=False):
    bet_scope = get_object_or_404(BetScope, pk=scope_id)
    bet_scope.winner = winner
    bet_scope.save()
    if red:
        return redirect(red)
    return redirect('ea:bet_option_detail', scope_id)


@method_decorator(superuser_only, name='dispatch')
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


@superuser_only
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


@superuser_only
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


@superuser_only
def delete_club(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    club.delete()
    return redirect('ea:clubs')


@method_decorator(superuser_only, name='dispatch')
class ClubView(View):
    def get(self, *args, **kwargs):
        messages = kwargs.get('messages') or []
        if kwargs.get('form'):
            errors = kwargs.get('form').errors.as_data()
            for error in errors:
                messages.append(format_html('<div class="alert alert-danger">{}: {}</div>', error, errors[error][0]))
        context = {
            'club_list': [(ClubForm(instance=club), club)
                          for club in Club.objects.prefetch_related('user_set', 'user_set__userclubinfo').annotate(
                    total_user=Count('user')).all()],
            'form': kwargs.get('form') or ClubForm(),
            'messages': messages or kwargs.get('messages')
        }
        return render(self.request, 'easy_admin/club.html', context)

    def post(self, *args, **kwargs):
        print(self.request.POST)
        if self.request.POST.get('id'):
            club = get_object_or_404(Club, id=self.request.POST.get('id'))
            form = ClubForm(instance=club, data=self.request.POST)
            print(form.data)
        else:
            form = ClubForm(data=self.request.POST)
        if form.is_valid():
            form.save()
            return self.get(args, kwargs, messages=[success_message("Club added/edited successfully")])
        return self.get(args, kwargs, form=form)


@method_decorator(superuser_only, name='dispatch')
class UserView(View):
    def get(self, *args, **kwargs):
        table_header = (
            ('', 'ID'), ('', 'Joining Date'), ('', 'Last Bet'), ('', 'Name'), ('', 'Username'),
            ('', 'Email'), ('', 'Phone'), ('', 'Club'), ('', 'Total Bet'), ('', 'Balance'),
        )
        table_body = [
            (user.id, user.userclubinfo.date_joined, get_last_bet(user) and get_last_bet(user).created_at,
             user.get_full_name(),
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


@method_decorator(superuser_only, name='dispatch')
class BetView(View):
    def get(self, *args, **kwargs):
        table_header = (
            ('', 'ID'), ('', 'Username'), ('', 'Amount'), ('', 'Question'), ('', 'Answer'),
            ('', 'User Answer'), ('', 'Return Rate'), ('', 'Win Amount(p)'), ('', 'Winner'),
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


def get_name_from_code(code):
    for c, name in DEPOSIT_WITHDRAW_CHOICES:
        if code == c:
            return name
    return "Wrong"


@method_decorator(superuser_only, name='dispatch')
class MethodView(View):
    def get(self, *args, **kwargs):
        messages = kwargs.get('messages') or []
        if kwargs.get('form'):
            errors = kwargs.get('form').errors.as_data()
            for error in errors:
                messages.append(format_html('<div class="alert alert-danger">{}: {}</div>', error, errors[error][0]))

        context = {
            'available_methods': DepositWithdrawMethod.objects.all(),
            'method_choices': DEPOSIT_WITHDRAW_CHOICES,
            'form': kwargs.get('form') or MethodForm(),
            'messages': messages or kwargs.get('messages')
        }
        print(messages, kwargs.get('messages'))
        return render(self.request, 'easy_admin/method_list.html', context)

    def post(self, *args, **kwargs):
        if self.request.POST.get('id'):
            method = get_object_or_404(DepositWithdrawMethod, id=self.request.POST.get('id'))
            form = MethodForm(instance=method, data=self.request.POST)
        else:
            form = MethodForm(data=self.request.POST)
        if form.is_valid():
            method = form.save(commit=False)
            method.name = get_name_from_code(method.code)
            method.save()
            return self.get(args, kwargs, messages=[success_message("Method added/edited successfully")])
        return self.get(args, kwargs, form=form)


def delete_method(request, method_id):
    DepositWithdrawMethod.objects.filter(id=method_id).delete()
    return redirect('ea:methods')


@method_decorator(superuser_only, name='dispatch')
class ConfigureView(View):
    def get(self, *args, **kwargs):
        return render(self.request, 'easy_admin/configurations.html', context={
            'configurations': ConfigModel.objects.all(),
            'messages': kwargs.get('messages')
        })

    def post(self, *args, **kwargs):
        name = self.request.POST.get('name')
        value = self.request.POST.get('value')
        ConfigModel.objects.filter(name=name).update(value=value)
        return self.get(args, kwargs, messages=[success_message(f'{name} value updated successfully')])
