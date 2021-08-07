from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from betting.models import Bet, Game, Transaction
from users.models import User as MainUser, Club

User: MainUser = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'first_name', 'last_name', 'user_club', 'password',)
        read_only_fields = ('id',)
        write_only_fields = ('password',)


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


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('user', 'type', 'method', 'to', 'amount', 'transaction', 'account')
