import string
from random import choice, randint, random

import requests
from django.utils.crypto import get_random_string

from api.serializers import jwt_from_user
from betting.choices import DEPOSIT_CHOICES, A_DEPOSIT_CANCEL, A_DEPOSIT_ACCEPT, A_WITHDRAW_ACCEPT, A_WITHDRAW_CANCEL, A_TRANSFER_ACCEPT, A_TRANSFER_CANCEL, GAME_CHOICES, MATCH_STATUS_CHOICES
from betting.models import Match
from users.models import Club, User


def add_user(how_many, base_url='http://127.0.0.1:8000'):
    clubs = [club.id for club in Club.objects.all()]
    for i in range(how_many):
        print('Executing', i)
        users = [user.username for user in User.objects.all()]
        data = {
            'username': get_random_string(5),
            'email': get_random_string(5) + '@gmail.com',
            'phone': str(randint(999999, 9999199)),
            'user_club': choice(clubs),
            'password': get_random_string(10),
            'referer_username': choice(users),
            'first_name': get_random_string(5),
            'last_name': get_random_string(5),
        }
        response = requests.post(base_url + '/api/user/', data=data)
        user_id = response.json()['id']
        User.objects.filter(pk=user_id).update(balance=randint(1, 5000))
        print(response.status_code)


def add_club(how_many, base_url='http://127.0.0.1:8000'):
    jwt = jwt_from_user(User.objects.filter(is_superuser=True).first())
    for i in range(how_many):
        print('Executing', i)
        users = [user.id for user in User.objects.all() if not user.is_club_admin()]
        if len(users) == 0:
            print("No non admin user left")
            return
        data = {
            'name': get_random_string(5),
            'username': get_random_string(5),
            'password': get_random_string(5),
            'admin': choice(users),
        }
        response = requests.post(base_url + '/api/club/', data=data, headers={'x-auth-token': jwt})
        club_id = response.json()['id']
        Club.objects.filter(pk=club_id).update(balance=randint(10, 5000))
        print(response.status_code)


def add_announcement(how_many, base_url='http://127.0.0.1:8000'):
    jwt = jwt_from_user(User.objects.filter(is_superuser=True).first())
    for i in range(how_many):
        print('Executing', i)
        data = {'text': get_random_string(30)}
        response = requests.post(base_url + '/api/announcement/', data=data, headers={'x-auth-token': jwt})
        print(response.status_code)


def add_withdraw(how_many, base_url='http://127.0.0.1:8000'):
    super_jwt = jwt_from_user(User.objects.filter(is_superuser=True).first())
    status = [True, True, True, False, None]
    for i in range(how_many):
        print('Executing', i)
        amount = randint(500, 1000)
        acceptable_users = User.objects.filter(balance__gt=amount + 50).count()
        if not acceptable_users:
            print('No user has enough balance')
        choice_index = choice(range(acceptable_users))
        jwt = jwt_from_user(User.objects.filter(balance__gt=amount + 50)[choice_index])
        data = {
            'amount': amount,
            'method': choice(DEPOSIT_CHOICES)[0],
            'user_account': '01' + str(randint(100_000_000, 999_999_999)),
        }
        response = requests.post(base_url + '/api/withdraw/', data=data, headers={'x-auth-token': jwt})
        print(response.json())
        withdraw_id = response.json()['id']
        choosed = choice(status)
        if choosed:
            response = requests.post(base_url + '/api/actions/',
                                     json={'action_code': A_WITHDRAW_ACCEPT, 'withdraw_id': withdraw_id},
                                     headers={'x-auth-token': super_jwt})
            print(response.status_code)
        elif choosed == False:
            response = requests.post(base_url + '/api/actions/',
                                     json={'action_code': A_WITHDRAW_CANCEL, 'withdraw_id': withdraw_id},
                                     headers={'x-auth-token': super_jwt})
            print(response.status_code)


