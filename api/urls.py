from django.conf.urls import url
from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from . import views

router = DefaultRouter()

router.register('register', views.RegisterViewSet, 'register')
router.register('club', views.ClubViewSet, 'club')
router.register('bet', views.BetViewSet, 'bet')
router.register('match', views.MatchViewSet, 'match')
router.register('bet_scope', views.BetScopeViewSet, 'bet_scope')
router.register('transactions', views.TransactionViewSet, 'transactions')
router.register('user', views.UserListViewSet, 'user'),
router.register('user-detail-update', views.UserDetailsUpdateViewSet, 'user_detail_update')
router.register('announcement', views.AnnouncementViewSet, 'announcement')

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

    path('', include(router.urls), name='main_api'),
    path('login/', views.Login.as_view(), name='api_login'),
]
