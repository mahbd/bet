from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, views, mixins
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from betting.actions import *
from betting.choices import A_MATCH_LOCK, A_MATCH_HIDE, A_MATCH_GO_LIVE, A_MATCH_END_NOW, A_QUESTION_LOCK, \
    A_QUESTION_HIDE, A_QUESTION_END_NOW, A_QUESTION_SELECT_WINNER, A_QUESTION_UNSELECT_WINNER, \
    A_QUESTION_REFUND, A_REMOVE_GAME_EDITOR, A_MAKE_GAME_EDITOR, SOURCE_BANK, A_REFUND_BET, A_DEPOSIT_ACCEPT, \
    A_DEPOSIT_CANCEL, A_WITHDRAW_ACCEPT, A_WITHDRAW_CANCEL, A_TRANSFER_ACCEPT, A_TRANSFER_CANCEL
from betting.models import Bet, BetQuestion, Match, DepositMethod, Announcement, Deposit, Withdraw, Transfer, \
    QuestionOption, ConfigModel
from users.backends import jwt_writer, get_current_club
from users.models import Club, User as MainUser, Notification
from users.views import total_user_balance, total_club_balance
from .action_data import action_data
from .custom_permissions import MatchPermissionClass, BetPermissionClass, ClubPermissionClass, \
    TransactionPermissionClass, UserViewPermission, IsAdminOrReadOnly, TransferPermissionClass
from .serializers import ClubSerializer, BetSerializer, MatchSerializer, \
    UserListSerializer, BetQuestionSerializer, UserDetailsSerializer, AnnouncementSerializer, DepositSerializer, \
    WithdrawSerializer, TransferSerializer, NotificationSerializer, UserListSerializerClub, QuestionOptionSerializer, \
    TransferClubSerializer, BetQuestionDetailsSerializer, DepositMethodSerializer, ConfigModelSerializer, \
    MatchDetailsSerializer

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

    def get(self, request):
        return Response({'details': f"""
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
        Unselect Question Winner\n
        If a question is paid and you use this, everything will be changed 
        to as it was before payment. payload should be\n
        ['action_code': {A_QUESTION_UNSELECT_WINNER}, 'question_id': question id]\n\n
        Refund a question\n
        Refund a question. payload should be\n
        ['action_code': {A_QUESTION_REFUND}, 'question_id': question id]\n\n
        Make Game Editor\n
        User will be converted to game editor. payload should be\n
        ['action_code': {A_MAKE_GAME_EDITOR}, 'user_id': user id]\n\n
        Remove Game Editor\n
        User will be converted to regular user. payload should be\n
        ['action_code': {A_REMOVE_GAME_EDITOR}, 'user_id': user id]\n\n
        Refund bet\n
        This will refund a bet. If you don't supply percent, function will 
        automatically determine how much to refund. Using this API you can reduce 
        balance of user. payload should be\n
        ['action_code': {A_REFUND_BET}, 'bet_id': bet id, 'percent': Percent to refund]\n\n
        Accept Deposit. payload should be\n
        ['action_code': {A_DEPOSIT_ACCEPT}, 'deposit_id': deposit id]\n\n
        Cancel Deposit. payload should be\n
        ['action_code': {A_DEPOSIT_CANCEL}, 'deposit_id': deposit id]\n\n
        Cancel Deposit. payload should be\n
        ['action_code': {A_WITHDRAW_ACCEPT}, 'withdraw_id': withdraw id]\n\n
        Cancel Deposit. payload should be\n
        ['action_code': {A_WITHDRAW_CANCEL}, 'withdraw_id': withdraw id]\n\n
        Cancel Deposit. payload should be\n
        ['action_code': {A_TRANSFER_ACCEPT}, 'transfer_id': transfer id]\n\n
        Cancel Deposit. payload should be\n
        ['action_code': {A_TRANSFER_CANCEL}, 'transfer_id': transfer id]\n\n
        """})


class AllTransactionView(views.APIView):
    """
    get:
    User must be logged in
    """

    def get(self, *args, **kwargs):
        if self.request.GET.get('club'):
            club = get_current_club(self.request)
            all_deposit = Deposit.objects.filter(club=club)
            all_withdraw = []
            all_transfer = Transfer.objects.filter(club=club)
        else:
            if not (self.request.user and self.request.user.is_authenticated):
                return Response({'details': 'User is not authenticated'}, status=401)
            all_deposit = Deposit.objects.filter(user=self.request.user)
            all_withdraw = Withdraw.objects.filter(user=self.request.user)
            all_transfer = Transfer.objects.filter(sender=self.request.user)
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
                'transaction_id': (hasattr(query, 'reference') and query.reference) or None,
                'status': query.status,
                'created_at': query.created_at
            })
        all_transaction.sort(key=lambda x: x['created_at'], reverse=True)
        try:
            limit = int(self.request.GET.get('limit', 0))
            offset = int(self.request.GET.get('offset', 0))
            if limit:
                all_transaction = all_transaction[offset: offset + limit]
        except Exception as e:
            print(e)
        return Response({'results': all_transaction, 'count': len(all_transaction)})