def add_transfer(how_many, base_url='http://127.0.0.1:8000'):
    super_jwt = jwt_from_user(User.objects.filter(is_superuser=True).first())
    status = [True, True, True, False, None]
    for i in range(how_many):
        print('Executing', i)
        amount = randint(10, 100)
        acceptable_users = User.objects.filter(balance__gt=amount + 50, user_club__isnull=False,
                                               user_club__admin__isnull=False)
        if acceptable_users.count() == 0:
            print('No user has enough balance')
            break
        choice_index = choice(range(acceptable_users.count()))
        sender = acceptable_users[choice_index]
        jwt = jwt_from_user(sender)
        recipient = sender.user_club.admin.id
        data = {
            'amount': amount,
            'recipient': recipient,
        }
        response = requests.post(base_url + '/api/transfer/', json=data, headers={'x-auth-token': jwt})
        print(response.json(), data)
        try:
            withdraw_id = response.json()['id']
        except Exception as e:
            print(e)
            break
        choosed = choice(status)
        if choosed:
            response = requests.post(base_url + '/api/actions/',
                                     json={'action_code': A_TRANSFER_ACCEPT, 'transfer_id': withdraw_id},
                                     headers={'x-auth-token': super_jwt})
            print(response.status_code)
        elif choosed == False:
            response = requests.post(base_url + '/api/actions/',
                                     json={'action_code': A_TRANSFER_CANCEL, 'transfer_id': withdraw_id},
                                     headers={'x-auth-token': super_jwt})
            print(response.status_code)


def add_deposit(how_many, base_url='http://127.0.0.1:8000'):
    super_jwt = jwt_from_user(User.objects.filter(is_superuser=True).first())
    status = [True, True, True, False, None]
    users = list(User.objects.all())
    for i in range(how_many):
        print('Executing', i)
        jwt = jwt_from_user(choice(users))
        data = {
            'amount': randint(100, 1000),
            'method': choice(DEPOSIT_CHOICES)[0],
            'site_account': '017454512121',
            'user_account': '01' + str(randint(100_000_000, 999_999_999)),
            'reference': get_random_string(12, string.ascii_uppercase + string.digits)
        }
        response = requests.post(base_url + '/api/deposit/', data=data, headers={'x-auth-token': jwt})
        deposit_id = response.json()['id']
        choosed = choice(status)
        if choosed:
            response = requests.post(base_url + '/api/actions/',
                                     json={'action_code': A_DEPOSIT_ACCEPT, 'deposit_id': deposit_id},
                                     headers={'x-auth-token': super_jwt})
            print(response.status_code)
        elif choosed == False:
            response = requests.post(base_url + '/api/actions/',
                                     json={'action_code': A_DEPOSIT_CANCEL, 'deposit_id': deposit_id},
                                     headers={'x-auth-token': super_jwt})
            print(response.status_code)


def add_match(how_many, base_url='http://127.0.0.1:8000'):
    super_jwt = jwt_from_user(User.objects.filter(is_superuser=True).first())
    for i in range(how_many):
        data = {
            'game_name': choice([game[0] for game in GAME_CHOICES]),
            'score': randint(1, 100),
            'status': choice([s[0] for s in MATCH_STATUS_CHOICES]),
            'team_a_name': get_random_string(3, string.ascii_uppercase),
            'team_b_name': get_random_string(3, string.ascii_uppercase),
            'team_a_color': get_random_string(3, string.ascii_uppercase),
            'team_b_color': get_random_string(3, string.ascii_uppercase),
        }
        response = requests.post(base_url + '/api/match/', data=data, headers={'x-auth-token': super_jwt})
        print(response.status_code)


def add_question(how_many, base_url='http://127.0.0.1:8000'):
    super_jwt = jwt_from_user(User.objects.filter(is_superuser=True).first())
    matches = [match.id for match in Match.objects.all()]
    for i in range(how_many):
        options = [{
            'option': get_random_string(3, string.ascii_uppercase),
            'rate': random() + 0.5,
            'hidden': choice([False, False, False, False, True]),
            'limit': randint(100, 1000_000_00)

        } for _ in range(randint(2, 4))]
        data = {
            'match': choice(matches),
            'question': get_random_string(randint(10, 20), string.ascii_letters) + '?',
            'status': choice([s[0] for s in MATCH_STATUS_CHOICES]),
            'options': options,
        }
        response = requests.post(base_url + '/api/bet-question/', json=data, headers={'x-auth-token': super_jwt})
        print(response.status_code)
