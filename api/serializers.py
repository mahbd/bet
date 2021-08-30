from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from betting.models import Announcement, Bet, BetScope, Config, Deposit, Match, Withdraw, Transfer, \
    club_validator, bet_scope_validator, user_balance_validator, BET_CHOICES
from betting.views import value_from_option, get_last_bet
from users.backends import jwt_writer
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


def sum_filter_bet_set(bet_scope, choice, field='winning'):
    return bet_scope.bet_set.filter(choice=choice).aggregate(Sum(field))[f'{field}__sum'] or 0


def count_filter_bet_set(bet_scope, choice):
    return bet_scope.bet_set.filter(choice=choice).count()


class BetScopeSerializer(serializers.ModelSerializer):
    is_locked = serializers.SerializerMethodField(read_only=True)
    details = serializers.SerializerMethodField(read_only=True)

    def get_details(self, bet_scope: BetScope) -> dict:
        option1_bet = sum_filter_bet_set(bet_scope, BET_CHOICES[0][0], 'amount')
        option2_bet = sum_filter_bet_set(bet_scope, BET_CHOICES[1][0], 'amount')
        option3_bet = sum_filter_bet_set(bet_scope, BET_CHOICES[2][0], 'amount')
        option4_bet = sum_filter_bet_set(bet_scope, BET_CHOICES[3][0], 'amount')

        option1_bet_count = count_filter_bet_set(bet_scope, BET_CHOICES[0][0])
        option2_bet_count = count_filter_bet_set(bet_scope, BET_CHOICES[1][0])
        option3_bet_count = count_filter_bet_set(bet_scope, BET_CHOICES[2][0])
        option4_bet_count = count_filter_bet_set(bet_scope, BET_CHOICES[3][0])

        total_bet = option1_bet + option2_bet + option3_bet + option4_bet
        option1_benefit = total_bet - sum_filter_bet_set(bet_scope, BET_CHOICES[0][0])
        option2_benefit = total_bet - sum_filter_bet_set(bet_scope, BET_CHOICES[1][0])
        option3_benefit = total_bet - sum_filter_bet_set(bet_scope, BET_CHOICES[2][0])
        option4_benefit = total_bet - sum_filter_bet_set(bet_scope, BET_CHOICES[3][0])
        return {
            'option1_bet': option1_bet,
            'option2_bet': option2_bet,
            'option3_bet': option3_bet,
            'option4_bet': option4_bet,
            'option1_bet_count': option1_bet_count,
            'option2_bet_count': option2_bet_count,
            'option3_bet_count': option3_bet_count,
            'option4_bet_count': option4_bet_count,
            'option1_benefit': option1_benefit,
            'option2_benefit': option2_benefit,
            'option3_benefit': option3_benefit,
            'option4_benefit': option4_benefit,
        }

    # noinspection PyMethodMayBeStatic
    def get_is_locked(self, bet_scope: BetScope) -> bool:
        return bet_scope.is_locked()

    class Meta:
        model = BetScope
        fields = ('end_time', 'id', 'is_locked', 'locked', 'hide', 'match', 'option_1', 'option_1_rate', 'option_2',
                  'option_2_rate', 'details',
                  'option_3', 'option_3_rate', 'option_4', 'option_4_rate', 'question', 'winner', 'start_time',)
        read_only_fields = ('id', 'winner')


# noinspection PyMethodMayBeStatic
class BetSerializer(serializers.ModelSerializer):
    match_start_time = serializers.SerializerMethodField(read_only=True)
    match_name = serializers.SerializerMethodField(read_only=True)
    question = serializers.SerializerMethodField(read_only=True)
    your_answer = serializers.SerializerMethodField(read_only=True)

    def get_match_name(self, bet: Bet):
        return bet.bet_scope.match.title

    def get_match_start_time(self, bet: Bet):
        return str(bet.bet_scope.match.start_time)

    def get_question(self, bet: Bet):
        return bet.bet_scope.question

    def get_your_answer(self, bet: Bet):
        return value_from_option(bet.choice, bet.bet_scope)

    class Meta:
        model = Bet
        fields = ('answer', 'amount', 'bet_scope', 'choice', 'id', 'match_start_time', 'match_name', 'question',
                  'return_rate', 'is_winner', 'user', 'your_answer', 'winning', 'created_at')
        read_only_fields = ('id', 'user', 'answer', 'return_rate', 'is_winner')

    def validate(self, attrs):
        if not self.instance:
            attrs['user'] = self.context['request'].user
        amount = attrs.get('amount')
        bet_scope: BetScope = attrs.get('bet_scope')
        user: User = attrs.get('user')
        bet_scope_validator(bet_scope)
        Config().config_validator(user, amount, Bet, 'bet')
        user_balance_validator(user, amount + Config().get_config('min_balance'))
        return attrs


class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = ('admin', 'balance', 'id', 'name',)
        read_only_fields = ('admin', 'id',)


class DepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = '__all__'
        read_only_fields = ('id', 'user', 'user_balance', 'verified')
        extra_kwargs = {
            'account': {'required': True},
            'superuser_account': {'required': True},
            'transaction_id': {'required': True},
        }

    def validate(self, attrs):
        if not self.instance:
            attrs['user'] = self.context['request'].user
        amount = attrs.get('amount')
        user = attrs.get('user')
        Config().config_validator(user, amount, Deposit, 'deposit')
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
        fields = ('end_time', 'game_name', 'id', 'is_locked', 'is_live', 'locked', 'hide', 'start_time', 'title',)
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
        extra_kwargs = {'password': {'write_only': True}, 'user_club': {'required': True}}

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
        read_only_fields = ('id', 'user', 'verified', 'user_balance')

    def validate(self, attrs):
        if not self.instance:
            attrs['user'] = self.context['request'].user
        user = attrs.get('user')
        receiver: User = attrs.get('to')
        amount = attrs.get('amount')
        user_balance_validator(user, amount + Config().get_config('min_balance'))
        club_validator(user, receiver)
        Config().config_validator(user, amount, Transfer, 'transfer')
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
        read_only_fields = ('id', 'user', 'verified', 'user_balance')
        extra_kwargs = {'account': {'required': True}}

    def validate(self, attrs):
        if not self.instance:
            attrs['user'] = self.context['request'].user
        user = attrs.get('user')
        amount = attrs.get('amount')
        method = attrs.get('method')
        user_balance_validator(user, amount + Config().get_config('min_balance'), method)
        Config().config_validator(user, amount, Withdraw, 'withdraw')
        return attrs
