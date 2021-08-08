from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, generics, views
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from betting.models import Bet, Game, Transaction, CHOICE_FIRST, CHOICE_SECOND, CHOICE_DRAW
from users.backends import jwt_writer
from users.models import Club, User as MainUser
from .custom_permissions import IsOwnerOrAdminOrReadOnly, IsOwnerOrAdminOrCreateOnly, IsAdminGameEditorOrReadOnly, \
    BetPermissionClass
from .serializers import ClubSerializer, RegisterSerializer, BetSerializer, GameSerializer, TransactionSerializer, \
    UserSerializer

User: MainUser = get_user_model()


class RegisterViewSet(viewsets.ModelViewSet):
    """
    retrieve:
        Return a user instance.

    list:
        Return all users, ordered by most recently joined.

    create:
        Create a new user.

    delete:
        Remove an existing user.

    partial_update:
        Update one or more fields on an existing user.

    update:
        Update a user.
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [IsOwnerOrAdminOrCreateOnly]


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


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

    @action(methods=['GET'], detail=True)
    def club_users(self, request, pk, *args, **kwargs):
        club = get_object_or_404(Club, id=pk)
        users = User.objects.filter(user_club=club)
        return Response({"results": UserSerializer(users, many=True).data})


class BetViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        try:
            club_admin = bool(self.request.user.club)
        except Club.DoesNotExist:
            club_admin = False
        if club_admin:
            return Bet.objects.filter(user__user_club=self.request.user.club)
        return Bet.objects.filter(user=self.request.user)

    queryset = Bet.objects.all()
    serializer_class = BetSerializer
    permission_classes = [BetPermissionClass]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    permission_classes = [IsAdminGameEditorOrReadOnly]

    @action(methods=['GET'], detail=True)
    def ratio(self, request, pk, *args, **kwargs):
        game = get_object_or_404(Game, id=pk)
        first = sum([x.amount for x in game.bet_set.filter(choice=CHOICE_FIRST)]) + 1
        second = sum([x.amount for x in game.bet_set.filter(choice=CHOICE_SECOND)]) + 1
        draw = sum([x.amount for x in game.bet_set.filter(choice=CHOICE_DRAW)]) + 1
        data = {
            'first': first,
            'second': second,
            'draw': draw,
            'first_ratio': (first + second + draw) / first,
            'second_ratio': (first + second + draw) / second,
            'draw_ratio': (first + second + draw) / draw
        }
        return Response(data)


class TransactionListView(generics.ListCreateAPIView):
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
