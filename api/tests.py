import json
from datetime import timedelta

from django.test import TestCase, Client
from django.utils import timezone

from api.serializers import UserDetailsSerializer
from betting.choices import A_MATCH_LOCK, A_MATCH_HIDE, A_MATCH_GO_LIVE, A_MATCH_END_NOW, A_QUESTION_LOCK, \
    A_QUESTION_HIDE, A_QUESTION_END_NOW, A_QUESTION_SELECT_WINNER, A_QUESTION_UNSELECT_WINNER, \
    A_QUESTION_REFUND, \
    STATUS_LOCKED, STATUS_HIDDEN, STATUS_LIVE, STATUS_CLOSED, A_REMOVE_GAME_EDITOR, A_MAKE_GAME_EDITOR, STATUS_REFUNDED, \
    METHOD_BKASH, METHOD_ROCKET, STATUS_PENDING, A_REFUND_BET, STATUS_ACCEPTED, A_DEPOSIT_ACCEPT, A_DEPOSIT_CANCEL, \
    STATUS_CANCELLED, A_WITHDRAW_ACCEPT, A_WITHDRAW_CANCEL, A_TRANSFER_ACCEPT, A_TRANSFER_CANCEL
from betting.models import Match, BetQuestion, QuestionOption, Deposit, Withdraw, Transfer, DepositMethod, Announcement, \
    Bet
from betting.views import set_config_to_model
from users.models import User, Club

c = Client()


def increase_balance(user: User, amount):
    user.balance += amount
    user.save()


def set_up_helper() -> (Club, Club, User, User, str, str, str, dict, dict, int, int, int):
    club1 = Club.objects.create(name='Test Club1', balance=5000, username='test_club1', password='test_pass1')
    club2 = Club.objects.create(name='Test Club2', balance=5000, username='test_club2', password='test_pass2')
    user1 = User.objects.create_superuser(username='test1', email='teng@gmail.com',
                                          phone='01774545', user_club=club1, password='12354')
    user2 = User.objects.create_user(username='test2', email='test2@gmail.com',
                                     phone='0174545', user_club=club1, password='1234')
    jwt1 = c.post('/api/login/', data={'username': 'test1', 'password': '12354'}).json()['jwt']
    jwt2 = c.post('/api/login/', data={'username': 'test2', 'password': '1234'}).json()['jwt']
    headers_super = {'HTTP_x-auth-token': jwt1, 'content_type': 'application/json', }
    headers_user = {'HTTP_x-auth-token': jwt2, 'content_type': 'application/json', }
    match_id = Match.objects.create(team_a_name='A', team_b_name='B', game_name='football').id
    question_id = BetQuestion.objects.create(match_id=match_id, question='Winner?').id
    option_id = QuestionOption.objects.create(option='Bad Way', rate='1.3').id
    BetQuestion.objects.get(pk=question_id).options.add(question_id)
    return club1, club2, user1, user2, jwt1, jwt2, headers_super, headers_user, match_id, question_id, option_id


