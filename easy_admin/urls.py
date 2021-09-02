from django.urls import path
from django.views.decorators.cache import never_cache

from . import views

app_name = 'ea'

urlpatterns = [
    path('', views.Home.as_view(), name='home'),
    path('deposits/', views.DepositsView.as_view(), name='deposits'),
    path('withdraws/', views.WithdrawsView.as_view(), name='withdraws'),
    path('transfers/', views.TransferView.as_view(), name='transfers'),
    path('club_transfers/', views.ClubTransferView.as_view(), name='club_transfers'),
    path('matches/', views.MatchView.as_view(), name='matches'),
    path('bet_options/', views.BetOptionView.as_view(), name='bet_options'),
    path('bet_option_detail/<int:scope_id>/', views.BetOptionView.as_view(), name='bet_option_detail'),
    path('clubs/', views.ClubView.as_view(), name='clubs'),
    path('update-club/<int:club_id>/', views.ClubView.as_view(), name='update-club'),
    path('users/', views.UserView.as_view(), name='users'),
    path('bets/', views.BetView.as_view(), name='bets'),
    path('methods/', views.MethodView.as_view(), name='methods'),
    path('configure/', views.ConfigureView.as_view(), name='configure'),
    path('create_bet_scope/<int:match_id>/', views.create_bet_option, name='create_bet_scope'),
    path('update_bet_scope/<int:match_id>/<int:scope_id>/', views.update_bet_option, name='update_bet_scope'),

    path('lock_match/<int:match_id>/', views.lock_match, name='lock_match'),
    path('hide_match/<int:match_id>/', views.hide_match, name='hide_match'),
    path('lock_scope/<int:scope_id>/', views.lock_scope, name='lock_scope'),
    path('hide_scope/<int:scope_id>/', views.hide_scope, name='hide_scope'),
    path('pay_scope/<int:scope_id>/', views.pay_scope, name='pay_scope'),
    path('set_scope_winner/<int:scope_id>/<winner>/', views.set_scope_winner, name='scope_winner'),
    path('verify_transfer/<int:tra_id>/', views.verify_transfer, name='verify_transfer'),
    path('delete_transfer/<int:tra_id>/', views.deny_transfer, name='delete_transfer'),
    path('verify_club_transfer/<int:tra_id>/', views.verify_club_transfer, name='verify_club_transfer'),
    path('delete_club_transfer/<int:tra_id>/', views.deny_club_transfer, name='delete_club_transfer'),
    path('delete_deposit/<int:deposit_id>/', views.deny_deposit, name='delete_deposit'),
    path('delete_withdraw/<int:withdraw_id>/', views.deny_withdraw, name='delete_withdraw'),
    path('delete_method/<int:method_id>/', views.delete_method, name='delete_method'),
]
