from django.conf.urls import url
from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

router.register('register', views.RegisterViewSet, 'register')
router.register('club', views.ClubViewSet, 'club')
router.register('bet', views.BetViewSet, 'bet')
router.register('match', views.MatchViewSet, 'match')
router.register('bet_scope', views.BetScopeViewSet, 'bet_scope')
router.register('user', views.UserListViewSet, 'user'),
router.register('announcement', views.AnnouncementViewSet, 'announcement')
router.register('deposit', views.DepositViewSet, 'deposit')
router.register('withdraw', views.WithdrawViewSet, 'withdraw')
router.register('transfer', views.TransferViewSet, 'transfer')

app_name = 'api'

schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
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
    path('transactions/available_methods/', views.available_methods),
    path('all_transactions/', views.AllTransaction.as_view()),
    path('', include(router.urls), name='main_api'),
    path('login/', views.Login.as_view(), name='api_login'),
    path('user-detail-update/', views.UserDetailsUpdateRetrieveDestroy.as_view())
]
