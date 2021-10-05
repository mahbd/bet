from django.core.validators import MaxValueValidator
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
api_view

from api.validators import MinMaxLimitValidator, CountLimitValidator, UniqueMultiQuerysetValidator
from betting.models import Announcement, Bet, BetQuestion, Config, Deposit, Match, Withdraw, Transfer, \
    club_validator, bet_scope_validator, user_balance_validator, QuestionOption
from betting.views import get_last_bet
from users.backends import jwt_writer, get_current_club
from users.models import User, Club, Notification


def jwt_from_user(user: User):
    if user.referred_by:
        referred_by = user.referred_by.username
    else:
        referred_by = ""
    data = {
        'email': user.email,
        'first_name': user.first_name,
        'game_editor': user.game_editor,
        'id': user.id,
        'is_superuser': user.is_superuser,
        'login_key': user.login_key,
        'last_name': user.last_name,
        'phone': user.phone,
        'referred_by': referred_by,
        'username': user.username,
    }
    return jwt_writer(**data)


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = '__all__'


def sum_filter_bet_set(bet_question, choice, field='win_amount'):
    return bet_question.bet_set.filter(choice=choice).aggregate(Sum(field))[f'{field}__sum'] or 0


def count_filter_bet_set(bet_question, choice):
    return bet_question.bet_set.filter(choice=choice).count()


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = '__all__'


# noinspection PyMethodMayBeStatic
class BetQuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True)
    is_locked = serializers.SerializerMethodField(read_only=True)
    details = serializers.SerializerMethodField(read_only=True)
    match_name = serializers.SerializerMethodField(read_only=True)
    match_start_time = serializers.SerializerMethodField(read_only=True)

    def get_match_name(self, bet_question: BetQuestion):
        return bet_question.match.title

    def get_match_start_time(self, bet_question: BetQuestion):
        return str(bet_question.match.start_time)

    def get_details(self, bet_question: BetQuestion) -> dict:
        details = {}
        total_bet = bet_question.bet_set.all().aggregate(Sum('amount'))[f'amount__sum'] or 0
        for option in bet_question.options.all():
            details[f'{option.option}_bet'] = sum_filter_bet_set(bet_question, option, 'amount')
            details[f'{option.option}_bet_count'] = count_filter_bet_set(bet_question, option)
            details[f'{option.option}_benefit'] = total_bet - sum_filter_bet_set(bet_question, option)
        return details

    def get_is_locked(self, bet_scope: BetQuestion) -> bool:
        return bet_scope.is_locked()

    def create(self, validated_data):
        options = validated_data.pop('options', [])
        instance = BetQuestion.objects.create(**validated_data)
        for task_data in options:
            task = QuestionOption.objects.create(**task_data)
            instance.options.add(task)
        return instance

    def update(self, instance, validated_data):
        if hasattr(validated_data, 'options'):
            validated_data.pop('options')
        return super().update(instance, validated_data)

    class Meta:
        model = BetQuestion
        fields = ('end_time', 'id', 'is_locked', 'locked', 'hidden', 'match',
                  'details', 'match_name', 'match_start_time',
                  'options', 'question', 'winner',)
        read_only_fields = ('id',)


# noinspection PyMethodMayBeStatic
class BetSerializer(serializers.ModelSerializer):
    answer = serializers.SerializerMethodField(read_only=True)
    match_start_time = serializers.SerializerMethodField(read_only=True)
    match_name = serializers.SerializerMethodField(read_only=True)
    question = serializers.SerializerMethodField(read_only=True)
    your_answer = serializers.SerializerMethodField(read_only=True)
    user_details = serializers.SerializerMethodField(read_only=True)

    def get_answer(self, bet: Bet) -> str:
        return bet.bet_question.winner and bet.bet_question.winner.option

    def get_user_details(self, bet: Bet) -> dict:
        return UserListSerializer(bet.user).data

    def get_match_name(self, bet: Bet) -> str:
        return bet.bet_question.match.title

    def get_match_start_time(self, bet: Bet) -> str:
        return str(bet.bet_question.match.start_time)

    def get_question(self, bet: Bet) -> str:
        return bet.bet_question.question

    def get_your_answer(self, bet: Bet):
        return bet.choice.option

    class Meta:
        model = Bet
        fields = ('answer', 'amount', 'bet_question', 'choice', 'id', 'match_start_time', 'match_name', 'question',
                  'win_rate', 'is_winner', 'user', 'your_answer', 'win_amount', 'status',
                  'created_at', 'user_details', 'user_balance')
        read_only_fields = ('id', 'user', 'win_rate', 'is_winner')

    def validate(self, attrs):
        if not self.instance:
            attrs['user'] = self.context['request'].user
        amount = attrs.get('amount')
        bet_scope: BetQuestion = attrs.get('bet_question')
        user: User = attrs.get('user')
        bet_scope_validator(bet_scope)
        Config().config_validator(user, amount, Bet, 'bet')
        user_balance_validator(user, amount + Config().get_config('min_balance'))
        return attrs


