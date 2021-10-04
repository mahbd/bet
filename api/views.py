from django.contrib.auth import get_user_model
from django.http import Http404
from django.utils import timezone
from rest_framework import viewsets, permissions, views, mixins, generics
from rest_framework.decorators import action, api_view
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from betting.models import Bet, BetQuestion, Match, DepositWithdrawMethod, Announcement, Deposit, Withdraw, Transfer, \
    METHOD_CLUB, QuestionOption
from users.backends import jwt_writer, get_current_club
from users.models import Club, User as MainUser, login_key, Notification
from .custom_permissions import MatchPermissionClass, BetPermissionClass, RegisterPermissionClass, \
    ClubPermissionClass, TransactionPermissionClass, IsUser
from .serializers import ClubSerializer, RegisterSerializer, BetSerializer, MatchSerializer, \
    UserListSerializer, BetQuestionSerializer, UserSerializer, AnnouncementSerializer, DepositSerializer, \
    WithdrawSerializer, TransferSerializer, NotificationSerializer, UserListSerializerClub, QuestionOptionSerializer, \
    TransferClubSerializer

User: MainUser = get_user_model()


def determine_status(status):
    if status is None:
        return 'pending'
    elif status:
        return 'accepted'
    else:
        return 'denied'


def determine_type(query):
    if hasattr(query, 'recipient'):
        return 'transfer'
    if hasattr(query, 'club'):
        return 'deposit'
    return 'withdraw'


class AllTransaction(views.APIView):
    """
    get:
    User must be logged in
    """

    def get(self, *args, **kwargs):
        if self.request.GET.get('club'):
            club = get_current_club(self.request)
            all_deposit = Deposit.objects.filter(club__isnull=False).filter(club=club)[:40]
            all_withdraw = []
            all_transfer = Transfer.objects.filter(club__isnull=False).filter(club=club)[:40]
        else:
            all_deposit = Deposit.objects.exclude(method=METHOD_CLUB).filter(user=self.request.user)[:40]
            all_withdraw = Withdraw.objects.filter(user=self.request.user)[:40]
            all_transfer = Transfer.objects.filter(user=self.request.user)[:40]
        all_transaction = []
        for query in all_deposit + all_withdraw + all_transfer:
            all_transaction.append({
                'id': query.id,
                'type': determine_type(query),
                'method': (hasattr(query, 'method') and query.method) or None,
                'recipient': (hasattr(query, 'recipient') and query.recipient.username) or None,
                'user_account': (hasattr(query, 'user_account') and query.user_account) or None,
                'site_account': (hasattr(query, 'site_account') and query.site_account) or None,
                'amount': query.amount,
                'user_balance': query.balance,
                'transaction_id': (hasattr(query, 'transaction_id') and query.transaction_id) or None,
                'status': determine_status(query.status),
                'created_at': query.created_at
            })

        all_transaction.sort(key=lambda x: x['created_at'], reverse=True)
        return Response({'results': all_transaction})


class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.filter(expired=False)
    serializer_class = AnnouncementSerializer


class BetViewSet(mixins.CreateModelMixin,
                 mixins.RetrieveModelMixin,
                 mixins.ListModelMixin,
                 viewsets.GenericViewSet):
    """
    list:
    Returns list of bet of current user. User MUST bet logged in.\n
    To get clubs bet list add ?club_id={{ club_id }} . User MUST be admin of that club.
    create:
    Create a bet instance. You can not bet if bet scope is locked or if you don't have enough balance
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


class BetViewSetClub(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        club = get_current_club(self.request)
        return Bet.objects.filter(user__user_club=club)

    serializer_class = BetSerializer


class QuestionOptionViewSet(mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            viewsets.GenericViewSet):
    queryset = QuestionOption.objects.all()
    serializer_class = QuestionOptionSerializer
    permission_classes = [MatchPermissionClass]


class BetQuestionViewSet(viewsets.ModelViewSet):
    """
    This is the place where user can bet.
    list:
    Returns list of bet scopes. \n
    To get only active/bet_able scope list\n
    /api/bet_scope/?active=true\n
    ?active=true can be used for all GET request in this api\n
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
        is_winner = self.request.GET.get('is_winner')
        all_scope = BetQuestion.objects.select_related('match').all()
        if match_id:
            all_scope = all_scope.filter(match_id=match_id)
        if game_name:
            all_scope = all_scope.filter(match__game_name=game_name)
        if is_winner:
            return all_scope
        return all_scope.filter(winner__isnull=True)

    serializer_class = BetQuestionSerializer
    permission_classes = [MatchPermissionClass]


