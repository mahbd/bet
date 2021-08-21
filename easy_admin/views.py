from datetime import datetime

import pytz
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View

from betting.models import Deposit, DEPOSIT_WITHDRAW_CHOICES, Withdraw, Transfer, Match, GAME_CHOICES, BetScope
from betting.views import generate_admin_dashboard_data
from users.models import Club


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
        created_at = str(data.get('created_at'))
        if created_at:
            created_at = datetime.strptime(created_at, "%Y-%m-%d %I:%M %p")
            tz = pytz.timezone('Asia/Dhaka')
            data['created_at'] = tz.localize(created_at)
        self.model.objects.filter(id=data['id']).update(**data)
        return redirect(self.reverse_link())


class WithdrawsView(DepositsView):
    model = Withdraw
    template = 'easy_admin/withdraw.html'
    name = 'withdraw'

    def reverse_link(self):
        return reverse('ea:withdraws')


class TransferView(TemplateView):
    template_name = 'easy_admin/transfer.html'
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
    extra_context = {
        'unverified_transfers': Transfer.objects.exclude(verified=True),
        'table_data': table_data
    }


class MatchView(View):
    def get(self, *args, **kwargs):
        context = {
            'live_matches': Match.objects.filter(end_time__gte=timezone.now()),
            'game_list': GAME_CHOICES,
        }
        return render(self.request, 'easy_admin/match.html', context)


class BetOptionView(View):
    def get(self, *args, **kwargs):
        context = {
            'bet_scope_list': BetScope.objects.filter(winner__isnull=True)
        }
        return render(self.request, 'easy_admin/bet_option_list.html', context)


class ClubView(View):
    def get(self, *args, **kwargs):
        context = {
            'club_list': Club.objects.all()
        }
        return render(self.request, 'easy_admin/club.html', context)
