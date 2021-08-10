from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import viewsets, permissions, views, mixins
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from betting.models import Bet, BetScope, Match, Transaction, DepositWithdrawMethod
from users.backends import jwt_writer
from users.models import Club, User as MainUser
from .custom_permissions import MatchPermissionClass, BetPermissionClass, RegisterPermissionClass, \
    ClubPermissionClass, TransactionPermissionClass
from .serializers import ClubSerializer, RegisterSerializer, BetSerializer, MatchSerializer, TransactionSerializer, \
    UserSerializer, BetScopeSerializer

User: MainUser = get_user_model()


class RegisterViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                      mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    partial_update:
    Update part of user profile
    update:
    Update current user
    retrieve:
    Return the given user.
    list:
    ***********This is not allowed here.***********
    create:
    Create a new user instance. Logged in at same time. Use *jwt* sent through response.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [RegisterPermissionClass]


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:
    Return list of users.
    retrieve:
    Return user of that id or username. Example: \n
    by id: /api/users/10/
    by username: /api/users/miloy/
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_object(self):
        primary_key = self.kwargs[self.lookup_field]
        try:
            primary_key = int(primary_key)
            return get_object_or_404(self.queryset, pk=primary_key)
        except ValueError:
            return get_object_or_404(self.queryset, username=primary_key)


class Login(views.APIView):
    """
    post:
    REQUIRED username, password\n
    Return jwt key to authenticate user.
    get:
    Returns user details. User MUST be logged in
    """

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
            user.last_login = timezone.now()
            user.save()
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


class ClubViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  viewsets.GenericViewSet):
    """
    list:
    Returns list of clubs
    update:
    Update club name. User must be club admin.
    partial_update:
    Update club name. User must be club admin.
    retrieve:
    Returns club details of that id
    """
    queryset = Club.objects.all()
    serializer_class = ClubSerializer
    permission_classes = [ClubPermissionClass]

    @action(methods=['GET'], detail=True, permission_classes=[permissions.IsAuthenticated])
    def club_users(self, request, pk, *args, **kwargs):
        """
        get:
        Returns list of club users. User must be a member of that club
        """
        if pk != request.user.user_club_id:
            return Response({"errors": "You must be member of this club"}, status=400)
        club = get_object_or_404(Club, id=pk)
        users = User.objects.filter(user_club=club)
        return Response({"results": UserSerializer(users, many=True).data})


class BetViewSet(mixins.CreateModelMixin,
                 mixins.RetrieveModelMixin,
                 mixins.ListModelMixin,
                 viewsets.GenericViewSet):
    """
    list:
    Returns list of bet of current user. User MUST bet logged in.\n
    To get clubs bet list add ?club_id={{ club_id }} . User MUST be admin of that club.
    create:
    Create a bet instance.
    retrieve:
    Returns bet instance. User must be logged in and creator of that bet.
    """

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
    """
    list:
    Return a list of matches
    To get list of matches of a game \n
    /api/match/?game_name={{ game_name }}\n
    Allowed game names: football|cricket|tennis|others
    create:
    Create an instance of match. Only game_editor enabled user and superuser can create new match
    retrieve:
    Returns match details of the id
    update:
    Update the match. Only game_editor enabled user and superuser can update match. PATCH is suggested than PUT
    partial_update:
    Update the match. Only game_editor enabled user and superuser can update match.
    """

    def get_queryset(self, *args, **kwargs):
        game_name = self.request.GET.get('game_name')
        if game_name:
            return Match.objects.filter(game_name=game_name)
        return Match.objects.all()

    serializer_class = MatchSerializer
    permission_classes = [MatchPermissionClass]


class BetScopeViewSet(viewsets.ModelViewSet):
    """
    This is the place where user can bet.
    list:
    Returns list of bet scopes. \n
    To get list of scopes of a match \n
    /api/bet_scope/?match_id={{ match_id }}
    To get list of scopes of a game \n
    /api/bet_scope/?game_name={{ game_name }}\n
    Allowed game names: football|cricket|tennis|others
    create:
    Create an instance of bet scope. Only game_editor enabled user and superuser can create new bet scope
    retrieve:
    Returns bet_scope details of the id
    update:
    Update the bet_scope. Only game_editor enabled user and superuser can update bet_scope. PATCH is suggested than PUT
    partial_update:
    Update the bet_scope. Only game_editor enabled user and superuser can update bet_scope.
    retrieve:
    Returns bet_scope details
    """

    def get_queryset(self):
        match_id = self.request.GET.get('match_id')
        game_name = self.request.GET.get('game_name')
        if match_id:
            return BetScope.objects.filter(match_id=match_id)
        if game_name:
            return BetScope.objects.filter(match__game_name=game_name)
        return BetScope.objects.all()

    serializer_class = BetScopeSerializer
    permission_classes = [MatchPermissionClass]

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


class TransactionViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    """
    list:
    Returns list of transaction for current user. User must be logged in.
    retrieve:
    Returns selected transaction details. User must be the owner of that transaction.
    create:
    Create a transaction instance. You can deposit, withdraw and transfer money using this method.\n
    DEPOSIT\n
    To deposit money transfer money to the superuser and send the following details\n
    {\n
    "type": "deposit", // Don't change this\n
    "method": "bkash", // using which method you sent money. See below for details\n
    "amount": "1000", // Amount of money you sent to superuser\n
    "transaction_id": "fdksafkljdsfklj", // The transaction id when you sent money to superuser\n
    "account": "01735860134" // From which account you sent money\n
    }\n
    List of available methods: /api/transactions/available-methods/\n
    WITHDRAW\n
    {\n
    "type": "withdraw", // Don't change this\n
    "method": "bkash", // using which method you want to receive money. See below for details\n
    "amount": "1000", // Amount of money you want to withdraw\n
    "account": "01735860134" // In which account you want to get money\n
    }\n
    List of available methods: /api/transactions/available-methods/\n
    TRANSFER\n
    {\n
    "type": "withdraw", // Don't change this\n
    "method": "transfer", // Don't change this'\n
    "amount": "1000", // Amount of money you want to withdraw\n
    "to": "3" // To whom you want to send money\n
    }\n
    """

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    serializer_class = TransactionSerializer
    permission_classes = [TransactionPermissionClass]

    @action(detail=False, methods=['GET'], permission_classes=[])
    def available_methods(self, *args, **kwargs):
        """
        get:
        Returns a list of available methods for deposit and withdraw methods
        """
        methods = [{
            "id": method.code,
            "to_show": method.name,
            "numbers": [
                {
                    "id": 1,
                    "number": method.number1
                },
                {
                    "id": 2,
                    "number": method.number2
                }
            ]} for
            method in DepositWithdrawMethod.objects.all()]
        return Response({'methods': methods})
