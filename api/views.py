from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, generics, views
from rest_framework.response import Response

from betting.models import Bet, Game, Transaction
from users.backends import jwt_writer
from users.models import Club, User as MainUser
from .custom_permissions import IsOwnerOrAdminOrReadOnly, IsOwnerOrAdminOrCreateOnly, IsAdminOrReadOnly
from .serializers import ClubSerializer, RegisterSerializer, BetSerializer, GameSerializer, TransactionSerializer

User: MainUser = get_user_model()


class RegisterViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [IsOwnerOrAdminOrCreateOnly]


class Login(views.APIView):
    def post(self, *args, **kwargs):
        data = self.request.data
        if not data.get('username') or not data.get('password'):
            return Response({'Username or Password is not supplied.'}, status=400)
        user = User.objects.get(username=data.get('username'))
        if user.check_password(data.get('password')):
            data = RegisterSerializer(user).data
            jwt_str = jwt_writer(**data)
            return Response({'jwt': jwt_str})
        return Response({'Username or Password is not supplied.'}, status=400)

    def get(self, *args, **kwargs):
        if self.request.user and self.request.user.is_authenticated:
            return Response(RegisterSerializer(self.request.user).data)
        return Response({'result': 'User must be logged in'}, status=403)


class ClubViewSet(viewsets.ModelViewSet):
    queryset = Club.objects.all()
    serializer_class = ClubSerializer
    permission_classes = [IsOwnerOrAdminOrReadOnly]


class BetViewSet(viewsets.ModelViewSet):
    queryset = Bet.objects.all()
    serializer_class = BetSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    permission_classes = [IsAdminOrReadOnly]


class TransactionListView(generics.ListCreateAPIView):
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
