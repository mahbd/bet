from datetime import timedelta

from django.test import TestCase, Client
from django.utils import timezone

from api.serializers import UserSerializer
from betting.models import Match, BetQuestion, QuestionOption, Deposit, Withdraw, Transfer
from users.models import User, Club

c = Client()


def increase_balance(user: User, amount):
    user.balance += amount
    user.save()


def set_up_helper():
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
    match_id = c.post('/api/match/', data={'title': 'Super Game', 'game_name': 'football',
                                           'end_time': str(timezone.now() + timedelta(days=1))},
                      **headers_super).json()['id']
    question = c.post('/api/bet-question/',
                      data={'match': match_id, 'question': 'who will win?',
                            'options': [{'option': 'hello', 'rate': 1.6}]}, **headers_super).json()
    question_id, option_id = question['id'], question['options'][0]['id']
    return club1, club2, user1, user2, jwt1, jwt2, headers_super, headers_user, match_id, question_id, option_id


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


class RegisterTest(TestCase):
    def setUp(self):
        data = set_up_helper()
        (self.club, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id) = (data[i] for i in range(10))

    # Creation Test
    def test_can_register_valid_data(self):
        request = c.post('/api/register/', {'username': 'test3',
                                            'email': 'testing@gmail.com',
                                            'phone': '017745445',
                                            'user_club': self.club.id,
                                            'password': 'fds sdf'})
        self.assertEqual(request.status_code, 201, msg=f'Should be able to create user.\n{request.content}')

    def test_can_register_without_club(self):
        request = c.post('/api/register/', {'username': 'test3',
                                            'email': 'testing@gmail.com',
                                            'phone': '017745445',
                                            'password': 'fd sdf fd'})
        self.assertNotEqual(request.status_code, 201, msg=f"Should not be able to create user without club.")

    def test_duplicate_username(self):
        request = c.post('/api/register/', {'username': 'test2',
                                            'email': 'testing@gmail.com',
                                            'phone': '017745445',
                                            'password': 'fd sdf fd'})
        self.assertEqual(request.status_code, 400, msg=f"Should not be able to register with duplicate username.")

    def test_duplicate_username_club(self):
        request = c.post('/api/register/', {'username': 'test_club1',
                                            'email': 'testing@gmail.com',
                                            'phone': '017745445',
                                            'password': 'fd sdf fd'})
        self.assertEqual(request.status_code, 400, msg=f"Should not be able to register with duplicate username.")

    def test_duplicate_email(self):
        request = c.post('/api/register/', {'username': 'test3',
                                            'email': 'teng@gmail.com',
                                            'phone': '017745445',
                                            'password': 'fd sdf fd'})
        self.assertEqual(request.status_code, 400, msg=f"Should not be able to register with duplicate username.")

    def test_duplicate_phone(self):
        request = c.post('/api/register/', {'username': 'test3',
                                            'email': 'testing@gmail.com',
                                            'phone': '01774545',
                                            'password': 'fd sdf fd'})
        self.assertEqual(request.status_code, 400, msg=f"Should not be able to register with duplicate username.")

    # Update test
    def test_update_user_club(self):
        headers = {'HTTP_x-auth-token': self.jwt1, 'content_type': 'application/json', }
        response = c.get('/api/user-detail-update/', {'user_club': self.club2.id}, **headers)
        self.assertEqual(response.json()['club_detail']['name'], self.club.name, msg='Wrong club name')
        response = c.patch('/api/user-detail-update/', {'user_club': self.club2.id}, **headers)
        self.assertEqual(response.json()['club_detail']['name'], self.club2.name, msg='Club should be changed')

    def test_update_user_email_phone(self):
        headers = {'HTTP_x-auth-token': self.jwt1, 'content_type': 'application/json', }
        response = c.patch('/api/user-detail-update/', {'email': 'himan@gma.com', 'phone': '45454545'}, **headers)
        self.assertEqual(response.json()['phone'], '45454545', msg='Phone is not updated')
        self.assertEqual(response.json()['email'], 'himan@gma.com', msg='Email is not updated')


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

    def test_create_match_superuser(self):
        headers = {'HTTP_x-auth-token': self.jwt1, 'content_type': 'application/json', }
        response = c.post('/api/match/', data={'title': 'Super Game', 'game_name': 'football',
                                               'end_time': str(timezone.now() + timedelta(days=1))}, **headers)
        self.assertEqual(response.status_code, 201, f'Super user should be able to create match.\n{response.content}')

    def test_create_match_regular_user(self):
        headers = {'HTTP_x-auth-token': self.jwt2, 'content_type': 'application/json', }
        response = c.post('/api/match/', data={'title': 'Super Game', 'game_name': 'football',
                                               'end_time': str(timezone.now() + timedelta(days=1))}, **headers)
        self.assertNotEqual(response.status_code, 201, f'User shouldn\'t be able to create match')

    def test_update_match_superuser(self):
        headers = {'HTTP_x-auth-token': self.jwt1, 'content_type': 'application/json', }
        mid = c.post('/api/match/', data={'title': 'Super Game', 'game_name': 'football',
                                          'end_time': str(timezone.now() + timedelta(days=1))},
                     **headers).json()['id']
        c.patch(f'/api/match/{mid}/', data={'title': 'Fine Game', 'game_name': 'football'}, **headers)
        response = c.get(f'/api/match/{mid}/', **headers)
        self.assertEqual(response.json()['title'], 'Fine Game', f'Must be able to update.\n{response.content}')

    def test_update_match_user(self):
        headers = {'HTTP_x-auth-token': self.jwt1, 'content_type': 'application/json', }
        mid = c.post('/api/match/', data={'title': 'Super Game', 'game_name': 'football',
                                          'end_time': str(timezone.now() + timedelta(days=1))}, **headers).json()['id']
        headers['HTTP_x-auth-token'] = self.jwt2
        c.patch(f'/api/match/{mid}/', data={'title': 'Fine Game', 'game_name': 'football'}, **headers)
        response = c.get(f'/api/match/{mid}/', data={'title': 'Fine Game', 'game_name': 'football'}, **headers)
        self.assertNotEqual(response.json()['title'], 'Fine Game', f'Must be able to update.\n{response.content}')

    def test_delete_match_superuser(self):
        headers = {'HTTP_x-auth-token': self.jwt1, 'content_type': 'application/json', }
        mid = c.post('/api/match/', data={'title': 'Super Game', 'game_name': 'football',
                                          'end_time': str(timezone.now() + timedelta(days=1))},
                     **headers).json()['id']
        response = c.delete(f'/api/match/{mid}/', **headers)
        self.assertEqual(response.status_code, 204, 'Should be able to delete')

    def test_delete_match_user(self):
        headers = {'HTTP_x-auth-token': self.jwt1, 'content_type': 'application/json', }
        mid = c.post('/api/match/', data={'title': 'Super Game', 'game_name': 'football',
                                          'end_time': str(timezone.now() + timedelta(days=1))},
                     **headers).json()['id']
        headers = {'HTTP_x-auth-token': self.jwt2, 'content_type': 'application/json', }
        response = c.delete(f'/api/match/{mid}/', **headers)
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


