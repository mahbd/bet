from django.utils import timezone
from rest_framework import serializers

from betting.views import value_from_option
from users.backends import jwt_writer
from users.models import User, Club, Notification
from betting.models import Announcement, Bet, BetScope, Config, Deposit, Match, Withdraw, Transfer, \
    club_validator, bet_scope_validator, user_balance_validator, BET_CHOICES


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = '__all__'


class BetScopeSerializer(serializers.ModelSerializer):
    is_locked = serializers.SerializerMethodField(read_only=True)

    # noinspection PyMethodMayBeStatic
    def get_is_locked(self, bet_scope: BetScope) -> bool:
        return bet_scope.is_locked()

    class Meta:
        model = BetScope
        fields = ('end_time', 'id', 'is_locked', 'match', 'option_1', 'option_1_rate', 'option_2', 'option_2_rate',
                  'option_3', 'option_3_rate', 'option_4', 'option_4_rate', 'question', 'winner', 'start_time',)
        read_only_fields = ('id',)


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
        fields = ('end_time', 'game_name', 'id', 'is_locked', 'is_live', 'start_time', 'title',)
        read_only_fields = ('id',)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class RegisterSerializer(serializers.ModelSerializer):
    is_club_admin = serializers.SerializerMethodField(read_only=True)
    jwt = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'first_name', 'last_name', 'user_club', 'password',
                  'game_editor', 'is_club_admin', 'is_superuser', 'referred_by', 'login_key', 'jwt')
        read_only_fields = ('id', 'game_editor', 'is_club_admin', 'is_superuser')
        extra_kwargs = {'password': {'write_only': True}, 'user_club': {'required': True}}

    # noinspection PyMethodMayBeStatic
    def get_is_club_admin(self, user) -> bool:
        return user.is_club_admin()

    # noinspection PyMethodMayBeStatic
    def get_jwt(self, user) -> str:
        data = {
            'email': user.email,
            'first_name': user.first_name,
            'game_editor': user.game_editor,
            'id': user.id,
            'is_superuser': user.is_superuser,
            'login_key': user.login_key,
            'last_name': user.last_name,
            'phone': user.phone,
            'referred_by': user.referred_by,
            'username': user.username,
        }
        diff = (timezone.now() - user.date_joined).total_seconds()
        if diff > 60:
            return "Not allowed jwt. Please login to get JWT"
        return jwt_writer(**data)

    def create(self, validated_data):
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


class UserSerializer(serializers.ModelSerializer):
    referred_by = serializers.SerializerMethodField(read_only=True)
    is_club_admin = serializers.SerializerMethodField(read_only=True)
    refer_set = serializers.SerializerMethodField(read_only=True)

    # noinspection PyMethodMayBeStatic
    def get_is_club_admin(self, user) -> bool:
        return user.is_club_admin()

    # noinspection PyMethodMayBeStatic
    def get_refer_set(self, user: User):
        return UserListSerializer(user.refer_set.all(), many=True).data

    # noinspection PyMethodMayBeStatic
    def get_referred_by(self, user: User) -> dict:
        return UserListSerializer(user.referred_by).data

    class Meta:
        model = User
        exclude = ('groups', 'user_permissions', 'password')
        read_only_fields = ('id', 'balance', 'game_editor', 'is_club_admin', 'is_superuser', 'is_staff', 'referred_by')
        extra_kwargs = {'user_club': {'required': True}}
        depth = 1


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