class ActionTestCase(TestCase):
    def setUp(self) -> None:
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id, self.option_id) = (data[i] for i in range(11))
        self.api = '/api/actions/'
        self.club_jwt = c.post('/api/login/', data={'username': 'test_club1', 'password': 'test_pass1'}).json()['jwt']
        self.club_header = {'HTTP_club-token': self.club_jwt, 'content_type': 'application/json'}

    def test_lock_match(self):
        response = c.post(self.api, {'action_code': A_MATCH_LOCK, 'match_id': self.match_id}, **self.headers_super)
        self.assertEqual(response.status_code, 200, 'Should be able to lock match')
        match = Match.objects.get(pk=self.match_id)
        self.assertEqual(match.status, STATUS_LOCKED, 'Should be able to lock match')

    def test_lock_match_staff(self):
        self.user2.is_staff = True
        self.user2.save()
        response = c.post(self.api, {'action_code': A_MATCH_LOCK, 'match_id': self.match_id}, **self.headers_user)
        self.assertEqual(response.status_code, 200, 'Should be able to lock match')
        match = Match.objects.get(pk=self.match_id)
        self.assertEqual(match.status, STATUS_LOCKED, 'Should be able to lock match')

    def test_lock_match_game_editor(self):
        self.user2.game_editor = True
        self.user2.save()
        response = c.post(self.api, {'action_code': A_MATCH_LOCK, 'match_id': self.match_id}, **self.headers_user)
        self.assertEqual(response.status_code, 200, 'Should be able to lock match')
        match = Match.objects.get(pk=self.match_id)
        self.assertEqual(match.status, STATUS_LOCKED, 'Should be able to lock match')

    def test_lock_match_user(self):
        response = c.post(self.api, {'action_code': A_MATCH_LOCK, 'match_id': self.match_id}, **self.headers_user)
        self.assertEqual(response.status_code, 403, 'Should not be able to lock match')
        match = Match.objects.get(pk=self.match_id)
        self.assertNotEqual(match.status, STATUS_LOCKED, 'Should not be able to lock match')

    def test_hide_match(self):
        response = c.post(self.api, {'action_code': A_MATCH_HIDE, 'match_id': self.match_id}, **self.headers_super)
        self.assertEqual(response.status_code, 200, 'Should be able to hide match')
        match = Match.objects.get(pk=self.match_id)
        self.assertEqual(match.status, STATUS_HIDDEN, 'Should be able to hide match')

    def test_hide_match_user(self):
        Match.objects.filter(pk=self.match_id).update(status=STATUS_LIVE)
        response = c.post(self.api, {'action_code': A_MATCH_HIDE, 'match_id': self.match_id}, **self.headers_user)
        match = Match.objects.get(pk=self.match_id)
        self.assertEqual(response.status_code, 403, 'Should not be able to hide match')
        self.assertNotEqual(match.status, STATUS_HIDDEN, 'Should not be able to hide match')

    def test_match_go_live(self):
        response = c.post(self.api, {'action_code': A_MATCH_GO_LIVE, 'match_id': self.match_id}, **self.headers_super)
        self.assertEqual(response.status_code, 200, 'Should be able to go live')
        match = Match.objects.get(pk=self.match_id)
        self.assertEqual(match.status, STATUS_LIVE, 'Should be able to go live')

    def test_match_end_match(self):
        response = c.post(self.api, {'action_code': A_MATCH_END_NOW, 'match_id': self.match_id}, **self.headers_super)
        self.assertEqual(response.status_code, 200, 'Should be able to close match')
        match = Match.objects.get(pk=self.match_id)
        self.assertEqual(match.status, STATUS_CLOSED, 'Should be able to close match')

    def test_lock_question(self):
        response = c.post(self.api, {'action_code': A_QUESTION_LOCK, 'question_id': self.question_id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200, 'Should be able to lock question')
        question = BetQuestion.objects.get(pk=self.question_id)
        self.assertEqual(question.status, STATUS_LOCKED, 'Should be able to lock question')

    def test_hide_question(self):
        BetQuestion.objects.filter(pk=self.question_id).update(status=STATUS_LIVE)
        response = c.post(self.api, {'action_code': A_QUESTION_HIDE, 'question_id': self.question_id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200, 'Should be able to hide bet question')
        question = BetQuestion.objects.get(pk=self.question_id)
        self.assertEqual(question.status, STATUS_HIDDEN, 'Should be able to change start time of match')

    def test_end_question_now(self):
        response = c.post(self.api, {'action_code': A_QUESTION_END_NOW, 'question_id': self.question_id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200, 'Should be able to close question')
        question = BetQuestion.objects.get(pk=self.question_id)
        self.assertEqual(question.status, STATUS_CLOSED, 'Should be able to close question')

    def test_question_select_winner(self):
        response = c.post(self.api, {'action_code': A_QUESTION_SELECT_WINNER, 'question_id': self.question_id,
                                     'option_id': self.option_id}, **self.headers_super)
        self.assertEqual(response.status_code, 200, 'Should be able to change start time of match')
        question = BetQuestion.objects.get(pk=self.question_id)
        self.assertEqual(question.winner_id, self.option_id, 'Should be able to change start time of match')

    def test_question_unselect_winner(self):
        question = BetQuestion.objects.get(pk=self.question_id)
        question.winner_id = self.option_id
        question.save()
        response = c.post(self.api, {'action_code': A_QUESTION_UNSELECT_WINNER, 'question_id': self.question_id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200, 'Should be able to un pay question')
        question.refresh_from_db()
        self.assertEqual(question.status, STATUS_LOCKED, 'Should be able to un pay question')

    def test_question_refund(self):
        response = c.post(self.api, {'action_code': A_QUESTION_REFUND, 'question_id': self.question_id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200, 'Should be able to change start time of match')
        question = BetQuestion.objects.get(pk=self.question_id)
        self.assertEqual(question.status, STATUS_REFUNDED, 'Should be able to change start time of match')

    def test_make_game_editor(self):
        c.post(self.api, {'action_code': A_MAKE_GAME_EDITOR, 'user_id': self.user2.id},
               **self.headers_super)
        self.user2.refresh_from_db()
        self.assertEqual(self.user2.game_editor, True, 'Should be able to make game editor')

    def test_make_game_editor_user(self):
        c.post(self.api, {'action_code': A_MAKE_GAME_EDITOR, 'user_id': self.user2.id},
               **self.headers_user)
        self.user2.refresh_from_db()
        self.assertEqual(self.user2.game_editor, False, 'Should not be able to make game editor')

    def test_remove_game_editor(self):
        self.user2.game_editor = True
        self.user2.save()
        c.post(self.api, {'action_code': A_REMOVE_GAME_EDITOR, 'user_id': self.user2.id},
               **self.headers_super)
        self.user2.refresh_from_db()
        self.assertEqual(self.user2.game_editor, False, 'Should be able to make game editor')

    def test_remove_game_editor_user(self):
        self.user2.game_editor = True
        self.user2.save()
        c.post(self.api, {'action_code': A_REMOVE_GAME_EDITOR, 'user_id': self.user2.id},
               **self.headers_user)
        self.user2.refresh_from_db()
        self.assertEqual(self.user2.game_editor, True, 'Should not be able to make game editor')

    def test_refund(self):
        increase_balance(self.user2, 5000)
        bet_id = c.post('/api/bet/', data={'amount': 100, 'bet_question': self.question_id, 'choice': self.option_id},
                        **self.headers_user).json()['id']
        self.user2.refresh_from_db()
        self.assertEqual(4900, self.user2.balance, 'Balance should be decreased')
        response = c.post(self.api, {'action_code': A_REFUND_BET, 'bet_id': bet_id, 'percent': 90},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200, 'Should be able to refund')
        self.user2.refresh_from_db()
        bet = Bet.objects.get(pk=bet_id)
        self.assertEqual(bet.status, STATUS_REFUNDED, 'Status should be refunded')
        self.assertEqual(4900 + 100 * 0.9, self.user2.balance, 'Should be able to refund')
        response = c.post(self.api, {'action_code': A_REFUND_BET, 'bet_id': bet_id, 'percent': -90},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200, 'Should be able to refund')
        self.user2.refresh_from_db()
        bet = Bet.objects.get(pk=bet_id)
        self.assertEqual(bet.status, STATUS_REFUNDED, 'Status should be refunded')
        self.assertEqual(4900, self.user2.balance, 'Should be able to refund')


class TransactionTest(TestCase):
    def setUp(self) -> None:
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id, self.option_id) = (data[i] for i in range(11))
        self.club_jwt = c.post('/api/login/', data={'username': 'test_club1', 'password': 'test_pass1'}).json()['jwt']
        self.club_header = {'HTTP_club-token': self.club_jwt, 'content_type': 'application/json'}
        self.api = '/api/actions/'

    def test_accept_deposit(self):
        deposit = Deposit.objects.create(user=self.user2, amount=500, method=METHOD_ROCKET)
        balance = self.user2.balance
        response = c.post(self.api, {'action_code': A_DEPOSIT_ACCEPT, 'deposit_id': deposit.id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200)
        deposit.refresh_from_db()
        self.user2.refresh_from_db()
        self.assertEqual(deposit.status, STATUS_ACCEPTED)
        self.assertEqual(self.user2.balance, balance + 500)
        self.assertEqual(self.user2.balance, deposit.balance)
        response = c.post(self.api, {'action_code': A_DEPOSIT_CANCEL, 'deposit_id': deposit.id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200)
        deposit.refresh_from_db()
        self.user2.refresh_from_db()
        self.assertEqual(deposit.status, STATUS_CANCELLED)
        self.assertEqual(self.user2.balance, balance)

    def test_cancel_deposit(self):
        deposit = Deposit.objects.create(user=self.user2, amount=500, method=METHOD_ROCKET)
        balance = self.user2.balance
        response = c.post(self.api, {'action_code': A_DEPOSIT_CANCEL, 'deposit_id': deposit.id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200)
        deposit.refresh_from_db()
        self.user2.refresh_from_db()
        self.assertEqual(deposit.status, STATUS_CANCELLED)
        self.assertEqual(self.user2.balance, balance)

    def test_accept_withdraw(self):
        withdraw = Withdraw.objects.create(user=self.user2, amount=500)
        balance = self.user2.balance
        response = c.post(self.api, {'action_code': A_WITHDRAW_ACCEPT, 'withdraw_id': withdraw.id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200)
        withdraw.refresh_from_db()
        self.user2.refresh_from_db()
        self.assertEqual(withdraw.status, STATUS_ACCEPTED)
        self.assertEqual(self.user2.balance, balance)
        self.assertEqual(self.user2.balance, withdraw.balance)
        response = c.post(self.api, {'action_code': A_WITHDRAW_CANCEL, 'withdraw_id': withdraw.id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200)
        withdraw.refresh_from_db()
        self.user2.refresh_from_db()
        self.assertEqual(withdraw.status, STATUS_CANCELLED)
        self.assertEqual(self.user2.balance, balance + 500)

    def test_cancel_withdraw(self):
        withdraw = Withdraw.objects.create(user=self.user2, amount=500, method=METHOD_ROCKET)
        balance = self.user2.balance
        response = c.post(self.api, {'action_code': A_WITHDRAW_CANCEL, 'withdraw_id': withdraw.id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200)
        withdraw.refresh_from_db()
        self.user2.refresh_from_db()
        self.assertEqual(withdraw.status, STATUS_CANCELLED)
        self.assertEqual(self.user2.balance, balance + withdraw.amount)

    def test_accept_transfer(self):
        transfer = Transfer.objects.create(sender=self.user2, amount=500, recipient=self.user1)
        balance = self.user1.balance
        response = c.post(self.api, {'action_code': A_TRANSFER_ACCEPT, 'transfer_id': transfer.id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200)
        transfer.refresh_from_db()
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        self.assertEqual(transfer.status, STATUS_ACCEPTED)
        self.assertEqual(self.user1.balance, balance + 500)
        self.assertEqual(self.user2.balance, transfer.balance)
        response = c.post(self.api, {'action_code': A_TRANSFER_CANCEL, 'transfer_id': transfer.id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200)
        transfer.refresh_from_db()
        self.user1.refresh_from_db()
        self.assertEqual(transfer.status, STATUS_CANCELLED)
        self.assertEqual(self.user1.balance, balance)

    def test_cancel_transfer(self):
        transfer = Transfer.objects.create(sender=self.user2, amount=500, recipient=self.user1)
        balance = self.user1.balance
        response = c.post(self.api, {'action_code': A_TRANSFER_CANCEL, 'transfer_id': transfer.id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200)
        transfer.refresh_from_db()
        self.user1.refresh_from_db()
        self.assertEqual(transfer.status, STATUS_CANCELLED)
        self.assertEqual(self.user1.balance, balance)

    def test_accept_transfer_club(self):
        transfer = Transfer.objects.create(club=self.club1, amount=500, recipient=self.user1)
        balance = self.user1.balance
        response = c.post(self.api, {'action_code': A_TRANSFER_ACCEPT, 'transfer_id': transfer.id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200)
        transfer.refresh_from_db()
        self.user1.refresh_from_db()
        self.assertEqual(transfer.status, STATUS_ACCEPTED)
        self.assertEqual(self.user1.balance, balance + 500)
        self.assertEqual(self.club1.balance, transfer.balance)
        response = c.post(self.api, {'action_code': A_TRANSFER_CANCEL, 'transfer_id': transfer.id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200)
        transfer.refresh_from_db()
        self.user1.refresh_from_db()
        self.assertEqual(transfer.status, STATUS_CANCELLED)
        self.assertEqual(self.user1.balance, balance)

    def test_cancel_transfer_club(self):
        transfer = Transfer.objects.create(club=self.club1, amount=500, recipient=self.user1)
        balance = self.user1.balance
        response = c.post(self.api, {'action_code': A_TRANSFER_CANCEL, 'transfer_id': transfer.id},
                          **self.headers_super)
        self.assertEqual(response.status_code, 200)
        transfer.refresh_from_db()
        self.user2.refresh_from_db()
        self.assertEqual(transfer.status, STATUS_CANCELLED)
        self.assertEqual(self.user1.balance, balance)


class AllTransactionTestCase(TestCase):
    def setUp(self) -> None:
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id, self.option_id) = (data[i] for i in range(11))
        self.club_jwt = c.post('/api/login/', data={'username': 'test_club1', 'password': 'test_pass1'}).json()['jwt']
        self.club_header = {'HTTP_club-token': self.club_jwt, 'content_type': 'application/json'}
        self.api = '/api/all-transactions/'

    def test_get_all(self):
        Transfer.objects.create(amount=500, sender=self.user2, recipient=self.user1)
        Transfer.objects.create(amount=500, sender=self.user2, recipient=self.user1)
        Deposit.objects.create(amount=500, user=self.user2)
        Withdraw.objects.create(amount=500, user=self.user2)
        response = c.get(self.api, **self.headers_user)
        self.assertEqual(response.status_code, 200, 'Should be able to get list')
        self.assertEqual(response.json()['count'], 4, '4 transactions present')
        for response in response.json()['results']:
            if response['type'] == 'deposit':
                deposit = Deposit.objects.get(pk=response['id'])
                self.assertEqual(deposit.status, response['status'], 'status is not same')
            if response['type'] == 'withdraw':
                withdraw = Withdraw.objects.get(pk=response['id'])
                self.assertEqual(withdraw.status, response['status'], 'status is not same')
            if response['type'] == 'transfer':
                transfer = Transfer.objects.get(pk=response['id'])
                self.assertEqual(transfer.status, response['status'], 'status is not same')

    def test_limit(self):
        response = c.get(f'{self.api}?limit=10', **self.headers_user)
        self.assertEqual(response.status_code, 200)

    def test_limit_offset(self):
        response = c.get(f'{self.api}?limit=10&offset=5', **self.headers_user)
        self.assertEqual(response.status_code, 200)

    def test_get_all_club(self):
        increase_balance(self.user2, 5000)
        c.post('/api/bet/', data={'amount': 100, 'bet_question': self.question_id, 'choice': self.option_id},
               **self.headers_user)
        Deposit.objects.create(club=self.club1, amount=500)
        response = c.get(f'{self.api}?club=true', **self.club_header)
        self.assertEqual(response.status_code, 200, 'Should be able to get list')
        self.assertEqual(response.json()['count'], 2, '2 transactions present')
        for response in response.json()['results']:
            if response['type'] == 'deposit':
                deposit = Deposit.objects.get(pk=response['id'])
                self.assertEqual(deposit.status, response['status'], 'status is not same')
            if response['type'] == 'transfer':
                transfer = Transfer.objects.get(pk=response['id'])
                self.assertEqual(transfer.status, response['status'], 'status is not same')


class AnnouncementTest(TestCase):
    def setUp(self):
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id) = (data[i] for i in range(10))
        self.api = '/api/announcement/'

    def test_create_announcement(self):
        response = c.post(self.api, {'text': 'Test Announcement'}, **self.headers_super)
        self.assertEqual(response.status_code, 201, f'Create announcement by superuser\n {response.content}')
        self.assertEqual(response.json()['text'], 'Test Announcement', f'Wrong text')

    def test_create_announcement_user(self):
        response = c.post(self.api, {'text': 'Test Announcement'}, **self.headers_user)
        self.assertEqual(response.status_code, 403, f'Create announcement by superuser\n{response.content_type}')

    def test_update_announcement(self):
        response = c.post(self.api, {'text': 'Test Announcement'}, **self.headers_super)
        self.assertEqual(response.status_code, 201, f'Create announcement by superuser\n{response.content_type}')
        announcement = Announcement.objects.get(pk=response.json()['id'])
        response = c.patch(f'{self.api}{announcement.id}/', {'text': 'Test Announcement'}, **self.headers_super)
        self.assertEqual(response.json()['text'], 'Test Announcement', f'Wrong text')

    def test_update_announcement_user(self):
        response = c.post(self.api, {'text': 'Test Announcement'}, **self.headers_super)
        self.assertEqual(response.status_code, 201, f'Create announcement by superuser\n{response.content_type}')
        announcement = Announcement.objects.get(pk=response.json()['id'])
        response = c.patch(f'{self.api}{announcement.id}/', {'text': 'Test Announcement'}, **self.headers_user)
        self.assertEqual(response.status_code, 403, f'User can not update announcement\n')


class BetQuestionTest(TestCase):
    def setUp(self):
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id) = (data[i] for i in range(10))
        self.api = '/api/bet-question/'

    def test_get_bet_question(self):
        response = c.get(self.api)
        self.assertEqual(response.status_code, 200)

    def test_get_bet_question_fast(self):
        response = c.get(f'{self.api}?fast=true')
        self.assertEqual(response.status_code, 200)

    def test_create_bet_question(self):
        response = c.post(self.api,
                          data={'match': self.match_id, 'question': 'who will win?',
                                'options': [{'option': 'hello', 'rate': 1.6}]},
                          **self.headers_super)
        self.assertEqual(response.status_code, 201, msg=f'Should be able to create question\n{response.content}')

    def test_create_bet_question_regular(self):
        response = c.post(self.api,
                          data={'match': self.match_id, 'question': 'who will win?'}, **self.headers_user)
        self.assertEqual(response.status_code, 403, msg=f'Should not be able to create question\n{response.content}')

    def test_update_question(self):
        response = c.patch(f'{self.api}{self.question_id}/',
                           data={'question': 'My winner?'}, **self.headers_super)
        self.assertEqual(response.status_code, 200, msg='should be able to update match')
        self.assertEqual(response.json()['question'], 'My winner?',
                         msg=f'should be able to update match, {response.content}')

    def test_update_question_user(self):
        response = c.patch(f'{self.api}{self.question_id}/',
                           data={'question': 'My winner?'}, **self.headers_user)
        self.assertEqual(response.status_code, 403, msg='should not be able to update match')

    def test_delete_question(self):
        response = c.delete(f'{self.api}{self.question_id}/',
                            data={'question': 'My winner?'}, **self.headers_super)
        self.assertEqual(response.status_code, 204, msg='should be able to delete match')

    def test_delete_question_user(self):
        response = c.delete(f'{self.api}{self.question_id}/',
                            data={'question': 'My winner?'}, **self.headers_user)
        self.assertEqual(response.status_code, 403, msg='should not be able to delete match')


class BetTestCase(TestCase):
    def setUp(self) -> None:
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id, self.option_id) = (data[i] for i in range(11))

    def test_create_bet(self):
        increase_balance(self.user2, 5000)
        response = c.post('/api/bet/', data={'amount': 100, 'bet_question': self.question_id, 'choice': self.option_id},
                          **self.headers_user)
        self.user2.refresh_from_db()
        self.assertEqual(response.status_code, 201, msg=f'Should be able to bet\n {response.content}')
        self.assertEqual(response.json()['user_balance'], 4900, msg=f'User balance is not correct, {response.json()}')
        self.assertEqual(response.json()['win_rate'], QuestionOption.objects.get(id=self.option_id).rate)
        self.assertEqual(self.user2.balance, 4900,
                         msg=f'User balance is not correct, {UserDetailsSerializer(self.user2).data}')

    def test_create_bet_before_start(self):
        increase_balance(self.user2, 5000)
        Match.objects.update(id=self.question_id, start_time=timezone.now() + timedelta(minutes=10))
        response = c.post('/api/bet/', data={'amount': 500, 'bet_question': self.question_id,
                                             'choice': self.option_id}, **self.headers_user)
        self.assertEqual(response.status_code, 201, msg=f'to bet before match start\n{response.content}')

    def test_create_bet_unauthenticated_user(self):
        increase_balance(self.user2, 5000)
        response = c.post('/api/bet/', data={'amount': 500, 'bet_question': self.question_id,
                                             'choice': self.option_id})
        self.assertEqual(response.status_code, 403, msg=f'to bet before match start\n{response.content}')

    def test_create_bet_low_balance(self):
        increase_balance(self.user2, 500)
        response = c.post('/api/bet/', data={'amount': 500, 'bet_question': self.question_id, 'choice': self.option_id},
                          **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'Should not be able to bet with 0 balance left')

    def test_create_bet_low_amount(self):
        increase_balance(self.user2, 5000)
        response = c.post('/api/bet/', data={'amount': 5, 'bet_question': self.question_id, 'choice': self.option_id},
                          **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'Should not be able to bet with low amount')

    def test_create_bet_huge_amount(self):
        increase_balance(self.user2, 5000000)
        response = c.post('/api/bet/', data={'amount': 500000, 'bet_question': self.question_id,
                                             'choice': self.option_id}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'Should not be able to bet with low amount')

    def test_create_bet_match_ended(self):
        increase_balance(self.user2, 5000)
        Match.objects.update(id=self.match_id, status=STATUS_CLOSED)
        response = c.post('/api/bet/', data={'amount': 500, 'bet_question': self.question_id,
                                             'choice': self.option_id}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'Should not be able to bet to ended match')

    def test_create_bet_match_locked(self):
        increase_balance(self.user2, 5000)
        Match.objects.update(id=self.match_id, status=STATUS_LOCKED)
        response = c.post('/api/bet/', data={'amount': 500, 'bet_question': self.question_id,
                                             'choice': self.option_id}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'Should not be able to bet to locked match')

    def test_create_bet_question_ended(self):
        increase_balance(self.user2, 5000)
        BetQuestion.objects.update(id=self.question_id, status=STATUS_CLOSED)
        response = c.post('/api/bet/', data={'amount': 500, 'bet_question': self.question_id,
                                             'choice': self.option_id}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'Should not be able to bet to ended question')

    def test_create_bet_question_locked(self):
        increase_balance(self.user2, 5000)
        BetQuestion.objects.update(id=self.question_id, status=STATUS_LOCKED)
        response = c.post('/api/bet/', data={'amount': 500, 'bet_question': self.question_id,
                                             'choice': self.option_id}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'Should not be able to bet to ended question')


class ClubTest(TestCase):
    def setUp(self):
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id) = (data[i] for i in range(10))
        self.api = '/api/club/'

    def test_create_club(self):
        response = c.post(self.api, {'name': 'Hi Club', 'username': 'abc_ab', 'password': '123456'},
                          **self.headers_super)
        self.assertEqual(response.status_code, 201, f'Should be able to create club\n{response.content}')

    def test_create_club_duplicate_club_username(self):
        response = c.post(self.api, {'name': 'Hi Club', 'username': 'test_club1', 'password': '123456'},
                          **self.headers_super)
        self.assertEqual(response.status_code, 400, 'Should not be able to create club')

    def test_create_club_duplicate_username(self):
        response = c.post(self.api, {'name': 'Hi Club', 'username': 'test1', 'password': '123456'},
                          **self.headers_super)
        self.assertEqual(response.status_code, 400, 'Should be able to create club')

    def test_create_club_regular_user(self):
        response = c.post(self.api, {'name': 'Hi Club', 'username': 'club_bb', 'password': '123456'},
                          **self.headers_user)
        self.assertEqual(response.status_code, 403, 'Should not be able to create club')

    # Update club details
    def test_update_club(self):
        response = c.patch(f'{self.api}{self.club1.id}/', {'name': 'Hi Club2', 'club_commission': 5.0,
                                                           'username': 'abc_ab1', 'password': '123457'},
                           **self.headers_super)
        self.assertEqual(response.status_code, 200, f'Should be able to update club\n{response.content}')
        data = response.json()
        self.club1.refresh_from_db()
        self.assertEqual(data['name'], 'Hi Club2', f'Should be able to update club\n{response.content}')
        self.assertEqual(data['club_commission'], 5.0, f'Should be able to update club\n{response.content}')
        self.assertEqual(data['username'], 'abc_ab1', f'Should be able to update club\n{response.content}')
        self.assertEqual(self.club1.password, '123457', f'Should be able to update club\n{response.content}')

    def test_update_club_admin(self):
        self.club1.admin = self.user2
        self.club1.save()
        response = c.patch(f'{self.api}{self.club1.id}/', {'name': 'Hi Club2', 'club_commission': 5.0,
                                                           'username': 'abc_ab1', 'password': '123457'},
                           **self.headers_user)
        self.assertEqual(response.status_code, 200, f'Should be able to update club\n{response.content}')
        data = response.json()
        self.assertEqual(data['name'], 'Hi Club2', f'Should be able to update club\n{response.content}')
        self.assertEqual(data['club_commission'], 5.0, f'Should be able to update club\n{response.content}')
        self.assertEqual(data['username'], 'abc_ab1', f'Should be able to update club\n{response.content}')

    def test_update_club_user(self):
        response = c.patch(f'{self.api}{self.club1.id}/', {'name': 'Hi Club2', 'club_commission': 5.0,
                                                           'username': 'abc_ab1', 'password': '123457'},
                           **self.headers_user)
        self.assertEqual(response.status_code, 403, f'Should not be able to update club')

    def test_update_club_duplicate_username(self):
        response = c.patch(f'{self.api}{self.club1.id}/', {'username': 'test1'}, **self.headers_super)
        self.assertEqual(response.status_code, 400, f'duplicate username should be prohibited\n{response.content}')


class ConfigTestCase(TestCase):
    def setUp(self) -> None:
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id, self.option_id) = (data[i] for i in range(11))
        self.api = '/api/configuration/'
        c.get('/bet/initialize/')

    def test_update_config(self):
        response = c.patch(f'{self.api}max_bet/', {'value': 10000}, **self.headers_super)
        self.assertEqual(response.status_code, 200, 'Settings should be changeable')
        self.assertEqual(response.json()['value'], '10000', 'Settings should be changeable')

    def test_update_config_user(self):
        response = c.patch(f'{self.api}max_bet/', {'value': 10000}, **self.headers_user)
        self.assertEqual(response.status_code, 403, 'Settings should be changeable')

    def test_get_config(self):
        response = c.get(f'{self.api}max_bet/', **self.headers_super)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['value'], '25000')

    def test_get_config_user(self):
        response = c.get(f'{self.api}max_bet/', **self.headers_user)
        self.assertEqual(response.status_code, 403)

    def test_delete_config(self):
        response = c.delete(f'{self.api}max_bet/', **self.headers_super)
        self.assertEqual(response.status_code, 405)


class DashboardTest(TestCase):
    def setUp(self) -> None:
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id, self.option_id) = (data[i] for i in range(11))
        self.api = '/api/dashboard/'

    def test_dashboard_data_super(self):
        response = c.get(self.api, {}, **self.headers_super)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(response.json()['details'], dict), True)

    def test_dashboard_data_user(self):
        response = c.get(self.api, {}, **self.headers_user)
        self.assertEqual(response.status_code, 403)

    def test_dashboard_data_ann(self):
        response = c.get(self.api)
        self.assertEqual(response.status_code, 403)


class DepositMethodTest(TestCase):
    def setUp(self) -> None:
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id, self.option_id) = (data[i] for i in range(11))
        self.api = '/api/deposit-method/'
        self.method1 = c.post(self.api, {'method': METHOD_BKASH, 'number1': '01454567'}, **self.headers_super).json()
        self.method2 = c.post(self.api, {'method': METHOD_BKASH, 'number1': '01454567'}, **self.headers_super).json()

    def test_create_deposit_method(self):
        response = c.post(self.api, {'method': METHOD_BKASH, 'number1': '01454567'}, **self.headers_super)
        self.assertEqual(response.status_code, 201, 'should be able to create deposit')

    def test_create_deposit_method_wrong_method(self):
        response = c.post(self.api, {'method': 'kkk', 'number1': '01454567'}, **self.headers_super)
        self.assertEqual(response.status_code, 400, 'should not be able to create deposit, wrong data')

    def test_create_deposit_method_user(self):
        response = c.post(self.api, {'method': METHOD_BKASH, 'number1': '01454567'}, **self.headers_user)
        self.assertEqual(response.status_code, 403, 'should not be able to create deposit')

    def test_create_deposit_method_ann(self):
        response = c.post(self.api, {'method': METHOD_BKASH, 'number1': '01454567'})
        self.assertEqual(response.status_code, 403, 'should not be able to create deposit')

    def test_get_deposit_method_ann(self):
        response = c.get(self.api, {})
        self.assertEqual(response.status_code, 200, 'should not be able to get deposit method list')
        data = response.json()
        self.assertEqual(data['count'], 2, 'Total amount of data')

    def test_update_deposit_method(self):
        method_id = self.method1['id']
        response = c.patch(f'{self.api}{method_id}/', {
            'convert_rate': 1.05, 'method': METHOD_ROCKET, 'number1': '454545212', 'number2': '0124575454'
        }, **self.headers_super)
        self.assertEqual(response.status_code, 200, 'Should be able to update')
        method = DepositMethod.objects.get(pk=method_id)
        self.assertEqual(method.method, METHOD_ROCKET)
        self.assertEqual(method.convert_rate, 1.05)
        self.assertEqual(method.number1, '454545212')
        self.assertEqual(method.number2, '0124575454')

    def test_update_deposit_method_user(self):
        method_id = self.method1['id']
        response = c.patch(f'{self.api}{method_id}/', {
            'convert_rate': 1.05, 'method': METHOD_ROCKET, 'number1': '454545212', 'number2': '0124575454'
        }, **self.headers_user)
        self.assertEqual(response.status_code, 403, 'Should be able to update')


class DepositTestCase(TestCase):
    def setUp(self) -> None:
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id, self.option_id) = (data[i] for i in range(11))
        self.api = '/api/deposit/'
        self.dep_id = Deposit.objects.create(amount=500, user_account='01445', site_account='014454548',
                                             method=METHOD_ROCKET, reference='fd7sf454f78fad').id

    def test_get_deposit(self):
        response = c.get(self.api, {}, **self.headers_super)
        self.assertEqual(response.status_code, 200)
        response = c.get(self.api)
        self.assertEqual(response.status_code, 403)

    def test_create_deposit(self):
        response = c.post(self.api,
                          data={'amount': 500, 'deposit_source': 'bank', 'user_account': '01445', 'site_account': '014',
                                'method': 'rocket', 'reference': 'fd7sf454f78fad'}, **self.headers_user)
        self.assertEqual(response.status_code, 201, msg=f'to deposit\n{response.content}')
        deposit = Deposit.objects.get(id=response.json()['id'])
        self.assertEqual(deposit.user, self.user2, 'Wrong user')
        self.assertEqual(deposit.status, STATUS_PENDING, 'Wrong user')

    def test_create_deposit_low(self):
        response = c.post(self.api,
                          data={'amount': 10, 'deposit_source': 'bank', 'user_account': '01445', 'site_account': '014',
                                'method': 'rocket', 'reference': 'fd7sf454f78fad'}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'low amount of deposit should not be allowed')

    def test_create_deposit_high(self):
        response = c.post(self.api,
                          data={'amount': 100000, 'deposit_source': 'bank', 'user_account': '01445',
                                'site_account': '014454548',
                                'method': 'rocket', 'reference': 'fd7sf454f78fad'}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'high amount of deposit should not be allowed')

    def test_update_deposit(self):
        response = c.patch(f'{self.api}{self.dep_id}/',
                           data={'amount': 800,
                                 'site_account': '014454548',
                                 'method': 'rocket', 'reference': 'fd7sf454f78fad'}, **self.headers_user)
        self.assertEqual(response.status_code, 405, msg=f'Not updatable')

    def test_update_deposit_superuser(self):
        response = c.patch(f'{self.api}{self.dep_id}/',
                           data={'amount': 800,
                                 'site_account': '014454548',
                                 'method': 'rocket', 'reference': 'fd7sf454f78fad'}, **self.headers_super)
        self.assertEqual(response.status_code, 405, msg=f'Not updatable')


class LoginTest(TestCase):
    def setUp(self):
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id) = (data[i] for i in range(10))

    def test_login_user(self):
        request = c.post('/api/login/', data={'username': 'test2', 'password': '1234'})
        self.assertEqual(request.status_code, 200, msg=f'User should be able to login.\n{request.content}')
        request = c.post('/api/login/', data={'username': 'test1', 'password': '12354'})
        self.assertEqual(request.status_code, 200, msg=f'User should be able to login.\n{request.content}')

    def test_login_club(self):
        request = c.post('/api/login/', data={'username': 'test_club1', 'password': 'test_pass1'})
        self.assertEqual(request.status_code, 200, msg=f'Club should be able to login.\n{request.content}')

    def test_login_user_wrong_password(self):
        request = c.post('/api/login/', data={'username': 'test1', 'password': '1254'})
        self.assertNotEqual(request.status_code, 200, msg='User should not be able to login')

    def test_login_user_wrong_username(self):
        request = c.post('/api/login/', data={'username': 'test5', 'password': '1254'})
        self.assertNotEqual(request.status_code, 200, msg='User should not be able to login')


class MatchTest(TestCase):
    def setUp(self):
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id) = (data[i] for i in range(10))
        self.match_data = {
            'game_name': 'football',
            'team_a_name': 'A',
            'team_b_name': 'B',
        }
        self.api = '/api/match/'

    def test_get_match(self):
        response = c.get(self.api)
        self.assertEqual(response.status_code, 200)

    def test_get_match_fast(self):
        response = c.get(f"{self.api}?fast=true")
        self.assertEqual(response.status_code, 200)

    def test_create_match_superuser(self):
        headers = {'HTTP_x-auth-token': self.jwt1, 'content_type': 'application/json', }
        response = c.post('/api/match/', self.match_data, **headers)
        self.assertEqual(response.status_code, 201, f'Super user should be able to create match.\n{response.content}')

    def test_create_match_regular_user(self):
        headers = {'HTTP_x-auth-token': self.jwt2, 'content_type': 'application/json', }
        response = c.post('/api/match/', self.match_data, **headers)
        self.assertNotEqual(response.status_code, 201, f'User shouldn\'t be able to create match')

    def test_update_match_superuser(self):
        response = c.patch(f'/api/match/{self.match_id}/', data={'team_a_name': 'India'}, **self.headers_super)
        self.assertEqual(response.json()['team_a_name'], 'India', f'Must be able to update.\n{response.content}')

    def test_update_match_user(self):
        response = c.patch(f'/api/match/{self.match_id}/', data={'team_a_name': 'India'}, **self.headers_user)
        self.assertEqual(response.status_code, 403, f'Must not be able to update.\n{response.content}')

    def test_delete_match_superuser(self):
        response = c.delete(f'/api/match/{self.match_id}/', **self.headers_super)
        self.assertEqual(response.status_code, 204, 'Should be able to delete')

    def test_delete_match_user(self):
        response = c.delete(f'/api/match/{self.match_id}/', **self.headers_user)
        self.assertEqual(response.status_code, 403, 'Should not be able to delete')


class QuestionOptionTest(TestCase):
    def setUp(self):
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id) = (data[i] for i in range(10))

    def test_update_question_option(self):
        response = c.patch(f'/api/question-option/1/',
                           {'option': 'hello2', 'rate': '1.7'}, **self.headers_super)
        self.assertEqual(response.status_code, 200, msg=f'Should be able to update option\n{response.content}')
        self.assertEqual(response.json()['option'], 'hello2',
                         msg=f'Should be able to update option\n{response.content}')
        self.assertEqual(response.json()['rate'], 1.7,
                         msg=f'Should be able to update option\n{response.content}')

    def test_update_question_option_regular_user(self):
        response = c.patch(f'/api/question-option/1/',
                           {'option': 'hello2', 'rate': '1.7'}, **self.headers_user)
        self.assertEqual(response.status_code, 403, msg=f'Should be able to update option\n{response.content}')


class UserTestCase(TestCase):
    def setUp(self):
        data = set_up_helper()
        (self.club, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id) = (data[i] for i in range(10))
        self.api = '/api/user/'

    def test_get_users(self):
        response = c.get(self.api)
        self.assertEqual(response.status_code, 200)

    # Creation Test
    def test_can_register_valid_data(self):
        response = c.post(self.api, {'username': 'test3', 'email': 'testing@gmail.com',
                                         'phone': '017745445', 'user_club': self.club.id,
                                         'password': 'fds_sdf'})
        self.assertEqual(response.status_code, 201, msg=f'Should be able to create user.\n{response.content}')
        user = User.objects.get(pk=response.json()['id'])
        self.assertEqual(user.check_password('fds_sdf'), True, 'Password should be correct')
        self.assertEqual(user.username, 'test3', 'Username should be correct')
        self.assertEqual(user.phone, '017745445', 'Username should be correct')
        self.assertEqual(user.email, 'testing@gmail.com', 'Username should be correct')
        self.assertEqual(user.user_club_id, self.club.id, 'Username should be correct')

    def test_register_referrer(self):
        response = c.post('/api/user/', {'username': 'test3', 'email': 'testing@gmail.com',
                                         'phone': '017745445', 'user_club': self.club.id,
                                         'password': 'fds_sdf', 'referer_username': self.user2.username})
        self.assertEqual(response.status_code, 201, msg=f'Should be able to create user.\n{response.content}')
        user = User.objects.get(pk=response.json()['id'])
        self.assertEqual(user.referred_by.id, self.user2.id, 'Password should be correct')

    def test_can_register_without_club(self):
        request = c.post('/api/user/', {'username': 'test3',
                                        'email': 'testing@gmail.com',
                                        'phone': '017745445',
                                        'password': 'fd sdf fd'})
        self.assertNotEqual(request.status_code, 201, msg=f"Should not be able to create user without club.")

    def test_duplicate_username(self):
        request = c.post('/api/user/', {'username': 'test2',
                                        'email': 'testing@gmail.com',
                                        'phone': '017745445',
                                        'password': 'fd sdf fd'})
        self.assertEqual(request.status_code, 400, msg=f"Should not be able to register with duplicate username.")

    def test_duplicate_username_club(self):
        request = c.post('/api/user/', {'username': 'test_club1',
                                        'email': 'testing@gmail.com',
                                        'phone': '017745445',
                                        'password': 'fd sdf fd'})
        self.assertEqual(request.status_code, 400, msg=f"Should not be able to register with duplicate username.")

    def test_duplicate_email(self):
        request = c.post('/api/user/', {'username': 'test3',
                                        'email': 'teng@gmail.com',
                                        'phone': '017745445',
                                        'password': 'fd sdf fd'})
        self.assertEqual(request.status_code, 400, msg=f"Should not be able to register with duplicate username.")

    def test_duplicate_phone(self):
        request = c.post('/api/user/', {'username': 'test3',
                                        'email': 'testing@gmail.com',
                                        'phone': '01774545',
                                        'password': 'fd sdf fd'})
        self.assertEqual(request.status_code, 400, msg=f"Should not be able to register with duplicate username.")

    # Update test
    def test_update_user_club(self):
        response = c.patch(f'/api/user/{self.user2.id}/', {'user_club': self.club2.id}, **self.headers_user)
        self.assertEqual(response.status_code, 200, 'Should be able to update club')
        self.user2 = User.objects.get(pk=self.user2.id)
        self.assertEqual(self.user2.user_club.id, self.club2.id, msg='Club should be changed')

    def test_update_other_user_club(self):
        response = c.patch(f'/api/user/{self.user1.id}/', {'user_club': self.club2.id}, **self.headers_user)
        self.assertEqual(response.status_code, 403, 'Should be able to update club')

    def test_update_user_email_phone(self):
        response = c.patch(f'/api/user/{self.user2.id}/',
                           {'email': 'han@gma.com', 'phone': '45454545'}, **self.headers_user)
        self.assertEqual(response.status_code, 200, 'should be able to update')
        self.user2 = User.objects.get(pk=self.user2.id)
        self.assertEqual(self.user2.phone, '45454545', msg='Phone is not updated')
        self.assertEqual(self.user2.email, 'han@gma.com', msg='Email is not updated')

    def test_change_password(self):
        response = c.patch(f'/api/user/{self.user2.id}/', {'password': 'fds_sdf'}, **self.headers_user)
        self.assertEqual(response.status_code, 200, 'Should be able to change password')
        self.user2.refresh_from_db()
        self.assertEqual(self.user2.check_password('fds_sdf'), True, 'Password should be correct')


class TransferTestCase(TestCase):
    def setUp(self) -> None:
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id, self.option_id) = (data[i] for i in range(11))
        self.api = '/api/transfer/'
        self.api_full = '/api/transfer/?club=true'
        self.club1: Club = self.club1
        self.club1.admin = self.user2
        self.club1.balance = 500000
        self.club1.save()
        increase_balance(self.user2, 5000000)
        self.club_jwt = c.post('/api/login/', data={'username': 'test_club1', 'password': 'test_pass1'}).json()['jwt']
        self.club_header = {'HTTP_club-token': self.club_jwt, 'content_type': 'application/json'}
        self.transfer_id = Transfer.objects.create(club=self.club1, amount=500).id

    def test_get_transfer(self):
        response = c.get(self.api, {}, **self.headers_super)
        self.assertEqual(response.status_code, 200)
        response = c.get(self.api)
        self.assertEqual(response.status_code, 403)

    def test_create_club_transfer(self):
        response = c.post(self.api_full, data={'amount': 500}, **self.club_header)
        self.assertEqual(response.status_code, 201, msg=f'to withdraw\n{response.content}')
        self.assertEqual(Transfer.objects.get(id=response.json()['id']).club, self.club1, 'Wrong user')
        self.assertEqual(Transfer.objects.get(id=response.json()['id']).recipient, self.club1.admin, 'Wrong user')

    def test_create_club_transfer_multi(self):
        c.post(self.api_full, data={'amount': 500}, **self.club_header)
        response = c.post(self.api_full, data={'amount': 500}, **self.club_header)
        self.assertEqual(response.status_code, 400, msg=f'not to withdraw\n{response.content}\n '
                                                        f'TC: {Transfer.objects.filter(sender=self.user2).count()}')

    def test_create_club_transfer_low(self):
        response = c.post(self.api_full, data={'amount': 5}, **self.club_header)
        self.assertEqual(response.status_code, 400, msg=f'low amount of withdraw should not be allowed')

    def test_create_club_transfer_high(self):
        response = c.post(self.api_full, data={'amount': 50000}, **self.club_header)
        self.assertEqual(response.status_code, 400, msg=f'high amount of deposit should not be allowed')

    def test_update_club_transfer(self):
        response = c.patch(f'{self.api}{self.transfer_id}/?club=true', data={'amount': 500}, **self.club_header)
        self.assertEqual(response.status_code, 405, msg=f'Not updatable')

    def test_update_club_transfer_superuser(self):
        response = c.patch(f'{self.api}{self.transfer_id}/?club=true', data={'amount': 500}, **self.club_header)
        self.assertEqual(response.status_code, 405, msg=f'Not updatable')

    def test_create_transfer(self):
        response = c.post(self.api,
                          data={'amount': 500, 'recipient': self.user1.id}, **self.headers_user)
        self.assertEqual(response.status_code, 201, msg=f'to withdraw\n{response.content}')
        transfer = Transfer.objects.get(id=response.json()['id'])
        self.assertEqual(transfer.sender, self.user2, 'Wrong user')
        self.assertEqual(transfer.recipient, self.user1, 'Wrong user')

    def test_create_transfer_when_disabled(self):
        set_config_to_model('disable_user_transfer', '1')
        response = c.post(self.api,
                          data={'amount': 500, 'recipient': self.user1.id}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'transfer disabled temporary')

    def test_create_transfer_when_enabled(self):
        set_config_to_model('disable_user_transfer', '1')
        set_config_to_model('disable_user_transfer', '0')
        response = c.post(self.api,
                          data={'amount': 500, 'recipient': self.user1.id}, **self.headers_user)
        self.assertEqual(response.status_code, 201, msg=f'to withdraw\n{response.content}')
        self.assertEqual(Transfer.objects.get(id=response.json()['id']).sender, self.user2, 'Wrong user')

    def test_create_transfer_multi(self):
        response = c.post(self.api,
                          data={'amount': 500, 'recipient': self.user1.id}, **self.headers_user)
        self.assertEqual(response.status_code, 201, f'able to create transfer\n{response.content}')
        response = c.post(self.api,
                          data={'amount': 500, 'recipient': self.user1.id}, **self.headers_user)
        self.assertEqual(response.status_code, 201, f'able to create transfer\n{response.content}')
        response = c.post(self.api,
                          data={'amount': 500, 'recipient': self.user1.id}, **self.headers_user)
        self.assertEqual(response.status_code, 400,
                         msg=f'not to withdraw\n TC: {Transfer.objects.filter(sender=self.user2).count()}')

    def test_create_transfer_low(self):
        response = c.post(self.api,
                          data={'amount': 10, 'recipient': self.user1.id}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'low amount of withdraw should not be allowed')

    def test_create_transfer_high(self):
        response = c.post(self.api,
                          data={'amount': 50000, 'recipient': self.user1.id}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'high amount of deposit should not be allowed')

    def test_update_transfer(self):
        response = c.patch(f'{self.api}{self.transfer_id}/',
                           data={'amount': 500, 'recipient': self.user1.id}, **self.headers_user)
        self.assertEqual(response.status_code, 405, msg=f'Not updatable')

    def test_update_transfer_superuser(self):
        response = c.patch(f'{self.api}{self.transfer_id}/',
                           data={'amount': 500, 'recipient': self.user1.id}, **self.headers_super)
        self.assertEqual(response.status_code, 405, msg=f'Not updatable')