class BetQuestionTest(TestCase):
    def setUp(self):
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id) = (data[i] for i in range(10))

    def test_create_bet_question(self):
        response = c.post('/api/bet-question/',
                          data={'match': self.match_id, 'question': 'who will win?',
                                'options': [{'option': 'hello', 'rate': 1.6}]},
                          **self.headers_super)
        self.assertEqual(response.status_code, 201, msg=f'Should be able to create question\n{response.content}')

    def test_create_bet_question_regular(self):
        response = c.post('/api/bet-question/',
                          data={'match': self.match_id, 'question': 'who will win?'}, **self.headers_user)
        self.assertEqual(response.status_code, 403, msg=f'Should not be able to create question\n{response.content}')

    def test_update_question(self):
        response = c.patch(f'/api/bet-question/{self.question_id}/',
                           data={'question': 'My winner?'}, **self.headers_super)
        self.assertEqual(response.status_code, 200, msg='should be able to update match')
        self.assertEqual(response.json()['question'], 'My winner?',
                         msg=f'should be able to update match, {response.content}')

    def test_update_question_user(self):
        response = c.patch(f'/api/bet-question/{self.question_id}/',
                           data={'question': 'My winner?'}, **self.headers_user)
        self.assertEqual(response.status_code, 403, msg='should not be able to update match')

    def test_delete_question(self):
        response = c.delete(f'/api/bet-question/{self.question_id}/',
                            data={'question': 'My winner?'}, **self.headers_super)
        self.assertEqual(response.status_code, 204, msg='should be able to delete match')

    def test_delete_question_user(self):
        response = c.delete(f'/api/bet-question/{self.question_id}/',
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
                         msg=f'User balance is not correct, {UserSerializer(self.user2).data}')

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
        Match.objects.update(id=self.match_id, end_time=timezone.now() - timedelta(minutes=1))
        response = c.post('/api/bet/', data={'amount': 500, 'bet_question': self.question_id,
                                             'choice': self.option_id}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'Should not be able to bet to ended match')

    def test_create_bet_match_locked(self):
        increase_balance(self.user2, 5000)
        Match.objects.update(id=self.match_id, locked=True)
        response = c.post('/api/bet/', data={'amount': 500, 'bet_question': self.question_id,
                                             'choice': self.option_id}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'Should not be able to bet to locked match')

    def test_create_bet_question_ended(self):
        increase_balance(self.user2, 5000)
        BetQuestion.objects.update(id=self.question_id, end_time=timezone.now() - timedelta(minutes=1))
        response = c.post('/api/bet/', data={'amount': 500, 'bet_question': self.question_id,
                                             'choice': self.option_id}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'Should not be able to bet to ended question')

    def test_create_bet_question_locked(self):
        increase_balance(self.user2, 5000)
        BetQuestion.objects.update(id=self.question_id, locked=True)
        response = c.post('/api/bet/', data={'amount': 500, 'bet_question': self.question_id,
                                             'choice': self.option_id}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'Should not be able to bet to ended question')


