from django.contrib.auth import get_user_model
from rest_framework import serializers

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
