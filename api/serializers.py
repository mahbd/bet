from rest_framework import serializers

from betting.models import Bet, BetScope, Match, Transaction, TYPE_WITHDRAW, club_validator, \
    user_balance_validator, bet_scope_validator
from users.backends import jwt_writer
from users.models import User, Club


def bet_or_trans_validator(attrs):
    sender: User = attrs.get('user')
    receiver: User = attrs.get('to')
    t_type = attrs.get('type', TYPE_WITHDRAW)
    amount = attrs.get('amount')
    method = attrs.get('method')
    user_balance_validator(sender, amount, t_type)
    club_validator(sender, t_type, method, receiver)
    return attrs


class RegisterSerializer(serializers.ModelSerializer):
    is_club_admin = serializers.SerializerMethodField(default=False, read_only=True)
    jwt = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'balance', 'first_name', 'last_name', 'user_club', 'password',
                  'game_editor', 'is_club_admin', 'is_superuser', 'referred_by', 'jwt')
        read_only_fields = ('id', 'balance', 'game_editor', 'is_club_admin', 'is_superuser')
        extra_kwargs = {'password': {'write_only': True}, 'user_club': {'required': True}}

    # noinspection PyMethodMayBeStatic
    def get_is_club_admin(self, user):
        return user.is_club_admin()

    # noinspection PyMethodMayBeStatic
    def get_jwt(self, user):
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


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name')
        read_only_fields = ('id',)


class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = ('id', 'game_name', 'admin')
        read_only_fields = ('id',)


class BetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bet
        fields = ('id', 'user', 'bet_scope', 'choice', 'amount')
        read_only_fields = ('id',)
        extra_kwargs = {'user': {'required': False}}

    def validate(self, attrs):
        if not self.instance:
            attrs['user'] = self.context['request'].user
        bet_scope: BetScope = attrs.get('bet_scope')
        sender: User = attrs.get('user')
        t_type = attrs.get('type', TYPE_WITHDRAW)
        amount = attrs.get('amount')
        bet_scope_validator(bet_scope)
        user_balance_validator(sender, amount, t_type)
        return attrs


class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = (
            'id', 'game_name', 'start_time', 'end_time')
        read_only_fields = ('id',)


class BetScopeSerializer(serializers.ModelSerializer):
    is_locked = serializers.SerializerMethodField(default=False, read_only=True)

    # noinspection PyMethodMayBeStatic
    def get_is_locked(self, bet_scope: BetScope):
        return bet_scope.is_locked()

    class Meta:
        fields = ('id', 'match', 'question', 'option_1', 'option_1_rate', 'option_2', 'option_2_rate', 'option_3',
                  'option_3_rate', 'option_4', 'option_4_rate', 'winner', 'start_time', 'end_time', 'is_locked')
        read_only_fields = ('id',)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('id', 'user', 'type', 'method', 'to', 'amount', 'transaction_id', 'account')
        read_only_fields = ('id', 'user')

    def validate(self, attrs):
        if not self.instance:
            attrs['user'] = self.context['request'].user
        return bet_or_trans_validator(attrs)
