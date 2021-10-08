from random import choice, randint

import requests
from django.utils.crypto import get_random_string

from api.serializers import jwt_from_user
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
        print(response.status_code)


def add_announcement(how_many, base_url='http://127.0.0.1:8000'):
    jwt = jwt_from_user(User.objects.filter(is_superuser=True).first())
    for i in range(how_many):
        print('Executing', i)
        data = {'text': get_random_string(30)}
        response = requests.post(base_url + '/api/announcement/', data=data, headers={'x-auth-token': jwt})
        print(response.status_code)



