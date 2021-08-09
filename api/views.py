from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, generics, views
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from betting.models import Bet, BetScope, Match, Transaction, DepositWithdrawMethod
from users.backends import jwt_writer
from users.models import Club, User as MainUser
from .custom_permissions import IsOwnerOrAdminOrReadOnly, IsOwnerOrAdminOrCreateOnly, IsAdminMatchEditorOrReadOnly, \
    BetPermissionClass
from .serializers import ClubSerializer, RegisterSerializer, BetSerializer, MatchSerializer, TransactionSerializer, \
    UserSerializer, BetScopeSerializer

User: MainUser = get_user_model()


class RegisterViewSet(viewsets.ModelViewSet):
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
        user = User.objects.filter(username=data.get('username'))
        if not user:
            return Response({'Username or Password is wrong.'}, status=400)
        else:
            user = user[0]
        if user.check_password(data.get('password')):
            data = RegisterSerializer(user).data
            jwt_str = jwt_writer(**data)
            return Response({'jwt': jwt_str})
        return Response({'Username or Password is wrong.'}, status=400)

    def get(self, *args, **kwargs):
        if self.request.user and self.request.user.is_authenticated:
            data = RegisterSerializer(self.request.user).data
            data['refer_set'] = [x.id for x in self.request.user.refer_set.all()]
            return Response(data)
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
        club_id = self.request.GET.get('club_id')
        if club_id:
            club = get_object_or_404(Club, id=club_id)
            if club.admin == self.request.user:
                return Bet.objects.filter(user__user_club=club)
        return Bet.objects.filter(user=self.request.user)

    serializer_class = BetSerializer
    permission_classes = [BetPermissionClass]


class MatchViewSet(viewsets.ModelViewSet):
    def get_queryset(self, *args, **kwargs):
        game_name = self.request.GET.get('game_name')
        if game_name:
            return Match.objects.filter(game_name=game_name)
        return Match.objects.all()

    serializer_class = MatchSerializer
    permission_classes = [IsAdminMatchEditorOrReadOnly]


class BetScopeViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        match_id = self.request.GET.get('match_id', -1)
        return BetScope.objects.filter(match_id=match_id)

    serializer_class = BetScopeSerializer
    permission_classes = [IsAdminMatchEditorOrReadOnly]

    # @action(methods=['GET'], detail=True)
    # def ratio(self, request, pk, *args, **kwargs):
    #     game = get_object_or_404(Game, id=pk)
    #     first = sum([x.amount for x in game.bet_set.filter(choice=CHOICE_FIRST)]) + 1
    #     second = sum([x.amount for x in game.bet_set.filter(choice=CHOICE_SECOND)]) + 1
    #     draw = sum([x.amount for x in game.bet_set.filter(choice=CHOICE_DRAW)]) + 1
    #     data = {
    #         'option_1': first,
    #         'option_2': second,
    #         'draw': draw,
    #         'option_1_rate': (first + second + draw) / first,
    #         'option_2_rate': (first + second + draw) / second,
    #         'draw_rate': (first + second + draw) / draw
    #     }
    #     return Response(data)


# noinspection PyMethodMayBeStatic
class AvailableMethods(views.APIView):
    def get(self, *args, **kwargs):
        methods = [(method.code, method.game_name) for method in DepositWithdrawMethod.objects.all()]
        return Response({'methods': methods})


class TransactionListView(generics.ListCreateAPIView):
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
