from typing import Union, Type

from django.shortcuts import get_object_or_404
from django.utils import timezone

from betting.choices import METHOD_TRANSFER, STATUS_PAID, STATUS_PENDING, STATUS_REFUNDED, STATUS_LOCKED, STATUS_HIDDEN, \
    STATUS_LIVE, STATUS_CLOSED, STATUS_ACCEPTED, STATUS_CANCELLED
from betting.models import Match, BetQuestion, Deposit, Transfer, Withdraw, Bet, QuestionOption
from users.models import User
from users.views import notify_user, notify_club


def create_deposit(user_id: Union[int, Type[int]], amount: Union[int, float],
                   source: str, method=None, description=None, club=False) -> Deposit:
    deposit = Deposit()
    if not club:
        deposit.user_id = user_id
    else:
        deposit.club_id = user_id
    deposit.method = method
    deposit.amount = amount
    deposit.description = description
    deposit.deposit_source = source
    deposit.save()
    return deposit


# Match
def lock_match(match_id: int) -> Union[Match, bool]:
    if not match_id or not Match.objects.filter(pk=match_id).exists():
        return False
    return Match.objects.filter(pk=match_id).update(status=STATUS_LOCKED)


def hide_match(match_id: int) -> Union[Match, bool]:
    if not match_id or not Match.objects.filter(pk=match_id).exists():
        return False
    return Match.objects.filter(pk=match_id).update(status=STATUS_HIDDEN)


def go_live_match(match_id) -> Union[Match, bool]:
    if not match_id or not Match.objects.filter(pk=match_id).exists():
        return False
    return Match.objects.filter(pk=match_id).update(status=STATUS_LIVE)


def end_match_now(match_id) -> Union[Match, bool]:
    if not match_id or not Match.objects.filter(pk=match_id).exists():
        return False
    return Match.objects.filter(pk=match_id).update(status=STATUS_CLOSED)


# Bet Question
def hide_question(question_id: int) -> Union[BetQuestion, bool]:
    if not question_id or not BetQuestion.objects.filter(pk=question_id).exists():
        return False
    return BetQuestion.objects.filter(pk=question_id).update(status=STATUS_HIDDEN)


def end_question_now(question_id: int) -> Union[BetQuestion, bool]:
    if not question_id or not BetQuestion.objects.filter(pk=question_id).exists():
        return False
    return BetQuestion.objects.filter(pk=question_id).update(status=STATUS_CLOSED)


def lock_question(question_id: int) -> Union[BetQuestion, bool]:
    if not question_id or not BetQuestion.objects.filter(pk=question_id).exists():
        return False
    return BetQuestion.objects.filter(pk=question_id).update(status=STATUS_LOCKED)


def select_question_winner(question_id: int, option_id: int) -> Union[BetQuestion, bool]:
    if not question_id or not BetQuestion.objects.filter(pk=question_id).exists():
        return False
    if not option_id or not QuestionOption.objects.filter(pk=option_id).exists():
        return False
    question = BetQuestion.objects.get(pk=question_id)
    winner = QuestionOption.objects.get(pk=option_id)
    question.status = STATUS_PAID
    question.winner = winner
    bet_winners = question.bet_set.values('id').filter(choice=winner)
    bet_losers = question.bet_set.exclude(choice=winner)
    for bet in bet_winners:
        pay_bet(bet.id)
    bet_losers.update(is_winner=False, status=STATUS_PAID)
    question.save()  # To avoid reprocessing the bet scope
    return question


def unselect_question_winner(question_id: int) -> Union[BetQuestion, bool]:
    if not question_id or not BetQuestion.objects.filter(pk=question_id).exists():
        return False
    question = BetQuestion.objects.get(pk=question_id)
    if not question.winner:
        return False
    winner = QuestionOption.objects.get(pk=question.winner_id)
    question.status = STATUS_LOCKED
    question.winner = None
    bet_winners = question.bet_set.values('id').filter(choice=winner)
    bet_losers = question.bet_set.exclude(choice=winner)
    for bet in bet_winners:
        un_pay_bet(bet.id)
    bet_losers.update(is_winner=None, status=STATUS_PENDING)
    question.save()  # To avoid reprocessing the bet scope
    return question