class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = ('admin', 'balance', 'id', 'name', 'username', 'password', 'club_commission')
        read_only_fields = ('admin', 'id',)
        extra_kwargs = {
            'password': {'write_only': True},
            'username': {'validators': [UniqueMultiQuerysetValidator(User.objects.all(), Club.objects.all())]}
        }


class DepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = ('id', 'amount', 'balance', 'club', 'created_at', 'deposit_source', 'method', 'site_account',
                  'transaction_id', 'user', 'user_account', 'status')
        read_only_fields = ('id', 'balance', 'user', 'deposit_source', 'status')
        extra_kwargs = {
            'user_account': {'required': True},
            'site_account': {'required': True},
            'transaction_id': {'required': True},
            'amount': {'validators': [MinMaxLimitValidator('deposit')]},
        }

    def validate(self, attrs):
        attrs['user'] = self.context['request'].user
        CountLimitValidator('deposit', Deposit).__call__(attrs.get('user'))
        return attrs


class MatchSerializer(serializers.ModelSerializer):
    is_live = serializers.SerializerMethodField(read_only=True)
    is_locked = serializers.SerializerMethodField(read_only=True)

    # noinspection PyMethodMayBeStatic
    def get_is_live(self, match: Match) -> bool:
        return match.is_live()

    # noinspection PyMethodMayBeStatic
    def get_is_locked(self, match: Match) -> bool:
        return match.is_locked()

    class Meta:
        model = Match
        fields = ('end_time', 'game_name', 'id', 'is_locked', 'is_live', 'locked', 'hidden', 'start_time', 'title',)
        read_only_fields = ('id',)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class RegisterSerializer(serializers.ModelSerializer):
    is_club_admin = serializers.SerializerMethodField(read_only=True)
    jwt = serializers.SerializerMethodField(read_only=True)
    referer_username = serializers.CharField(default='no_data', required=False, trim_whitespace=True)
    referred_by = serializers.SerializerMethodField(read_only=True)

    def get_referred_by(self, user: User):
        return UserListSerializer(user).data

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'first_name', 'last_name', 'user_club', 'password',
                  'game_editor', 'is_club_admin', 'is_superuser', 'referred_by', 'login_key', 'jwt',
                  'referer_username')
        read_only_fields = ('id', 'game_editor', 'is_club_admin', 'is_superuser',)
        extra_kwargs = {
            'password': {'write_only': True},
            'user_club': {'required': True},
            'username': {'validators': [UniqueMultiQuerysetValidator(User.objects.all(), Club.objects.all())]}
        }

    # noinspection PyMethodMayBeStatic
    def get_is_club_admin(self, user) -> bool:
        return user.is_club_admin()

    # noinspection PyMethodMayBeStatic
    def get_jwt(self, user) -> str:
        jwt = jwt_from_user(user)
        diff = (timezone.now() - user.date_joined).total_seconds()
        if diff > 60:
            return "Not allowed jwt. Please login to get JWT"
        return jwt

    def validate(self, attrs):
        if not self.instance:
            u = attrs.get('referer_username', None)
            user = User.objects.filter(username=u)
            if user:
                attrs['referred_by'] = user[0]
        return attrs

    def create(self, validated_data):
        validated_data.pop('referer_username')
        user = super().create(validated_data)
        user.set_password(validated_data.get('password'))
        user.save()
        return user


