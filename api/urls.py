from django.conf.urls import url
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

router.register('announcement', views.AnnouncementViewSet, 'announcement')
router.register('bet', views.BetViewSet, 'bet')
router.register('bet-question', views.BetQuestionViewSet, 'bet_question')
router.register('club', views.ClubViewSet, 'club')
router.register('configuration', views.ConfigModelViewSet, 'config')
router.register('deposit', views.DepositViewSet, 'deposit')
router.register('deposit-method', views.DepositMethodViewSet, 'deposit_method')
router.register('match', views.MatchViewSet, 'match')
router.register('notification', views.NotificationViewSet, 'notification')
router.register('question-option', views.QuestionOptionViewSet, 'question_option')
router.register('transfer', views.TransferViewSet, 'transfer')
router.register('user', views.UserViewSet, 'user'),
router.register('withdraw', views.WithdrawViewSet, 'withdraw')

app_name = 'api'

schema_view = get_schema_view(
    openapi.Info(
        title="Bet24 API Documentation",
        default_version='v1',
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    path('', include(router.urls), name='main_api'),
    path('actions/', views.ActionView.as_view()),
    path('all-transactions/', views.AllTransactionView.as_view()),
    path('dashboard/', views.DashboardView.as_view()),
    path('login/', csrf_exempt(views.Login.as_view()), name='api_login'),
]