class WithdrawTestCase(TestCase):
    def setUp(self) -> None:
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id, self.option_id) = (data[i] for i in range(11))
        self.api = '/api/withdraw/'
        increase_balance(self.user2, 5000)
        self.withdraw_id = c.post(self.api,
                                  data={'amount': 500, 'user_account': '01445154', 'method': 'rocket', },
                                  **self.headers_user).json()['id']

    def test_get_withdraw(self):
        response = c.get(self.api, {}, **self.headers_super)
        self.assertEqual(response.status_code, 200)
        response = c.get(self.api)
        self.assertEqual(response.status_code, 403)

    def test_create_withdraw(self):
        response = c.post(self.api,
                          data={'amount': 500, 'user_account': '01445154', 'method': 'rocket', }, **self.headers_user)
        self.assertEqual(response.status_code, 201, msg=f'to withdraw\n{response.content}')
        self.assertEqual(Withdraw.objects.get(id=response.json()['id']).user, self.user2, 'Wrong user')

    def test_create_withdraw_low(self):
        response = c.post(self.api,
                          data={'amount': 10, 'user_account': '01445154', 'method': 'rocket', }, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'low amount of withdraw should not be allowed')

    def test_create_withdraw_high(self):
        response = c.post(self.api,
                          data={'amount': 100000, 'user_account': '01445', 'method': 'rocket'}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'high amount of deposit should not be allowed')

    def test_update_withdraw(self):
        response = c.patch(f'{self.api}{self.withdraw_id}/',
                           data={'amount': 800, 'user_account': '014454548', 'method': 'rocket'}, **self.headers_user)
        self.assertEqual(response.status_code, 405, msg=f'Not updatable')

    def test_update_withdraw_superuser(self):
        response = c.patch(f'{self.api}{self.withdraw_id}/',
                           data={'amount': 800, 'site_account': '014454548', 'method': 'rocket'}, **self.headers_super)
        self.assertEqual(response.status_code, 405, msg=f'Not updatable')
