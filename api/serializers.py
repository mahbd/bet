from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from betting.models import Bet, Game, Transaction, TYPE_WITHDRAW, METHOD_TRANSFER
from users.models import User, Club


def user_balance_validator(data):
    user: User = data.get('user')
    amount = data.get('amount')
    t_type = data.get('type', TYPE_WITHDRAW)
    if t_type == TYPE_WITHDRAW:
        if user.balance < amount:
            raise ValidationError('User does not have enough balance.')


def club_validator(data):
    sender: User = data.get('user')
    receiver: User = data.get('to')
    data.get('amount')
    t_type = data.get('type')
    method = data.get('method')
    if t_type == TYPE_WITHDRAW and method == METHOD_TRANSFER:
        if sender.user_club != receiver.user_club:
            raise ValidationError("Transaction outside club is not allowed")
        try:
            sender_admin = bool(sender.club)
        except Club.DoesNotExist:
            sender_admin = False
        try:
            receiver_admin = bool(receiver.club)
        except Club.DoesNotExist:
            receiver_admin = False
        if not sender_admin and not receiver_admin:
            raise ValidationError("Transaction can not be done between regular users")
        if not receiver:
            raise ValidationError("Recipients is not selected")


def game_time_validator(data):
    game: Game = data.get('game')
    if game.locked or game.time_locked():
        raise ValidationError("Bet time passed. You can not bet now")


class RegisterSerializer(serializers.ModelSerializer):
    is_club_admin = serializers.SerializerMethodField(default=False, read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'balance', 'first_name', 'last_name', 'user_club', 'password',
                  'game_editor', 'is_club_admin', 'is_superuser')
        read_only_fields = ('id', 'balance', 'game_editor', 'is_club_admin', 'is_superuser')
        extra_kwargs = {'password': {'write_only': True}, 'user_club': {'required': True}}

    def get_is_club_admin(self, user):
        return user.is_club_admin()

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
        fields = ('id', 'name', 'admin')
        read_only_fields = ('id',)


class BetSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = Bet
        fields = ('id', 'user', 'game', 'choice', 'amount')
        read_only_fields = ('id',)
        extra_kwargs = {'user': {'required': False}}
        validators = [user_balance_validator, game_time_validator]

    def create(self, validated_data):
        print(validated_data)
        return super().create(validated_data)


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = (
            'id', 'name', 'first', 'second', 'start', 'end', 'locked', 'first_ratio', 'second_ratio', 'draw_ratio')
        read_only_fields = ('id',)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('id', 'user', 'type', 'method', 'to', 'amount', 'transaction_id', 'account')
        read_only_fields = ('id',)
        validators = [user_balance_validator, club_validator]
