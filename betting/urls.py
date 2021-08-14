from django.urls import path

from . import views

app_name = 'betting'

urlpatterns = [
    path('post_test/', views.test_post, name='post_test'),
    path('get_file/', views.get_file),
    path('lock_betscope/<int:bet_scope_id>/', views.lock_bet_scope, name='lock_bet_scope'),
    path('lock_betscope/<int:bet_scope_id>/<str:rm>/', views.lock_bet_scope, name='lock_bet_scope'),
]
