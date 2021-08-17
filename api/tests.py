import random
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from django.utils.crypto import get_random_string

from betting.models import Match, GAME_CHOICES, BetScope
from users.models import User


def create_running_match_auto():
    match = Match()
    match.game_name = random.choice(GAME_CHOICES)[0]
    match.title = get_random_string(length=random.randint(1, 50))
    match.end_time = timezone.now() + timedelta(days=random.randint(1, 10))
    match.save()
    return match


def create_running_bet_scope_auto():
    match = create_running_match_auto()
    scope = BetScope()
    scope.match = match
    scope.question = get_random_string(length=random.randint(1, 50)) + '?'
    scope.option_1 = get_random_string(length=random.randint(1, 25))
    scope.option_2 = get_random_string(length=random.randint(1, 25))
    scope.option_1_rate = random.random() * 10
    scope.option_2_rate = random.random() * 10
    scope.save()
    return scope


def create_locked_bet_scope_auto():
    scope = create_running_bet_scope_auto()
    scope.locked = True
    scope.save()
    return scope


def create_user_auto():
    user = User()
    return user


class BetTest(TestCase):
    def setUp(self) -> None:
        self.scope1 = create_running_bet_scope_auto()
        self.scope2 = create_locked_bet_scope_auto()
        self.user = create_user_auto()