def refund_question(question_id: int) -> bool:
    if not question_id or not BetQuestion.objects.filter(pk=question_id).exists():
        return False
    question = BetQuestion.objects.get(pk=question_id)
    for bet in question.bet_set.all():
        refund_bet(bet.id)
    question.status = STATUS_REFUNDED
    question.save()  # To avoid reprocessing the bet scope
    return True


# Bet
def refund_bet(bet_id: int, percent=None) -> Union[Bet, bool]:
    # TODO: Verify logic
    if not bet_id or not Bet.objects.filter(pk=bet_id).exists():
        return False
    bet = Bet.objects.get(pk=bet_id)
    if bet.is_winner:
        change = (bet.win_amount / bet.win_rate) - bet.win_amount
    else:
        change = bet.win_amount / bet.win_rate
    if percent:
        change = bet.amount * float(percent) / 100
    bet.user.balance += change
    bet.user.save()
    notify_user(bet.user, f'Bet cancelled for match ##{bet.bet_question.match.__str__()}## '
                          f'on ##{bet.bet_question.question}##. Balance '
                          f'refunded by {change} BDT')
    bet.status = STATUS_REFUNDED
    bet.save()
    return bet


def pay_bet(bet_id: int):
    if not bet_id or not Bet.objects.filter(pk=bet_id).exists():
        return False
    bet = Bet.objects.select_related('bet_question', 'bet_question__match', 'user').get(pk=bet_id)
    bet.user.balance += bet.amount
    bet.user.save()
    notify_user(bet.user, f'You won bdt {bet.amount} for match ##{bet.bet_question.match.title}## '
                          f'on question ##{bet.bet_question.question}##. Balance ')
    bet.is_winner = True
    bet.status = STATUS_PAID
    bet.user_balance = bet.user.balance
    bet.save()


def un_pay_bet(bet_id: int):
    if not bet_id or not Bet.objects.filter(pk=bet_id).exists():
        return False
    bet = Bet.objects.select_related('bet_question', 'bet_question__match', 'user').get(pk=bet_id)
    bet.user.balance -= bet.amount
    bet.user.save()
    notify_user(bet.user, f'match ##{bet.bet_question.match.title}## '
                          f'on question ##{bet.bet_question.question}## one of your'
                          f'bet win status cancelled')
    bet.is_winner = None
    bet.status = STATUS_PENDING
    bet.save()


def accept_deposit(deposit_id: int, message=None) -> Deposit:
    deposit = get_object_or_404(Deposit, pk=deposit_id)
    if deposit.user:
        deposit.user.balance += deposit.amount
        deposit.user.save()
        deposit.balance = deposit.user.balance
        notify_user(deposit.user, message or f"Deposit request on {deposit.created_at} amount"
                                             f"{deposit.amount} confirmed")
    elif deposit.club:
        deposit.club.balance += deposit.amount
        deposit.club.save()
        deposit.balance = deposit.club.balance
        notify_club(deposit.club, message or f"Deposit request on {deposit.created_at} amount"
                                             f"{deposit.amount} confirmed")
    deposit.status = True
    deposit.save()
    return deposit


def accept_withdraw(withdraw_id: int) -> Withdraw:
    """
    Mark status true if status is null
    Reduce balance and mark status true if status is False
    """
    withdraw: Withdraw = get_object_or_404(Withdraw, pk=withdraw_id)
    if withdraw.status is None:
        withdraw.status = True
        withdraw.save()
    else:
        withdraw.status = True
        withdraw.user.balance -= withdraw.amount
        withdraw.user.save()
        withdraw.balance = withdraw.user.balance
        withdraw.save()
    notify_user(withdraw.user, f'Withdraw request create on {withdraw.created_at} is accepted.')
    return withdraw


def accept_transfer(transfer_id: int) -> Union[Transfer, bool]:
    transfer = get_object_or_404(Transfer, pk=transfer_id)
    if transfer.status == STATUS_ACCEPTED:
        return False
    if transfer.status == STATUS_CANCELLED:
        sender = transfer.sender or transfer.club
        sender.balance -= transfer.amount
        sender.save()
        deposit = create_deposit(transfer.recipient_id, transfer.amount, METHOD_TRANSFER, METHOD_TRANSFER)
        accept_deposit(deposit.id)
        notify_user(transfer.recipient, f'You  received {transfer.amount} tk '
                                        f'with transfer id ##{transfer.id}##')
    if transfer.status == STATUS_PENDING:
        deposit = create_deposit(transfer.recipient_id, transfer.amount, METHOD_TRANSFER, METHOD_TRANSFER)
        accept_deposit(deposit.id)
        notify_user(transfer.recipient, f'You  received {transfer.amount} tk from user ##{transfer.sender.username}##, '
                                        f'with transfer id ##{transfer.id}##')
    transfer.status = STATUS_ACCEPTED
    transfer.save()
    return transfer


