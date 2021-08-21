from django.urls import path

from . import views

app_name = 'ea'

urlpatterns = [
    path('', views.Home.as_view(), name='home'),
    path('deposits/', views.DepositsView.as_view(), name='deposits'),
    path('withdraws/', views.WithdrawsView.as_view(), name='withdraws'),
    path('transfers/', views.TransferView.as_view(), name='transfers'),
    path('matches/', views.MatchView.as_view(), name='matches'),
    path('bet_options/', views.BetOptionView.as_view(), name='bet_options'),
    path('clubs/', views.ClubView.as_view(), name='clubs'),
]