class DepositTestCase(TestCase):
    def setUp(self) -> None:
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id, self.option_id) = (data[i] for i in range(11))
        self.api = '/api/deposit/'
        self.dep_id = c.post(self.api,
                             data={'amount': 500, 'deposit_source': 'bank', 'user_account': '01445',
                                   'site_account': '014454548', 'method': 'rocket',
                                   'transaction_id': 'fd7sf454f78fad'}, **self.headers_user).json()['id']

    def test_create_deposit(self):
        response = c.post(self.api,
                          data={'amount': 500, 'deposit_source': 'bank', 'user_account': '01445', 'site_account': '014',
                                'method': 'rocket', 'transaction_id': 'fd7sf454f78fad'}, **self.headers_user)
        self.assertEqual(response.status_code, 201, msg=f'to deposit\n{response.content}')
        self.assertEqual(Deposit.objects.get(id=response.json()['id']).user, self.user2, 'Wrong user')

    def test_create_deposit_low(self):
        response = c.post(self.api,
                          data={'amount': 10, 'deposit_source': 'bank', 'user_account': '01445', 'site_account': '014',
                                'method': 'rocket', 'transaction_id': 'fd7sf454f78fad'}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'low amount of deposit should not be allowed')

    def test_create_deposit_high(self):
        response = c.post(self.api,
                          data={'amount': 100000, 'deposit_source': 'bank', 'user_account': '01445',
                                'site_account': '014454548',
                                'method': 'rocket', 'transaction_id': 'fd7sf454f78fad'}, **self.headers_user)
        self.assertEqual(response.status_code, 400, msg=f'high amount of deposit should not be allowed')

    def test_update_deposit(self):
        response = c.patch(f'{self.api}{self.dep_id}/',
                           data={'amount': 800,
                                 'site_account': '014454548',
                                 'method': 'rocket', 'transaction_id': 'fd7sf454f78fad'}, **self.headers_user)
        self.assertEqual(response.status_code, 405, msg=f'Not updatable')

    def test_update_deposit_superuser(self):
        response = c.patch(f'{self.api}{self.dep_id}/',
                           data={'amount': 800,
                                 'site_account': '014454548',
                                 'method': 'rocket', 'transaction_id': 'fd7sf454f78fad'}, **self.headers_super)
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