class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = '__all__'
        read_only_fields = ('id', 'sender', 'status', 'balance')
        extra_kwargs = {
            'amount': {'validators': [MinMaxLimitValidator('withdraw')]},
            'recipient': {'required': True}
        }

    def validate(self, attrs):
        recipient: User = attrs.get('recipient')
        user, amount = self.context['request'].user, attrs.get('amount')
        attrs['sender'] = user
        MaxValueValidator(user.balance - Config().get_config('min_balance'), 'Not enough balance').__call__(amount)
        CountLimitValidator('transfer', Transfer, field_check='sender').__call__(attrs.get('sender'))
        club_validator(user, recipient)
        return attrs


class TransferClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = '__all__'
        read_only_fields = ('id', 'sender', 'status', 'balance')
        extra_kwargs = {
            'amount': {'validators': [MinMaxLimitValidator('withdraw')]}
        }

    def validate(self, attrs):
        club, amount = get_current_club(self.context['request']), attrs.get('amount')
        if club is None:
            raise ValidationError(f"Bad data sent or doesn't have enough permission")
        attrs['club'] = club
        attrs['recipient'] = club.admin
        MaxValueValidator(club.balance - Config().get_config('min_balance'), 'Not enough balance').__call__(amount)
        CountLimitValidator('transfer', Transfer, field_check='club').__call__(attrs.get('club'))
        return attrs


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name')
        read_only_fields = ('id',)


# noinspection PyMethodMayBeStatic
class UserListSerializerClub(serializers.ModelSerializer):
    join_date = serializers.SerializerMethodField(read_only=True)
    last_bet = serializers.SerializerMethodField(read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    total_bet = serializers.SerializerMethodField(read_only=True)
    total_commission = serializers.SerializerMethodField(read_only=True)

    def get_join_date(self, user):
        return user.userclubinfo.date_joined

    def get_last_bet(self, user):
        return get_last_bet(user) and get_last_bet(user).created_at

    def get_full_name(self, user):
        return user.get_full_name()

    def get_total_bet(self, user):
        return user.userclubinfo.total_bet

    def get_total_commission(self, user):
        return user.userclubinfo.total_commission

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'join_date', 'last_bet',
                  'full_name', 'total_bet', 'total_commission')
        read_only_fields = ('id',)


class UserSerializer(serializers.ModelSerializer):
    referred_by = serializers.SerializerMethodField(read_only=True)
    is_club_admin = serializers.SerializerMethodField(read_only=True)
    refer_set = serializers.SerializerMethodField(read_only=True)
    club_detail = serializers.SerializerMethodField(read_only=True)
    jwt = serializers.SerializerMethodField(read_only=True)

    # noinspection PyMethodMayBeStatic
    def get_is_club_admin(self, user) -> bool:
        return user.is_club_admin()

    # noinspection PyMethodMayBeStatic
    def get_refer_set(self, user: User):
        return UserListSerializer(user.refer_set.all(), many=True).data

    # noinspection PyMethodMayBeStatic
    def get_referred_by(self, user: User) -> dict:
        return UserListSerializer(user.referred_by).data

    def get_jwt(self, user) -> str:
        jwt = jwt_from_user(user)
        return jwt

    def get_club_detail(self, user: User) -> dict:
        return ClubSerializer(user.user_club).data

    class Meta:
        model = User
        exclude = ('groups', 'user_permissions', 'password')
        read_only_fields = ('id', 'balance', 'game_editor', 'is_club_admin', 'is_superuser', 'is_staff', 'referred_by')


class WithdrawSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdraw
        fields = '__all__'
        read_only_fields = ('id', 'user', 'status', 'user_balance')
        extra_kwargs = {
            'account': {'required': True},
            'amount': {'validators': [MinMaxLimitValidator('withdraw')]}
        }

    def validate(self, attrs):
        attrs['user'] = self.context['request'].user
        user, amount = attrs.get('user'), attrs.get('amount')
        MaxValueValidator(user.balance - Config().get_config('min_balance'), 'Not enough balance').__call__(amount)
        CountLimitValidator('withdraw', Withdraw).__call__(attrs.get('user'))
        return attrs
