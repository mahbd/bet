from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

router.register('register', views.RegisterSerializer, 'register')
router.register('club', views.ClubViewSet, 'club')

urlpatterns = [
    path('', include(router.urls))
]