class TransferTestCase(TestCase):
    def setUp(self) -> None:
        data = set_up_helper()
        (self.club1, self.club2, self.user1, self.user2, self.jwt1, self.jwt2, self.headers_super, self.headers_user,
         self.match_id, self.question_id, self.option_id) = (data[i] for i in range(11))
        self.api = '/api/transfer/'
        increase_balance(self.user2, 500000)
        self.club1.admin = self.user2
        self.club1.save()
        self.transfer_id = c.post(self.api,
                                  data={'amount': 500, 'recipient': self.user1.id}, **self.headers_user).json()['id']

    def test_create_transfer(self):
        response = c.post(self.api,
                          data={'amount': 500, 'recipient': self.user1.id}, **self.headers_user)
        self.assertEqual(response.status_code, 201, msg=f'to withdraw\n{response.content}')
        self.assertEqual(Transfer.objects.get(id=response.json()['id']).sender, self.user2, 'Wrong user')

    def test_create_transfer_multi(self):
        c.post(self.api,
               data={'amount': 500, 'recipient': self.user1.id}, **self.headers_user)
        response = c.post(self.api,
                          data={'amount': 500, 'recipient': self.user1.id}, **self.headers_user)
        self.assertEqual(response.status_code, 400,
                         msg=f'not to withdraw\n{response.content}\n TC: {Transfer.objects.filter(sender=self.user2).count()}')

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


class TransferClubTestCase(TestCase):
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
        self.club_jwt = c.post('/api/login/', data={'username': 'test_club1', 'password': 'test_pass1'}).json()['jwt']
        self.club_header = {'HTTP_club-token': self.club_jwt, 'content_type': 'application/json'}
        self.transfer_id = c.post(self.api_full,
                                  data={'amount': 500}, **self.club_header).json()['id']

    def test_create_club_transfer(self):
        response = c.post(self.api_full, data={'amount': 500}, **self.club_header)
        self.assertEqual(response.status_code, 201, msg=f'to withdraw\n{response.content}')
        self.assertEqual(Transfer.objects.get(id=response.json()['id']).club, self.club1, 'Wrong user')
        self.assertEqual(Transfer.objects.get(id=response.json()['id']).recipient, self.club1.admin, 'Wrong user')

    def test_create_transfer_multi(self):
        c.post(self.api_full, data={'amount': 500}, **self.club_header)
        response = c.post(self.api_full, data={'amount': 500}, **self.club_header)
        self.assertEqual(response.status_code, 400, msg=f'not to withdraw\n{response.content}\n '
                                                        f'TC: {Transfer.objects.filter(sender=self.user2).count()}')

    def test_create_transfer_low(self):
        response = c.post(self.api_full, data={'amount': 5}, **self.club_header)
        self.assertEqual(response.status_code, 400, msg=f'low amount of withdraw should not be allowed')

    def test_create_transfer_high(self):
        response = c.post(self.api_full, data={'amount': 50000}, **self.club_header)
        self.assertEqual(response.status_code, 400, msg=f'high amount of deposit should not be allowed')

    def test_update_transfer(self):
        response = c.patch(f'{self.api}{self.transfer_id}/?club=true', data={'amount': 500}, **self.club_header)
        self.assertEqual(response.status_code, 405, msg=f'Not updatable')

    def test_update_transfer_superuser(self):
        response = c.patch(f'{self.api}{self.transfer_id}/', data={'amount': 500}, **self.club_header)
        self.assertEqual(response.status_code, 405, msg=f'Not updatable')
