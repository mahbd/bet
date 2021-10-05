from django.contrib.auth import get_user_model
from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, views, mixins, generics
from rest_framework.decorators import action, api_view
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from betting.actions import *
from betting.choices import A_MATCH_LOCK, A_MATCH_HIDE, A_MATCH_GO_LIVE, A_MATCH_END_NOW, A_QUESTION_LOCK, \
    A_QUESTION_HIDE, A_QUESTION_END_NOW, A_QUESTION_SELECT_WINNER, A_QUESTION_PAY, A_QUESTION_UN_PAY, A_QUESTION_REFUND
from betting.models import Bet, BetQuestion, Match, DepositWithdrawMethod, Announcement, Deposit, Withdraw, Transfer, \
    QuestionOption
from users.backends import jwt_writer, get_current_club
from users.models import Club, User as MainUser, login_key, Notification
from .action_data import action_data
from .custom_permissions import MatchPermissionClass, BetPermissionClass, RegisterPermissionClass, \
    ClubPermissionClass, TransactionPermissionClass, UserViewPermission
from .serializers import ClubSerializer, RegisterSerializer, BetSerializer, MatchSerializer, \
    UserListSerializer, BetQuestionSerializer, UserDetailsSerializer, AnnouncementSerializer, DepositSerializer, \
    WithdrawSerializer, TransferSerializer, NotificationSerializer, UserListSerializerClub, QuestionOptionSerializer, \
    TransferClubSerializer

User: MainUser = get_user_model()


def determine_type(query):
    if hasattr(query, 'recipient'):
        return 'transfer'
    if hasattr(query, 'club'):
        return 'deposit'
    return 'withdraw'


def permission_error():
    return Response({'details': 'User does not have enough permission'}, status=403)


def failed_to_do(data):
    return Response({'details': f'Failed to complete the action due to data.\n{data}'}, status=400)


def completed_successfully(data):
    return Response({'details': f'Failed to complete the action due to data.'}, status=200)


class ActionView(views.APIView):
    def post(self, request):
        f"""
        Do various operation\n
        *************  Match Actions ******************\n
        Lock Match\n
        To lock a match. payload should be\n
        ['action_code': {A_MATCH_LOCK}, 'match_id': match id]\n\n
        Hide Match\n
        To hide a match. payload should be\n
        ['action_code': {A_MATCH_HIDE}, 'match_id': match id]\n\n
        Go Live Match\n
        To hide a match. payload should be\n
        ['action_code': {A_MATCH_GO_LIVE}, 'match_id': match id]\n\n
        End Match now\n
        To hide a match. payload should be\n
        ['action_code': {A_MATCH_END_NOW}, 'match_id': match id]\n\n
        **************** Question Actions *****************\n
        Lock Question\n
        To lock a question. payload should be\n
        ['action_code': {A_QUESTION_LOCK}, 'question_id': question id]\n\n
        Hide Question\n
        To hide a question. payload should be\n
        ['action_code': {A_QUESTION_HIDE}, 'question_id': question id]\n\n
        Question End Now\n
        To end a question. payload should be\n
        ['action_code': {A_QUESTION_END_NOW}, 'question_id': question id]\n\n
        Select Question Winner\n
        To select a question winner. payload should be\n
        ['action_code': {A_QUESTION_SELECT_WINNER}, 'question_id': question id, 'option_id': option id]\n\n
        Pay Question\n
        To pay a question. payload should be\n
        ['action_code': {A_QUESTION_PAY}, 'question_id': question id]\n\n
        Revert Payment Question\n
        If a question is paid and you use this, everything will be changed 
        to as it was before payment. payload should be\n
        ['action_code': {A_QUESTION_UN_PAY}, 'question_id': question id]\n\n
        Refund a question. payload should be\n
        ['action_code': {A_QUESTION_REFUND}, 'question_id': question id]\n\n
        """
        user: User = self.request.user
        club: Club = get_current_club(self.request)
        data = dict(self.request.data)
        action_code = data.get('action_code')
        to_do = action_data.get(action_code, None)
        if not to_do:
            return Response({'details': 'Invalid action'}, status=400)
        if eval(to_do['permission']):
            eval(to_do.get('prepare', 'True'))
            response = eval(to_do['function'])
            if not response:
                return failed_to_do(data)
            return completed_successfully(data)
        return permission_error()


class AllTransactionView(views.APIView):
    """
    get:
    User must be logged in
    """

    def get(self, *args, **kwargs):
        if self.request.GET.get('club'):
            club = get_current_club(self.request)
            all_deposit = Deposit.objects.filter(club=club)[:40]
            all_withdraw = []
            all_transfer = Transfer.objects.filter(club=club)[:40]
        else:
            if not (self.request.user and self.request.user.is_authenticated):
                return Response({'details': 'User is not authenticated'}, status=401)
            all_deposit = Deposit.objects.filter(user=self.request.user)[:40]
            all_withdraw = Withdraw.objects.filter(user=self.request.user)[:40]
            all_transfer = Transfer.objects.filter(sender=self.request.user)[:40]
        all_transaction = []
        for query in list(all_deposit) + list(all_withdraw) + list(all_transfer):
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
                'status': query.status,
                'created_at': query.created_at
            })
        all_transaction.sort(key=lambda x: x['created_at'], reverse=True)
        return Response({'results': all_transaction, 'count': len(all_transaction)})


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
    Returns list of clubs\n
    You can search club by name\n
    """
    queryset = Club.objects.all()
    serializer_class = ClubSerializer
    permission_classes = [ClubPermissionClass]
    filter_backends = [SearchFilter]
    search_fields = ['name']


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
            data = UserDetailsSerializer(self.request.user).data
            return Response(data)
        return Response({'detail': 'User must be logged in'}, status=403)


class MatchViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of matches\n
    To get list of matches of a game \n
    You can filter by status and game_name\n
    You can search by game_name, team_a_name and team_b_name\n
    create:
    Create an instance of match. Only game_editor enabled user and superuser can create new match
    retrieve:
    Returns match details of the id
    update:
    Update the match. Only game_editor enabled user and superuser can update match. PATCH is suggested than PUT
    partial_update:
    Update the match. Only game_editor enabled user and superuser can update match.
    """
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [MatchPermissionClass]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['game_name', 'team_a_name', 'team_b_name']
    filterset_fields = ['game_name', 'status']


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


class UserViewSet(viewsets.ModelViewSet):
    """
    list:
    Return list of users.\n
    Filterable fields: user_club, referred_by\n
    Searchable fields: username, first_name, last_name\n
    """

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserDetailsSerializer
        if self.request.user.id == int(self.kwargs.get('pk')) or self.request.user.is_superuser:
            return UserDetailsSerializer
        elif self.request.GET.get('club'):
            return UserListSerializerClub
        else:
            return UserListSerializer

    permission_classes = [UserViewPermission]
    queryset = User.objects.all()
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['username', 'first_name', 'last_name']
    filterset_fields = ['user_club', 'referred_by']
