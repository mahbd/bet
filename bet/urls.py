from django.contrib.staticfiles import views
from django.urls import re_path

from . import admin
from django.urls import path, include

admin.site.site_header = 'SuperBetting Admin Panel'
admin.site.index_title = 'Admin Site'

urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),
    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('bet/', include('betting.urls')),
    path('users/', include('users.urls')),
    # path('__debug__/', include(debug_toolbar.urls)),
    re_path(r'^static/(?P<path>.*)$', views.serve)
]
