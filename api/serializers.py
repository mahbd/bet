from django.utils import timezone
from rest_framework import serializers

from betting.models import Bet, BetScope, Match, club_validator, \
    user_balance_validator, bet_scope_validator, METHOD_BET, Announcement, Deposit, Withdraw, Transfer
from users.backends import jwt_writer
from users.models import User, Club


class RegisterSerializer(serializers.ModelSerializer):
    is_club_admin = serializers.SerializerMethodField(read_only=True)
    jwt = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'first_name', 'last_name', 'user_club', 'password',
                  'game_editor', 'is_club_admin', 'is_superuser', 'referred_by', 'jwt')
        read_only_fields = ('id', 'game_editor', 'is_club_admin', 'is_superuser')
        extra_kwargs = {'password': {'write_only': True}, 'user_club': {'required': True}}

    # noinspection PyMethodMayBeStatic
    def get_is_club_admin(self, user) -> bool:
        return user.is_club_admin()

    # noinspection PyMethodMayBeStatic
    def get_jwt(self, user) -> str:
        data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone': user.phone,
            'last_name': user.last_name,
            'first_name': user.first_name,
            'game_editor': user.game_editor,
            'is_superuser': user.is_superuser,
            'referred_by': user.referred_by,
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

    def update(self, instance, validated_data):
        user = super().update(instance, validated_data)
        user.set_password(validated_data.get('password'))
        user.save()
        return user


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
        exclude = ('groups', 'user_permissions')
        read_only_fields = ('id', 'balance', 'game_editor', 'is_club_admin', 'is_superuser', 'is_staff', 'referred_by')
        extra_kwargs = {'user_club': {'required': True}, 'password': {'write_only': True}}
        depth = 1

    def update(self, instance, validated_data):
        user = super().update(instance, validated_data)
        if validated_data.get('password'):
            user.set_password(validated_data.get('password'))
            user.save()
        return user


class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = ('id', 'name', 'admin', 'balance')
        read_only_fields = ('id', 'admin')


class BetSerializer(serializers.ModelSerializer):
    match_name = serializers.SerializerMethodField(read_only=True)
    match_start_time = serializers.SerializerMethodField(read_only=True)

    def get_match_name(self, bet: Bet):
        return bet.bet_scope.match.title

    def get_match_start_time(self, bet: Bet):
        return str(bet.bet_scope.match.start_time)

    class Meta:
        model = Bet
        fields = ('id', 'user', 'bet_scope', 'choice', 'amount')
        read_only_fields = ('id', 'user')
        extra_kwargs = {'user': {'required': False}}

    def validate(self, attrs):
        if not self.instance:
            attrs['user'] = self.context['request'].user
        bet_scope: BetScope = attrs.get('bet_scope')
        sender: User = attrs.get('user')
        amount = attrs.get('amount')
        bet_scope_validator(bet_scope)
        user_balance_validator(sender, amount)
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
        fields = (
            'id', 'game_name', 'title', 'is_locked', 'is_live', 'start_time', 'end_time')
        read_only_fields = ('id',)


class BetScopeSerializer(serializers.ModelSerializer):
    is_locked = serializers.SerializerMethodField(read_only=True)

    # noinspection PyMethodMayBeStatic
    def get_is_locked(self, bet_scope: BetScope) -> bool:
        return bet_scope.is_locked()

    class Meta:
        model = BetScope
        fields = ('id', 'match', 'question', 'option_1', 'option_1_rate', 'option_2', 'option_2_rate', 'option_3',
                  'option_3_rate', 'option_4', 'option_4_rate', 'winner', 'start_time', 'end_time', 'is_locked')
        read_only_fields = ('id',)


class DepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = '__all__'
        read_only_fields = ('id', 'user', 'verified')
        extra_kwargs = {'transaction_id': {'required': True}, 'account': {'required': True},
                        'superuser_account': {'required': True}}

    def validate(self, attrs):
        if not self.instance:
            attrs['user'] = self.context['request'].user
        return attrs


class WithdrawSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdraw
        fields = '__all__'
        read_only_fields = ('id', 'user', 'verified')
        extra_kwargs = {'account': {'required': True}}

    def validate(self, attrs):
        if not self.instance:
            attrs['user'] = self.context['request'].user
        user = attrs.get('user')
        amount = attrs.get('amount')
        method = attrs.get('method')
        user_balance_validator(user, amount, method)
        return attrs


class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = '__all__'
        read_only_fields = ('id', 'user', 'verified')

    def validate(self, attrs):
        if not self.instance:
            attrs['user'] = self.context['request'].user
        user = attrs.get('user')
        receiver: User = attrs.get('to')
        amount = attrs.get('amount')
        method = attrs.get('method')
        user_balance_validator(user, amount, method)
        club_validator(user, receiver)
        return attrs


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = '__all__'
