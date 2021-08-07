from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

router.register('register', views.RegisterViewSet, 'register')
router.register('club', views.ClubViewSet, 'club')
router.register('bet', views.BetViewSet, 'bet')
router.register('game', views.GameViewSet, 'game')

app_name = 'api'

urlpatterns = [
    path('', include(router.urls)),
    path('login/', views.Login.as_view(), name='api_login'),
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list')
]
