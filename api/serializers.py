from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from betting.models import Bet, Game, Transaction, TYPE_WITHDRAW, METHOD_TRANSFER
from users.models import User, Club


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'balance', 'first_name', 'last_name', 'user_club', 'password',)
        read_only_fields = ('id', 'balance',)
        extra_kwargs = {'password': {'write_only': True}, 'user_club': {'required': True}}

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


class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = ('name', 'admin')


class BetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bet
        fields = ('user', 'game', 'choice', 'amount',)

    def update(self, instance: Bet, validated_data):
        if instance.game.locked or instance.game.time_locked():
            raise ValidationError('Can not change locked bet')
        return super().update(instance, validated_data)


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ('first', 'second', 'start', 'end', 'locked')


def user_balance_validator(data):
    user: User = data.get('user')
    amount = data.get('amount')
    t_type = data.get('type')
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


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('user', 'type', 'method', 'to', 'amount', 'transaction_id', 'account')
        validators = [user_balance_validator, club_validator]