class ChangePassword(views.APIView):
    """
    Change user password\n
    Only post is allowed. User must be logged in. Use this API to change user password.
    Payload\n
    {'password': 'New Password'}
    """

    def post(self, *args, **kwargs):
        user = self.request.user
        password = self.request.POST.get('password') or self.request.data.get('password')
        if password and user and user.is_authenticated:
            user.set_password(password)
            user.last_login = timezone.now()
            user.login_key = login_key()
            user.save()
            data = RegisterSerializer(user).data
            data.pop('jwt')
            jwt_str = jwt_writer(**data)
            return Response({'jwt': jwt_str})
        return Response({'detail': 'Password is not supplied or user is not logged in.'}, status=400)


class ClubViewSet(viewsets.ModelViewSet):
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
        club = get_object_or_404(Club, id=pk)
        users = User.objects.filter(user_club=club)
        return Response({"results": UserListSerializer(users, many=True).data})


class DepositViewSet(viewsets.ModelViewSet):
    """
    Deposit View\n
    User Must be logged in to make any request
    create:
    Create new Deposit request\n
    list:
    By default shows all deposits\n
    add ?pending=true     to see only pending requests\n
    add ?confirmed=true     to see only confirmed requests\n
    """

    def get_queryset(self):
        return Deposit.objects.filter(user=self.request.user)

    serializer_class = DepositSerializer
    permission_classes = [TransactionPermissionClass]
    http_method_names = ['get', 'post', 'head', 'options']


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
        username, password = data.get('username'), data.get('password')
        if username is None or password is None:
            return Response({'detail': 'Username or Password is not supplied.'}, status=400)
        user = User.objects.filter(username=username)
        if not user.exists():
            club = Club.objects.filter(username=username)
            if not club:
                return Response({'detail': 'Username or Password is wrong.'}, status=400)
            club = club[0]
            data = ClubSerializer(club).data
            data['key'] = password
            jwt_str = jwt_writer(**data)
            return Response({'jwt': jwt_str})
        else:
            user = user[0]
        if user.check_password(password):
            user.last_login = timezone.now()
            user.save()
            data = RegisterSerializer(user).data
            data.pop('jwt')
            jwt_str = jwt_writer(**data)
            return Response({'jwt': jwt_str})
        return Response({'detail': 'Username or Password is wrong.'}, status=400)

    def get(self, *args, **kwargs):
        if self.request.user and self.request.user.is_authenticated:
            data = UserSerializer(self.request.user).data
            return Response(data)
        return Response({'detail': 'User must be logged in'}, status=403)


class MatchViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of matches\n
    To get list of matches of a game \n
    /api/match/?game_name={{ game_name }}\n
    To get only active matches \n
    /api/match/?active_only=true \n
    To get only active matches of a game\n
    /api/match/?active_only=true&game_name={{ game_name }} \n
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
        active_only = self.request.GET.get('active_only', False)
        match_list = Match.objects.all()
        if active_only:
            match_list = match_list.filter(end_time__gte=timezone.now())
        if game_name:
            match_list = match_list.filter(game_name=game_name)
        return match_list

    serializer_class = MatchSerializer
    permission_classes = [MatchPermissionClass]


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class RegisterViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin,
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


@api_view(['GET'])
def available_methods(request):
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


class WithdrawViewSet(viewsets.ModelViewSet):
    """
    User must be logged in
    create:
    Request will be denied if user doesn't have enough balance
    """

    def get_queryset(self):
        return Withdraw.objects.filter(user=self.request.user)

    serializer_class = WithdrawSerializer
    permission_classes = [TransactionPermissionClass]
    http_method_names = ['get', 'post', 'head', 'options']


class TransferViewSet(viewsets.ModelViewSet):
    """
        User must be logged in
        create:
        Request will be denied if user doesn't have enough balance or at least one of them is not club admin
        or both of them is not of same club
    """

    def get_queryset(self):
        if self.request.GET.get('club'):
            club = get_current_club(self.request)
            self.permission_classes = []
            return Transfer.objects.filter(club=club)
        self.permission_classes = [TransactionPermissionClass]
        return Transfer.objects.filter(sender=self.request.user)

    def get_serializer_class(self):
        return TransferClubSerializer if self.request.GET.get('club') else TransferSerializer

    http_method_names = ['get', 'post', 'head', 'options']


class UserListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:
    Return list of users.
    """
    queryset = User.objects.values('id', 'username', 'first_name', 'last_name').all()
    serializer_class = UserListSerializer
    lookup_field = 'username'


class UserListViewSetClub(viewsets.ReadOnlyModelViewSet):
    """
    list:
    Return list of club users.
    """

    def get_queryset(self):
        club = get_current_club(self.request)
        if not club:
            raise Http404
        return User.objects.filter(user_club=club)

    serializer_class = UserListSerializerClub
    lookup_field = 'username'


class UserDetailsUpdateRetrieveDestroy(generics.RetrieveUpdateDestroyAPIView):
    """
    retrieve:
    Return user of that id or username. Example: \n
    by id: /api/users/10/\n
    by username: /api/users/miloy/

    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsUser]

    def get_object(self):
        return self.request.user