class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    Return list of announcement\n
    Filterable fields: expired\n
    """
    queryset = Announcement.objects.filter(expired=False)
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['expired']


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
    Filterable fields: match, match__game_name, status\n
    Searchable fields: question, match__team_a_name, match__team_b_name, winner
    """

    def get_serializer_class(self):
        if self.request.GET.get('fast'):
            return BetQuestionSerializer
        return BetQuestionDetailsSerializer

    queryset = BetQuestion.objects.select_related('match').all()
    permission_classes = [MatchPermissionClass]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['question', 'match__team_a_name', 'match__team_b_name']
    filterset_fields = ['match', 'match__game_name', 'status', 'winner']


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


class ConfigModelViewSet(viewsets.ModelViewSet):
    """
    Only superuser can add, change and delete. Anyone can view.
    """
    queryset = ConfigModel.objects.all()
    serializer_class = ConfigModelSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'name'
    http_method_names = ['get', 'post', 'patch', 'head', 'options']


class DepositMethodViewSet(viewsets.ModelViewSet):
    """
    Only superuser can add, change and delete. Anyone can view.
    """
    queryset = DepositMethod.objects.all()
    serializer_class = DepositMethodSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['number1', 'number2']


class DashboardView(views.APIView):
    def get(self, request):
        if not self.request.user or not self.request.user.is_superuser:
            return Response({'details': 'You does not have permission'}, status=403)
        data = {
            'total_user_balance': total_user_balance(),
            'total_club_balance': total_club_balance(),
            'total_user': User.objects.all().count(),
            'total_user_deposit': Deposit.objects.filter(deposit_source=SOURCE_BANK, status=STATUS_ACCEPTED
                                                         ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_user_withdraw': Withdraw.objects.filter(status=STATUS_ACCEPTED
                                                           ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_club_transfer': Transfer.objects.filter(club__isnull=False, status=STATUS_ACCEPTED
                                                           ).aggregate(Sum('amount'))['amount__sum'] or 0

        }
        return Response({'details': data})


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
        if self.request.GET.get('club'):
            club = get_current_club(self.request)
            return Deposit.objects.filter(club=club)
        return Deposit.objects.filter(user=self.request.user)

    serializer_class = DepositSerializer
    permission_classes = [TransactionPermissionClass]
    http_method_names = ['get', 'post', 'head', 'options']
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    filterset_fields = ['status']


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
            data = UserDetailsSerializer(user).data
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
    To get only list of matches use ?fast=truen \n
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

    def get_serializer_class(self):
        if self.request.GET.get('fast'):
            return MatchSerializer
        return MatchDetailsSerializer

    queryset = Match.objects.all()
    permission_classes = [MatchPermissionClass]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['game_name', 'team_a_name', 'team_b_name']
    filterset_fields = ['game_name', 'status']


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


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
        list:
        Returns list of transfers\n
        add ?club=true   to do club transfer and related operation\n
        Filterable field: status\n
        Searchable fields: sender__username, sender__first_name, sender__last_name,
                     recipient__username, recipient__first_name, recipient__last_name
    """

    def get_queryset(self):
        if self.request.GET.get('club'):
            club = get_current_club(self.request)
            return Transfer.objects.filter(club=club)
        return Transfer.objects.filter(sender=self.request.user)

    def get_serializer_class(self):
        if self.request.GET.get('club'):
            return TransferClubSerializer
        return TransferSerializer

    http_method_names = ['get', 'post', 'head', 'options']
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['sender__username', 'sender__first_name', 'sender__last_name',
                     'recipient__username', 'recipient__first_name', 'recipient__last_name', ]
    filterset_fields = ['status']
    permission_classes = [TransferPermissionClass]


class UserViewSet(viewsets.ModelViewSet):
    """
    list:
    Return list of users.\n
    Filterable fields: user_club, referred_by\n
    Searchable fields: username, first_name, last_name\n
    """

    def get_serializer_class(self):
        user = self.request.user
        if self.request.method == 'POST':
            return UserDetailsSerializer
        if user and (user.id == int(self.kwargs.get('pk')) or user.is_superuser):
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
