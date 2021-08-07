from django.contrib.auth import get_user_model
from rest_framework import viewsets

from users.models import Club, User as MainUser
from .custom_permissions import IsOwnerOrAdminOrReadOnly, IsOwnerOrAdminOrCreateOnly
from .serializers import ClubSerializer, RegisterSerializer

User: MainUser = get_user_model()


class ClubViewSet(viewsets.ModelViewSet):
    queryset = Club.objects.all()
    serializer_class = ClubSerializer
    permission_classes = [IsOwnerOrAdminOrReadOnly]


class RegisterViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [IsOwnerOrAdminOrCreateOnly]