def cancel_withdraw(withdraw_id: int) -> Withdraw:
    """
    Increase user balance and make withdraw status false
    """
    withdraw = get_object_or_404(Withdraw, pk=withdraw_id)
    withdraw.status = STATUS_CANCELLED
    withdraw.user.balance += withdraw.amount
    withdraw.user.save()
    withdraw.balance = withdraw.user.balance
    withdraw.save()
    notify_user(withdraw.user,
                f"Withdraw of {withdraw.amount}BDT via {withdraw.method} to number {withdraw.user_account} "
                f"placed on {withdraw.created_at} has been canceled and refunded")
    return withdraw


def cancel_deposit(deposit_id: int, delete=False) -> Deposit:
    deposit = get_object_or_404(Deposit, pk=deposit_id)
    if deposit.status == STATUS_ACCEPTED:
        # Change user Balance
        if deposit.user:
            deposit.user.balance -= deposit.amount
            deposit.user.save()
            # Change deposit status
            notify_user(deposit.user, f"Deposit request has been canceled placed on {deposit.created_at}."
                                      f"Contact admin if you think it was wrong. Transaction id: "
                                      f"{deposit.reference} Amount: {deposit.amount} From "
                                      f"account: {deposit.user_account} To account {deposit.site_account} "
                                      f"Method: {deposit.method}")
        elif deposit.club:
            deposit.club.balance -= deposit.amount
            deposit.club.save()
            deposit.balance = deposit.club.balance
            # Change deposit status
            notify_club(deposit.club, f"Deposit request has been canceled placed on {deposit.created_at}."
                                      f"Contact admin if you think it was wrong. Transaction id: "
                                      f"{deposit.reference} Amount: {deposit.amount} From "
                                      f"account: {deposit.user_account} To account {deposit.site_account} "
                                      f"Method: {deposit.method}")
    deposit.status = STATUS_CANCELLED
    if not delete:
        deposit.save()
        return deposit
    print("Trying to delete")


def cancel_transfer(transfer_id: int) -> Transfer:
    # TODO: Check logic
    transfer = get_object_or_404(Transfer, pk=transfer_id)
    if transfer.sender:
        notify_user(transfer.sender, f"Transfer of {transfer.amount}BDT to user {transfer.recipient.username} "
                                     f"placed on {transfer.created_at} has been canceled and refunded")
        notify_user(transfer.recipient, f"Transfer of {transfer.amount}BDT to you from {transfer.sender.username} "
                                        f"placed on {transfer.created_at} has been canceled")
    if transfer.club:
        notify_club(transfer.club, f"Transfer of {transfer.amount}BDT to user {transfer.recipient.username} "
                                   f"placed on {transfer.created_at} has been canceled and refunded")
        notify_user(transfer.recipient, f"Transfer of {transfer.amount}BDT to you from {transfer.club.name} "
                                        f"placed on {transfer.created_at} has been canceled")
    if transfer.status == STATUS_ACCEPTED:
        transfer.recipient.balance -= transfer.amount
        transfer.recipient.save()
    if transfer.status is None:
        if transfer.sender:
            transfer.sender.balance += transfer.amount
            transfer.sender.save()
        if transfer.club:
            transfer.club.balance += transfer.amount
            transfer.club.save()
    transfer.status = STATUS_CANCELLED
    transfer.save()
    return transfer


# User
def make_game_editor(user_id: int) -> Union[User, int]:
    if not user_id or not User.objects.filter(pk=user_id).exists():
        return False
    return User.objects.filter(pk=user_id).update(game_editor=True)


def remove_game_editor(user_id: int) -> Union[User, int]:
    if not user_id or not User.objects.filter(pk=user_id).exists():
        return False
    return User.objects.filter(pk=user_id).update(game_editor=False)
