from django.core.validators import MaxValueValidator
from django.db.models import Sum
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.validators import MinMaxLimitValidator, CountLimitValidator, UniqueMultiQuerysetValidator, \
    BetQuestionValidator, QuestionOptionValidator, TransferUserValidator
from betting.models import Announcement, Bet, BetQuestion, Deposit, Match, Withdraw, Transfer, \
    QuestionOption, DepositMethod, ConfigModel
from betting.views import get_last_bet, get_config_from_model
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
    details = serializers.SerializerMethodField(read_only=True)

    def get_details(self, option: QuestionOption) -> dict:
        details = {
            'bet_count': option.bet_set.all().count(),
            'bet': option.bet_set.all().aggregate(Sum('amount'))[f'amount__sum'] or 0,
            'to_return': option.bet_set.all().aggregate(Sum('win_amount'))[f'win_amount__sum'] or 0,
        }
        return details

    class Meta:
        model = QuestionOption
        fields = ['details', 'option', 'rate', 'hidden', 'limit', 'created_at']


# noinspection PyMethodMayBeStatic
class BetQuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True)
    match_name = serializers.SerializerMethodField(read_only=True)
    match_start_time = serializers.SerializerMethodField(read_only=True)

    def get_match_name(self, bet_question: BetQuestion):
        return bet_question.match.__str__()

    def get_match_start_time(self, bet_question: BetQuestion):
        return str(bet_question.match.start_time)

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
        fields = ('id', 'match',
                  'match_name', 'match_start_time',
                  'options', 'question', 'status', 'winner',)


# noinspection PyMethodMayBeStatic
class BetSerializer(serializers.ModelSerializer):
    answer = serializers.SerializerMethodField(read_only=True)
    match_start_time = serializers.SerializerMethodField(read_only=True)
    match_name = serializers.SerializerMethodField(read_only=True)
    question = serializers.SerializerMethodField(read_only=True)
    your_answer = serializers.SerializerMethodField(read_only=True)
    user_details = serializers.SerializerMethodField(read_only=True)
    useless = serializers.SerializerMethodField(read_only=True)

    def get_answer(self, bet: Bet) -> str:
        return bet.bet_question.winner and bet.bet_question.winner.option

    def get_user_details(self, bet: Bet) -> dict:
        return UserListSerializer(bet.user).data

    def get_match_name(self, bet: Bet) -> str:
        return bet.bet_question.match.__str__()

    def get_match_start_time(self, bet: Bet) -> str:
        return str(bet.bet_question.match.start_time)

    def get_question(self, bet: Bet) -> str:
        return bet.bet_question.question

    def get_your_answer(self, bet: Bet):
        return bet.choice.option

    def get_useless(self, bet: Bet):
        return bet.win_amount if bet.is_winner else 0

    class Meta:
        model = Bet
        fields = ('answer', 'amount', 'bet_question', 'choice', 'id', 'match_start_time', 'match_name', 'question',
                  'win_rate', 'is_winner', 'user', 'your_answer', 'win_amount', 'status',
                  'created_at', 'user_details', 'user_balance', 'useless',)
        read_only_fields = ('id', 'user', 'win_rate', 'is_winner')
        extra_kwargs = {
            'amount': {'validators': [MinMaxLimitValidator('bet')]},
            'bet_question': {'validators': [BetQuestionValidator()]},
            'choice': {'validators': [QuestionOptionValidator(Bet)]},
        }

    def validate(self, attrs):
        attrs['user'] = self.context['request'].user
        amount = attrs.get('amount')
        user: User = attrs.get('user')
        MaxValueValidator(user.balance - float(get_config_from_model('min_balance')), 'Not enough balance').__call__(
            amount)
        CountLimitValidator('withdraw', Withdraw).__call__(attrs.get('user'))
        return attrs


# noinspection PyMethodMayBeStatic
class ClubSerializer(serializers.ModelSerializer):
    total_user = serializers.SerializerMethodField(read_only=True)
    total_user_balance = serializers.SerializerMethodField(read_only=True)

    def get_total_user(self, club: Club) -> int:
        return club.user_set.all().count()

    def get_total_user_balance(self, club: Club):
        return club.user_set.all().aggregate(Sum('balance'))['balance__sum'] or 0

    class Meta:
        model = Club
        fields = ('admin', 'balance', 'club_commission', 'id', 'name', 'password', 'username',
                  'total_user', 'total_user_balance')
        read_only_fields = ('admin', 'id',)
        extra_kwargs = {
            'password': {'write_only': True},
            'username': {'validators': [UniqueMultiQuerysetValidator(User.objects.all(), Club.objects.all())]}
        }


class ConfigModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigModel
        fields = '__all__'


class DepositMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepositMethod
        fields = '__all__'


class DepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = ('id', 'amount', 'balance', 'club', 'created_at', 'deposit_source', 'method', 'site_account',
                  'reference', 'user', 'user_account', 'status')
        read_only_fields = ('id', 'balance', 'user', 'deposit_source', 'status')
        extra_kwargs = {
            'user_account': {'required': True},
            'site_account': {'required': True},
            'reference': {'required': True},
            'amount': {'validators': [MinMaxLimitValidator('deposit')]},
        }

    def validate(self, attrs):
        attrs['user'] = self.context['request'].user
        if get_config_from_model('disable_deposit') != '0':
            raise ValidationError('Money transfer is temporary disabled.')
        CountLimitValidator('deposit', Deposit).__call__(attrs.get('user'))
        return attrs


class MatchSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField(read_only=True)

    def get_questions(self, match: Match) -> list:
        return []

    class Meta:
        model = Match
        fields = ('created_at', 'game_name', 'id', 'questions', 'match_type', 'score', 'status', 'start_time',
                  'team_a_name', 'team_b_name', 'team_a_color', 'team_b_color')
        read_only_fields = ('id',)


class MatchDetailsSerializer(MatchSerializer):
    def get_questions(self, match: Match) -> list:
        question_list = match.betquestion_set.all()
        return BetQuestionSerializer(question_list, many=True).data

    class Meta:
        model = Match
        fields = ('created_at', 'game_name', 'id', 'questions', 'score', 'status', 'start_time',
                  'team_a_name', 'team_b_name', 'team_a_color', 'team_b_color')
        read_only_fields = ('id',)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class TransferSerializer(serializers.ModelSerializer):
    account_type = serializers.SerializerMethodField(read_only=True)

    def get_account_type(self, *args, **kwargs):
        user = self.context['request'].user
        if user and user.is_club_admin():
            return 'club_admin'
        return 'user'

    class Meta:
        model = Transfer
        fields = ('account_type', 'amount', 'balance', 'club', 'created_at', 'description',
                  'id', 'recipient', 'sender', 'status')
        read_only_fields = ('sender', 'status', 'balance')
        extra_kwargs = {
            'amount': {'validators': [MinMaxLimitValidator('transfer')]},
            'recipient': {'required': True}
        }

    def validate(self, attrs):
        user, amount = self.context['request'].user, attrs.get('amount')
        attrs['sender'] = user
        if get_config_from_model('disable_user_transfer') != '0':
            raise ValidationError('Money transfer is temporary disabled.')
        TransferUserValidator(user).__call__(attrs.get('recipient'))
        MaxValueValidator(user.balance - float(get_config_from_model('min_balance')), 'Not enough balance').__call__(
            amount)
        CountLimitValidator('transfer', Transfer, field_check='sender').__call__(attrs.get('sender'))
        return attrs


class TransferClubSerializer(serializers.ModelSerializer):
    account_type = serializers.CharField(max_length=255, read_only=True, default='club')

    class Meta:
        model = Transfer
        fields = '__all__'
        read_only_fields = ('id', 'sender', 'status', 'balance')
        extra_kwargs = {
            'amount': {'validators': [MinMaxLimitValidator('transfer')]}
        }

    def validate(self, attrs):
        club, amount = get_current_club(self.context['request']), attrs.get('amount')
        if club is None:
            raise ValidationError(f"Bad data sent or doesn't have enough permission")
        attrs['club'] = club
        attrs['recipient'] = club.admin
        if get_config_from_model('disable_club_transfer') != '0':
            raise ValidationError('Money transfer is temporary disabled.')
        MaxValueValidator(club.balance - float(get_config_from_model('min_balance')), 'Not enough balance').__call__(
            amount)
        CountLimitValidator('transfer', Transfer, field_check='club').__call__(attrs.get('club'))
        return attrs


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'username', 'user_club',)


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
        fields = ('id', 'full_name', 'join_date', 'last_bet',
                  'total_bet', 'total_commission', 'username',)


# noinspection PyMethodMayBeStatic
class UserDetailsSerializer(serializers.ModelSerializer):
    club_detail = serializers.SerializerMethodField(read_only=True)
    is_club_admin = serializers.SerializerMethodField(read_only=True)
    jwt = serializers.SerializerMethodField(read_only=True)
    referred_by = serializers.SerializerMethodField(read_only=True)
    refer_set = serializers.SerializerMethodField(read_only=True)
    referer_username = serializers.CharField(default='no_data', required=False, trim_whitespace=True)

    def get_is_club_admin(self, user) -> bool:
        return user.is_club_admin()

    def get_refer_set(self, user: User):
        return UserListSerializer(user.refer_set.all(), many=True).data

    def get_referred_by(self, user: User) -> dict:
        return UserListSerializer(user.referred_by).data

    def get_jwt(self, user) -> str:
        jwt = jwt_from_user(user)
        return jwt

    def get_club_detail(self, user: User) -> dict:
        return ClubSerializer(user.user_club).data

    def create(self, validated_data: dict):
        password = validated_data.pop('password', None)
        referrer = validated_data.pop('referer_username', None)
        user = User.objects.filter(username=referrer)
        if user:
            validated_data['referred_by'] = user[0]
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        validated_data.pop('referer_username', None)
        password = validated_data.get('password', None)
        if password:
            instance.set_password(password)
            instance.save()
            return instance
        else:
            return super().update(instance, validated_data)

    class Meta:
        model = User
        exclude = ('groups', 'user_permissions')
        read_only_fields = ('id', 'balance', 'game_editor', 'is_superuser', 'is_staff', 'referred_by')
        extra_kwargs = {
            'password': {'write_only': True},
            'user_club': {'required': True},
            'username': {'validators': [UniqueMultiQuerysetValidator(User.objects.all(), Club.objects.all())]},
        }


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
        if get_config_from_model('disable_withdraw') != '0':
            raise ValidationError('Money withdraw is temporary disabled.')
        MaxValueValidator(user.balance - float(get_config_from_model('min_balance')), 'Not enough balance').__call__(
            amount)
        CountLimitValidator('withdraw', Withdraw).__call__(attrs.get('user'))
        return attrs
