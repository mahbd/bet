from django.urls import path

from . import views

app_name = 'betting'

urlpatterns = [
    path('post_test/', views.test_post, name='post_test'),
    path('get_file/', views.get_file),
]
