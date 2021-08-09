from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.renderers import OpenAPIRenderer
from rest_framework.routers import DefaultRouter
from rest_framework.schemas import get_schema_view

from . import views

router = DefaultRouter()

router.register('register', views.RegisterViewSet, 'register')
router.register('club', views.ClubViewSet, 'club')
router.register('bet', views.BetViewSet, 'bet')
router.register('match', views.MatchViewSet, 'match')
router.register('bet_scope', views.BetScopeViewSet, 'bet_scope')
router.register('user', views.UserViewSet, 'user')

app_name = 'api'

schema_view = get_schema_view(title='Users API', renderer_classes=[OpenAPIRenderer])

urlpatterns = [
    path('doc_open/', schema_view, name='doc_open'),
    path('', include(router.urls), name='main_api'),
    path('login/', views.Login.as_view(), name='api_login'),
    path('transactions/available-methods/', views.AvailableMethods.as_view(), name='available_methods'),
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    path('doc/', TemplateView.as_view(
        template_name='api/documentation.html',
        extra_context={'schema_url': 'api:doc_open'}
    ), name='swagger-ui'),
]
